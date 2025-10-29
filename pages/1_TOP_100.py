# pages/1_TOP_100.py : 시가총액 Top 100 메뉴

import streamlit as st
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

st.title("시가총액 Top 100 🏆")
st.write("---")

# 데이터 로딩 중에 스피너를 표시
with st.spinner('데이터를 불러오는 중입니다...'):
    top_100_df = data_fetcher.get_top_100_market_cap_stocks()

if not top_100_df.empty:
    st.dataframe(top_100_df, use_container_width=True, height=35 * (len(top_100_df) + 1))
else:
    st.error("시가총액 정보를 불러오는 데 실패했습니다.")
