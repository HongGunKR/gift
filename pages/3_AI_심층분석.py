import os
from io import BytesIO

import streamlit as st

from app.agents import langgraph

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

st.title("AI 심층 분석 (RAG) 📑")
st.write("---")

# --- reports 폴더 설정 ---
# 분석할 파일을 저장하고 관리할 폴더의 경로를 지정합니다.
REPORTS_DIR = "reports"

# 만약 reports 폴더가 존재하지 않으면, 새로 생성합니다.
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

# --- 사용자 입력 방식 선택 ---
# 라디오 버튼을 사용하여 두 가지 옵션을 제공합니다.
source_option = st.radio(
    "분석할 파일 소스를 선택하세요:",
    ("파일 직접 업로드", "서버에서 파일 선택"),
    horizontal=True
)

# 최종적으로 분석할 파일을 담을 변수
file_to_analyze = None
file_name_to_analyze = None

# --- 선택된 옵션에 따라 다른 UI를 표시 ---

if source_option == "파일 직접 업로드":
    uploaded_file = st.file_uploader(
        "분석할 PDF 파일을 업로드하세요. 업로드 후 자동으로 `reports` 폴더에 저장됩니다.",
        type="pdf"
    )
    if uploaded_file is not None:
        # 1. 파일을 저장할 경로를 생성합니다. (예: reports/삼성전자_보고서.pdf)
        save_path = os.path.join(REPORTS_DIR, uploaded_file.name)
        
        # 2. 업로드된 파일의 내용을 지정된 경로에 저장합니다.
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"'{uploaded_file.name}' 파일이 `reports` 폴더에 성공적으로 저장되었습니다.")
        
        # 3. 분석할 파일 객체와 파일명을 변수에 할당합니다.
        file_to_analyze = uploaded_file
        file_name_to_analyze = uploaded_file.name

elif source_option == "서버에서 파일 선택":
    # reports 폴더 안의 PDF 파일 목록을 가져옵니다.
    pdf_files = [f for f in os.listdir(REPORTS_DIR) if f.endswith(".pdf")]
    
    if not pdf_files:
        st.warning("`reports` 폴더에 분석할 PDF 파일이 없습니다. 파일을 직접 업로드해주세요.")
    else:
        selected_file_name = st.selectbox(
            "`reports` 폴더에서 분석할 파일을 선택하세요.",
            pdf_files,
            index=None,
            placeholder="파일을 선택해주세요..."
        )
        if selected_file_name:
            # 1. 선택된 파일의 전체 경로를 생성합니다.
            file_path = os.path.join(REPORTS_DIR, selected_file_name)
            
            # 2. 해당 파일을 열어서 파일 객체로 만듭니다.
            with open(file_path, "rb") as f:
                # agent 함수에 전달하기 위해 메모리상에 파일 객체를 복사합니다.
                file_to_analyze = BytesIO(f.read())
            
            # 3. 분석할 파일명을 변수에 할당합니다.
            file_name_to_analyze = selected_file_name

# --- 공통 분석 실행 로직 ---

# 분석할 파일이 확정되었을 경우에만 질문 입력창을 보여줍니다.
if file_to_analyze and file_name_to_analyze:
    st.info(f"**분석 대상 파일:** `{file_name_to_analyze}`")
    question = st.text_input("문서 내용에 대해 질문할 내용을 입력하세요.")
    
    if st.button("RAG 기반 AI 문서 분석 실행하기"):
        if question:
            with st.spinner('AI가 문서를 읽고 질문에 대한 답변을 생성 중입니다...'):
                # agent 함수는 파일 이름(name) 속성을 사용하므로, 이를 명시적으로 지정해줍니다.
                file_to_analyze.name = file_name_to_analyze
                
                # RAG 분석 함수를 호출합니다.
                answer = langgraph.get_rag_analysis(file_to_analyze, question)
                st.success(answer)
        else:
            st.warning("질문을 입력해주세요.")
