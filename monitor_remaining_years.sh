#!/bin/bash
# Monitor 4 parallel scrapers for remaining years 1992-1995

echo "=============================================="
echo "  REMAINING YEARS SCRAPING DASHBOARD"
echo "=============================================="
echo "Started: $(date)"
echo ""

# Check scraper processes
echo "--- SCRAPER STATUS ---"
for i in {5..8}; do
  if [ -f "scraper${i}.pid" ]; then
    PID=$(cat "scraper${i}.pid" 2>/dev/null)
    if ps -p "$PID" > /dev/null 2>&1; then
      echo "✅ Scraper $i (PID $PID) is RUNNING"
    else
      echo "❌ Scraper $i (PID $PID) is NOT RUNNING"
    fi
  else
    echo "⚪ Scraper $i - No PID file found"
  fi
done

echo ""
echo "--- PROGRESS FILES ---"

# 1992 progress
if [ -f "scraping_progress_1992.json" ]; then
  echo ""
  echo "📊 1992 Progress:"
  cat scraping_progress_1992.json | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  Completed months: {', '.join(data.get('completed_months', []))}\"[:100])
    print(f\"  Total cases: {data.get('total_cases_scraped', 0)}\")
    print(f\"  Last updated: {data.get('last_updated', 'N/A')}\")
except Exception as e:
    print(f\"  Error reading file: {e}\")
"
fi

# 1993 progress
if [ -f "scraping_progress_1993.json" ]; then
  echo ""
  echo "📊 1993 Progress:"
  cat scraping_progress_1993.json | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  Completed months: {', '.join(data.get('completed_months', []))}\"[:100])
    print(f\"  Total cases: {data.get('total_cases_scraped', 0)}\")
    print(f\"  Last updated: {data.get('last_updated', 'N/A')}\")
except Exception as e:
    print(f\"  Error reading file: {e}\")
"
fi

# 1994 progress
if [ -f "scraping_progress_1994.json" ]; then
  echo ""
  echo "📊 1994 Progress:"
  cat scraping_progress_1994.json | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  Completed months: {', '.join(data.get('completed_months', []))}\"[:100])
    print(f\"  Total cases: {data.get('total_cases_scraped', 0)}\")
    print(f\"  Last updated: {data.get('last_updated', 'N/A')}\")
except Exception as e:
    print(f\"  Error reading file: {e}\")
"
fi

# 1995 progress
if [ -f "scraping_progress_1995.json" ]; then
  echo ""
  echo "📊 1995 Progress:"
  cat scraping_progress_1995.json | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  Completed months: {', '.join(data.get('completed_months', []))}\"[:100])
    print(f\"  Total cases: {data.get('total_cases_scraped', 0)}\")
    print(f\"  Last updated: {data.get('last_updated', 'N/A')}\")
except Exception as e:
    print(f\"  Error reading file: {e}\")
"
fi

echo ""
echo "--- OVERALL STATISTICS ---"
TOTAL_CASES=$(find RESTRUCTURED_DB -name '*.json' 2>/dev/null | wc -l)
REPO_SIZE=$(du -sh . 2>/dev/null | awk '{print $1}')
echo "Total cases in database: $TOTAL_CASES"
echo "Repository size: $REPO_SIZE"

echo ""
echo "--- RECENT LOG ACTIVITY ---"
for i in {5..8}; do
  if [ -f "scraper${i}.log" ]; then
    echo ""
    echo "📝 Scraper $i (last 3 lines):"
    tail -n 3 "scraper${i}.log" 2>/dev/null | sed 's/^/    /'
  fi
done

echo ""
echo "=============================================="
echo "Monitoring complete: $(date)"
echo "=============================================="
