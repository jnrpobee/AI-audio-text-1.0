"""
Shared base utilities for analysis agents.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import BadRequestError, OpenAI


from ..config import get_openai_client, get_settings
from ..utils import response_to_text


@dataclass
class AgentMessage:
    role: str
    content: str


class AgentBase:
    def __init__(
        self,
        system_prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        client: Optional[OpenAI] = None,
    ) -> None:
        settings = get_settings()
        self.client = client or get_openai_client()
        self.system_prompt = system_prompt
        self.model = model or settings.models.reasoning
        self.temperature = temperature if temperature is not None else settings.default_temperature

    def _run(
        self,
        user_content: str,
        *,
        extra_messages: Optional[List[AgentMessage]] = None,
    ) -> Any:
        message_payload: List[Dict[str, Any]] = []
        if self.system_prompt:
            message_payload.append(
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": self.system_prompt}],
                }
            )
        message_payload.append(
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_content}],
            }
        )

        if extra_messages:
            for msg in extra_messages:
                message_payload.append(
                    {"role": msg.role, "content": [{"type": "input_text", "text": msg.content}]}
                )

        request_kwargs: Dict[str, Any] = {
            "model": self.model,
            "input": message_payload,
        }
        if self.temperature is not None:
            request_kwargs["temperature"] = self.temperature

        try:
            return self.client.responses.create(**request_kwargs)
        except BadRequestError as exc:
            if self._is_temperature_unsupported(exc) and "temperature" in request_kwargs:
                request_kwargs.pop("temperature", None)
                return self.client.responses.create(**request_kwargs)
            raise

    @staticmethod
    def _is_temperature_unsupported(exc: BadRequestError) -> bool:
        message = (getattr(exc, "message", None) or str(exc) or "").lower()
        return "temperature" in message and ("unsupported parameter" in message or "not supported" in message)

    def _run_and_parse_text(
        self,
        user_content: str,
        *,
        extra_messages: Optional[List[AgentMessage]] = None,
    ) -> str:
        response = self._run(user_content, extra_messages=extra_messages)
        return response_to_text(response)
