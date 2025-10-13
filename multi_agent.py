"""멀티 에이전트 기반 종목 분석 유틸리티."""

from __future__ import annotations

from typing import Dict, List, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

import data_fetcher


class MultiAgentResult(TypedDict):
    stock_name: str
    ticker: Optional[str]
    ratios: Dict[str, float]
    fundamentals: str
    news_items: List[Dict[str, str]]
    news_summary: str
    risk_analysis: str
    final_recommendation: str


load_dotenv()

_SHARED_LLM: Optional[ChatOpenAI] = None

def _format_ratio_context(ratios: Dict[str, float]) -> str:
    if not ratios:
        return "재무 지표를 확보하지 못했습니다."
    segments = []
    for key in ("BPS", "PER", "PBR", "EPS", "DIV", "DPS"):
        if key in ratios and ratios[key] not in (None, "NaN"):
            try:
                value = float(ratios[key])
                if key in ("EPS", "DPS", "BPS"):
                    segments.append(f"{key}: {value:,.0f}")
                elif key == "DIV":
                    segments.append(f"{key}: {value:.2f}%")
                else:
                    segments.append(f"{key}: {value:.2f}")
            except (TypeError, ValueError):
                continue
    return ", ".join(segments) if segments else "재무 지표를 확보하지 못했습니다."


def _render_news_context(news_items: List[Dict[str, str]]) -> str:
    if not news_items:
        return "관련 뉴스를 찾지 못했습니다."
    lines = []
    for item in news_items:
        title = (item.get("title") or "제목 없음").strip()
        snippet = (item.get("snippet") or "").strip()
        link = item.get("link") or ""
        line = f"- {title}"
        if snippet:
            line += f"\n  요약: {snippet}"
        if link:
            line += f"\n  링크: {link}"
        lines.append(line)
    return "\n".join(lines)


def _get_shared_llm() -> ChatOpenAI:
    global _SHARED_LLM
    if _SHARED_LLM is None:
        # 온도는 낮게 유지하여 일관된 분석을 유도합니다.
        _SHARED_LLM = ChatOpenAI(model_name="gpt-4o", temperature=0.2)
    return _SHARED_LLM


def _fundamental_agent(stock_name: str, ratio_context: str) -> str:
    prompt = ChatPromptTemplate.from_template(
        """당신은 주식 애널리스트입니다. 아래 정보를 바탕으로 {stock_name}의 펀더멘털을 분석해주세요.

정보:
{ratio_context}

요구사항:
- 재무 지표를 간결하게 요약하고 의미를 해석하세요.
- 동종 업계 평균과 비교했을 때의 상대적 위치를 추정하세요 (가정 가능).
- 투자자가 주목해야 할 긍정/부정 포인트를 bullet로 정리하세요.
"""
    )
    chain = prompt | _get_shared_llm() | StrOutputParser()
    return chain.invoke({"stock_name": stock_name, "ratio_context": ratio_context})


def _news_agent(stock_name: str, news_items: List[Dict[str, str]]) -> str:
    prompt = ChatPromptTemplate.from_template(
        """당신은 금융 저널리스트입니다. 아래 기사 목록을 바탕으로 {stock_name}에 영향을 줄 수 있는 핵심 이슈를 정리하세요.

기사 목록:
{news_context}

요구사항:
- 3~5개의 핵심 이슈로 나누어 bullet 포맷으로 요약하세요.
- 각 이슈의 투자 영향 (긍정/부정/중립)을 표기하세요.
- 중복된 이슈는 통합하고, 신뢰도가 낮으면 주석으로 표시하세요.
"""
    )
    chain = prompt | _get_shared_llm() | StrOutputParser()
    return chain.invoke(
        {"stock_name": stock_name, "news_context": _render_news_context(news_items)}
    )


def _risk_agent(stock_name: str, fundamental: str, news_summary: str) -> str:
    prompt = ChatPromptTemplate.from_template(
        """당신은 리스크 매니저입니다. 다음 두 에이전트의 보고서를 검토하고 위험 요인을 식별하세요.

펀더멘털 분석:
{fundamental}

뉴스 분석:
{news_summary}

요구사항:
- 단기(1개월), 중기(3~6개월) 관점에서의 주요 리스크를 bullet로 정리하세요.
- 각 리스크의 발생 가능성을 High/Medium/Low 로 표기하세요.
- 리스크 완화 전략이나 모니터링 포인트를 함께 제안하세요.
"""
    )
    chain = prompt | _get_shared_llm() | StrOutputParser()
    return chain.invoke(
        {
            "stock_name": stock_name,
            "fundamental": fundamental,
            "news_summary": news_summary,
        }
    )


def _synthesis_agent(
    stock_name: str, fundamental: str, news_summary: str, risk_report: str
) -> str:
    prompt = ChatPromptTemplate.from_template(
        """당신은 최고투자책임자(CIO)입니다. 아래 팀원들의 보고서를 토대로 투자 메모를 작성하세요.

펀더멘털 분석:
{fundamental}

뉴스 분석:
{news_summary}

리스크 분석:
{risk_report}

요구사항:
- 서론, 본론, 결론 구조로 5단락 이내로 작성하세요.
- 본론에는 투자 기회와 리스크를 균형 있게 정리하세요.
- 마지막에는 `투자 판단` 섹션을 별도로 만들어 (매수/관망/매도) 중 하나를 추천하고 근거를 제시하세요.
"""
    )
    chain = prompt | _get_shared_llm() | StrOutputParser()
    return chain.invoke(
        {
            "stock_name": stock_name,
            "fundamental": fundamental,
            "news_summary": news_summary,
            "risk_report": risk_report,
        }
    )


def run_multi_agent_analysis(
    stock_name: str, ticker: Optional[str] = None
) -> MultiAgentResult:
    """
    펀더멘털/뉴스/리스크/최종 의견 에이전트가 순차 협업하여 리포트를 생성합니다.
    """
    if not ticker:
        ticker = data_fetcher.get_stock_name_ticker_map().get(stock_name)

    ratios: Dict[str, float] = {}
    if ticker:
        ratios = data_fetcher.get_financial_ratios(ticker)

    ratio_context = _format_ratio_context(ratios)
    fundamental_report = _fundamental_agent(stock_name, ratio_context)

    news_items = data_fetcher.search_news(stock_name)
    news_summary = _news_agent(stock_name, news_items)

    risk_report = _risk_agent(stock_name, fundamental_report, news_summary)

    final_recommendation = _synthesis_agent(
        stock_name, fundamental_report, news_summary, risk_report
    )

    return MultiAgentResult(
        stock_name=stock_name,
        ticker=ticker,
        ratios=ratios,
        fundamentals=fundamental_report,
        news_items=news_items,
        news_summary=news_summary,
        risk_analysis=risk_report,
        final_recommendation=final_recommendation,
    )
