from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class TelegramNotifier:
    def __init__(self, token: str | None = None, chat_id: str | None = None) -> None:
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def send(self, text: str) -> None:
        if not self.is_configured():
            print("Telegram ayarlanmadigi icin mesaj terminale yazildi:")
            print(text)
            return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = json.dumps(
            {
                "chat_id": self.chat_id,
                "text": text,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.status >= 300:
                    raise RuntimeError(f"Telegram mesaj gonderimi basarisiz oldu: {response.status}")
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Telegram baglanti hatasi: {exc}") from exc
