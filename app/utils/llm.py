"""공통 LLM 유틸리티."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any, Dict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import BasePromptTemplate
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class LLMUnavailableError(RuntimeError):
    """필수 환경 변수 누락 등으로 LLM을 사용할 수 없을 때 발생."""


def _ensure_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise LLMUnavailableError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")


@lru_cache(maxsize=1)
def get_shared_llm(model_name: str = "gpt-4o", temperature: float = 0.2) -> ChatOpenAI:
    """
    공용 ChatOpenAI 인스턴스를 반환합니다.
    실패 시 LLMUnavailableError를 발생시켜 호출 측에서 우아하게 처리하도록 합니다.
    """
    _ensure_api_key()
    try:
        return ChatOpenAI(model_name=model_name, temperature=temperature)
    except Exception as exc:  # pragma: no cover - 외부 SDK 내부 예외
        raise LLMUnavailableError(str(exc)) from exc


def invoke_prompt_safely(
    prompt: BasePromptTemplate,
    variables: Dict[str, Any],
    *,
    fallback_message: str,
    log_context: str,
    model_name: str = "gpt-4o",
    temperature: float = 0.2,
) -> str:
    """
    PromptTemplate → ChatOpenAI → StrOutputParser 체인을 실행합니다.
    실행 중 오류가 발생하면 로그를 남기고 fallback_message 를 반환합니다.
    """
    try:
        llm = get_shared_llm(model_name=model_name, temperature=temperature)
    except LLMUnavailableError as exc:
        logger.warning(
            "LLM unavailable; returning fallback",
            extra={"context": log_context, "error": str(exc)},
        )
        return fallback_message

    chain = prompt | llm | StrOutputParser()
    try:
        return chain.invoke(variables)
    except Exception as exc:
        logger.error(
            "LLM invocation failed; using fallback",
            extra={"context": log_context, "error": str(exc)},
            exc_info=exc,
        )
        return fallback_message


__all__ = ["LLMUnavailableError", "get_shared_llm", "invoke_prompt_safely"]
