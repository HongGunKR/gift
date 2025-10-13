"""LangGraph 시각화 스크립트.

agent.py에 정의된 LangGraph 워크플로우를 PNG/SVG로 내보냅니다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from agent import (  # noqa: E402
    AgentState,
    final_report_node,
    initial_analysis_node,
    route_by_classification,
    search_general_news_node,
    search_negative_news_node,
    search_positive_news_node,
)
from langchain_core.runnables.graph_mermaid import MermaidDrawMethod  # noqa: E402
from langgraph.graph import END, StateGraph  # noqa: E402

DRAW_METHOD_ALIASES = {
    "pyppeteer": MermaidDrawMethod.PYPPETEER,
}


def _create_workflow() -> StateGraph:
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
    return workflow


def _draw_graph(output: Path, draw_method: MermaidDrawMethod, fmt: str) -> None:
    workflow = _create_workflow()
    app = workflow.compile()
    graph = app.get_graph()

    output.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "png":
        image_bytes = graph.draw_mermaid_png(draw_method=draw_method)
        output.write_bytes(image_bytes)
    elif fmt == "svg":
        draw_svg = getattr(graph, "draw_mermaid_svg", None)
        if draw_svg is None:
            raise RuntimeError(
                "현재 langgraph 버전에서 SVG 렌더링을 지원하지 않습니다."
            )
        svg_text = draw_svg(draw_method=draw_method)
        output.write_text(svg_text, encoding="utf-8")
    else:
        raise ValueError(f"Unsupported format: {fmt!r}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LangGraph 워크플로우를 이미지로 저장합니다."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("langgraph_flowchart.png"),
        help="출력 파일 경로 (기본: diagram/langgraph_flowchart.png)",
    )
    parser.add_argument(
        "--format",
        choices=("png", "svg"),
        default="png",
        help="출력 포맷",
    )
    parser.add_argument(
        "--draw-method",
        choices=tuple(DRAW_METHOD_ALIASES.keys()),
        default="pyppeteer",
        help="Mermaid 다이어그램 렌더링 방식",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    draw_method = DRAW_METHOD_ALIASES[args.draw_method]

    try:
        _draw_graph(args.output, draw_method, args.format)
        print(f"✅ 그래프가 '{args.output}'에 저장되었습니다. (format={args.format})")
    except Exception as exc:  # pragma: no cover - CLI 에러 메시지
        print("❌ 그래프 생성 중 오류가 발생했습니다:", exc)
        raise


if __name__ == "__main__":
    main()
