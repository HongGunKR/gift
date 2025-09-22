# pages/2_검색.py : 종목 검색 및 LangGraph 분석 메뉴

import streamlit as st
import data_fetcher
import agent
from datetime import datetime, timedelta

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
            col1, col2 = st.columns([1, 3])
            with col1:
                latest_info = stock_df.iloc[-1]
                st.metric("현재가", f"{latest_info['종가']:,} 원")
                st.metric("시가", f"{latest_info['시가']:,} 원")
                st.metric("고가", f"{latest_info['고가']:,} 원")
                st.metric("저가", f"{latest_info['저가']:,} 원")
                st.metric("거래량", f"{latest_info['거래량']:,} 주")
            with col2:
                st.line_chart(stock_df['종가'])

            st.write("---")
            st.subheader("🤖 AI 종합 분석 (LangGraph)")
            if st.button("AI 종합 분석 시작하기"):
                with st.spinner('LangGraph Agent가 정보를 수집하고 분석 중입니다...'):
                    ratios = data_fetcher.get_financial_ratios(ticker)
                    if ratios:
                        final_report = agent.run_analysis_agent(stock_to_display, ticker, ratios)
                        st.markdown(final_report)
                    else:
                        st.error("분석에 필요한 재무 정보를 가져오지 못했습니다.")