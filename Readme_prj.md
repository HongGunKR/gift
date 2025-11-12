📌 **AI 과제 주제: 나만의 AI Agent 개발하기**
대한민국 주식 시장 입문 투자자를 위한 Streamlit 기반 AI 브리핑 서비스 **모두의 선물**을 기획·개발했습니다. 핵심 구성은 다음과 같습니다.
- pykrx, Yahoo Finance, DuckDuckGo 데이터를 결합한 시장 데이터 파이프라인을 구축해 지수·섹터·글로벌 지표를 실시간에 가깝게 제공합니다.
- LangGraph로 설계한 에이전트가 재무 지표, 뉴스, 사용자 문서를 단계적으로 분석해 행동 가능한 인사이트를 도출합니다.
- FastAPI와 Swagger UI를 통해 동일한 분석 기능을 REST API로 노출하고, Docker Compose 템플릿으로 재현 가능한 배포 환경을 마련했습니다.

📍 **과제 개요**
입문 투자자가 시장 전반과 특정 종목을 신속하게 이해할 수 있는 종합형 AI Agent 완성을 목표로 했습니다.
- Streamlit 멀티 페이지 UI에서 KOSPI/KOSDAQ 지수, 섹터 흐름, 글로벌 선물·환율을 한눈에 비교할 수 있는 대시보드를 구현했습니다.
- LangGraph 멀티 에이전트가 재무 해석 → 뉴스 탐색 → 리스크 평가 → 최종 코멘트를 순차적으로 수행해 사용자 맞춤형 투자 보고서를 제공합니다.
- FAISS 기반 RAG 체인을 이용해 기업 공시·보고서 등 PDF 문서에 대한 질의응답 기능을 제공하고, Streamlit UI에서 대화형으로 활용할 수 있게 했습니다.

🎯 **과제 목표**
- 입문 투자자를 위한 실시간 시장 브리핑과 종목별 분석 리포트를 자동화합니다.
- LangGraph 멀티 에이전트가 재무 지표, 뉴스, 리스크 정보를 조합해 투자 결정을 돕는 결론과 체크포인트를 제공합니다.
- 문서 기반 RAG 기능으로 기업 보고서 탐색 시간을 단축하고, 사용자 질문에 근거 기반 답변을 제공합니다.

🚀 **과제 수행 가이드라인**
① **AI Agent 주제 선정**  
대한민국 주식 시장 초보 투자자를 위한 “AI 주식 브리핑 비서”를 주제로 선정했습니다.
- 실시간 시장 지표, 시가총액 Top 100, 개별 종목 기술 분석을 통합해 정보 분산 문제를 해결했습니다.
- LangGraph 기반 종합 리포트를 통해 단순 데이터 나열이 아닌 actionable insight를 제공합니다.
- 사용자 문서 기반 RAG 답변으로 기업별 자료 이해도를 높이고 맞춤형 경험을 제공했습니다.

② **평가 기술 요소**
1) **Prompt Engineering**  
에이전트마다 역할, 기대 출력, 판단 기준을 명시한 프롬프트 템플릿을 설계했습니다.
- 재무 분석 노드에 Few-shot 예시를 추가해 핵심 지표 해석 방식과 톤을 통일했습니다.
- 뉴스 요약 노드에는 Chain-of-Thought 지시를 적용해 기사 근거를 먼저 정리하고 결론을 제시하도록 했습니다.
- 데이터 부족·API 오류 시 사용자에게 재시도를 안내하는 예외 프롬프트를 구성했습니다.

2) **LangChain & LangGraph 기반 Multi Agent 구현**  
LangGraph 조건부 엣지로 `재무 → 뉴스 → 리스크 → 최종 코멘트` 노드를 구성해 단계별 분석을 자동화했습니다.
- 각 노드는 OpenAI 모델과 DuckDuckGo Tool Agent를 조합해 최신 데이터를 확보합니다.
- `app/agents/multi_agent.py`에서 펀더멘털, 뉴스, 리스크, 최종 의사결정 에이전트를 LangChain `AgentExecutor`로 묶어 협업 플로우를 완성했습니다.
- 멀티턴 지원을 위해 사용자 질문과 이전 결과 요약을 메모리에 저장해 후속 질문에서도 맥락을 유지합니다.

3) **RAG (Retrieval-Augmented Generation)**  
업로드 또는 `reports/` 디렉터리에 저장된 PDF 문서를 LangChain 로더로 분할하고 OpenAI 임베딩으로 벡터화했습니다.
- FAISS 벡터스토어를 구축해 유사도 기반 검색 결과를 RetrievalQA 체인에 전달, 근거 기반 답변을 생성했습니다.
- 암호화 파일, 과도한 페이지 수 등의 예외를 감지해 사용자에게 원인을 안내하고 임시 파일을 자동 정리합니다.
- 긴 문서는 RecursiveCharacterTextSplitter로 청크화한 뒤 OpenAI 임베딩을 batch 요청으로 생성해 `max_tokens_per_request` 제한을 회피하면서도 안정적으로 대응합니다.

4) **서비스 개발 및 패키징 (Streamlit + FastAPI + Docker)**  
Streamlit 멀티 페이지 앱으로 시장 대시보드, Top 100, 종목 분석, 문서 RAG 화면을 분리해 사용자 흐름을 명확히 했습니다.
- FastAPI(`app/web/api.py`)에서 멀티 에이전트 분석, 대시보드 데이터, Top 100 리스트를 REST 엔드포인트로 제공하고 Swagger UI(`/docs`)와 OpenAPI 스키마(`/openapi.json`)를 자동 노출했습니다.
- `deployments/docker-compose.yml`로 Streamlit, FastAPI, RAG 벡터스토어 서비스를 한번에 기동하고, 환경 변수·로깅 구성을 컨테이너 간 공유하도록 했습니다.

5) **데이터 엔지니어링 & 캐싱 전략 (추가 적용)**  
pykrx, Yahoo Finance와 같이 실패 확률이 높은 외부 소스를 안정적으로 활용하기 위해 다층 캐싱과 재시도 로직을 구현했습니다.
- `app/services/data_fetcher.py`에서 Streamlit 실행 여부를 감지해 `st.cache_data`와 `functools.lru_cache`를 자동 선택하고, 글로벌 지표는 메모리+디스크 이중 캐시(`.cache/global_snapshot.json`)에 저장해 장애 후 즉시 복원합니다.
- Yahoo Finance 호출에는 지수형 백오프와 최대 3회 재시도를 적용하고, 실패 시 마지막 성공 데이터를 즉시 반환해 사용자 경험 저하를 최소화했습니다.
- 데이터 파이프라인 상태와 예외는 구조화 로그로 남겨 FastAPI·Streamlit 환경 어디에서든 동일한 모니터링을 가능하게 했습니다.

6) **테스트 & 관측성 (추가 적용)**  
품질 보증과 운영 편의성을 위해 테스트 및 관측성을 강화했습니다.
- `tests/test_data_fetcher.py`에서 글로벌 데이터 폴백 동작을 Pytest로 검증해 캐시 복원 로직이 예상대로 작동하는지 확인합니다.
- FastAPI와 Streamlit 공용 로거 설정을 통해 에이전트 실행·데이터 수집·에러 상황을 한곳에서 추적할 수 있도록 했습니다.
- LangGraph 워크플로우를 `diagram/visualize_graph.py` 스크립트로 PyGraphviz를 활용해 시각화함으로써 에이전트 플로우 점검 및 협업 설명에 활용했습니다.
