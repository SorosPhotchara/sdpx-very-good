FROM mcr.microsoft.com/playwright:v1.63.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    E2E_PYTHON=/opt/paireval-venv/bin/python

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/paireval-venv
COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN /opt/paireval-venv/bin/pip install --no-cache-dir -r /tmp/backend-requirements.txt

COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci

COPY backend ./backend
COPY frontend ./frontend

CMD ["node", "frontend/e2e/run.mjs"]
