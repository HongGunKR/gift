"""FastAPI 서버: Swagger 기반 API 문서 제공."""

from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agents import MultiAgentResult, run_multi_agent_analysis
from app.services import data_fetcher


def _frame_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    return df.reset_index().rename(columns={"index": "date"}).to_dict(orient="records")


class NewsItemModel(BaseModel):
    title: str = ""
    snippet: str = ""
    link: Optional[str] = None


class MultiAgentResponseModel(BaseModel):
    stock_name: str
    ticker: Optional[str] = None
    ratios: Dict[str, float] = Field(default_factory=dict)
    fundamentals: str
    news_summary: str
    risk_analysis: str
    final_recommendation: str
    news_items: List[NewsItemModel] = Field(default_factory=list)


class MultiAgentRequestModel(BaseModel):
    stock_name: str = Field(..., description="분석할 종목명 (예: 삼성전자)")
    ticker: Optional[str] = Field(None, description="종목 코드 (선택)")


class MarketOverviewModel(BaseModel):
    indices: List[Dict[str, Any]]
    sectors: List[Dict[str, Any]]
    globals: List[Dict[str, Any]]


app = FastAPI(
    title="모두의 선물 API",
    description="멀티 에이전트 기반 AI 주식 분석 서비스의 Programmatic API",
    version="1.1.0",
    contact={
        "name": "모두의 선물 팀",
        "url": "https://github.com/HongGunKR/gift.git",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", summary="상태 점검")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/dashboard/overview",
    response_model=MarketOverviewModel,
    summary="시장 대시보드 데이터 조회",
)
def get_dashboard_overview() -> MarketOverviewModel:
    try:
        indices_df = data_fetcher.get_market_indices()
        sectors_df = data_fetcher.get_sector_performance()
        global_snapshot = data_fetcher.get_global_market_snapshot()

        indices = _frame_to_records(indices_df)
        sectors = (
            sectors_df.reset_index(drop=True).to_dict(orient="records")
            if sectors_df is not None and not sectors_df.empty
            else []
        )

        return MarketOverviewModel(
            indices=indices, sectors=sectors, globals=global_snapshot
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/analysis/multi-agent",
    response_model=MultiAgentResponseModel,
    summary="멀티 에이전트 종목 분석 실행",
)
def analyze_with_multi_agent(
    payload: MultiAgentRequestModel,
) -> MultiAgentResponseModel:
    try:
        result: MultiAgentResult = run_multi_agent_analysis(
            stock_name=payload.stock_name, ticker=payload.ticker
        )
        return MultiAgentResponseModel(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/market/top100",
    summary="시가총액 Top 100 데이터 조회",
)
def get_top_100() -> List[Dict[str, Any]]:
    try:
        top_df = data_fetcher.get_top_100_market_cap_stocks()
        return top_df.reset_index().rename(columns={"index": "rank"}).to_dict(
            orient="records"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.web.api:app", host="0.0.0.0", port=8502, reload=True)
