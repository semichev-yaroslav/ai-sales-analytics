from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMInsightEngine:
    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_summary(self, payload: dict[str, Any]) -> str | None:
        prompt = (
            "Ты senior revenue analyst. Сформируй управленческие выводы по аналитике AI sales bot. "
            "Ответ: 1 абзац executive summary + 3 приоритетные рекомендации. "
            "Пиши по-русски, коротко и конкретно.\n\n"
            f"Данные: {json.dumps(payload, ensure_ascii=False)}"
        )

        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                temperature=0.2,
                max_output_tokens=500,
            )
            text = response.output_text.strip()
            return text or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM insight generation failed: %s", exc)
            return None
