# 🎁 모두의 선물 (AI Stock Analysis Agent)

**모두의 선물**은 대한민국 주식 시장에 입문한 투자자에게 “읽기 쉬운” 시장 브리핑을 제공하는 AI 기반 스트림릿 애플리케이션입니다. pykrx와 다양한 외부 데이터 소스를 결합하고, LangGraph/LLM 에이전트가 재무지표·뉴스·사용자 문서를 분석해 행동 가능한 인사이트를 만들어 냅니다.

## ✨ 주요 기능 (Key Features)

- **다차원 시장 대시보드**  
  - KOSPI·KOSDAQ·KOSPI200 등 핵심 지수의 일별 추세, 전일 대비 절대/퍼센트 변동을 한눈에 확인합니다.  
  - pykrx 기반 섹터 퍼포먼스를 계산해 상승/하락 업종을 테이블로 강조합니다.  
  - Yahoo Finance 실시간 스냅샷을 이용해 S&P/Nasdaq 선물, WTI, USD/KRW 환율을 함께 모니터링합니다.

- **시가총액 Top 100 리더보드**  
  - 최신 영업일 기준 pykrx 데이터를 호출하고, 실패 시 마지막 정상 데이터를 캐시에서 복원해 서비스 다운타임을 최소화합니다.

- **스마트 종목 검색 & 기술적 인사이트**  
  - 종목명 일부만 입력해도 자동 완성 목록을 제공합니다.  
  - 52주 고저 대비 위치, 5/20/60일 이동평균 괴리율, 거래량 20일 평균 대비 증감, 5·20·60거래일 수익률 등 핵심 지표를 탭으로 시각화합니다.

- **LangGraph 기반 AI 종합 분석**  
  - 재무지표 해석 → 분류(positive/neutral/negative) → 분기별 뉴스 수집 → 최종 보고서의 다단계 플로우를 LangGraph로 구현했습니다.  
  - DuckDuckGo 검색이 실패하거나 뉴스가 없을 경우에도 안내 메시지를 반환하도록 보강했습니다.

- **멀티 에이전트 오케스트레이션 & Swagger API**  
  - 펀더멘털·뉴스·리스크·최종 의사결정 에이전트가 협업하여 심층 분석 리포트를 생성합니다. (`app/agents/multi_agent.py`)  
  - FastAPI 기반 `app/web/api.py` 서버를 통해 동일 기능을 REST/JSON으로 제공하며, 자동 생성되는 Swagger UI(`/docs`)와 OpenAPI 스키마(`/openapi.json`)를 제공합니다.

- **RAG 문서 Q&A**  
  - 업로드/서버 저장 PDF를 선택해 질문하면, OpenAI 임베딩과 FAISS 벡터스토어를 활용해 문서 맥락 기반 답변을 제공합니다.  
  - 임시 파일을 자동 정리하고, 오류 발생 시 친절한 메시지를 표시합니다.

- **자동 다이어그램 생성**  
  - `diagram/visualize_graph.py` 스크립트로 LangGraph 워크플로우를 PNG로 렌더링할 수 있습니다.
- **고가용성 데이터 파이프라인**  
  - 글로벌 지표는 메모리 및 디스크(JSON) 캐시에 동시 저장되며, 외부 API가 429/네트워크 오류를 반환해도 마지막 성공 데이터를 즉시 복원합니다.  
  - Yahoo Finance 호출은 지수형 백오프를 적용해 자체적으로 3회 재시도하며, 실패 원인은 UI 캡션과 로그로 모두 확인할 수 있습니다.
- **기본 테스트 스위트**  
  - `tests/test_data_fetcher.py`로 글로벌 데이터 실패 시 플레이스홀더가 안전하게 반환되는지 검증합니다.

## 🧱 아키텍처 & 데이터 파이프라인

- **Streamlit UI**  
  - `메인.py`: 시장 대시보드 (지수/섹터/글로벌)  
  - `pages/1_TOP_100.py`: 시총 상위 100  
  - `pages/2_검색.py`: 종목 검색 + 기술적 지표 + LangGraph 분석  
  - `pages/3_AI_심층분석.py`: RAG 기반 문서 질의

- **데이터 서비스 (`app/services/data_fetcher.py`)**  
  - Streamlit 실행 여부를 감지해 `st.cache_data` 또는 `functools.lru_cache`를 투명하게 선택, FastAPI 단독 실행 시에도 동일한 캐싱을 제공합니다.  
  - pykrx/뉴스/글로벌 데이터는 메모리 캐시와 `.cache/global_snapshot.json` 디스크 캐시를 함께 사용해 장애 복원력을 높였습니다.  
  - `logging` 기반 구조화 로그와 `get_last_data_error` 헬퍼를 제공해 UI/백엔드에서 오류 원인을 즉시 확인할 수 있습니다.
- pykrx 지수/섹터 데이터, DuckDuckGo 뉴스, Yahoo Finance 글로벌 스냅샷을 모듈화했습니다.

- **기술적 지표 모듈 (`analytics/technical.py`)**  
  - pandas rolling 연산으로 이동평균·거래량 평균을 계산하고, 괴리율·52주 고저 대비·최근 수익률을 딕셔너리 형태로 제공합니다.

- **AI Agent (`app/agents/langgraph.py`)**  
  - LangGraph의 조건부 엣지를 사용해 분석→뉴스→보고서 플로우를 구성합니다.  
  - LLM 응답 파싱, 뉴스 포맷팅, 임시 파일 관리 등 안정성을 강화했습니다.

- **멀티 에이전트 & API**  
  - `app/agents/multi_agent.py`: 펀더멘털·뉴스·리스크·최종 의사결정을 담당하는 네 개의 LLM 에이전트가 협업합니다.  
  - `app/web/api.py`: FastAPI + Swagger UI를 이용해 프로그램형 인터페이스를 제공합니다.

## 📂 프로젝트 구조

```
/모두의선물
├── analytics/
│   ├── __init__.py
│   └── technical.py                # 이동평균, 거래량, 수익률 등 계산
├── architecture/
│   └── Readme.md
├── diagram/
│   ├── visualize_graph.py
│   └── langgraph_flowchart.png
├── deployments/
│   ├── Dockerfile
│   └── docker-compose.yml
├── tests/                         # 단위/통합 테스트
├── pages/
│   ├── 1_TOP_100.py
│   ├── 2_검색.py
│   └── 3_AI_심층분석.py
├── reports/                        # 업로드/관리용 PDF 저장소
├── .env                            # OPENAI_API_KEY 등 환경 변수
├── .dockerignore
├── .gitignore
├── 메인.py                         # 메인 대시보드
├── app/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── langgraph.py            # LangGraph 기반 분석 에이전트
│   │   └── multi_agent.py          # 협업 에이전트 오케스트레이터
│   ├── services/
│   │   ├── __init__.py
│   │   └── data_fetcher.py         # 외부 데이터 수집 및 캐시
│   ├── utils/
│   │   ├── __init__.py
│   │   └── llm.py                  # 공용 LLM 유틸리티
│   └── web/
│       ├── __init__.py
│       └── api.py                  # FastAPI 엔드포인트
├── requirements.txt
└── Readme.md
```

## 🛠️ 설치 & 실행

### 1. 레포지토리 클론

```bash
git clone https://github.com/HongGunKR/gift
cd gift
```

### 2. 필수 시스템 의존성

LangGraph 다이어그램 생성을 위해 Graphviz 라이브러리가 필요합니다.

- **macOS (Homebrew)**  
  `brew install graphviz`
- **Ubuntu/Debian**  
  `sudo apt-get update && sudo apt-get install -y graphviz libgraphviz-dev`

### 3. 환경 변수

루트 디렉토리에 `.env` 파일을 만들고 OpenAI API 키를 지정하세요.

```env
OPENAI_API_KEY="sk-..."
```

### 4. 파이썬 의존성 설치

```bash
pip install -r requirements.txt
```

> `requests` (Yahoo Finance), `duckduckgo-search` (뉴스), `pykrx`(시장 데이터), `faiss-cpu`(RAG), `fastapi`, `uvicorn` 등 네트워크 액세스가 필요합니다. 방화벽이 있는 환경이라면 허용 정책을 먼저 점검하세요.  
> macOS에서 `pygraphviz` 설치가 실패할 경우:
> - Apple Silicon: `LDFLAGS="-L/opt/homebrew/lib/" CPPFLAGS="-I/opt/homebrew/include/" pip install pygraphviz`
> - Intel Mac: `LDFLAGS="-L$(brew --prefix graphviz)/lib" CPPFLAGS="-I$(brew --prefix graphviz)/include" pip install pygraphviz`

### 5. 애플리케이션 실행

**옵션 A · Docker Compose (권장)**

```bash
docker-compose -f deployments/docker-compose.yml up --build
```

**옵션 B · 로컬 개발용 Streamlit**

```bash
streamlit run 메인.py
```

실행 후 브라우저에서 `http://localhost:8501` 접속.

**옵션 C · FastAPI 서버 (멀티 에이전트 & Swagger)**  

```bash
uvicorn app.web.api:app --host 0.0.0.0 --port 8502 --reload
```

- Swagger UI: `http://localhost:8502/docs`  
- ReDoc: `http://localhost:8502/redoc`  
- OpenAPI 스키마: `http://localhost:8502/openapi.json`

## 📖 사용 가이드

- **시장 대시보드**  
  - 상단 지표 카드에서 KOSPI/KOSDAQ/KOSPI200의 현재가·등락률을 확인하고, 추세 차트를 통해 최근 30일 흐름을 파악합니다.  
  - “주요 섹터 흐름” 표로 상승/하락 업종을 살피고, “글로벌 선물 · 환율” 카드로 해외 지표 영향을 점검하세요.

- **시가총액 Top 100**  
  - pykrx 호출이 실패하더라도 마지막 성공 데이터를 보여주므로, 일시적인 API 오류 시에도 분석을 계속할 수 있습니다.

- **종목 검색 & 기술적 분석**  
  - 검색창에 키워드를 입력 후 종목을 선택하면, 가격·이동평균·거래량 지표가 카드와 표, 차트로 표시됩니다.  
  - “AI 종합 분석” 버튼을 누르면 LangGraph 에이전트가 재무 지표와 최신 뉴스를 결합한 보고서를 생성합니다.

- **AI 심층 분석 (RAG)**  
  - `reports/` 폴더에 미리 넣어두거나, 페이지에서 직접 PDF를 업로드하세요.  
  - 질문을 입력하면 RAG 체인이 문서 맥락을 기반으로 답변합니다. 임시 파일은 자동 정리되어 디스크가 깔끔하게 유지됩니다.  
  - RAG 파이프라인 진행 상황과 오류는 `logging` 모듈로 기록되어 FastAPI/Streamlit 환경에서 동일하게 추적할 수 있습니다.

- **LangGraph 다이어그램**  
  - 에이전트 흐름을 시각화하려면 다음 명령을 실행하세요.
    ```bash
    python diagram/visualize_graph.py
    ```
  - `diagram/langgraph_flowchart.png`가 생성됩니다.
- **FastAPI 엔드포인트 활용**  
  - `/analysis/multi-agent`: POST JSON `{ "stock_name": "삼성전자" }` → 멀티에이전트 분석 리포트  
  - `/dashboard/overview`: GET → 시장 대시보드 데이터 (지수/섹터/글로벌 스냅샷)  
  - `/market/top100`: GET → 시가총액 Top 100 리스트  
  - Swagger UI에서 샘플 요청을 확인하고 바로 실행할 수 있습니다.

## ✅ 검증 & 트러블슈팅

- pykrx 또는 Yahoo Finance 호출이 빈번히 실패한다면  
  - 네트워크 연결/프록시 설정을 확인하고, 실패 시 캐시 데이터가 표시되는지 로그(`streamlit run` 터미널)에서 확인하세요.
- LangGraph 보고서가 생성되지 않으면  
  - `.env`에 OpenAI 키가 설정되었는지, 요금제 한도가 남아있는지 점검하세요.
- RAG 분석 오류  
  - PDF가 암호화되어 있거나 페이지 수가 매우 많은 경우 chunk 분할이 오래 걸릴 수 있습니다. 필요한 일부 페이지만 발췌해 업로드하는 것을 권장합니다.
- 글로벌 선물/환율 스냅샷 오류  
  - 애플리케이션은 3회까지 자동 재시도 후 마지막 성공 데이터를 디스크 캐시에서 복원합니다.  
  - Streamlit 대시보드 하단의 경고 메시지를 확인해 Rate Limit 또는 네트워크 이슈인지 진단하세요.  
  - 빈번한 429가 지속되면 서버 측 주기 캐시(예: 5분마다 백엔드 스케줄러 실행)나 보다 안정적인 데이터 API로 교체하는 것을 고려하세요.
- FastAPI 호출 오류  
  - `422` 응답은 요청 파라미터가 잘못된 경우이므로 Swagger UI의 스키마 정의를 참고하세요.  
  - `500` 응답이 지속되면 OpenAI API 키, 외부 네트워크 정책, pykrx 데이터 접근 권한을 점검하세요.

## 📌 개발 노트

- `data_fetcher._LAST_SUCCESS_CACHE`는 API 실패 시 사용자 경험을 보호하기 위한 로컬 메모리 캐시입니다. Streamlit 앱이 재시작되면 초기화됩니다.
- 글로벌 시장 데이터는 `.cache/global_snapshot.json`에 15분 동안 저장되며, 장애 시 자동으로 복원됩니다.
- `analytics/technical.py`는 pandas 기반 지표 계산만 담당합니다. 다른 페이지에서도 재사용할 수 있도록 설계했습니다.
- LangGraph 플로우 및 멀티 에이전트 오케스트레이터는 확장성을 염두에 두고 작성되었기 때문에, 추가 뉴스 소스나 정량 지표 노드를 쉽게 삽입할 수 있습니다.
- `app/agents/langgraph.py`와 `app/services/data_fetcher.py`는 `logging` 모듈을 사용하므로 환경 설정으로 로그 레벨/핸들러를 자유롭게 조정할 수 있습니다.
- `pytest` 설치 후 `pytest` 명령으로 기본 테스트(`tests/test_data_fetcher.py`)를 실행해 글로벌 데이터 폴백 동작을 검증할 수 있습니다.

필요한 기능이나 개선 아이디어가 있으면 Issues 또는 PR로 참여해 주세요! 🎉
