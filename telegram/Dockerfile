FROM python:3.12-slim
WORKDIR /app/src
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 POETRY_VIRTUALENVS_CREATE=false

RUN pip install --no-cache-dir poetry==1.8.3
COPY ./src/pyproject.toml  ./
RUN poetry install --no-interaction --no-ansi --no-root

EXPOSE 8000
CMD ["bash","-lc","poetry run python -m main"]