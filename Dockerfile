# -------------------------------------------
# File: Dockerfile
# -------------------------------------------
FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip \
    && pip install -r langgraph_agent/requirements.txt \
    && pip install -r web_dashboard/requirements.txt \
    && pip install .

ENTRYPOINT ["ai-review"]