#!/bin/bash
# Automatically commit progress every 15 minutes while scraper runs

cd /home/runner/work/Prudeus-Database/Prudeus-Database

COUNTER=0
while true; do
    # Wait 15 minutes between commits
    sleep 900
    
    # Check if scraper is still running
    if ! pgrep -f "python.*batch_scraper" > /dev/null; then
        echo "$(date): Scraper not running, exiting auto-commit"
        break
    fi
    
    COUNTER=$((COUNTER + 1))
    
    # Get current progress
    if [ -f scraping_progress.json ]; then
        TOTAL_CASES=$(jq -r '.total_cases_scraped' scraping_progress.json)
        CURRENT_YEAR=$(jq -r '.current_year' scraping_progress.json)
        COMPLETED_YEARS=$(jq -r '.completed_years | length' scraping_progress.json)
        
        echo "$(date): Auto-commit #$COUNTER - $TOTAL_CASES cases, year $CURRENT_YEAR"
        
        # Stage changes
        git add RESTRUCTURED_DB/ scraping_progress.json SCRAPING_STATUS.md 2>/dev/null
        
        # Commit if there are changes
        if git diff --staged --quiet; then
            echo "No changes to commit"
        else
            git commit -m "Auto-progress #$COUNTER: $TOTAL_CASES cases, year $CURRENT_YEAR"
            echo "Committed successfully"
        fi
    fi
done

echo "$(date): Auto-commit loop ended"
