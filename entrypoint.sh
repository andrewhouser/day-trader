#!/bin/bash
set -e

echo "Day Trader Agent - Entrypoint"
echo "Checking Ollama connectivity..."

OLLAMA_URL="${OLLAMA_BASE_URL:-http://host.docker.internal:11434}"

# Wait for Ollama to be reachable (quick check — don't block the API)
MAX_RETRIES=5
RETRY_COUNT=0
until curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "WARNING: Could not reach Ollama at ${OLLAMA_URL} after ${MAX_RETRIES} attempts"
        echo "Starting anyway — API will be available, agent tasks will fail until Ollama is reachable"
        break
    fi
    echo "Waiting for Ollama at ${OLLAMA_URL}... (attempt ${RETRY_COUNT}/${MAX_RETRIES})"
    sleep 2
done

echo "Ollama check complete"

# Ensure data directories exist
mkdir -p /app/trader/reports

# Seed portfolio.json if it doesn't exist (fresh install)
if [ ! -f /app/trader/portfolio.json ]; then
    echo '{"cash_usd":1000.00,"positions":[],"total_value_usd":1000.00,"starting_capital":1000.00,"last_updated":null,"trade_count":0,"all_time_high":1000.00,"all_time_low":1000.00}' > /app/trader/portfolio.json
    echo "Seeded default portfolio.json"
fi

# Run based on command
case "${1:-api}" in
    api)
        echo "Starting API server with background scheduler..."
        exec uvicorn server:app --host 0.0.0.0 --port 8000 --log-level info
        ;;
    scheduler)
        echo "Starting standalone scheduler (no API)..."
        exec python3 scheduler.py
        ;;
    hourly)
        echo "Running one-time hourly check..."
        exec python3 -c "from agents.agent import run_hourly_check; run_hourly_check()"
        ;;
    report)
        echo "Running one-time morning report..."
        exec python3 -c "from agents.agent import run_morning_report; run_morning_report()"
        ;;
    research)
        echo "Running one-time research cycle..."
        exec python3 -c "from agents.agent import run_research; run_research()"
        ;;
    compact)
        echo "Running one-time memory compaction..."
        exec python3 -c "from agents.compactor import run_compaction; run_compaction()"
        ;;
    sentiment)
        echo "Running one-time sentiment analysis..."
        exec python3 -c "from agents.sentiment_agent import run_sentiment; run_sentiment()"
        ;;
    risk)
        echo "Running one-time risk monitor check..."
        exec python3 -c "from agents.risk_monitor import run_risk_monitor; run_risk_monitor()"
        ;;
    rebalance)
        echo "Running one-time portfolio rebalance..."
        exec python3 -c "from agents.rebalancer import run_rebalancer; run_rebalancer()"
        ;;
    performance)
        echo "Running one-time performance analysis..."
        exec python3 -c "from agents.performance_analyst import run_performance_analysis; run_performance_analysis()"
        ;;
    events)
        echo "Running one-time events calendar update..."
        exec python3 -c "from agents.events_agent import run_events_calendar; run_events_calendar()"
        ;;
    expansion)
        echo "Running one-time portfolio expansion analysis..."
        exec python3 -c "from agents.expansion import run_expansion_analysis; run_expansion_analysis()"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Usage: entrypoint.sh [api|scheduler|hourly|report|research|compact|sentiment|risk|rebalance|performance|events]"
        exit 1
        ;;
esac
