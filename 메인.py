# main.py : 메인 대시보드 (홈 화면)

import pandas as pd
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
    latest_date = market_indices_df.index[-1]
    st.caption(f"업데이트: {latest_date}")

    latest_row = market_indices_df.iloc[-1]
    previous_row = market_indices_df.iloc[-2] if len(market_indices_df) > 1 else latest_row
    deltas = latest_row - previous_row
    delta_pct = (
        ((latest_row - previous_row) / previous_row.replace(0, pd.NA) * 100)
        .fillna(0)
        if len(market_indices_df) > 1
        else pd.Series([0] * len(latest_row), index=market_indices_df.columns)
    )

    metric_columns = st.columns(len(market_indices_df.columns))
    for idx, column in enumerate(market_indices_df.columns):
        value = latest_row[column]
        delta_value = deltas[column] if column in deltas else 0
        delta_pct_value = delta_pct[column] if column in delta_pct else 0
        metric_columns[idx].metric(
            label=column,
            value=f"{value:,.2f}",
            delta=f"{delta_value:+,.2f} ({delta_pct_value:+.2f}%)",
        )

    st.line_chart(market_indices_df)

    if len(market_indices_df) > 1:
        summary_df = pd.DataFrame(
            {
                "현재가": latest_row,
                "전일대비": deltas,
                "등락률(%)": delta_pct,
            }
        )
        st.dataframe(summary_df.style.format({"현재가": "{:,.2f}", "전일대비": "{:+,.2f}", "등락률(%)": "{:+,.2f}"}))
else:
    st.error("지수 정보를 불러오는 데 실패했습니다.")

# 2. 섹터 모니터링
st.write("---")
st.subheader("주요 섹터 흐름")
sector_df = data_fetcher.get_sector_performance()
if not sector_df.empty:
    st.dataframe(
        sector_df.style.format(
            {"현재가": "{:,.2f}", "전일대비": "{:+,.2f}", "등락률(%)": "{:+,.2f}"}
        ),
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("섹터 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")

# 3. 글로벌 선물 및 환율
st.write("---")
st.subheader("글로벌 선물 · 환율 스냅샷")
global_snapshot = data_fetcher.get_global_market_snapshot()

if global_snapshot:
    chunk_size = 3
    for i in range(0, len(global_snapshot), chunk_size):
        chunk = global_snapshot[i : i + chunk_size]
        cols = st.columns(len(chunk))
        for col, item in zip(cols, chunk):
            price = item.get("price")
            change = item.get("change")
            change_pct_value = item.get("change_pct")
            if price is None:
                col.metric(label=item["label"], value="데이터 없음", delta="N/A")
                continue
            delta_text = (
                f"{change:+,.2f} ({change_pct_value:+.2f}%)"
                if change is not None and change_pct_value is not None
                else "변화 데이터 없음"
            )
            col.metric(label=item["label"], value=f"{price:,.2f}", delta=delta_text)
else:
    st.info("글로벌 선물 또는 환율 정보를 불러오지 못했습니다.")
