"""Notifier — multi-backend phone/desktop/LAN notification system.

Supports:
  • ntfy.sh  — zero-config push to phone app (recommended)
  • Telegram — requires bot token + chat ID (see NOTE at bottom)
  • Windows toast — local desktop bubble
  • LAN UDP broadcast — to other Kai instances on network

NOTE: Telegram bot setup requires talking to @BotFather on Telegram.
Kai cannot do this interactively. If you want Telegram support:
  1. Open Telegram, search @BotFather, send /newbot
  2. Follow prompts, get a token like "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
  3. Send a message to your bot, then visit:
     https://api.telegram.org/bot<TOKEN>/getUpdates
  4. Copy the "chat":{"id":...} number from the response
  5. Add to kai_config.json as "telegram_token" and "telegram_chat_id"
"""
from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import threading
import time
import urllib.request
from typing import Optional


class Notifier:
    """Sends messages to phone, desktop, and LAN devices."""

    def __init__(self, db, config: dict = None):
        self.db = db
        config = config or {}
        self.ntfy_topic = config.get("ntfy_topic", "kai-alerts")
        self.telegram_token = config.get("telegram_token", "")
        self.telegram_chat_id = config.get("telegram_chat_id", "")
        self._last_toast = 0

    def send(self, message: str, priority: str = "normal", title: str = "Kai") -> dict:
        """Send message to all configured backends. Returns per-channel results."""
        results = {"channels": [], "errors": []}

        if self.telegram_token:
            ok = self._send_telegram(message)
            results["channels"].append("telegram")
            if ok:
                self.db.log_notification("telegram", message, success=True)
            else:
                results["errors"].append("telegram failed")
                self.db.log_notification("telegram", message, success=False)

        # ntfy is always available
        ok = self._send_ntfy(message, priority, title)
        results["channels"].append("ntfy")
        if ok:
            self.db.log_notification("ntfy", message, success=True)
        else:
            results["errors"].append("ntfy failed")
            self.db.log_notification("ntfy", message, success=False)

        # Local toast (throttled to once per 30s, Windows 10+ only)
        now = time.time()
        if now - self._last_toast > 30 and platform.system() == "Windows" and int(platform.version().split(".")[0]) >= 10:
            self._send_toast(message, title)
            self._last_toast = now

        # LAN broadcast
        self._send_lan(message)

        return results

    def _send_ntfy(self, message: str, priority: str = "normal", title: str = "Kai") -> bool:
        try:
            data = message.encode("utf-8")
            headers = {"Content-Type": "text/plain"}
            if priority == "urgent":
                headers["Priority"] = "5"
                headers["Tags"] = "warning"
            elif priority == "high":
                headers["Priority"] = "4"
            if title:
                headers["Title"] = title
            req = urllib.request.Request(
                f"https://ntfy.sh/{self.ntfy_topic}",
                data=data, headers=headers,
            )
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception:
            return False

    def _send_telegram(self, message: str) -> bool:
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = json.dumps({
                "chat_id": self.telegram_chat_id,
                "text": message[:2000],
                "parse_mode": "HTML",
            }).encode()
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=15)
            return True
        except Exception:
            return False

    def _send_toast(self, message: str, title: str = "Kai"):
        try:
            esc_title = title.replace("'", "''")
            esc_msg = message[:80].replace("'", "''")
            ps = f'''
$null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime]
$template = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($template)
$texts = $xml.GetElementsByTagName("text")
$texts.Item(0).AppendChild($xml.CreateTextNode('{esc_title}'))
$texts.Item(1).AppendChild($xml.CreateTextNode('{esc_msg}'))
$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Kai").Show($toast)
'''
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True, timeout=5,
            )
        except Exception:
            pass

    def _send_lan(self, message: str):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.settimeout(1)
            s.sendto(f"KAI_NOTIFY:{message}".encode(), ("255.255.255.255", 5555))
            s.close()
        except Exception:
            pass

    def notify_phone(self, message: str, priority: str = "normal") -> dict:
        """Convenience: send specifically to phone (ntfy + Telegram)."""
        return self.send(message, priority=priority, title="Kai Alert")


# Telegram setup instructions — Kai cannot do this interactively.
# If you want Telegram notifications, forward this to the user:
"""
Hey — you asked about Telegram bot. I can't create one because that
requires talking to @BotFather on Telegram (he asks you questions).

But I wrote all the code. Here's what you need to do:

1. Open Telegram → search @BotFather → send /newbot
2. Pick a name (e.g. "Kai Notifier") and username (e.g. "kai_notifier_bot")
3. BotFather gives you a token — put it in kai_config.json as "telegram_token"
4. Send any message to your new bot
5. Visit this URL in browser (replace TOKEN):
   https://api.telegram.org/bot<TOKEN>/getUpdates
6. Copy the chat.id number from the response
7. Put it in kai_config.json as "telegram_chat_id"

Then Kai will use Telegram as the primary notification channel.
Until then, ntfy.sh works out of the box — just install the ntfy app
on your phone and subscribe to the topic "{ntfy_topic}".
"""
