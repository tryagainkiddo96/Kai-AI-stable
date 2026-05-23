#!/usr/bin/env python3
"""JARVIS HOLOGRAPHIC HUD WIDGET"""

import asyncio
import math
import os
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from kai_agent.assistant import KaiAssistant
except ImportError:
    KaiAssistant = None

import json as _json
import random as _random

_OFFLINE_MSGS = [
    "My primary neural core is taking a nap.",
    "Main processor on coffee break.",
    "Jarvis on a potato.",
    "Backup reserves engaged.",
]

def _load_config_key(key: str) -> str:
    cp = Path("kai_config.json")
    if cp.exists():
        try:
            with cp.open("r", encoding="utf-8") as f:
                return str(_json.load(f).get(key, "")).strip()
        except Exception:
            pass
    return ""

def _detect_provider_chain() -> list[tuple[str, str]]:
    cands = [
        ("groq", "llama-3.1-8b-instant", lambda: _load_config_key("groq_api_key") or os.environ.get("GROQ_API_KEY", "")),
        ("deepseek", "deepseek-chat", lambda: _load_config_key("deepseek_api_key") or os.environ.get("DEEPSEEK_API_KEY", "")),
        ("ollama", "llama3.2:3b", lambda: "local"),
    ]
    chain = [(p, m) for p, m, fn in cands if fn()]
    if not any(p == "ollama" for p, _ in chain):
        chain.append(("ollama", "llama3.2:3b"))
    return chain

class _OfflineAssistant:
    async def ask(self, msg):
        return "[Offline] " + _random.choice(_OFFLINE_MSGS)

# Colors
BG = "#050508"
PANEL_BG = "#0A0A14"
PANEL_BORDER = "#1A1A3A"
GOLD = "#FFB03A"
CYAN = "#4FC3F7"
GREEN = "#00E676"
RED = "#FF1744"
TEXT = "#C8D6E5"
TEXT_DIM = "#3A3A6A"
TEXT_BRIGHT = "#FFFFFF"
GRID = "#0D0D20"
GLOW = "#FFB03A"
USER_COL = "#4FC3F7"
KAI_COL = "#C8D6E5"
SYS_COL = "#FFB03A"

class HUDCanvas(tk.Canvas):
    def rounded_rect(self, x1, y1, x2, y2, r=6, **kw):
        pts = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1]
        self.create_polygon(pts, smooth=True, **kw)


class JarvisWidget:
    def __init__(self):
        self.workspace = Path(__file__).parent.parent
        self.result_queue = queue.Queue()
        self.drag_origin = None
        self.chat_busy = False
        self._stt = None
        self._tts = None
        self._startup_done = False
        self._boot_lines = []
        self._provider_chain = _detect_provider_chain()
        self._provider_idx = 0
        self._pulse = 0.0
        self._boot_scroll = 0
        self._messages = []
        self._fade = 0

        self.root = tk.Tk()
        self.root.title("K//AI")
        self.root.geometry("480x720+50+50")
        self.root.minsize(380, 600)
        self.root.configure(bg=BG)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.92)

        self.cv = HUDCanvas(self.root, bg=BG, highlightthickness=0)
        self.cv.pack(fill='both', expand=True)

        self._draw_grid()
        self._draw_frame()
        self._build_boot_screen()

        self.root.bind('<Button-1>', self._start_drag)
        self.root.bind('<B1-Motion>', self._drag)

        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._loop_thread.start()

        self.root.after(50, self._tick)
        self.root.after(100, self._poll)
        self.root.after(500, self._begin_boot)

    # --- Drawing helpers ---

    def _draw_grid(self):
        w = self.root.winfo_width() or 480
        h = self.root.winfo_height() or 720
        self.cv.delete('grid')
        step = 30
        for x in range(0, w, step):
            self.cv.create_line(x, 0, x, h, fill=GRID, width=1, tags='grid')
        for y in range(0, h, step):
            self.cv.create_line(0, y, w, y, fill=GRID, width=1, tags='grid')

    def _draw_frame(self):
        w = self.root.winfo_width() or 480
        h = self.root.winfo_height() or 720
        self.cv.delete('frame')

        # Corner brackets
        bw = 14
        self.cv.create_line(8, 8, 8, 8+bw, fill=GOLD, width=2, tags='frame')
        self.cv.create_line(8, 8, 8+bw, 8, fill=GOLD, width=2, tags='frame')
        self.cv.create_line(w-8, 8, w-8, 8+bw, fill=GOLD, width=2, tags='frame')
        self.cv.create_line(w-8, 8, w-8-bw, 8, fill=GOLD, width=2, tags='frame')
        self.cv.create_line(8, h-8, 8, h-8-bw, fill=GOLD, width=2, tags='frame')
        self.cv.create_line(8, h-8, 8+bw, h-8, fill=GOLD, width=2, tags='frame')
        self.cv.create_line(w-8, h-8, w-8, h-8-bw, fill=GOLD, width=2, tags='frame')
        self.cv.create_line(w-8, h-8, w-8-bw, h-8, fill=GOLD, width=2, tags='frame')

        # Header divider
        self.cv.create_line(20, 44, w-20, 44, fill="#1A1A3A", width=1, tags='frame')
        # Footer divider
        self.cv.create_line(20, h-28, w-20, h-28, fill="#1A1A3A", width=1, tags='frame')

    def _draw_arc_reactor(self, cx, cy, r, pulse):
        self.cv.delete('arc')
        for i in range(5):
            radius = r + i * 8 + pulse * 4
            alpha = max(20, 60 - i * 10)
            col = GOLD if i < 3 else CYAN
            self.cv.create_oval(cx-radius, cy-radius, cx+radius, cy+radius,
                               outline=col, width=1, tags='arc',
                               dash=(2, 4) if i > 2 else ())

        # Core glow
        for gr in range(4, 0, -1):
            gr_r = r * (gr / 5)
            self.cv.create_oval(cx-gr_r, cy-gr_r, cx+gr_r, cy+gr_r,
                               fill='', outline=GOLD, width=1, tags='arc',
                               stipple='gray25' if gr > 2 else '')
        self.cv.create_oval(cx-3, cy-3, cx+3, cy+3, fill=GOLD, outline='', tags='arc')

    def _write_text(self, x, y, text, color=TEXT, size=10, anchor='w', bold=False, tag=''):
        font = ('Consolas', size, 'bold' if bold else 'normal')
        self.cv.create_text(x, y, text=text, fill=color, font=font, anchor=anchor, tags=tag)

    # --- Boot screen ---

    def _build_boot_screen(self):
        self.cv.delete('boot')
        self.cv.delete('chat')
        self.cv.delete('input')
        self.cv.delete('chat_text')
        self.cv.delete('input_text')

    def _begin_boot(self):
        threading.Thread(target=self._boot_sequence, daemon=True).start()

    def _boot_sequence(self):
        steps = [
            (0, "> INITIALIZING KERNEL...", GREEN),
            (8, "  [OK] Neural core v3.12 loaded", TEXT_DIM),
            (15, "> SCANNING PROVIDER NETWORK...", GREEN),
        ]

        provider = self._provider_chain[0][0] if self._provider_chain else "offline"
        model = self._provider_chain[0][1] if self._provider_chain else "none"
        os.environ.setdefault("KAI_PROVIDER", provider)

        # Actually init the assistant
        for pct, line, color in steps:
            self.result_queue.put(('boot_line', (pct, line, color)))
            time.sleep(0.3)

        assistant = None
        if KaiAssistant is not None:
            try:
                assistant = KaiAssistant(model=model, workspace=self.workspace)
                self.result_queue.put(('boot_line', (22, f"  [OK] {provider.upper()} LINK ESTABLISHED", TEXT_DIM)))
            except Exception:
                assistant = _OfflineAssistant()
                self.result_queue.put(('boot_line', (22, f"  [WARN] {provider.upper()} FALLBACK MODE", SYS_COL)))
        else:
            assistant = _OfflineAssistant()
            self.result_queue.put(('boot_line', (22, "  [WARN] NO AI ENGINE FOUND", SYS_COL)))
        self._boot_assistant = assistant
        time.sleep(0.2)

        steps2 = [
            (30, "> AUTHENTICATING SECURE CHANNEL...", GREEN),
            (36, "  [OK] CONNECTION SECURE", TEXT_DIM),
            (42, "> LOADING AI PERSONA...", GREEN),
            (48, "  [OK] COGNITIVE MAP LOADED", TEXT_DIM),
            (55, "> ACTIVATING PERIPHERALS...", GREEN),
            (62, "  [OK] SCREEN AWARENESS ONLINE", TEXT_DIM),
            (68, "  [OK] CHESS ENGINE STANDBY", TEXT_DIM),
            (75, "  [OK] SPEECH SYNTHESIS READY", TEXT_DIM),
            (82, "> CALIBRATING HOLOGRAPHIC INTERFACE...", GREEN),
            (88, "  [OK] HUD CALIBRATED", TEXT_DIM),
            (94, "> FINALIZING...", GREEN),
            (100, "[ ALL SYSTEMS NOMINAL ]", GOLD),
        ]

        for pct, line, color in steps2:
            self.result_queue.put(('boot_line', (pct, line, color)))
            time.sleep(0.2 if "OK" in line else 0.3)

        # Screen awareness
        if hasattr(assistant, "screen_aware") and KaiAssistant is not None:
            try:
                sa = assistant.screen_aware
                sa.enabled = True
                sa.interval = 15.0
                sa.start()
            except Exception:
                pass

        time.sleep(0.5)
        self.result_queue.put(('boot_done', None))

    # --- Chat UI (built after boot) ---

    def _build_chat_ui(self):
        self.cv.delete('boot')
        w = self.root.winfo_width() or 480
        h = self.root.winfo_height() or 720

        # Chat area background
        self.cv.create_rectangle(16, 52, w-16, h-36, fill=PANEL_BG, outline=PANEL_BORDER, width=1, tags='chat')

        # Scrollable chat text
        self.chat_y = 65
        self.max_chat_y = h - 100

        # Input area
        inp_y = h - 32
        self.cv.create_rectangle(16, inp_y-24, w-60, inp_y, fill="#080810", outline=PANEL_BORDER, width=1, tags='input')
        self._write_text(22, inp_y-11, ">> ", color=GOLD, size=10, tag='input')

        # Send button
        self.cv.create_rectangle(w-56, inp_y-24, w-16, inp_y, fill="#1A1A2A", outline=CYAN, width=1, tags='input')
        self._write_text(w-36, inp_y-11, "SEND", color=CYAN, size=9, bold=True, anchor='c', tag='input')

        # Bind input
        self._input_buf = ""
        self.root.bind('<Key>', self._keypress)
        self.root.bind('<Return>', lambda e: self._send_msg())

        self._add_chat("KAI", "Interface online. Awaiting input.", KAI_COL)

    def _add_chat(self, sender, text, col):
        self._messages.append((sender, text, col))
        w = self.root.winfo_width() or 480
        self.cv.delete('chat_text')
        y = 65
        for s, t, c in self._messages[-20:]:
            prefix = f"[{s}] " if s != "KAI" else "> "
            display = prefix + t
            # Wrap long messages
            lines = []
            for para in display.split('\n'):
                while len(para) > 55:
                    lines.append(para[:55])
                    para = para[55:]
                lines.append(para)
            for line in lines:
                if y > self.root.winfo_height() - 100:
                    break
                self._write_text(24, y, line, color=c, size=9, tag='chat_text')
                y += 16
            y += 4
        self.chat_y = y

    def _keypress(self, evt):
        if not self._startup_done:
            return
        if evt.char and evt.char.isprintable():
            self._input_buf += evt.char
        elif evt.keysym == 'BackSpace':
            self._input_buf = self._input_buf[:-1]
        elif evt.keysym == 'Return':
            self._send_msg()
        self._update_input_display()

    def _update_input_display(self):
        self.cv.delete('input_text')
        w = self.root.winfo_width() or 480
        display = self._input_buf[-40:]
        self._write_text(38, (self.root.winfo_height() or 720)-43, display, color=TEXT_BRIGHT, size=10, tag='input_text')

    def _send_msg(self):
        if not self._startup_done or self.chat_busy or not self._input_buf.strip():
            return
        msg = self._input_buf.strip()
        self._input_buf = ""
        self._update_input_display()
        self._add_chat("YOU", msg, USER_COL)
        self.chat_busy = True
        threading.Thread(target=self._ask_assistant, args=(msg,), daemon=True).start()

    def _ask_assistant(self, message):
        if not self._provider_chain:
            reply = asyncio.run_coroutine_threadsafe(self.assistant.ask(message), self._loop)
            try:
                self.result_queue.put(('reply', reply.result(timeout=120)))
            except Exception as e:
                self.result_queue.put(('error', str(e)))
            self.chat_busy = False
            return
        start_idx = self._provider_idx
        for i in range(len(self._provider_chain)):
            idx = (start_idx + i) % len(self._provider_chain)
            if idx != self._provider_idx:
                p, m = self._provider_chain[idx]
                try:
                    self.assistant.client.set_provider(p, m)
                except Exception:
                    continue
                self._provider_idx = idx
            try:
                future = asyncio.run_coroutine_threadsafe(self.assistant.ask(message), self._loop)
                reply = future.result(timeout=120)
                self.result_queue.put(('reply', reply))
                self.chat_busy = False
                return
            except (asyncio.TimeoutError, Exception):
                continue
        self.result_queue.put(('error', 'All providers unavailable.'))
        self.chat_busy = False

    # --- Ticks & polls ---

    def _tick(self):
        self._pulse = (self._pulse + 0.05) % (math.pi * 2)
        cx = self.root.winfo_width() - 50
        cy = 24
        pulse_val = math.sin(self._pulse) * 3
        self._draw_arc_reactor(cx, cy, 12, pulse_val)
        self._draw_grid()
        self._draw_frame()
        self.root.after(50, self._tick)

    def _poll(self):
        try:
            while True:
                kind, data = self.result_queue.get_nowait()
                if kind == 'boot_line':
                    pct, line, color = data
                    w = self.root.winfo_width() or 480
                    h = self.root.winfo_height() or 720
                    self.cv.delete('boot')
                    self._boot_lines.append((line, color))
                    y = 80
                    for l, c in self._boot_lines[-15:]:
                        self._write_text(30, y, l, color=c, size=10, tag='boot')
                        y += 18
                    # Big percentage
                    self.cv.delete('pct')
                    self._write_text(w//2, h//2 + 40, f"{int(pct)}%", color=GOLD, size=36,
                                    bold=True, anchor='c', tag='pct')
                    # Progress arc
                    self.cv.delete('pct_arc')
                    r = 60
                    cx, cy2 = w//2, h//2 - 30
                    angle = (pct / 100.0) * 360
                    for deg in range(0, int(angle), 3):
                        rad = math.radians(deg - 90)
                        x = cx + r * math.cos(rad)
                        y2 = cy2 + r * math.sin(rad)
                        self.cv.create_oval(x-2, y2-2, x+2, y2+2, fill=GOLD, outline='', tags='pct_arc')
                    self.cv.create_text(cx, cy2, text="INIT", fill=TEXT_DIM, font=('Consolas', 8), anchor='c', tags='pct_arc')

                elif kind == 'boot_done':
                    self._startup_done = True
                    self.assistant = self._boot_assistant
                    self._build_chat_ui()

                elif kind == 'reply':
                    self._add_chat("KAI", data, KAI_COL)
                    if self._tts and self._tts.enabled:
                        self._tts.speak(data)

                elif kind == 'error':
                    self._add_chat("ERR", data, RED)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _start_drag(self, evt):
        self.drag_origin = evt.x_root, evt.y_root

    def _drag(self, evt):
        if not self.drag_origin:
            return
        dx = evt.x_root - self.drag_origin[0]
        dy = evt.y_root - self.drag_origin[1]
        self.root.geometry(f'+{int(self.root.winfo_x()+dx)}+{int(self.root.winfo_y()+dy)}')
        self.drag_origin = evt.x_root, evt.y_root

    def _on_close(self):
        self._loop.call_soon_threadsafe(self._loop.stop)
        self.root.destroy()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()


if __name__ == '__main__':
    JarvisWidget().run()
