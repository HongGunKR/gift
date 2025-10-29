from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def test_multi_agent_returns_fallback_when_llm_unavailable(monkeypatch):
    from app.agents import multi_agent
    from app.services import data_fetcher

    monkeypatch.setattr(
        data_fetcher, "get_stock_name_ticker_map", lambda: {"샘플": "000000"}
    )
    monkeypatch.setattr(data_fetcher, "get_financial_ratios", lambda ticker: {})
    monkeypatch.setattr(data_fetcher, "search_news", lambda _: [])

    # invoke_prompt_safely가 fallback 메시지를 그대로 반환하도록 변경
    monkeypatch.setattr(
        multi_agent,
        "invoke_prompt_safely",
        lambda prompt, variables, fallback_message, log_context, **kwargs: fallback_message,
    )

    result = multi_agent.run_multi_agent_analysis("샘플")

    assert result["fundamentals"] == "펀더멘털 분석을 준비하지 못했습니다."
    assert result["news_summary"] == "뉴스 요약을 제공하지 못했습니다."
    assert result["risk_analysis"] == "리스크 보고서를 준비하지 못했습니다."
    assert result["final_recommendation"] == "최종 추천을 생성하지 못했습니다."
