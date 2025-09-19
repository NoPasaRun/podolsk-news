FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir poetry==1.8.3

COPY pyproject.toml poetry.lock* ./

RUN poetry install --no-interaction --no-ansi --no-root
CMD ["bash","-lc","poetry run python -m src.worker"]
