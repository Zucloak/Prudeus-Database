#!/bin/bash
# Launch 4 parallel scrapers for Batch 3 scraping
# This splits the 1960-1995 range into 4 equal segments

cd /home/runner/work/Prudeus-Database/Prudeus-Database

echo "=============================================="
echo "  LAUNCHING QUAD PARALLEL SCRAPERS"
echo "=============================================="
echo ""

# Kill any existing scrapers first
echo "Checking for existing scraper processes..."
if pgrep -f "batch_scraper.py" > /dev/null; then
    echo "Found existing scrapers, stopping them..."
    pkill -f "batch_scraper.py"
    sleep 3
fi

# Clean up old log files
for i in {1..4}; do
    if [ -f "scraper${i}.log" ]; then
        mv "scraper${i}.log" "scraper${i}.log.old"
        echo "Archived old scraper${i}.log"
    fi
done

echo ""
echo "Starting 4 scrapers in parallel..."
echo ""

# Scraper 1: 1960-1968 (9 years) - resumes from May 1962
echo "🚀 Starting Scraper 1: Years 1960-1968 (Batch 3A)"
nohup python3 batch_scraper.py \
    --start-year 1960 \
    --end-year 1968 \
    --batch-name "Batch 3A" \
    --progress-file scraping_progress_1960-1968.json \
    --resume \
    > scraper1.log 2>&1 &
SCRAPER1_PID=$!
echo $SCRAPER1_PID > scraper1.pid
echo "   PID: $SCRAPER1_PID (saved to scraper1.pid)"

sleep 2

# Scraper 2: 1969-1977 (9 years) - fresh start
echo "🚀 Starting Scraper 2: Years 1969-1977 (Batch 3B)"
nohup python3 batch_scraper.py \
    --start-year 1969 \
    --end-year 1977 \
    --batch-name "Batch 3B" \
    --progress-file scraping_progress_1969-1977.json \
    > scraper2.log 2>&1 &
SCRAPER2_PID=$!
echo $SCRAPER2_PID > scraper2.pid
echo "   PID: $SCRAPER2_PID (saved to scraper2.pid)"

sleep 2

# Scraper 3: 1978-1986 (9 years) - resumes from September 1981
echo "🚀 Starting Scraper 3: Years 1978-1986 (Batch 3C)"
nohup python3 batch_scraper.py \
    --start-year 1978 \
    --end-year 1986 \
    --batch-name "Batch 3C" \
    --progress-file scraping_progress_1978-1986.json \
    --resume \
    > scraper3.log 2>&1 &
SCRAPER3_PID=$!
echo $SCRAPER3_PID > scraper3.pid
echo "   PID: $SCRAPER3_PID (saved to scraper3.pid)"

sleep 2

# Scraper 4: 1987-1995 (9 years) - fresh start
echo "🚀 Starting Scraper 4: Years 1987-1995 (Batch 3D)"
nohup python3 batch_scraper.py \
    --start-year 1987 \
    --end-year 1995 \
    --batch-name "Batch 3D" \
    --progress-file scraping_progress_1987-1995.json \
    > scraper4.log 2>&1 &
SCRAPER4_PID=$!
echo $SCRAPER4_PID > scraper4.pid
echo "   PID: $SCRAPER4_PID (saved to scraper4.pid)"

echo ""
echo "=============================================="
echo "  ALL 4 SCRAPERS LAUNCHED!"
echo "=============================================="
echo ""
echo "PIDs:"
echo "  Scraper 1: $SCRAPER1_PID"
echo "  Scraper 2: $SCRAPER2_PID"
echo "  Scraper 3: $SCRAPER3_PID"
echo "  Scraper 4: $SCRAPER4_PID"
echo ""
echo "Monitor progress with:"
echo "  ./quad_monitor.sh"
echo ""
echo "View live logs with:"
echo "  tail -f scraper1.log scraper2.log scraper3.log scraper4.log"
echo ""
echo "Stop all scrapers with:"
echo "  pkill -f batch_scraper.py"
echo ""
