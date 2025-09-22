from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage

import data_fetcher

from typing import TypedDict, List
from langgraph.graph import StateGraph, END

# Agent의 상태(State) 정의: 그래프의 각 노드를 거치며 데이터가 저장되고 업데이트됩니다.
class AgentState(TypedDict):
    stock_name: str
    ticker: str
    ratios: dict
    initial_analysis: str
    classification: str # "positive", "negative", "neutral"
    news: List[dict]
    final_report: str

# LLM 모델 초기화 (한 번만 선언하여 재사용)
llm = ChatOpenAI(model_name="gpt-4o")

# --- 각 노드(Node)에 해당하는 함수들을 정의합니다. ---
def initial_analysis_node(state: AgentState):
    """1차 분석 노드: 기업 개요와 재무 정보를 종합하여 초기 분석 및 판단을 수행합니다."""
    print("--- 1. 1차 분석 노드 실행 ---")
    stock_name = state['stock_name']
    ratios = state['ratios']
    
    # 기존 프롬프트를 활용하여 기업 개요와 재무 분석을 동시에 요청
    ratios_str = (f"PER: {ratios['PER']:.2f}, PBR: {ratios['PBR']:.2f}, EPS: {ratios['EPS']:,}원, 배당수익률: {ratios['DIV']:.2f}%")
    
    prompt = PromptTemplate.from_template(
        """당신은 전문 애널리스트입니다. '{stock_name}' 기업의 개요와 다음 재무 지표를 분석해주세요.
        - 기업의 주요 사업, 주력 제품 설명
        - 재무 지표({ratios_str})를 해석하고, 이를 바탕으로 기업의 현재 상태를 'positive', 'negative', 'neutral' 중 하나로 분류해주세요.
        - 분류에 대한 이유를 간략하게 설명해주세요.
        
        출력 형식은 "분류: [positive/negative/neutral]\n설명: [분석 내용]" 이어야 합니다.
        """
    )
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"stock_name": stock_name, "ratios_str": ratios_str})
    
    # 응답에서 '분류'와 '설명'을 분리
    parts = response.split("\n설명: ")
    classification = parts[0].replace("분류: ", "").strip()
    analysis_text = parts[1].strip()

    return {"initial_analysis": analysis_text, "classification": classification}

def search_positive_news_node(state: AgentState):
    """호재성 뉴스를 검색하는 노드"""
    print("--- 2a. 호재성 뉴스 검색 노드 실행 ---")
    news = data_fetcher.search_news(f"{state['stock_name']} 호재 전망 신제품")
    return {"news": news}

def search_negative_news_node(state: AgentState):
    """악재성 뉴스를 검색하는 노드"""
    print("--- 2b. 악재성 뉴스 검색 노드 실행 ---")
    news = data_fetcher.search_news(f"{state['stock_name']} 악재 리스크 우려")
    return {"news": news}

def search_general_news_node(state: AgentState):
    """일반 뉴스를 검색하는 노드"""
    print("--- 2c. 일반 뉴스 검색 노드 실행 ---")
    news = data_fetcher.search_news(f"{state['stock_name']} 주가")
    return {"news": news}

def final_report_node(state: AgentState):
    """최종 보고서 생성 노드: 모든 정보를 종합하여 최종 리포트를 작성합니다."""
    print("--- 3. 최종 보고서 생성 노드 실행 ---")
    prompt = ChatPromptTemplate.from_template(
        """당신은 유능한 투자 분석가입니다. 다음 정보를 종합하여 '{stock_name}'에 대한 최종 투자 분석 보고서를 작성해주세요.

        1. **초기 분석 결과**: {initial_analysis}
        2. **관련 최신 뉴스 요약**: {news}

        **보고서 작성 가이드**:
        - 서론, 본론, 결론의 구조로 작성해주세요.
        - 초기 분석 내용을 바탕으로 기업의 현재 상황을 설명하고, 검색된 뉴스가 이를 어떻게 뒷받침하는지 분석해주세요.
        - 최종적으로 투자자가 고려해야 할 기회 요인과 리스크 요인을 균형 있게 제시해주세요.
        - 친절하고 이해하기 쉬운 어조로 작성하되, 전문성을 잃지 마세요.
        """
    )
    chain = prompt | llm | StrOutputParser()
    report = chain.invoke({
        "stock_name": state['stock_name'],
        "initial_analysis": state['initial_analysis'],
        "news": state['news']
    })
    return {"final_report": report}

def route_by_classification(state: AgentState):
    """1차 분석 결과(classification)에 따라 다음 노드를 결정합니다."""
    classification = state["classification"]
    if classification == "positive":
        return "search_positive_news"
    elif classification == "negative":
        return "search_negative_news"
    else:
        return "search_general_news"

# --- 그래프(Graph)를 조립하고 실행하는 메인 함수 ---
def run_analysis_agent(stock_name: str, ticker: str, ratios: dict):
    """LangGraph Agent를 실행하여 종합 분석 보고서를 생성합니다."""
    
    # 그래프 정의
    workflow = StateGraph(AgentState)

    # 노드 추가
    workflow.add_node("initial_analysis", initial_analysis_node)
    workflow.add_node("search_positive_news", search_positive_news_node)
    workflow.add_node("search_negative_news", search_negative_news_node)
    workflow.add_node("search_general_news", search_general_news_node)
    workflow.add_node("final_report", final_report_node)

    # 엣지(Edge) 연결
    workflow.set_entry_point("initial_analysis")

    # 조건부 엣지를 사용하여 1차 분석 후 다음 단계를 결정합니다.
    workflow.add_conditional_edges(
        "initial_analysis",
        route_by_classification,
        {
            "search_positive_news": "search_positive_news",
            "search_negative_news": "search_negative_news",
            "search_general_news": "search_general_news"
        }
    )

    # 3개의 뉴스 노드 모두 최종 보고서 노드로 연결합니다.
    workflow.add_edge("search_positive_news", "final_report")
    workflow.add_edge("search_negative_news", "final_report")
    workflow.add_edge("search_general_news", "final_report")

    workflow.add_edge("final_report", END)

    # 그래프 컴파일
    app = workflow.compile()

    # 초기 상태 설정 및 실행
    initial_state = {
        "stock_name": stock_name,
        "ticker": ticker,
        "ratios": ratios
    }
    final_state = app.invoke(initial_state)
    
    return final_state['final_report']


def get_rag_analysis(uploaded_file, question):
    """
    업로드된 PDF 파일 내용에 근거하여 사용자의 질문에 답변하는 RAG 체인을 실행합니다.
    
    Args:
        uploaded_file: Streamlit의 file_uploader를 통해 업로드된 파일 객체.
        question (str): 사용자의 질문.
        
    Returns:
        str: AI가 생성한 답변.
    """
    try:
        # 1. 업로드된 파일을 임시 경로에 저장
        # PyPDFLoader가 파일 경로를 인자로 받기 때문에 임시 저장이 필요합니다.
        with open(uploaded_file.name, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 2. PDF 문서 로드 및 분할
        # PyPDFLoader로 PDF를 읽어옵니다.
        loader = PyPDFLoader(uploaded_file.name)
        # RecursiveCharacterTextSplitter로 문서를 AI가 처리하기 좋은 작은 조각(chunk)으로 나눕니다.
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs = loader.load_and_split(text_splitter)

        # 3. 텍스트 임베딩 및 벡터 저장소(Vector Store) 생성
        # 나눈 텍스트 조각들을 OpenAI의 임베딩 모델을 사용해 벡터(숫자 배열)로 변환합니다.
        embeddings = OpenAIEmbeddings()
        # FAISS를 사용하여 메모리 내에 벡터 저장소를 만들고, 변환된 텍스트 조각들을 저장합니다.
        # 이 저장소는 질문과 가장 유사한 텍스트 조각을 빠르게 찾아주는 역할을 합니다.
        vector_store = FAISS.from_documents(docs, embeddings)

        # 4. 프롬프트 템플릿 정의
        # 이 템플릿은 AI에게 'context'에 주어진 문서 내용만을 참고하여 답변하라고 지시합니다.
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

        # 5. LangChain 체인 구성
        #llm = ChatOpenAI(model_name="gpt-4o")
        
        # (5-1) Document Chain: LLM이 프롬프트와 검색된 문서를 받아 답변을 생성하는 부분
        document_chain = create_stuff_documents_chain(llm, prompt)
        
        # (5-2) Retrieval Chain: 사용자의 질문을 받아 벡터 저장소에서 관련 문서를 검색하고,
        #                       그 결과를 Document Chain에 전달하는 전체 흐름
        retriever = vector_store.as_retriever()
        retrieval_chain = create_retrieval_chain(retriever, document_chain)

        # 6. 체인 실행 및 결과 반환
        response = retrieval_chain.invoke({"input": question})
        
        # response 딕셔너리에서 'answer' 키의 값을 반환합니다.
        return response['answer']

    except Exception as e:
        print(f"RAG 분석 중 오류가 발생했습니다: {e}")
        return f"RAG 분석 중 오류가 발생했습니다: {e}"