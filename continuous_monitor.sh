#!/bin/bash
# Continuous monitoring and progress reporting for quad scrapers
# This script monitors all 4 scrapers and provides periodic updates

cd /home/runner/work/Prudeus-Database/Prudeus-Database

# Configuration
CHECK_INTERVAL=180  # Check every 3 minutes
REPORT_INTERVAL=600  # Report to user every 10 minutes

echo "=============================================="
echo "  CONTINUOUS QUAD SCRAPER MONITORING"
echo "=============================================="
echo "Check interval: ${CHECK_INTERVAL} seconds (3 minutes)"
echo "Report interval: ${REPORT_INTERVAL} seconds (10 minutes)"
echo ""

iteration=0
last_report_time=$(date +%s)

while true; do
  iteration=$((iteration + 1))
  current_time=$(date +%s)
  elapsed_since_report=$((current_time - last_report_time))
  
  echo ""
  echo "=== Iteration $iteration - $(date) ==="
  
  # Check if all scrapers are still running
  running_count=0
  for i in {1..4}; do
    if [ -f "scraper${i}.pid" ]; then
      PID=$(cat "scraper${i}.pid" 2>/dev/null)
      if ps -p "$PID" > /dev/null 2>&1; then
        running_count=$((running_count + 1))
      else
        echo "⚠️  WARNING: Scraper $i (PID $PID) is NOT running!"
      fi
    fi
  done
  
  if [ $running_count -eq 0 ]; then
    echo ""
    echo "🎉 ALL SCRAPERS HAVE COMPLETED!"
    echo ""
    ./quad_monitor.sh
    break
  fi
  
  echo "✅ $running_count scraper(s) still running"
  
  # Get current stats
  TOTAL_CASES=$(find RESTRUCTURED_DB -name '*.json' 2>/dev/null | wc -l)
  REPO_SIZE=$(du -sh . 2>/dev/null | awk '{print $1}')
  
  echo "📊 Current stats:"
  echo "   Total cases: $TOTAL_CASES"
  echo "   Repository size: $REPO_SIZE"
  
  # Show progress from each scraper
  echo ""
  echo "📈 Individual scraper progress:"
  for f in scraping_progress_1960-1968.json scraping_progress_1969-1977.json scraping_progress_1978-1986.json scraping_progress_1987-1995.json; do
    if [ -f "$f" ]; then
      SCRAPER_CASES=$(cat $f | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('total_cases_scraped', 0))" 2>/dev/null)
      CURRENT_YEAR=$(cat $f | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('current_year', 'N/A'))" 2>/dev/null)
      echo "   $f: $SCRAPER_CASES cases (year: $CURRENT_YEAR)"
    fi
  done
  
  # Provide detailed report every REPORT_INTERVAL
  if [ $elapsed_since_report -ge $REPORT_INTERVAL ]; then
    echo ""
    echo "=== DETAILED STATUS REPORT ==="
    ./quad_monitor.sh
    last_report_time=$(date +%s)
  fi
  
  # Wait before next check
  echo ""
  echo "⏱️  Waiting ${CHECK_INTERVAL} seconds until next check..."
  sleep $CHECK_INTERVAL
done

echo ""
echo "=============================================="
echo "  MONITORING COMPLETE"
echo "=============================================="
echo ""
echo "Final status:"
./quad_monitor.sh
