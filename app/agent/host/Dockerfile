FROM python:3.12-slim

# 작업 디렉토리 설정
WORKDIR /app

# Poetry 설치
RUN pip install poetry==1.6.1

# Poetry 가상 환경 생성하지 않도록 설정
RUN poetry config virtualenvs.create false

# 의존성 파일 복사 및 설치
COPY app/agent/host/pyproject.toml app/agent/host/poetry.lock* /app/

# 의존성 설치
RUN cd /app && poetry install --no-dev --no-interaction --no-ansi

# 프로젝트 전체 복사
COPY . /app/

# 환경 변수 설정
ENV HOST_AGENT_PORT=10000
ENV PYTHONPATH=/app

# 서비스 포트 노출
EXPOSE 10000

# 애플리케이션 실행
CMD ["python", "-m", "app.agent.host.run_agent"] 