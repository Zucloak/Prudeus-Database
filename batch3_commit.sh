#!/bin/bash
# Auto-commit script for Batch 3 scraping progress
# This script commits progress periodically while the scraper runs

REPO_DIR="/home/runner/work/Prudeus-Database/Prudeus-Database"
cd "$REPO_DIR"

# Get scraper PID
SCRAPER_PID=$(cat scraper.pid 2>/dev/null || echo "")

# Check if scraper is running
if [ -z "$SCRAPER_PID" ] || ! ps -p "$SCRAPER_PID" > /dev/null 2>&1; then
    echo "Scraper not running, nothing to commit"
    exit 0
fi

# Get current progress
if [ -f scraping_progress.json ]; then
    TOTAL_CASES=$(python3 -c "import json; f=open('scraping_progress.json'); d=json.load(f); print(d.get('total_cases_scraped', 0))" 2>/dev/null || echo "0")
    CURRENT_YEAR=$(python3 -c "import json; f=open('scraping_progress.json'); d=json.load(f); print(d.get('current_year', 'N/A'))" 2>/dev/null || echo "N/A")
    COMPLETED_YEARS=$(python3 -c "import json; f=open('scraping_progress.json'); d=json.load(f); print(len(d.get('completed_years', [])))" 2>/dev/null || echo "0")
    
    echo "=== Batch 3 Progress Commit ==="
    echo "Time: $(date)"
    echo "Total cases: $TOTAL_CASES"
    echo "Current year: $CURRENT_YEAR"
    echo "Completed years: $COMPLETED_YEARS"
    
    # Stage all changes
    git add -A
    
    # Check if there are changes to commit
    if git diff --cached --quiet; then
        echo "No changes to commit"
    else
        # Commit with progress message
        git commit -m "Batch 3 progress: $TOTAL_CASES cases, processing year $CURRENT_YEAR ($COMPLETED_YEARS years complete)" || echo "Commit failed"
        echo "✅ Changes committed"
    fi
else
    echo "No progress file found"
fi
