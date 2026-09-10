FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

WORKDIR /app

COPY mcp_server/pyproject.toml mcp_server/poetry.lock* /app/mcp_server/
RUN cd /app/mcp_server && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

COPY voice/pyproject.toml voice/poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

COPY voice/ .
COPY mcp_server/ /app/mcp_server/

ENV MCP_SERVER_PATH=/app/mcp_server/server.py

CMD ["python", "main.py"]
