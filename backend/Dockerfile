FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml ./
COPY chatdocs ./chatdocs
RUN pip install ".[otel]"
COPY alembic.ini ./
COPY migrations ./migrations
# Non-root user (EN-04 T-EN04.8: the PDF parser must not run as root)
RUN useradd --system --uid 10001 chatdocs
USER chatdocs
EXPOSE 8000
CMD ["uvicorn", "chatdocs.adapters.http.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "35"]
