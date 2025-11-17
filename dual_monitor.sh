#!/bin/bash
# Monitor both parallel scrapers
REPO_DIR="/home/runner/work/Prudeus-Database/Prudeus-Database"
cd "$REPO_DIR"

echo "=== DUAL SCRAPER MONITORING ==="
echo "Started: $(date)"
echo ""

# Get PIDs
SCRAPER1_PID=$(cat scraper1.pid 2>/dev/null || echo "")
SCRAPER2_PID=$(cat scraper2.pid 2>/dev/null || echo "")

echo "Scraper 1 (1960-1977): PID $SCRAPER1_PID"
echo "Scraper 2 (1978-1995): PID $SCRAPER2_PID"
echo ""

# Check if both are running
if [ -n "$SCRAPER1_PID" ] && ps -p "$SCRAPER1_PID" > /dev/null 2>&1; then
    echo "✅ Scraper 1 is running"
else
    echo "❌ Scraper 1 is not running"
fi

if [ -n "$SCRAPER2_PID" ] && ps -p "$SCRAPER2_PID" > /dev/null 2>&1; then
    echo "✅ Scraper 2 is running"
else
    echo "❌ Scraper 2 is not running"
fi

echo ""
echo "=== Progress Summary ==="

# Scraper 1 progress
if [ -f scraping_progress_1960-1977.json ]; then
    echo "--- Scraper 1 (1960-1977) ---"
    cat scraping_progress_1960-1977.json | python3 -m json.tool 2>/dev/null || cat scraping_progress_1960-1977.json
fi

# Scraper 2 progress
if [ -f scraping_progress_1978-1995.json ]; then
    echo ""
    echo "--- Scraper 2 (1978-1995) ---"
    cat scraping_progress_1978-1995.json | python3 -m json.tool 2>/dev/null || cat scraping_progress_1978-1995.json
fi

echo ""
echo "=== Recent Activity ==="
echo "--- Scraper 1 Last 10 Lines ---"
tail -10 scraper1.log 2>/dev/null || echo "No log yet"

echo ""
echo "--- Scraper 2 Last 10 Lines ---"
tail -10 scraper2.log 2>/dev/null || echo "No log yet"

echo ""
echo "=== Database Statistics ==="
TOTAL_CASES=$(find RESTRUCTURED_DB -name "*.json" 2>/dev/null | wc -l)
REPO_SIZE=$(du -sh . 2>/dev/null | awk '{print $1}')
echo "Total cases in database: $TOTAL_CASES"
echo "Repository size: $REPO_SIZE"
