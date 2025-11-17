#!/bin/bash
# Quad Scraper Monitoring Script
# Monitors 4 parallel scrapers for Batch 3 scraping

echo "=============================================="
echo "    QUAD SCRAPER MONITORING DASHBOARD"
echo "=============================================="
echo "Started: $(date)"
echo ""

# Check scraper processes
echo "--- SCRAPER STATUS ---"
for i in {1..4}; do
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
find . -name "scraping_progress_*.json" -type f | sort | while read file; do
  echo ""
  echo "📊 $file:"
  if [ -f "$file" ]; then
    cat "$file" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"  Completed years: {len(data.get('completed_years', []))} - {data.get('completed_years', [])}\"[:100])
    print(f\"  Current year: {data.get('current_year', 'None')}\")
    print(f\"  Completed months: {', '.join(data.get('completed_months', []))}\"[:100])
    print(f\"  Total cases: {data.get('total_cases_scraped', 0)}\")
    print(f\"  Last updated: {data.get('last_updated', 'N/A')}\")
except Exception as e:
    print(f\"  Error reading file: {e}\")
"
  fi
done

echo ""
echo "--- OVERALL STATISTICS ---"
TOTAL_CASES=$(find RESTRUCTURED_DB -name '*.json' 2>/dev/null | wc -l)
REPO_SIZE=$(du -sh . 2>/dev/null | awk '{print $1}')
echo "Total cases in database: $TOTAL_CASES"
echo "Repository size: $REPO_SIZE"

# Calculate progress percentage (target: 29,000 cases)
TARGET=29000
if [ "$TOTAL_CASES" -gt 0 ]; then
  PERCENT=$(echo "scale=1; $TOTAL_CASES * 100 / $TARGET" | bc)
  echo "Progress: ${PERCENT}% of estimated ${TARGET} cases"
fi

echo ""
echo "--- RECENT LOG ACTIVITY ---"
for i in {1..4}; do
  if [ -f "scraper${i}.log" ]; then
    echo ""
    echo "📝 Scraper $i (last 5 lines):"
    tail -n 5 "scraper${i}.log" 2>/dev/null | sed 's/^/    /'
  fi
done

echo ""
echo "=============================================="
echo "Monitoring complete: $(date)"
echo "=============================================="
