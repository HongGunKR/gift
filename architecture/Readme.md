## Architecture
사용자 및 외부 인터페이스: 사용자가 앱과 상호작용하고, 인터넷을 통해 외부와 연결됩니다.

배포 및 환경 관리 (Docker Compose): docker-compose.yml, Dockerfile, .env 파일이 Docker 컨테이너를 빌드하고 실행하는 과정을 관리합니다. OPENAI_API_KEY는 .env 파일을 통해 안전하게 컨테이너로 주입됩니다.

애플리케이션 계층 (Streamlit App): Streamlit 서버가 포트 8501을 통해 실행되며, 메인.py와 pages 폴더의 각 페이지가 사용자 인터페이스를 제공합니다.

AI Agent & 데이터 로직: agent.py는 LangGraph로 AI의 복잡한 추론 과정을 관리하고, RAG로 문서 기반 질문에 답합니다. data_fetcher.py는 외부 API로부터 데이터를 수집합니다.

외부 데이터 소스 및 저장소: pykrx에서 주식 데이터, DuckDuckGo Search에서 뉴스, OpenAI API에서 LLM 서비스를 제공받습니다. reports 폴더는 사용자가 업로드한 PDF 문서를 저장하고 컨테이너와 호스트 간에 공유됩니다.

다이어그램 생성 (로컬 유틸리티): visualize_graph.py 스크립트가 agent.py의 LangGraph 구조를 분석하여 langgraph_flowchart.png 이미지로 로컬에 저장합니다.