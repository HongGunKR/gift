# 1. 베이스 이미지로 Python 3.11 슬림 버전을 사용합니다.
FROM python:3.11-slim

# 2. 시스템에 필요한 라이브러리(Graphviz)를 먼저 설치합니다.
RUN apt-get update && apt-get install -y graphviz libgraphviz-dev gcc && rm -rf /var/lib/apt/lists/*

# 3. 컨테이너 내부에 /app 이라는 작업 디렉토리를 만듭니다.
WORKDIR /app

# 4. requirements.txt 파일을 먼저 복사하여 Python 패키지를 설치합니다.
# (소스 코드보다 먼저 설치하면, 소스 코드만 변경되었을 때 이 단계를 캐시로 재사용하여 빌드 속도가 빨라집니다.)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. .dockerignore에 명시된 파일을 제외한 나머지 프로젝트 파일 전체를 복사합니다.
COPY . .

# 6. 컨테이너 외부로 Streamlit(8501)과 FastAPI(8502) 포트를 노출합니다.
EXPOSE 8501 8502

# 7. 컨테이너가 시작될 때 실행할 기본 명령어를 설정합니다.
# (파일 이름을 '메인.py'로 변경하셨으므로, 여기에 반영합니다.)
CMD ["streamlit", "run", "메인.py", "--server.port=8501", "--server.address=0.0.0.0"]
