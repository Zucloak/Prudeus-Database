#!/bin/bash
# Script to continue Batch 2 scraping (1937-1959)
# Will say "cheese" after each year and "macaroni" when batch is complete

echo "Starting Batch 2 continuation: 1937-1959"
echo "Current time: $(date)"
echo ""

python3 batch_scraper.py \
    --start-year 1937 \
    --end-year 1959 \
    --output-dir RESTRUCTURED_DB \
    --progress-file scraping_progress_batch2.json \
    --batch-name "Batch 2" \
    --resume

echo ""
echo "Batch 2 scraping completed at: $(date)"
