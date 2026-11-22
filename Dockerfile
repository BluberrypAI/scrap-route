FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
# 기본 이미지에 든 setuptools·wheel(jaraco.context 포함)의 알려진 취약점 때문에 먼저 올린다
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "resource_ai.main:app", "--host", "0.0.0.0", "--port", "8000"]
