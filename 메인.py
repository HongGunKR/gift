# main.py : 메인 대시보드 (홈 화면)

import streamlit as st
import data_fetcher

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

# 페이지 설정 
st.set_page_config(
    page_title="모두의 선물",
    page_icon="🎁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사이드바
with st.sidebar:
    st.title("모두의 선물 🎁")
    st.write("---")
    st.write("AI 기반 주식 분석 서비스입니다.")
    st.write("투자에 대한 최종 책임은 본인에게 있습니다.")

# 메인 화면
st.title("시장 현황 대시보드 📈")
st.write("---")

# 1. 주요 지수 현황
st.subheader("주요 지수 현황")
market_indices_df = data_fetcher.get_market_indices()

if not market_indices_df.empty:
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            label="KOSPI",
            value=f"{market_indices_df['KOSPI'].iloc[-1]:,.2f}",
            delta=f"{market_indices_df['KOSPI'].iloc[-1] - market_indices_df['KOSPI'].iloc[-2]:,.2f}"
        )
    with col2:
        st.metric(
            label="KOSDAQ",
            value=f"{market_indices_df['KOSDAQ'].iloc[-1]:,.2f}",
            delta=f"{market_indices_df['KOSDAQ'].iloc[-1] - market_indices_df['KOSDAQ'].iloc[-2]:,.2f}"
        )
    
    st.line_chart(market_indices_df)
else:
    st.error("지수 정보를 불러오는 데 실패했습니다.")