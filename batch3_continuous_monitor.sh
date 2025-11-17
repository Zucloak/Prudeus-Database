#!/bin/bash
# Continuous monitoring and auto-commit for Batch 3 scraping
# This script runs in the background and commits progress every 30 minutes

REPO_DIR="/home/runner/work/Prudeus-Database/Prudeus-Database"
cd "$REPO_DIR"

# Commit interval in seconds (30 minutes = 1800 seconds)
COMMIT_INTERVAL=1800

# Monitor interval in seconds (5 minutes = 300 seconds)
MONITOR_INTERVAL=300

echo "=== Batch 3 Continuous Monitoring Started ==="
echo "Started at: $(date)"
echo "Commit interval: $COMMIT_INTERVAL seconds (30 minutes)"
echo "Monitor interval: $MONITOR_INTERVAL seconds (5 minutes)"
echo ""

# Track time for commits
LAST_COMMIT=$(date +%s)

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - LAST_COMMIT))
    
    # Get scraper PID
    SCRAPER_PID=$(cat scraper.pid 2>/dev/null || echo "")
    
    # Check if scraper is still running
    if [ -n "$SCRAPER_PID" ] && ps -p "$SCRAPER_PID" > /dev/null 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Scraper running (PID: $SCRAPER_PID)"
        
        # Display progress
        if [ -f scraping_progress.json ]; then
            TOTAL_CASES=$(python3 -c "import json; f=open('scraping_progress.json'); d=json.load(f); print(d.get('total_cases_scraped', 0))" 2>/dev/null || echo "0")
            CURRENT_YEAR=$(python3 -c "import json; f=open('scraping_progress.json'); d=json.load(f); print(d.get('current_year', 'N/A'))" 2>/dev/null || echo "N/A")
            COMPLETED_YEARS=$(python3 -c "import json; f=open('scraping_progress.json'); d=json.load(f); print(len(d.get('completed_years', [])))" 2>/dev/null || echo "0")
            REPO_SIZE=$(du -sh . 2>/dev/null | awk '{print $1}')
            
            echo "  Progress: $TOTAL_CASES cases | Year: $CURRENT_YEAR | Complete: $COMPLETED_YEARS years | Size: $REPO_SIZE"
        fi
        
        # Auto-commit if interval has passed
        if [ $ELAPSED -ge $COMMIT_INTERVAL ]; then
            echo "  [$(date '+%H:%M:%S')] 💾 Committing progress..."
            ./batch3_commit.sh
            LAST_COMMIT=$(date +%s)
            echo "  [$(date '+%H:%M:%S')] ✅ Commit complete"
        else
            TIME_TO_NEXT_COMMIT=$((COMMIT_INTERVAL - ELAPSED))
            MINUTES=$((TIME_TO_NEXT_COMMIT / 60))
            echo "  Next commit in: ${MINUTES} minutes"
        fi
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  Scraper not running"
        
        # Check if scraping is complete
        if [ -f scraping_progress.json ]; then
            COMPLETED_YEARS=$(python3 -c "import json; f=open('scraping_progress.json'); d=json.load(f); print(len(d.get('completed_years', [])))" 2>/dev/null || echo "0")
            
            if [ "$COMPLETED_YEARS" -ge "36" ]; then
                echo "  ✅ Scraping appears to be complete (36 years done)!"
                echo "  Running final commit..."
                ./batch3_commit.sh
                echo "  Monitoring stopped - scraping complete"
                exit 0
            else
                echo "  ⚠️  Scraping may have stopped prematurely (only $COMPLETED_YEARS years complete)"
                echo "  Check batch3_scraper.log for details"
            fi
        fi
        
        echo "  Monitoring stopped"
        exit 1
    fi
    
    # Wait before next check
    sleep $MONITOR_INTERVAL
    echo ""
done
