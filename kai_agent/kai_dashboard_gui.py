#!/usr/bin/env python3
"""KAI DASHBOARD — PyQt6 Interactive GUI."""
from __future__ import annotations

import asyncio
import os
import sys
import time
import json
import re
import threading
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLineEdit, QLabel, QSplitter, QFrame,
    QScrollArea, QGroupBox, QGridLayout, QMessageBox, QTabWidget,
    QProgressBar, QStatusBar, QComboBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QColor, QTextCursor, QIcon, QKeySequence, QShortcut

# Colors
ACCENT = "#E8733A"
ACCENT_DIM = "#C45A28"
TEXT = "#F5E6D0"
TEXT_DIM = "#8B7355"
BG = "#1A1A1A"
BG_PANEL = "#242424"
BG_INPUT = "#2D2D2D"
BORDER = "#3A3A3A"
WARN = "#E8C547"
SUCCESS = "#7CB342"
ERROR = "#E53935"
INFO = "#42A5F5"
USER_BG = "#1E3A5F"
KAI_BG = "#3D2418"
SYS_BG = "#2D2D1E"

try:
    import sounddevice  # noqa: F401
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

SKILLS = [
    ("💬 Chat", "chat", "Ask questions, get answers, brainstorm"),
    ("🌐 Web", "web", "Browse, search, screenshot websites"),
    ("📁 Files", "files", "Read, write, search, organize files"),
    ("⌨️ Shell", "shell", "Run PowerShell/Bash commands"),
    ("🐉 Kali", "kali", "Security tools via WSL Kali"),
    ("🔓 Pentest", "pentest", "AI-assisted penetration testing"),
    ("🧠 Memory", "memory", "Store and recall information"),
    ("📊 Learn", "learn", "Learning stats and skill analysis"),
    ("🔧 Hardware", "hardware", "System info and device control"),
    ("🎭 Chimera", "chimera", "Stealth fingerprint mutation"),
    ("🤖 Legion", "legion", "Multi-bot worker management"),
    ("👁️ Vision", "vision", "OCR, screen capture, image analysis"),
    ("🔍 Research", "research", "Deep web research via Tavily"),
    ("📡 Autonomy", "autonomy", "Autonomous task execution"),
    ("🛫 Autopilot", "autopilot", "Clipboard & window monitoring"),
    ("🖥️ Screen", "screen", "Screenshot + OCR awareness"),
    ("🐝 Swarm", "swarm", "Multi-agent parallel execution"),
    ("🤖 Autocoder", "autocoder", "Autonomous coding loop"),
]


class StreamingWorker(QThread):
    token = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, assistant, text):
        super().__init__()
        self.assistant = assistant
        self.text = text
        self._loop = None

    def run(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def _stream():
                async for tk in self.assistant.ask_stream(self.text):
                    self.token.emit(tk)
            loop.run_until_complete(_stream())
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            loop.close()


class STTWorker(QThread):
    """Background thread for speech-to-text."""
    result = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def run(self):
        try:
            from kai_agent.kai_stt import KaiSTT
            stt = KaiSTT()
            if not stt.available:
                self.error.emit("STT backend not available. Install: pip install faster-whisper sounddevice")
                return
            text = stt.listen(duration=10.0, silence_timeout=2.0)
            if text:
                self.result.emit(text)
            else:
                self.error.emit("No speech detected")
        except Exception as exc:
            self.error.emit(f"STT error: {exc}")

    def stop(self):
        self._stop_event.set()


class SwarmRunner(QThread):
    """Background thread for running swarm tasks."""
    task_update = pyqtSignal(str)
    finished = pyqtSignal(str)

    def __init__(self, swarm, tasks):
        super().__init__()
        self.swarm = swarm
        self.tasks = tasks

    def run(self):
        try:
            run_id = self.swarm.create_swarm(self.tasks)
            self.swarm.execute_swarm(run_id)
            report = self.swarm.merge_results(run_id)
            self.finished.emit(report)
        except Exception as exc:
            self.task_update.emit(f"❌ Swarm error: {exc}")
            self.finished.emit(f"Swarm failed: {exc}")


class KaiDashboard(QMainWindow):
    def __init__(self, assistant, workspace):
        super().__init__()
        self.assistant = assistant
        self.workspace = Path(workspace)
        self.messages = []
        self.terminal_buffer = ""

        # Initialize autonomous modules
        from kai_agent.autopilot import Autopilot
        from kai_agent.screen_awareness import ScreenAwareness
        from kai_agent.swarm import SwarmController
        from kai_agent.autocoder import Autocoder

        self.autopilot = Autopilot(assistant, interval=2.0)
        self.autopilot.add_callback(lambda msg, data=None: self._on_autopilot_event(msg))

        # Use assistant's screen_aware for context injection + shared state
        self.screen_aware = assistant.screen_aware
        self.screen_aware.add_callback(lambda msg: self._on_screen_event(msg))

        self.swarm = SwarmController(assistant, assistant.legion, max_workers=4)
        self.swarm.add_callback(lambda msg: self._on_swarm_event(msg))

        self.autocoder = Autocoder(assistant, workspace)
        self.autocoder.add_callback(lambda msg: self._on_autocoder_event(msg))

        # Swarm task queue for batch creation
        self._swarm_tasks: list[dict] = []

        # Lazy-loaded media modules
        self._stt = None
        self._stt_recording = False

        self.init_ui()
        self.setWindowTitle(f"KAI Dashboard — {assistant.client.provider} / {assistant.client.model}")
        self.resize(1400, 900)
        self.show()
        self.chat_input.setFocus()

    def init_ui(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background: {BG}; }}
            QPushButton {{
                background: {BG_PANEL};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                text-align: left;
            }}
            QPushButton:hover {{ background: {BORDER}; }}
            QPushButton:pressed {{ background: {ACCENT_DIM}; }}
            QPushButton:checked {{
                background: {ACCENT};
                border-color: {ACCENT};
            }}
            QLineEdit {{
                background: {BG_INPUT};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }}
            QLineEdit:focus {{ border-color: {ACCENT}; }}
            QTextEdit {{
                background: {BG_PANEL};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 6px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
            }}
            QLabel {{
                color: {TEXT_DIM};
                font-size: 12px;
            }}
            QSplitter::handle {{ background: {BORDER}; }}
            QStatusBar {{
                background: {BG_PANEL};
                color: {TEXT_DIM};
                font-size: 11px;
                border-top: 1px solid {BORDER};
            }}
            QTabWidget::pane {{
                border: 1px solid {BORDER};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background: {BG_PANEL};
                color: {TEXT_DIM};
                padding: 6px 14px;
                border: 1px solid {BORDER};
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: {ACCENT};
                color: {TEXT};
            }}
            QGroupBox {{
                border: 1px solid {BORDER};
                border-radius: 6px;
                margin-top: 8px;
                font-weight: bold;
                color: {TEXT};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {ACCENT};
            }}
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(12, 8, 12, 4)
        self.logo = QLabel("    /\\_/\\  KAI DASHBOARD")
        self.logo.setStyleSheet(f"color: {ACCENT}; font-size: 16px; font-weight: bold;")
        top_bar.addWidget(self.logo)

        self.provider_label = QLabel(f"Provider: {self.assistant.client.provider}  |  Model: {self.assistant.client.model}")
        self.provider_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        top_bar.addWidget(self.provider_label, 1)

        self.status_indicator = QLabel("● Online")
        self.status_indicator.setStyleSheet(f"color: {SUCCESS}; font-size: 12px;")
        top_bar.addWidget(self.status_indicator)
        layout.addLayout(top_bar)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left sidebar — skills
        sidebar = QWidget()
        sidebar.setMaximumWidth(220)
        sidebar.setStyleSheet(f"background: {BG_PANEL}; border-right: 1px solid {BORDER};")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 8, 8, 8)
        sidebar_layout.setSpacing(6)

        skills_title = QLabel("SKILLS")
        skills_title.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 14px; padding: 4px;")
        sidebar_layout.addWidget(skills_title)

        self.skill_buttons = {}
        for icon, skill_id, tooltip in SKILLS:
            btn = QPushButton(f"  {icon}  {skill_id.capitalize()}")
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, s=skill_id: self.activate_skill(s))
            self.skill_buttons[skill_id] = btn
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # Quick actions
        qa = QLabel("QUICK ACTIONS")
        qa.setStyleSheet(f"color: {WARN}; font-weight: bold; font-size: 13px; padding: 4px;")
        sidebar_layout.addWidget(qa)

        self.btn_clear = QPushButton("🗑️ Clear Chat")
        self.btn_clear.clicked.connect(self.clear_chat)
        sidebar_layout.addWidget(self.btn_clear)

        self.btn_export = QPushButton("📥 Export Chat")
        self.btn_export.clicked.connect(self.export_chat)
        sidebar_layout.addWidget(self.btn_export)

        sidebar_layout.addSpacing(8)

        # Autonomous module toggles
        auto_label = QLabel("AUTONOMOUS")
        auto_label.setStyleSheet(f"color: {SUCCESS}; font-weight: bold; font-size: 13px; padding: 4px;")
        sidebar_layout.addWidget(auto_label)

        self.btn_autopilot = QPushButton("🛫 Autopilot [OFF]")
        self.btn_autopilot.setCheckable(True)
        self.btn_autopilot.clicked.connect(self.toggle_autopilot)
        sidebar_layout.addWidget(self.btn_autopilot)

        self.btn_screen = QPushButton("🖥️ Screen Aware [OFF]")
        self.btn_screen.setCheckable(True)
        self.btn_screen.clicked.connect(self.toggle_screen)
        sidebar_layout.addWidget(self.btn_screen)

        self.btn_autocoder_start = QPushButton("🤖 Autocoder [IDLE]")
        self.btn_autocoder_start.clicked.connect(self.toggle_autocoder)
        sidebar_layout.addWidget(self.btn_autocoder_start)

        sidebar_layout.addStretch()

        splitter.addWidget(sidebar)

        # Center — tabbed interface: Chat, Swarm, Autocoder
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Tab 1: Chat + Terminal
        chat_tab = QWidget()
        chat_tab_layout = QVBoxLayout(chat_tab)
        chat_tab_layout.setContentsMargins(0, 0, 0, 0)
        chat_tab_layout.setSpacing(0)

        center_split = QSplitter(Qt.Orientation.Vertical)

        # Chat area
        chat_widget = QWidget()
        chat_layout_v = QVBoxLayout(chat_widget)
        chat_layout_v.setContentsMargins(0, 0, 0, 0)
        chat_layout_v.setSpacing(4)

        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setStyleSheet(f"""
            QTextEdit {{
                background: {BG};
                color: {TEXT};
                border: none;
                border-bottom: 1px solid {BORDER};
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 13px;
                line-height: 1.5;
                padding: 8px;
            }}
        """)
        chat_layout_v.addWidget(self.chat_view)

        # Chat input
        input_row = QHBoxLayout()
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.setToolTip("Voice input — click then speak")
        self.mic_btn.setStyleSheet(f"""
            QPushButton {{ background: {BG_INPUT}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 18px; font-size: 16px; }}
            QPushButton:hover {{ background: {ACCENT}; color: white; }}
            QPushButton:disabled {{ opacity: 0.4; }}
        """)
        self.mic_btn.clicked.connect(self.start_voice_input)
        input_row.addWidget(self.mic_btn)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type a message or command...")
        self.chat_input.returnPressed.connect(self.send_message)
        input_row.addWidget(self.chat_input)

        self.send_btn = QPushButton("Send")
        self.send_btn.setStyleSheet(f"QPushButton {{ background: {ACCENT}; color: white; font-weight: bold; }} QPushButton:hover {{ background: {ACCENT_DIM}; }}")
        self.send_btn.clicked.connect(self.send_message)
        input_row.addWidget(self.send_btn)
        chat_layout_v.addLayout(input_row)

        center_split.addWidget(chat_widget)

        # Terminal area
        term_widget = QWidget()
        term_layout = QVBoxLayout(term_widget)
        term_layout.setContentsMargins(0, 0, 0, 0)
        term_layout.setSpacing(4)

        term_header = QHBoxLayout()
        term_title = QLabel("⌨️ Terminal / Command Output")
        term_title.setStyleSheet(f"color: {TEXT_DIM}; font-weight: bold; font-size: 12px; padding: 2px 8px;")
        term_header.addWidget(term_title)
        term_header.addStretch()

        self.term_clear = QPushButton("Clear")
        self.term_clear.clicked.connect(lambda: self.terminal_view.clear())
        self.term_clear.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        term_header.addWidget(self.term_clear)
        term_layout.addLayout(term_header)

        self.terminal_view = QTextEdit()
        self.terminal_view.setReadOnly(True)
        self.terminal_view.setStyleSheet(f"""
            QTextEdit {{
                background: #0D0D0D;
                color: #00FF00;
                border: none;
                border-top: 1px solid {BORDER};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
            }}
        """)
        term_layout.addWidget(self.terminal_view)

        # Terminal input
        term_input_row = QHBoxLayout()
        self.term_input = QLineEdit()
        self.term_input.setPlaceholderText("Enter shell command...")
        self.term_input.returnPressed.connect(self.run_shell_command)
        self.term_input.setStyleSheet(f"""
            QLineEdit {{
                background: #0D0D0D;
                color: #00FF00;
                border: none;
                border-top: 1px solid {BORDER};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 4px 8px;
            }}
        """)
        term_input_row.addWidget(self.term_input)
        self.term_exec = QPushButton("Run")
        self.term_exec.clicked.connect(self.run_shell_command)
        term_input_row.addWidget(self.term_exec)
        term_layout.addLayout(term_input_row)

        center_split.addWidget(term_widget)
        center_split.setSizes([600, 300])
        chat_tab_layout.addWidget(center_split)
        tabs.addTab(chat_tab, "💬 Chat")

        # Tab 2: Swarm Controller
        swarm_tab = QWidget()
        swarm_layout = QVBoxLayout(swarm_tab)
        swarm_layout.setContentsMargins(12, 12, 12, 12)
        swarm_layout.setSpacing(8)

        swarm_desc = QLabel("Multi-Agent Parallel Execution — Create tasks and run them simultaneously.")
        swarm_desc.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        swarm_layout.addWidget(swarm_desc)

        # Swarm input area
        swarm_input_group = QGroupBox("Add Swarm Tasks")
        swarm_input_layout = QVBoxLayout(swarm_input_group)

        self.swarm_task_input = QTextEdit()
        self.swarm_task_input.setPlaceholderText("Enter tasks (one per line, or one per paragraph):\n\nTask 1: Analyze this Python file for bugs\nTask 2: Write unit tests for the auth module\nTask 3: Review README for clarity")
        self.swarm_task_input.setMaximumHeight(120)
        swarm_input_layout.addWidget(self.swarm_task_input)

        swarm_btn_row = QHBoxLayout()
        self.swarm_add_btn = QPushButton("➕ Add Tasks")
        self.swarm_add_btn.clicked.connect(self.swarm_add_tasks)
        self.swarm_add_btn.setStyleSheet(f"background: {ACCENT}; color: white; font-weight: bold;")
        swarm_btn_row.addWidget(self.swarm_add_btn)

        self.swarm_clear_tasks = QPushButton("🗑️ Clear Queue")
        self.swarm_clear_tasks.clicked.connect(self.swarm_clear_queue)
        swarm_btn_row.addWidget(self.swarm_clear_tasks)

        self.swarm_run_btn = QPushButton("▶️ Run Swarm")
        self.swarm_run_btn.clicked.connect(self.swarm_run)
        self.swarm_run_btn.setStyleSheet(f"background: {SUCCESS}; color: white; font-weight: bold;")
        swarm_btn_row.addWidget(self.swarm_run_btn)

        self.swarm_workers = QComboBox()
        self.swarm_workers.addItems(["2", "3", "4", "5", "8"])
        self.swarm_workers.setCurrentText("4")
        self.swarm_workers.setStyleSheet(f"background: {BG_INPUT}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 4px; padding: 4px;")
        swarm_btn_row.addWidget(QLabel("Workers:"))
        swarm_btn_row.addWidget(self.swarm_workers)

        swarm_input_layout.addLayout(swarm_btn_row)
        swarm_layout.addWidget(swarm_input_group)

        # Swarm status
        self.swarm_status = QLabel("Queue: 0 tasks | Status: Idle")
        self.swarm_status.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: bold;")
        swarm_layout.addWidget(self.swarm_status)

        # Swarm results
        self.swarm_results = QTextEdit()
        self.swarm_results.setReadOnly(True)
        self.swarm_results.setPlaceholderText("Swarm results will appear here...")
        swarm_layout.addWidget(self.swarm_results)

        tabs.addTab(swarm_tab, "🐝 Swarm")

        # Tab 3: Autocoder
        coder_tab = QWidget()
        coder_layout = QVBoxLayout(coder_tab)
        coder_layout.setContentsMargins(12, 12, 12, 12)
        coder_layout.setSpacing(8)

        coder_desc = QLabel("Autonomous Coding Loop — Describe a task, Kai plans, codes, tests, and commits.")
        coder_desc.setStyleSheet(f"color: {TEXT_DIM}; font-size: 12px;")
        coder_layout.addWidget(coder_desc)

        # Task input
        coder_input_group = QGroupBox("Coding Task")
        coder_input_layout = QVBoxLayout(coder_input_group)

        self.coder_task_input = QTextEdit()
        self.coder_task_input.setPlaceholderText("Describe the coding task:\n\nExample: Create a Python REST API with FastAPI that has /health, /users, and /items endpoints with SQLite storage.")
        self.coder_task_input.setMaximumHeight(100)
        coder_input_layout.addWidget(self.coder_task_input)

        coder_btn_row = QHBoxLayout()
        self.coder_start_btn = QPushButton("🚀 Start")
        self.coder_start_btn.clicked.connect(self.autocoder_start)
        self.coder_start_btn.setStyleSheet(f"background: {ACCENT}; color: white; font-weight: bold;")
        coder_btn_row.addWidget(self.coder_start_btn)

        self.coder_stop_btn = QPushButton("⏹️ Stop")
        self.coder_stop_btn.clicked.connect(self.autocoder_stop)
        self.coder_stop_btn.setEnabled(False)
        coder_btn_row.addWidget(self.coder_stop_btn)

        self.coder_approve_btn = QPushButton("✅ Approve")
        self.coder_approve_btn.clicked.connect(self.autocoder_approve)
        self.coder_approve_btn.setEnabled(False)
        self.coder_approve_btn.setStyleSheet(f"background: {SUCCESS}; color: white; font-weight: bold;")
        coder_btn_row.addWidget(self.coder_approve_btn)

        self.coder_reject_btn = QPushButton("❌ Reject")
        self.coder_reject_btn.clicked.connect(self.autocoder_reject)
        self.coder_reject_btn.setEnabled(False)
        self.coder_reject_btn.setStyleSheet(f"background: {ERROR}; color: white; font-weight: bold;")
        coder_btn_row.addWidget(self.coder_reject_btn)

        self.coder_dryrun = QPushButton("🧪 Dry Run")
        self.coder_dryrun.setCheckable(True)
        self.coder_dryrun.setToolTip("Preview changes without writing files")
        self.coder_dryrun.clicked.connect(self.toggle_coder_dryrun)
        coder_btn_row.addWidget(self.coder_dryrun)

        coder_input_layout.addLayout(coder_btn_row)
        coder_layout.addWidget(coder_input_group)

        # Autocoder status
        self.coder_status = QLabel("Status: Idle")
        self.coder_status.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: bold;")
        coder_layout.addWidget(self.coder_status)

        # Autocoder progress
        self.coder_progress = QProgressBar()
        self.coder_progress.setVisible(False)
        coder_layout.addWidget(self.coder_progress)

        # Autocoder step log
        self.coder_log = QTextEdit()
        self.coder_log.setReadOnly(True)
        self.coder_log.setPlaceholderText("Coding steps will appear here...")
        coder_layout.addWidget(self.coder_log)

        tabs.addTab(coder_tab, "🤖 Autocoder")

        splitter.addWidget(tabs)
        splitter.setSizes([220, 1180])

        layout.addWidget(splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Welcome message
        self._append_system("Kai is ready! Select a skill or type a message.")

    def _append_message(self, role, content):
        self.chat_view.moveCursor(QTextCursor.MoveOperation.End)
        ts = datetime.now().strftime("%H:%M:%S")
        bg = USER_BG if role == "user" else (KAI_BG if role == "kai" else SYS_BG)
        color = INFO if role == "user" else (ACCENT if role == "kai" else WARN)
        label = "YOU" if role == "user" else ("KAI" if role == "kai" else "SYS")
        html = f'<div style="margin: 6px 0;"><span style="color: {color}; font-weight: bold;">{label}</span> <span style="color: {TEXT_DIM}; font-size: 11px;">{ts}</span><div style="background: {bg}; padding: 8px 12px; border-radius: 6px; margin-top: 4px; color: {TEXT};">{content}</div></div>'
        self.chat_view.insertHtml(html)
        self.chat_view.moveCursor(QTextCursor.MoveOperation.End)

    def _append_system(self, content):
        self._append_message("system", content)

    def _append_terminal(self, text, color=None):
        self.terminal_view.moveCursor(QTextCursor.MoveOperation.End)
        if color:
            self.terminal_view.insertHtml(f'<span style="color: {color};">{text}</span>\n')
        else:
            self.terminal_view.insertPlainText(text + "\n")
        self.terminal_view.moveCursor(QTextCursor.MoveOperation.End)

    def send_message(self):
        text = self.chat_input.text().strip()
        if not text:
            return
        self.chat_input.clear()
        self._append_message("user", text)

        if text.startswith("/"):
            self._handle_command(text)
            return

        # Show thinking indicator
        self._show_thinking(True)

        self._stream_worker = StreamingWorker(self.assistant, text)
        self._stream_worker.token.connect(self._on_token)
        self._stream_worker.finished.connect(self._on_stream_done)
        self._stream_worker.error.connect(self._on_error)
        self._stream_worker.start()

        # Prep message bubble for streaming
        self._message_html_prefix = self._make_message_html("kai", "")
        self.chat_view.moveCursor(QTextCursor.MoveOperation.End)
        self.chat_view.insertHtml(self._message_html_prefix)
        self._stream_buffer = ""

    def _make_message_html(self, role, content):
        ts = datetime.now().strftime("%H:%M:%S")
        bg = USER_BG if role == "user" else (KAI_BG if role == "kai" else SYS_BG)
        color = INFO if role == "user" else (ACCENT if role == "kai" else WARN)
        label = "YOU" if role == "user" else ("KAI" if role == "kai" else "SYS")
        safe = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        return f'<div style="margin: 6px 0;"><span style="color: {color}; font-weight: bold;">{label}</span> <span style="color: {TEXT_DIM}; font-size: 11px;">{ts}</span><div id="msg-bubble" style="background: {bg}; padding: 8px 12px; border-radius: 6px; margin-top: 4px; color: {TEXT}; white-space: pre-wrap;">{safe}</div></div>'

    def _show_thinking(self, show):
        if show:
            self.send_btn.setText("⏳")
            self.send_btn.setEnabled(False)
            self.status_bar.showMessage("Kai is thinking...")
        else:
            self.send_btn.setText("Send")
            self.send_btn.setEnabled(True)
            self.status_bar.showMessage("Ready")

    def _on_token(self, token):
        self._stream_buffer += token
        # Replace the last bubble content with typing cursor
        cursor = self.chat_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock, QTextCursor.MoveMode.KeepAnchor, 2)
        rendered = self._render_streaming_text(self._stream_buffer)
        bg = KAI_BG
        ts = datetime.now().strftime("%H:%M:%S")
        html = f'<div style="margin: 6px 0;"><span style="color: {ACCENT}; font-weight: bold;">KAI</span> <span style="color: {TEXT_DIM}; font-size: 11px;">{ts}</span><div style="background: {bg}; padding: 8px 12px; border-radius: 6px; margin-top: 4px; color: {TEXT}; white-space: pre-wrap;">{rendered}<span style="color: {ACCENT}; animation: blink 1s step-end infinite;">▌</span></div></div>'
        cursor.removeSelectedText()
        cursor.insertHtml(html)
        self.chat_view.moveCursor(QTextCursor.MoveOperation.End)

    def _render_streaming_text(self, text):
        """Basic markdown rendering for streaming text."""
        # Escape HTML
        safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Code blocks: ```lang\ncode\n``` → styled block
        safe = re.sub(
            r'```(\w*)\n(.*?)```',
            r'<div style="background: #0D0D0D; border: 1px solid #3A3A3A; border-radius: 4px; padding: 8px; margin: 4px 0; font-family: Consolas, monospace; font-size: 12px; overflow-x: auto;"><div style="color: #6B7280; font-size: 10px; margin-bottom: 4px;">\1</div><span style="color: #E5E7EB;">\2</span></div>',
            safe, flags=re.DOTALL
        )
        # Inline code: `code` → styled span
        safe = re.sub(r'`([^`]+)`', r'<code style="background: #3D3D3D; padding: 1px 4px; border-radius: 3px; font-family: Consolas, monospace; color: #F97316;">\1</code>', safe)
        # Bold: **text** → bold
        safe = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', safe)
        # Italic: *text* → italic
        safe = re.sub(r'\*(.+?)\*', r'<i>\1</i>', safe)
        # Line breaks
        safe = safe.replace("\n", "<br>")
        return safe

    def _on_stream_done(self):
        self._show_thinking(False)
        # Finalize: remove cursor, render full text
        cursor = self.chat_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock, QTextCursor.MoveMode.KeepAnchor, 2)
        rendered = self._render_streaming_text(self._stream_buffer)
        bg = KAI_BG
        ts = datetime.now().strftime("%H:%M:%S")
        html = f'<div style="margin: 6px 0;"><span style="color: {ACCENT}; font-weight: bold;">KAI</span> <span style="color: {TEXT_DIM}; font-size: 11px;">{ts}</span><div style="background: {bg}; padding: 8px 12px; border-radius: 6px; margin-top: 4px; color: {TEXT}; white-space: pre-wrap;">{rendered}</div></div>'
        cursor.removeSelectedText()
        cursor.insertHtml(html)
        self.chat_view.moveCursor(QTextCursor.MoveOperation.End)

    def _ask_assistant(self, text):
        return asyncio.run(self.assistant.ask(text))

    def _on_error(self, error):
        self._show_thinking(False)
        self._append_message("kai", f"Error: {error}")

    def _handle_command(self, cmd):
        parts = cmd[1:].strip().split(None, 1)
        action = parts[0].lower() if parts else ""
        arg = parts[1] if len(parts) > 1 else ""

        if action == "clear":
            self.chat_view.clear()
            self._append_system("Chat cleared.")
        elif action == "provider":
            if not arg:
                self._append_system(f"Current: {self.assistant.client.provider} | {self.assistant.client.model}")
            else:
                provider_parts = arg.split(None, 1)
                result = self.assistant.client.set_provider(provider_parts[0])
                self._append_system(f"Provider: {result}")
                self.provider_label.setText(f"Provider: {self.assistant.client.provider}  |  Model: {self.assistant.client.model}")
        elif action == "model":
            if arg:
                result = self.assistant.client.set_model(arg)
                self._append_system(f"Model: {result}")
                self.provider_label.setText(f"Provider: {self.assistant.client.provider}  |  Model: {self.assistant.client.model}")
        elif action == "memory":
            if arg:
                results = self.assistant.memory.search(arg)
                self._append_message("kai", f"Memory results for '{arg}':\n{results}")
        elif action == "skills":
            try:
                skills = self.assistant.skills_system.list_skills()
                self._append_message("kai", f"Skills:\n{skills}")
            except Exception as exc:
                self._append_message("kai", f"Skills error: {exc}")
        elif action == "mood":
            try:
                mood = self.assistant.emotions.get_summary()
                self._append_message("kai", f"Mood:\n{mood}")
            except Exception as exc:
                self._append_message("kai", f"Mood error: {exc}")
        elif action == "autopilot":
            if arg == "on":
                self.autopilot.start()
                self.btn_autopilot.setText("🛫 Autopilot [ON]")
                self.btn_autopilot.setChecked(True)
                self._append_system("🛫 Autopilot started.")
            elif arg == "off":
                self.autopilot.stop()
                self.btn_autopilot.setText("🛫 Autopilot [OFF]")
                self.btn_autopilot.setChecked(False)
                self._append_system("🛫 Autopilot stopped.")
            else:
                status = self.autopilot.status()
                self._append_system(f"Autopilot: {'ON' if status['enabled'] else 'OFF'} | Interval: {status['interval']}s")
        elif action == "screen":
            if arg == "on":
                self.screen_aware.start()
                self.btn_screen.setText("🖥️ Screen Aware [ON]")
                self.btn_screen.setChecked(True)
                self._append_system("🖥️ Screen awareness started.")
            elif arg == "off":
                self.screen_aware.stop()
                self.btn_screen.setText("🖥️ Screen Aware [OFF]")
                self.btn_screen.setChecked(False)
                self._append_system("🖥️ Screen awareness stopped.")
            else:
                status = self.screen_aware.status()
                self._append_system(f"Screen: {'ON' if status['enabled'] else 'OFF'} | Captures: {status['captures_count']}")
        elif action == "swarm":
            if arg == "status":
                s = self.swarm.status()
                self._append_system(f"Swarm: running={s['running']} | total={s['total_tasks']} | done={s['done_tasks']} | errors={s['error_tasks']}")
            elif arg.startswith("run "):
                self._swarm_tasks.append({"description": arg[4:80], "prompt": arg[4:]})
                self.swarm_status.setText(f"Queue: {len(self._swarm_tasks)} tasks | Status: Idle")
                self._append_system(f"Task added. Queue: {len(self._swarm_tasks)}")
            else:
                self._append_system("/swarm status — Show swarm status\n/swarm run <task> — Add a single task\nUse Swarm tab for batch execution.")
        elif action == "autocoder":
            if arg == "stop":
                self.autocoder_stop()
                self._append_system("🤖 Autocoder stopped.")
            elif arg == "status":
                s = self.autocoder.get_status()
                pending = s.get("pending_changes", [])
                status_text = f"Autocoder: {s['status_msg']} | Running: {s['running']} | Steps: {s['total_steps']}"
                if pending:
                    status_text += f" | {len(pending)} pending change(s)"
                self._append_system(status_text)
            elif arg == "approve":
                self.autocoder_approve()
            elif arg == "reject":
                self.autocoder_reject()
            elif arg == "dryrun":
                self.autocoder.dry_run = not self.autocoder.dry_run
                self._append_system(f"🧪 Dry-run: {'ON' if self.autocoder.dry_run else 'OFF'}")
            elif arg:
                self.coder_task_input.setPlainText(arg)
                self._append_system("Task set. Click 🚀 Start in Autocoder tab or run /autocoder start.")
            else:
                self._append_system("/autocoder <task> — Set a coding task\n/autocoder status — Check status\n/autocoder stop — Stop running task\n/autocoder approve|reject — Approve/reject pending changes\n/autocoder dryrun — Toggle dry-run mode")
        elif action == "look":
            if not self.assistant.vision.is_available:
                self._append_system("⚠️ Vision unavailable. Install: pip install opencv-python")
                return
            if arg == "motion":
                result = self.assistant.vision.detect_motion()
                self._append_system(f"Motion: {'YES' if result['motion'] else 'no'} (level: {result['level']:.4f})")
            elif arg == "presence":
                result = self.assistant.vision.detect_presence()
                self._append_system(f"Faces detected: {result['faces']}")
            elif arg == "save":
                path = self.assistant.vision.save_frame()
                self._append_system(f"Frame saved: {path}" if path else "Failed to capture frame")
            else:
                result = self.assistant.vision.analyze_scene()
                self._append_system(f"Scene: {result.get('summary', 'No data')}\nEvents: {', '.join(result.get('events', []))}")
        elif action == "listen":
            self.start_voice_input()
        elif action == "help":
            help_text = (
                "Commands:\n"
                "/clear — Clear chat\n"
                "/provider <name> — Switch AI provider\n"
                "/model <name> — Switch model\n"
                "/memory <query> — Search memory\n"
                "/skills — List available skills\n"
                "/mood — Show Kai's mood\n"
                "/autopilot on|off|status — Toggle clipboard monitoring\n"
                "/screen on|off|status — Toggle screen awareness\n"
                "/swarm status|run <task> — Swarm control\n"
                "/autocoder <task>|status|stop — Autonomous coding\n"
                "/look [motion|presence|save] — Vision commands\n"
                "/listen — Voice input via microphone\n"
            )
            self._append_message("kai", help_text)
        else:
            self._append_system(f"Unknown command: /{action}. Type /help for commands.")

    def run_shell_command(self):
        cmd = self.term_input.text().strip()
        if not cmd:
            return
        self.term_input.clear()
        self._append_terminal(f"$ {cmd}", color="#00FFFF")
        self.status_bar.showMessage(f"Running: {cmd}")

        try:
            result = self.assistant.tools.run_shell(cmd)
            data = json.loads(result)
            stdout = data.get("stdout", "")
            stderr = data.get("stderr", "")
            rc = data.get("returncode", -1)
            if stdout:
                self._append_terminal(stdout, color="#00FF00")
            if stderr:
                self._append_terminal(stderr, color=ERROR)
            self._append_terminal(f"[exit {rc}]", color=WARN)
        except Exception as exc:
            self._append_terminal(f"Error: {exc}", color=ERROR)
        self.status_bar.showMessage("Ready")

    def activate_skill(self, skill_id):
        for btn in self.skill_buttons.values():
            btn.setChecked(False)
        self.skill_buttons[skill_id].setChecked(True)

        prompts = {
            "chat": "What can I help you with?",
            "web": "What would you like me to browse or search?",
            "files": "What file operations do you need?",
            "shell": "Ready to run shell commands.",
            "kali": "Kali Linux tools ready. What target?",
            "pentest": "Enter pentest mode: /pentest on",
            "memory": "What should I search in memory?",
            "learn": "Checking learning stats...",
            "hardware": "Gathering hardware info...",
            "chimera": "Current fingerprint status:",
            "legion": "Legion worker army status:",
            "vision": "Ready for screen capture/OCR.",
            "research": "What topic should I research?",
            "autonomy": "Autonomy system ready.",
            "autopilot": "Clipboard & window monitoring — toggle with /autopilot on/off",
            "screen": "Screenshot + OCR awareness — toggle with /screen on/off",
            "swarm": "Multi-agent parallel execution — use the Swarm tab",
            "autocoder": "Autonomous coding loop — use the Autocoder tab",
        }
        self._append_system(f"[Skill: {skill_id}] {prompts.get(skill_id, '')}")
        self.chat_input.setFocus()

    def clear_chat(self):
        self.chat_view.clear()
        self.messages.clear()
        self._append_system("Chat history cleared.")

    def export_chat(self):
        path = self.workspace / f"kai_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(self.messages, indent=2), encoding="utf-8")
        self._append_system(f"Chat exported to: {path}")

    # === Autonomous Module Toggles ===

    def toggle_autopilot(self):
        if self.autopilot.enabled:
            self.autopilot.stop()
            self.btn_autopilot.setText("🛫 Autopilot [OFF]")
            self.btn_autopilot.setChecked(False)
            self._append_terminal("🛫 Autopilot stopped.", color=WARN)
        else:
            self.autopilot.start()
            self.btn_autopilot.setText("🛫 Autopilot [ON]")
            self.btn_autopilot.setChecked(True)
            self._append_terminal("🛫 Autopilot started — monitoring clipboard & windows.", color=SUCCESS)

    def toggle_screen(self):
        if self.screen_aware.enabled:
            self.screen_aware.stop()
            self.btn_screen.setText("🖥️ Screen Aware [OFF]")
            self.btn_screen.setChecked(False)
            self._append_terminal("🖥️ Screen awareness stopped.", color=WARN)
        else:
            self.screen_aware.start()
            self.btn_screen.setText("🖥️ Screen Aware [ON]")
            self.btn_screen.setChecked(True)
            self._append_terminal("🖥️ Screen awareness started — capturing every 10s.", color=SUCCESS)

    def toggle_autocoder(self):
        if self.autocoder.running:
            self.autocoder_stop()
        else:
            task = self.coder_task_input.toPlainText().strip()
            if not task:
                self._append_system("⚠️ Enter a coding task first in the Autocoder tab.")
                return
            self.autocoder_start()

    # === Autocoder ===

    def autocoder_start(self):
        task = self.coder_task_input.toPlainText().strip()
        if not task:
            self._append_system("⚠️ Enter a coding task description first.")
            return
        self.coder_start_btn.setEnabled(False)
        self.coder_stop_btn.setEnabled(True)
        self.coder_progress.setVisible(True)
        self.coder_progress.setRange(0, 0)  # Busy indicator
        self.coder_log.clear()
        self._append_terminal(f"🤖 Autocoder started: {task[:100]}...", color=ACCENT)
        self.autocoder.start_task(task)
        self._poll_autocoder_status()

    def autocoder_stop(self):
        self.autocoder.stop()
        self.coder_start_btn.setEnabled(True)
        self.coder_stop_btn.setEnabled(False)
        self.coder_approve_btn.setEnabled(False)
        self.coder_reject_btn.setEnabled(False)
        self.coder_progress.setRange(0, 100)
        self.coder_progress.setValue(100)
        self.coder_progress.setVisible(False)
        self._append_terminal("⏹️ Autocoder stopped.", color=WARN)

    def autocoder_approve(self):
        if self.autocoder.approve_changes():
            self.coder_approve_btn.setEnabled(False)
            self.coder_reject_btn.setEnabled(False)
            self._append_terminal("✅ Changes approved. Applying...", color=SUCCESS)

    def autocoder_reject(self):
        if self.autocoder.reject_changes():
            self.coder_approve_btn.setEnabled(False)
            self.coder_reject_btn.setEnabled(False)
            self._append_terminal("❌ Changes rejected.", color=ERROR)

    def toggle_coder_dryrun(self):
        self.autocoder.dry_run = self.coder_dryrun.isChecked()
        state = "ON" if self.coder_dryrun.isChecked() else "OFF"
        self._append_terminal(f"🧪 Autocoder dry-run: {state}", color=INFO)

    def _poll_autocoder_status(self):
        QTimer.singleShot(1000, self._update_autocoder_ui)

    def _update_autocoder_ui(self):
        status = self.autocoder.get_status()
        pending = status.get("pending_changes", [])
        awaiting = status.get("status_msg") == "awaiting_approval" and pending

        status_text = f"Status: {status['status_msg']} | Task: {status['current_task'][:60]}"
        if pending:
            status_text += f" | {len(pending)} pending change(s)"
        self.coder_status.setText(status_text)

        # Enable approve/reject when awaiting approval
        if awaiting:
            self.coder_approve_btn.setEnabled(True)
            self.coder_reject_btn.setEnabled(True)

        self.coder_log.clear()
        for step in status.get("steps", []):
            self.coder_log.append(f"[{step['step']}] {step['message']}")
        self.coder_log.moveCursor(QTextCursor.MoveOperation.End)
        if status["running"]:
            self._poll_autocoder_status()
        else:
            self.coder_start_btn.setEnabled(True)
            self.coder_stop_btn.setEnabled(False)
            self.coder_approve_btn.setEnabled(False)
            self.coder_reject_btn.setEnabled(False)
            self.coder_progress.setRange(0, 100)
            self.coder_progress.setValue(100)
            self.coder_progress.setVisible(False)

    # === Swarm ===

    def swarm_add_tasks(self):
        text = self.swarm_task_input.toPlainText().strip()
        if not text:
            self._append_system("⚠️ Enter tasks in the Swarm input.")
            return
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines:
            clean = line.lstrip("0123456789.-) ")
            if clean:
                self._swarm_tasks.append({"description": clean[:80], "prompt": clean})
        self.swarm_task_input.clear()
        self.swarm_status.setText(f"Queue: {len(self._swarm_tasks)} tasks | Status: Idle")
        self._append_terminal(f"🐝 Added {len(lines)} tasks to swarm queue.", color=SUCCESS)

    def swarm_clear_queue(self):
        self._swarm_tasks.clear()
        self.swarm_status.setText("Queue: 0 tasks | Status: Idle")
        self.swarm_results.clear()
        self._append_terminal("🗑️ Swarm queue cleared.", color=WARN)

    def swarm_run(self):
        if not self._swarm_tasks:
            self._append_system("⚠️ No tasks in queue. Add tasks first.")
            return
        workers = int(self.swarm_workers.currentText())
        self.swarm.max_workers = workers
        self.swarm_status.setText(f"Queue: {len(self._swarm_tasks)} tasks | Status: Running...")
        self.swarm_run_btn.setEnabled(False)
        self._append_terminal(f"🐝 Starting swarm with {workers} workers...", color=ACCENT)

        self._swarm_thread = SwarmRunner(self.swarm, self._swarm_tasks)
        self._swarm_thread.task_update.connect(self._on_swarm_task_update)
        self._swarm_thread.finished.connect(self._on_swarm_finished)
        self._swarm_thread.start()

    def _on_swarm_task_update(self, msg):
        self.swarm_results.append(msg)
        self.swarm_results.moveCursor(QTextCursor.MoveOperation.End)

    def _on_swarm_finished(self, report):
        self.swarm_run_btn.setEnabled(True)
        self.swarm_status.setText(f"Queue: {len(self._swarm_tasks)} tasks | Status: Complete")
        self.swarm_results.append("\n" + "="*60 + "\n")
        self.swarm_results.append(report)
        self.swarm_results.moveCursor(QTextCursor.MoveOperation.End)
        self._swarm_tasks.clear()
        self._append_terminal("✅ Swarm run complete.", color=SUCCESS)

    # === Event Callbacks ===

    def _on_autopilot_event(self, message):
        self._append_terminal(f"[Autopilot] {message}", color=INFO)
        # Inject as proactive Kai message in chat
        self._append_message("kai", message)

    def _on_screen_event(self, message):
        self._append_terminal(f"[Screen] {message}", color=WARN)

    def _on_swarm_event(self, message):
        self._append_terminal(f"[Swarm] {message}", color=ACCENT)

    def _on_autocoder_event(self, message):
        self._append_terminal(f"[Autocoder] {message}", color=SUCCESS)

    # === Voice Input ===

    def start_voice_input(self):
        if self._stt_recording:
            self._append_system("⚠️ Already recording. Please wait...")
            return
        if not HAS_AUDIO:
            self._append_system("⚠️ Audio capture not available. Install: pip install sounddevice numpy")
            return
        self._stt_recording = True
        self.mic_btn.setText("🔴")
        self.mic_btn.setStyleSheet(f"""
            QPushButton {{ background: #E53935; color: white; border: 1px solid #E53935; border-radius: 18px; font-size: 16px; }}
        """)
        self.status_bar.showMessage("🎤 Listening... Speak now")

        self._stt_worker = STTWorker()
        self._stt_worker.result.connect(self._on_stt_result)
        self._stt_worker.error.connect(self._on_stt_error)
        self._stt_worker.start()

    def _on_stt_result(self, text):
        self._stt_recording = False
        self.mic_btn.setText("🎤")
        self.mic_btn.setStyleSheet(f"""
            QPushButton {{ background: {BG_INPUT}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 18px; font-size: 16px; }}
            QPushButton:hover {{ background: {ACCENT}; color: white; }}
        """)
        self.status_bar.showMessage("Ready")
        self.chat_input.setText(text)
        self._append_terminal(f"🎤 Transcribed: {text}", color=SUCCESS)
        # Auto-send after a brief delay so user can review
        QTimer.singleShot(500, lambda: self._send_if_text())

    def _send_if_text(self):
        text = self.chat_input.text().strip()
        if text:
            self.send_message()

    def _on_stt_error(self, error):
        self._stt_recording = False
        self.mic_btn.setText("🎤")
        self.mic_btn.setStyleSheet(f"""
            QPushButton {{ background: {BG_INPUT}; color: {TEXT}; border: 1px solid {BORDER}; border-radius: 18px; font-size: 16px; }}
            QPushButton:hover {{ background: {ACCENT}; color: white; }}
        """)
        self.status_bar.showMessage("Ready")
        self._append_terminal(f"🎤 {error}", color=ERROR)


def main():
    from kai_agent.assistant import KaiAssistant
    workspace = Path(".").resolve()
    model = os.environ.get("KAI_MODEL", "llama3.2:3b")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    assistant = KaiAssistant(model=model, workspace=workspace)
    dashboard = KaiDashboard(assistant, workspace)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
