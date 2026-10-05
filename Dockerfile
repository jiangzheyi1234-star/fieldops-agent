FROM node:24-bookworm-slim AS web
WORKDIR /src/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY requirements.lock pyproject.toml ./
COPY fieldops/ ./fieldops/
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-deps --no-cache-dir . \
    && useradd --create-home --uid 10001 fieldops && mkdir -p data && chown -R fieldops:fieldops /app
COPY --from=web /src/web/dist ./web/dist
COPY evaluation/results/summary.json ./evaluation/results/summary.json
USER fieldops
EXPOSE 8765
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/meta', timeout=2)"
CMD ["uvicorn", "fieldops.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8765"]
