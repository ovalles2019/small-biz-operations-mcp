FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SMALL_BIZ_OPS_DATA=/data \
    SMALL_BIZ_OPS_DEMO=1

RUN mkdir -p /data

COPY pyproject.toml README.md ./
COPY small_biz_ops_mcp ./small_biz_ops_mcp

RUN pip install --no-cache-dir -e ".[web]"

EXPOSE 10000

CMD ["small-biz-ops-ui"]
