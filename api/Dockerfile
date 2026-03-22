FROM python:3.12-slim

WORKDIR /app

# Install Node.js for Nansen CLI
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm i -g nansen-cli && \
    apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/
COPY api/ /app/api/

ENV PYTHONPATH=/app/src:/app

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8010"]
