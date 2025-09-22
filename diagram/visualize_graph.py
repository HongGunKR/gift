# visualize_graph.py : agent.py의 LangGraph 구조를 이미지로 저장하는 스크립트
from dotenv import load_dotenv
load_dotenv()

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from agent import (
    AgentState,
    initial_analysis_node,
    search_positive_news_node,
    search_negative_news_node,
    search_general_news_node,
    final_report_node,
    route_by_classification
)
from langgraph.graph import StateGraph, END

from langchain_core.runnables.graph_mermaid import MermaidDrawMethod

def generate_graph_image():
    """
    agent.py에 정의된 그래프 구조를 그대로 가져와서 png 이미지로 저장합니다.
    """
    print("LangGraph 구조를 이미지로 생성합니다...")

    # 1. agent.py와 동일하게 그래프를 정의하고 조립합니다.
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
            "search_general_news": "search_general_news"
        }
    )

    workflow.add_edge("search_positive_news", "final_report")
    workflow.add_edge("search_negative_news", "final_report")
    workflow.add_edge("search_general_news", "final_report")
    workflow.add_edge("final_report", END)

    # 2. 그래프를 컴파일합니다.
    app = workflow.compile()

    # 3. 그래프 구조를 PNG 이미지 데이터로 생성합니다.
    # 이 부분이 핵심 기능입니다.
    image_bytes = app.get_graph().draw_mermaid_png(
        draw_method=MermaidDrawMethod.PYPPETEER
    )

    # 4. 이미지 저장위치를 추출합니다.
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 5. 이미지 저장위치를 설정합니다.
    output_path = os.path.join(script_dir, "langgraph_flowchart.png")

    # 6. 생성된 이미지 데이터를 파일로 저장합니다.
    with open(output_path, "wb") as f:
        f.write(image_bytes)
        
    print(f"✅ '{output_path}' 파일이 성공적으로 저장되었습니다.")

# 이 스크립트를 직접 실행했을 때만 함수가 호출되도록 합니다.
if __name__ == "__main__":
    generate_graph_image()