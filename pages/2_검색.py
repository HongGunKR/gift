# pages/2_검색.py : 종목 검색 및 LangGraph 분석 메뉴

import pandas as pd
import streamlit as st

from analytics import compute_indicator_snapshot, prepare_price_frame
from app.agents import langgraph
from app.services import data_fetcher

# 메뉴 순서 지정을 위한 CSS 코드
st.markdown(
    """
    <style>
    /* 사이드바 전체를 대상으로 Flexbox 레이아웃을 명시적으로 지정 */
    section[data-testid="stSidebar"] > div:first-child {
        display: flex;
        flex-direction: column;
    }
    
    /* 메뉴(페이지 네비게이션)의 순서를 '1'번으로, 맨 위로 설정 */
    [data-testid="stSidebarNav"] {
        order: 1;
    }

    /* 직접 작성한 사이드바 내용 컨테이너의 순서를 '2'번으로, 메뉴 아래로 설정 */
    section[data-testid="stSidebar"] > div:first-child > div:first-child {
        order: 2;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("종목 검색 및 AI 종합 분석 🔍")
st.write("---")

# 3. 종목 검색 기능
search_term = st.text_input("종목명 또는 키워드를 입력하세요 (예: 삼성)")

if search_term:
    matching_stocks = data_fetcher.search_stocks_by_keyword(search_term)
    stock_to_display = None

    if not matching_stocks:
        st.warning("검색된 종목이 없습니다.")
    elif len(matching_stocks) == 1:
        stock_to_display = matching_stocks[0]
    else:
        selection = st.selectbox("여러 종목이 검색되었습니다. 하나를 선택하세요.", ["-- 종목을 선택해주세요 --"] + matching_stocks)
        if selection != "-- 종목을 선택해주세요 --":
            stock_to_display = selection

    if stock_to_display:
        stock_df, ticker = data_fetcher.get_stock_info_by_name(stock_to_display)
        
        if stock_df is not None:
            st.success(f"'{stock_to_display}' (종목코드: {ticker}) 기본 정보")

            enriched_df = prepare_price_frame(stock_df)
            snapshot = compute_indicator_snapshot(enriched_df)

            col1, col2 = st.columns([1, 1])
            with col1:
                latest_info = stock_df.iloc[-1]
                st.metric("현재가", f"{latest_info['종가']:,} 원")
                st.metric("시가", f"{latest_info['시가']:,} 원")
                st.metric("고가", f"{latest_info['고가']:,} 원")
                st.metric("저가", f"{latest_info['저가']:,} 원")
                st.metric("거래량", f"{latest_info['거래량']:,} 주")
            with col2:
                st.metric(
                    "5일 이동평균",
                    f"{snapshot.get('ma_5', 0):,.2f}",
                    delta=f"{snapshot.get('ma_gap_5_pct', 0):+.2f}% 괴리",
                )
                st.metric(
                    "20일 이동평균",
                    f"{snapshot.get('ma_20', 0):,.2f}",
                    delta=f"{snapshot.get('ma_gap_20_pct', 0):+.2f}% 괴리",
                )
                st.metric(
                    "52주 고점 대비",
                    f"{snapshot.get('high_52', 0):,.2f}",
                    delta=f"{snapshot.get('distance_high_pct', 0):+.2f}% 격차",
                )
                st.metric(
                    "52주 저점 대비",
                    f"{snapshot.get('low_52', 0):,.2f}",
                    delta=f"{snapshot.get('distance_low_pct', 0):+.2f}% 상승",
                )
                volume_delta = snapshot.get("volume_gap_pct", 0)
                st.metric(
                    "거래량 (vs 20일 평균)",
                    f"{snapshot.get('volume', 0):,.0f}",
                    delta=f"{volume_delta:+.2f}%",
                )

            price_tab, indicator_tab = st.tabs(["가격/거래량 차트", "세부 지표"])
            with price_tab:
                moving_avg_columns = [col for col in ["MA5", "MA20", "MA60"] if col in enriched_df.columns]
                chart_data = enriched_df[["종가", *moving_avg_columns]].dropna()
                if not chart_data.empty:
                    st.line_chart(chart_data)
                st.bar_chart(enriched_df["거래량"].tail(120))

            with indicator_tab:
                indicator_data = [
                    {
                        "지표": "5일 이동평균",
                        "현재": snapshot.get("ma_5", 0),
                        "괴리율(%)": snapshot.get("ma_gap_5_pct", 0),
                    },
                    {
                        "지표": "20일 이동평균",
                        "현재": snapshot.get("ma_20", 0),
                        "괴리율(%)": snapshot.get("ma_gap_20_pct", 0),
                    },
                    {
                        "지표": "60일 이동평균",
                        "현재": snapshot.get("ma_60", 0),
                        "괴리율(%)": snapshot.get("ma_gap_60_pct", 0),
                    },
                    {
                        "지표": "거래량 (20일 평균 대비)",
                        "현재": snapshot.get("volume", 0),
                        "괴리율(%)": snapshot.get("volume_gap_pct", 0),
                    },
                    {
                        "지표": "52주 고점",
                        "현재": snapshot.get("high_52", 0),
                        "괴리율(%)": snapshot.get("distance_high_pct", 0),
                    },
                    {
                        "지표": "52주 저점",
                        "현재": snapshot.get("low_52", 0),
                        "괴리율(%)": snapshot.get("distance_low_pct", 0),
                    },
                ]
                indicator_df = pd.DataFrame(indicator_data)
                st.dataframe(
                    indicator_df.style.format(
                        {"현재": "{:,.2f}", "괴리율(%)": "{:+.2f}"}
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

                returns_data = [
                    {"기간": "5 거래일", "수익률(%)": snapshot.get("return_5_pct", 0)},
                    {"기간": "20 거래일", "수익률(%)": snapshot.get("return_20_pct", 0)},
                    {"기간": "60 거래일", "수익률(%)": snapshot.get("return_60_pct", 0)},
                ]
                returns_df = pd.DataFrame(returns_data)
                st.dataframe(
                    returns_df.style.format({"수익률(%)": "{:+.2f}"}),
                    hide_index=True,
                    use_container_width=True,
                )

            st.write("---")
            st.subheader("🤖 AI 종합 분석 (LangGraph)")
            if st.button("AI 종합 분석 시작하기"):
                with st.spinner('LangGraph Agent가 정보를 수집하고 분석 중입니다...'):
                    ratios = data_fetcher.get_financial_ratios(ticker)
                    if ratios:
                        final_report = langgraph.run_analysis_agent(
                            stock_to_display, ticker, ratios
                        )
                        st.markdown(final_report)
                    else:
                        st.error("분석에 필요한 재무 정보를 가져오지 못했습니다.")
