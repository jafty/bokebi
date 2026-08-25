FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system bokebi && adduser --system --ingroup bokebi bokebi
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x entrypoint.sh && chown -R bokebi:bokebi /app
USER bokebi
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
