# syntax=docker/dockerfile:1
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY app/requirements.txt .
RUN pip install -r requirements.txt
COPY app/copilot ./copilot
RUN useradd --uid 10001 --create-home appuser
USER 10001
EXPOSE 8000
CMD ["uvicorn", "copilot.main:app", "--host", "0.0.0.0", "--port", "8000"]
