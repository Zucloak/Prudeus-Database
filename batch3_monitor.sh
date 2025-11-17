#!/bin/bash
# Monitor Batch 3 scraper and provide progress updates

SCRAPER_PID=$(cat scraper.pid 2>/dev/null || echo "")
REPO_DIR="/home/runner/work/Prudeus-Database/Prudeus-Database"

cd "$REPO_DIR"

echo "=== Batch 3 Monitoring Script ==="
echo "Started: $(date)"
echo "Scraper PID: $SCRAPER_PID"
echo ""

# Check if scraper is running
if [ -n "$SCRAPER_PID" ] && ps -p "$SCRAPER_PID" > /dev/null 2>&1; then
    echo "✅ Scraper is running (PID: $SCRAPER_PID)"
else
    echo "❌ Scraper is not running"
    echo "Check batch3_scraper.log for details"
    exit 1
fi

# Display current progress
echo ""
echo "=== Current Progress ==="
if [ -f scraping_progress.json ]; then
    echo "Progress file found:"
    cat scraping_progress.json | python3 -m json.tool 2>/dev/null || cat scraping_progress.json
    
    # Extract key metrics
    TOTAL_CASES=$(python3 -c "import json; f=open('scraping_progress.json'); d=json.load(f); print(d.get('total_cases_scraped', 0))" 2>/dev/null || echo "0")
    CURRENT_YEAR=$(python3 -c "import json; f=open('scraping_progress.json'); d=json.load(f); print(d.get('current_year', 'N/A'))" 2>/dev/null || echo "N/A")
    COMPLETED_YEARS=$(python3 -c "import json; f=open('scraping_progress.json'); d=json.load(f); print(len(d.get('completed_years', [])))" 2>/dev/null || echo "0")
    
    echo ""
    echo "Summary:"
    echo "  Total cases scraped: $TOTAL_CASES"
    echo "  Current year: $CURRENT_YEAR"
    echo "  Completed years: $COMPLETED_YEARS"
else
    echo "No progress file found yet"
fi

# Count cases in database
echo ""
echo "=== Database Statistics ==="
CASES_1960=$(find RESTRUCTURED_DB/1960 -name "*.json" 2>/dev/null | wc -l)
echo "Cases in 1960: $CASES_1960"

# Show repository size
echo ""
echo "=== Repository Size ==="
TOTAL_SIZE=$(du -sh . 2>/dev/null | awk '{print $1}')
DB_SIZE=$(du -sh RESTRUCTURED_DB 2>/dev/null | awk '{print $1}')
echo "Total repository: $TOTAL_SIZE"
echo "Database directory: $DB_SIZE"

# Show last few lines of log
echo ""
echo "=== Recent Log Entries (last 15 lines) ==="
if [ -f batch3_scraper.log ]; then
    tail -15 batch3_scraper.log
else
    echo "No log file found"
fi

echo ""
echo "=== Monitoring Complete ==="
echo "Run this script again to check progress"
