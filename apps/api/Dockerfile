FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
RUN uv sync --frozen --no-dev --package researchflow-api

COPY apps/api/src apps/api/src
EXPOSE 8000
CMD [".venv/bin/python", "-m", "uvicorn", "researchflow.main:app", "--app-dir", "apps/api/src", "--host", "0.0.0.0", "--port", "8000"]
