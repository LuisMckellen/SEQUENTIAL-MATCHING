FROM python:3.12.7-slim
WORKDIR /app
RUN pip install --no-cache-dir networkx==3.6.1
COPY kit.py policy.py ./
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 65534:65534
ENTRYPOINT ["python", "policy.py"]
