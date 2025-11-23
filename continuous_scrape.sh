#!/bin/bash
# Continuous scraping script that commits in batches

BATCH_SIZE=300
BATCHES_PER_COMMIT=4
START_BATCH=13

batch_num=$START_BATCH
commit_counter=0
cases_since_commit=0

echo "=== CONTINUOUS SCRAPING STARTED ==="
echo "Start time: $(date)"
echo "Batch size: $BATCH_SIZE cases"
echo "Commit frequency: every $BATCHES_PER_COMMIT batches"
echo ""

while true; do
    echo "----------------------------------------"
    echo "Batch $batch_num - $(date +%H:%M:%S)"
    echo "----------------------------------------"
    
    # Run scraper
    python3 scrape_discovered_cases.py RESTRUCTURED_DB $BATCH_SIZE 2>&1 | tee batch${batch_num}_log.txt | grep -E "(Successfully scraped|Failed|Success rate)"
    
    # Extract scraped count
    scraped=$(grep "Successfully scraped:" batch${batch_num}_log.txt | tail -1 | awk '{print $3}')
    
    if [ -z "$scraped" ]; then
        scraped=0
    fi
    
    echo "→ Scraped: $scraped cases"
    
    cases_since_commit=$((cases_since_commit + scraped))
    batch_num=$((batch_num + 1))
    commit_counter=$((commit_counter + 1))
    
    # Check if we should commit
    if [ $commit_counter -ge $BATCHES_PER_COMMIT ] && [ $cases_since_commit -gt 0 ]; then
        echo ""
        echo "=== TIME TO COMMIT ==="
        echo "Cases scraped since last commit: $cases_since_commit"
        echo "Next batch will be: $batch_num"
        echo "======================="
        break
    fi
    
    # If no cases scraped in multiple batches, we might be done
    if [ $scraped -eq 0 ]; then
        zero_count=$((zero_count + 1))
        if [ $zero_count -ge 3 ]; then
            echo ""
            echo "=== NO MORE CASES AVAILABLE ==="
            echo "Stopping after 3 consecutive empty batches"
            break
        fi
    else
        zero_count=0
    fi
    
    sleep 2
done

echo ""
echo "Batch group completed at $(date)"
echo "Total cases in this commit: $cases_since_commit"
