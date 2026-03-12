from __future__ import annotations

from pathlib import Path

import httpx


class TelegramDelivery:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

    def send_summary(self, text: str) -> None:
        response = httpx.post(
            f"{self.base_url}/sendMessage",
            data={"chat_id": self.chat_id, "text": text},
            timeout=20,
        )
        response.raise_for_status()

    def send_chart(self, image_path: Path, caption: str | None = None) -> None:
        with image_path.open("rb") as file_handle:
            response = httpx.post(
                f"{self.base_url}/sendPhoto",
                data={"chat_id": self.chat_id, "caption": caption or image_path.name},
                files={"photo": file_handle},
                timeout=60,
            )
            response.raise_for_status()
