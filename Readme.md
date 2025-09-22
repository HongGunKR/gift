# 🎁 모두의 선물 (AI Stock Analysis Agent)

**모두의 선물**은 대한민국 주식 시장에 관심 있는 초보 투자자를 위해 설계된 AI 기반 주식 분석 웹 애플리케이션입니다. 복잡한 데이터를 AI가 대신 분석하여, 누구나 쉽게 이해할 수 있는 투자 인사이트를 제공하는 것을 목표로 합니다.

## ✨ 주요 기능 (Key Features)

  * **실시간 시장 대시보드**: KOSPI, KOSDAQ 등 주요 지수 현황을 실시간으로 추적합니다.
  * **시가총액 Top 100**: 현재 시장을 주도하는 상위 100개 기업을 한눈에 파악할 수 있습니다.
  * **스마트 종목 검색**: 종목명의 일부만 입력해도 관련된 모든 종목을 찾아주는 편리한 검색 기능을 제공합니다.
  * **다중 페이지 UI**: 각 기능이 독립된 페이지로 구성되어 있어 사용성이 뛰어납니다.
  * **AI 종합 분석 (LangGraph)**: 사용자가 선택한 종목에 대해 AI Agent가 기업 개요, 재무 상태, 최신 뉴스를 종합적으로 분석하고, 상황에 맞는 맞춤형 리포트를 생성합니다.
  * **AI 심층 분석 (RAG)**: 사용자가 직접 업로드한 사업보고서나 리포트(PDF) 내용에만 근거하여 AI가 질문에 답변하여, 신뢰도 높은 분석을 제공합니다.
  * **자동 다이어그램 생성**: 프로젝트에 포함된 스크립트를 통해 AI Agent의 복잡한 작동 흐름을 이미지로 시각화할 수 있습니다.

## 🛠️ 기술 스택 (Tech Stack)

  * **Frontend**: `Streamlit`
  * **Data Handling**: `pandas`, `pykrx`, `duckduckgo-search`
  * **AI / LLM**: `LangChain`, `LangGraph`, `OpenAI`
  * **Deployment**: `Docker`, `Docker Compose`
  * **Dependencies**:
      * `python-dotenv` (환경 변수 관리)
      * `pygraphviz`, `Graphviz` (다이어그램 시각화)
      * `pypdf`, `faiss-cpu` (RAG)

## 📂 프로젝트 구조 (Project Structure)

```
/모두의선물
|-- 📂 deployments/
|   |-- 📜 Dockerfile
|   └── 📜 docker-compose.yml
|-- 📂 diagram/
|   ├── 📜 visualize_graph.py
|   └── 🖼️ langgraph_flowchart.png
|-- 📂 pages/
|   ├── 📜 1_TOP100.py
|   ├── 📜 2_검색.py
|   └── 📜 3_AI_심층분석.py
|-- 📂 reports/
|   └── (분석용 PDF 파일 저장소)
|-- 📜 .dockerignore
|-- 📜 .env
|-- 📜 메인.py
|-- 📜 agent.py
|-- 📜 data_fetcher.py
|-- 📜 requirements.txt
```

## 🚀 설치 및 실행 방법 (Installation & Setup)

### 1\. 프로젝트 복제 (Clone Repository)

```bash
git clone <your-repository-url>
cd 모두의선물
```

### 2\. 시스템 의존성 설치 (Graphviz)

AI Agent 다이어그램 생성을 위해 `Graphviz`가 시스템에 설치되어 있어야 합니다.

  * **macOS (Homebrew 사용 시):**
    ```bash
    brew install graphviz
    ```
  * **Ubuntu/Debian:**
    ```bash
    sudo apt-get update && sudo apt-get install -y graphviz libgraphviz-dev
    ```

### 3\. 환경 변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고 OpenAI API 키를 입력합니다.

**📜 `.env`**

```env
OPENAI_API_KEY="sk-..."
```

### 4\. Python 라이브러리 설치

```bash
pip install -r requirements.txt
```

*macOS에서 `pygraphviz` 설치 오류 발생 시, 아래 명령어를 먼저 실행하세요.*

  * *(Apple Silicon Mac)* `LDFLAGS="-L/opt/homebrew/lib/" CPPFLAGS="-I/opt/homebrew/include/" pip install pygraphviz`
  * *(Intel Mac)* `LDFLAGS="-L$(brew --prefix graphviz)/lib" CPPFLAGS="-I$(brew --prefix graphviz)/include" pip install pygraphviz`

### 5\. 애플리케이션 실행

#### 방법 1: Docker Compose 사용 (권장)

가장 간단하고 안정적인 실행 방법입니다.

```bash
# -f 플래그로 compose 파일 경로 지정하여 실행
docker-compose -f deployments/docker-compose.yml up --build
```

#### 방법 2: Streamlit 직접 실행 (개발용)

```bash
# (파일 이름을 '메인.py'로 변경했으므로)
streamlit run 메인.py
```

실행 후 웹 브라우저에서 **`http://localhost:8501`** 로 접속하세요.

## 📖 사용 방법 (How to Use)

  * **AI 종합 분석**: `검색` 메뉴에서 원하는 종목을 찾은 뒤, 'AI 종합 분석 시작하기' 버튼을 클릭하세요.
  * **AI 심층 분석 (RAG)**: `reports` 폴더에 분석할 PDF 파일을 넣거나, `AI 심층 분석` 메뉴에서 직접 파일을 업로드하세요. 그 후, 문서 내용에 대한 질문을 입력하고 분석 버튼을 클릭하세요.
  * **Agent 다이어그램 생성**: 프로젝트 구조를 시각화하고 싶을 때, 터미널에서 아래 명령어를 실행하세요. `diagram` 폴더 안에 `langgraph_flowchart.png` 파일이 생성됩니다.
    ```bash
    python diagram/visualize_graph.py
    ```