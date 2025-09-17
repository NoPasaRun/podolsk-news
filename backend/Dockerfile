FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 POETRY_VIRTUALENVS_CREATE=false

# ставим poetry через pip (надёжнее чем curl-скрипт)
RUN pip install --no-cache-dir poetry==1.8.3

# сначала зависимости, чтобы кешировалось
COPY pyproject.toml poetry.lock* ./

COPY src ./src
RUN poetry install --no-interaction --no-ansi

EXPOSE 8000
CMD ["bash","-lc","poetry run uvicorn src.app.main:app --host 0.0.0.0 --port 8000"]