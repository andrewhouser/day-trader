FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py scheduler.py api.py server.py entrypoint.sh ./
COPY agents/ ./agents/
COPY core/ ./core/
COPY research/ ./research/
COPY trader/ ./trader/

RUN chmod +x entrypoint.sh

ENV TZ=America/New_York

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["api"]
