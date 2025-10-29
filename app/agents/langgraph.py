"""LangGraph 기반 분석 에이전트."""

import logging
import os
import tempfile
from typing import List, Tuple, TypedDict

from dotenv import load_dotenv
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_openai import OpenAIEmbeddings
from langgraph.graph import END, StateGraph

from app.services import data_fetcher
from app.utils import LLMUnavailableError, get_shared_llm, invoke_prompt_safely

load_dotenv()

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    stock_name: str
    ticker: str
    ratios: dict
    initial_analysis: str
    classification: str  # "positive", "negative", "neutral"
    news: List[dict]
    final_report: str


VALID_CLASSIFICATIONS = {"positive", "negative", "neutral"}


def _format_ratio_value(value, decimals: int = 2, suffix: str = "") -> str:
    if value in (None, "", "NaN"):
        return "데이터 없음"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "데이터 없음"
    return f"{number:,.{decimals}f}{suffix}"


def _build_ratio_prompt(ratios: dict) -> str:
    if not ratios:
        return "재무 지표를 확보하지 못했습니다."
    per = _format_ratio_value(ratios.get("PER"))
    pbr = _format_ratio_value(ratios.get("PBR"))
    eps = _format_ratio_value(ratios.get("EPS"), 0, "원")
    div = _format_ratio_value(ratios.get("DIV"), 2, "%")
    return f"PER: {per}, PBR: {pbr}, EPS: {eps}, 배당수익률: {div}"


def _sanitize_classification(raw: str) -> str:
    candidate = (raw or "").strip().lower()
    if candidate not in VALID_CLASSIFICATIONS:
        return "neutral"
    return candidate


def _parse_initial_response(response: str) -> Tuple[str, str]:
    if not response:
        return "neutral", "LLM 응답을 해석하지 못했습니다."
    if "\n설명" in response:
        head, tail = response.split("\n설명", 1)
        classification = head.replace("분류:", "").strip()
        analysis = tail.replace(":", "", 1).strip()
    else:
        classification = "neutral"
        analysis = response.strip()
    sanitized = _sanitize_classification(classification)
    analysis_text = analysis or "LLM 분석 결과가 비어 있습니다."
    return sanitized, analysis_text


def _format_news_for_prompt(news_items: List[dict]) -> str:
    if not news_items:
        return "관련 뉴스를 찾지 못했습니다."
    lines = []
    for item in news_items:
        title = (item.get("title") or "제목 없음").strip()
        snippet = (item.get("snippet") or "").strip()
        link = item.get("link")
        entry = f"- {title}"
        if snippet:
            entry += f"\n  요약: {snippet}"
        if link:
            entry += f"\n  링크: {link}"
        lines.append(entry)
    return "\n".join(lines)


def initial_analysis_node(state: AgentState):
    """1차 분석 노드: 기업 개요와 재무 정보를 종합하여 초기 분석 및 판단을 수행합니다."""
    logger.info("initial_analysis node invoked", extra={"stock": state["stock_name"]})
    stock_name = state["stock_name"]
    ratios = state.get("ratios") or {}
    ratios_str = _build_ratio_prompt(ratios)

    prompt = PromptTemplate.from_template(
        """당신은 전문 애널리스트입니다. '{stock_name}' 기업의 개요와 다음 재무 지표를 분석해주세요.
        - 기업의 주요 사업, 주력 제품 설명
        - 재무 지표({ratios_str})를 해석하고, 이를 바탕으로 기업의 현재 상태를 'positive', 'negative', 'neutral' 중 하나로 분류해주세요.
        - 분류에 대한 이유를 간략하게 설명해주세요.
        
        출력 형식은 "분류: [positive/negative/neutral]\n설명: [분석 내용]" 이어야 합니다.
        """
    )
    response = invoke_prompt_safely(
        prompt,
        {"stock_name": stock_name, "ratios_str": ratios_str},
        fallback_message="분류: neutral\n설명: LLM 분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        log_context="initial_analysis_node",
    )

    classification, analysis_text = _parse_initial_response(response)
    return {"initial_analysis": analysis_text, "classification": classification}


def search_positive_news_node(state: AgentState):
    """호재성 뉴스를 검색하는 노드"""
    logger.info("search_positive_news node invoked", extra={"stock": state["stock_name"]})
    query = f"{state['stock_name']} 호재 전망 신제품"
    news = data_fetcher.search_news(query)
    if not news:
        news = data_fetcher.search_news(state["stock_name"])
    return {"news": news or []}


def search_negative_news_node(state: AgentState):
    """악재성 뉴스를 검색하는 노드"""
    logger.info("search_negative_news node invoked", extra={"stock": state["stock_name"]})
    query = f"{state['stock_name']} 악재 리스크 우려"
    news = data_fetcher.search_news(query)
    if not news:
        news = data_fetcher.search_news(state["stock_name"])
    return {"news": news or []}


def search_general_news_node(state: AgentState):
    """일반 뉴스를 검색하는 노드"""
    logger.info("search_general_news node invoked", extra={"stock": state["stock_name"]})
    news = data_fetcher.search_news(f"{state['stock_name']} 주가")
    return {"news": news or []}


def final_report_node(state: AgentState):
    """최종 보고서 생성 노드: 모든 정보를 종합하여 최종 리포트를 작성합니다."""
    logger.info("final_report node invoked", extra={"stock": state["stock_name"]})
    prompt = ChatPromptTemplate.from_template(
        """당신은 유능한 투자 분석가입니다. 다음 정보를 종합하여 '{stock_name}'에 대한 최종 투자 분석 보고서를 작성해주세요.

        1. **초기 분석 결과**: {initial_analysis}
        2. **LLM 분류 (positive/negative/neutral)**: {classification}
        3. **관련 최신 뉴스 요약**: {news}

        **보고서 작성 가이드**:
        - 서론, 본론, 결론의 구조로 작성해주세요.
        - 초기 분석 내용을 바탕으로 기업의 현재 상황을 설명하고, 검색된 뉴스가 이를 어떻게 뒷받침하는지 분석해주세요.
        - 최종적으로 투자자가 고려해야 할 기회 요인과 리스크 요인을 균형 있게 제시해주세요.
        - 친절하고 이해하기 쉬운 어조로 작성하되, 전문성을 잃지 마세요.
        """
    )
    initial_analysis = state.get("initial_analysis") or "초기 분석 결과를 확보하지 못했습니다."
    news_text = _format_news_for_prompt(state.get("news") or [])
    report = invoke_prompt_safely(
        prompt,
        {
            "stock_name": state["stock_name"],
            "initial_analysis": initial_analysis,
            "classification": _sanitize_classification(state.get("classification")),
            "news": news_text,
        },
        fallback_message="LLM 보고서를 생성하지 못했습니다. 잠시 후 다시 시도해주세요.",
        log_context="final_report_node",
    )
    return {"final_report": report}


def route_by_classification(state: AgentState):
    """1차 분석 결과(classification)에 따라 다음 노드를 결정합니다."""
    classification = _sanitize_classification(state.get("classification"))
    if classification == "positive":
        return "search_positive_news"
    if classification == "negative":
        return "search_negative_news"
    return "search_general_news"


def run_analysis_agent(stock_name: str, ticker: str, ratios: dict):
    """LangGraph Agent를 실행하여 종합 분석 보고서를 생성합니다."""
    workflow = StateGraph(AgentState)

    workflow.add_node("initial_analysis", initial_analysis_node)
    workflow.add_node("search_positive_news", search_positive_news_node)
    workflow.add_node("search_negative_news", search_negative_news_node)
    workflow.add_node("search_general_news", search_general_news_node)
    workflow.add_node("final_report", final_report_node)

    workflow.set_entry_point("initial_analysis")

    workflow.add_conditional_edges(
        "initial_analysis",
        route_by_classification,
        {
            "search_positive_news": "search_positive_news",
            "search_negative_news": "search_negative_news",
            "search_general_news": "search_general_news",
        },
    )

    workflow.add_edge("search_positive_news", "final_report")
    workflow.add_edge("search_negative_news", "final_report")
    workflow.add_edge("search_general_news", "final_report")
    workflow.add_edge("final_report", END)

    app = workflow.compile()

    initial_state = {
        "stock_name": stock_name,
        "ticker": ticker,
        "ratios": ratios or {},
    }
    final_state = app.invoke(initial_state)

    return final_state.get("final_report", "최종 보고서를 생성하지 못했습니다.")


def get_rag_analysis(uploaded_file, question):
    """
    업로드된 PDF 파일 내용에 근거하여 사용자의 질문에 답변하는 RAG 체인을 실행합니다.

    Args:
        uploaded_file: Streamlit의 file_uploader를 통해 업로드된 파일 객체.
        question (str): 사용자의 질문.

    Returns:
        str: AI가 생성한 답변.
    """
    temp_path = None
    try:
        file_bytes = (
            uploaded_file.getbuffer()
            if hasattr(uploaded_file, "getbuffer")
            else uploaded_file.read()
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(file_bytes)
            temp_path = tmp_file.name

        loader = PyPDFLoader(temp_path)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs = loader.load_and_split(text_splitter)

        try:
            embeddings = OpenAIEmbeddings()
        except Exception as exc:
            logger.error("Failed to initialize embeddings", extra={"error": str(exc)})
            return "임베딩 설정을 확인할 수 없어 RAG 분석을 수행하지 못했습니다."
        vector_store = FAISS.from_documents(docs, embeddings)

        prompt = ChatPromptTemplate.from_template(
            """
            당신은 제공된 문서의 내용을 분석하고 답변하는 AI 어시스턴트입니다. 
            주어진 'Context' 정보에만 근거하여 사용자의 질문에 답변해주세요. 
            문서에 없는 내용은 답변할 수 없다고 솔직하게 말해야 합니다.

            **Context:**
            {context}

            **Question:** {input}
            """
        )

        try:
            llm = get_shared_llm()
        except LLMUnavailableError as exc:
            logger.error("LLM unavailable for RAG", extra={"error": str(exc)})
            return "LLM 설정을 확인할 수 없어 RAG 분석을 수행하지 못했습니다."

        document_chain = create_stuff_documents_chain(llm, prompt)
        retriever = vector_store.as_retriever()
        retrieval_chain = create_retrieval_chain(retriever, document_chain)

        response = retrieval_chain.invoke({"input": question})
        return response.get("answer", "답변을 생성하지 못했습니다.")

    except LLMUnavailableError as exc:
        logger.error("LLM unavailable during RAG preparation", extra={"error": str(exc)})
        return "LLM 설정을 확인할 수 없어 RAG 분석을 수행하지 못했습니다."
    except Exception as exc:
        logger.error("RAG analysis failed", exc_info=exc)
        return "RAG 분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


__all__ = ["run_analysis_agent", "get_rag_analysis", "AgentState"]
