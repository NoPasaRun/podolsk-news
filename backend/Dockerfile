FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir poetry==1.8.3

COPY pyproject.toml aerich.ini poetry.lock* ./

RUN poetry install --no-interaction --no-ansi --no-root

EXPOSE 8000
WORKDIR /app/src

CMD ["bash","-lc","poetry run aerich upgrade && poetry run uvicorn wsgi:app --host 0.0.0.0 --port 8000 --proxy-headers"]