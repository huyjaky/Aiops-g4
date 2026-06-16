FROM python:3.10-slim
COPY wheels /wheels
RUN pip install --no-index --find-links=/wheels fastapi uvicorn requests pyyaml
