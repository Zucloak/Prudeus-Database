#!/bin/bash
# Monitor scraper progress and commit periodically

cd /home/runner/work/Prudeus-Database/Prudeus-Database

while true; do
    # Wait 10 minutes between commits
    sleep 600
    
    # Check if scraper is still running
    if ! pgrep -f "python.*batch_scraper" > /dev/null; then
        echo "Scraper not running, exiting monitor"
        exit 0
    fi
    
    # Get current progress
    if [ -f scraping_progress.json ]; then
        TOTAL_CASES=$(jq -r '.total_cases_scraped' scraping_progress.json)
        CURRENT_YEAR=$(jq -r '.current_year' scraping_progress.json)
        COMPLETED_YEARS=$(jq -r '.completed_years | length' scraping_progress.json)
        
        echo "=== Progress Update ==="
        echo "Total cases: $TOTAL_CASES"
        echo "Current year: $CURRENT_YEAR"
        echo "Completed years: $COMPLETED_YEARS"
        
        # Add and commit new cases
        git add RESTRUCTURED_DB/ scraping_progress.json
        git commit -m "Progress: $TOTAL_CASES cases, year $CURRENT_YEAR" || true
        
        echo "Committed progress"
    fi
done
