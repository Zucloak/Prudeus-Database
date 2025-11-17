#!/bin/bash
# Launch 4 parallel scrapers for remaining years 1992-1995
# This completes the Batch 3 scraping faster by running years in parallel

cd /home/runner/work/Prudeus-Database/Prudeus-Database

echo "=============================================="
echo "  LAUNCHING PARALLEL SCRAPERS FOR 1992-1995"
echo "=============================================="
echo ""

# Kill any existing scrapers first
echo "Checking for existing scraper processes..."
if pgrep -f "batch_scraper.py" > /dev/null; then
    echo "Found existing scrapers, stopping them..."
    pkill -f "batch_scraper.py"
    sleep 3
fi

# Clean up old log files for scrapers 5-8
for i in {5..8}; do
    if [ -f "scraper${i}.log" ]; then
        mv "scraper${i}.log" "scraper${i}.log.old"
        echo "Archived old scraper${i}.log"
    fi
done

echo ""
echo "Ensuring Python dependencies are installed..."
python3 -m pip install -q requests beautifulsoup4 lxml 2>/dev/null || true

echo ""
echo "Starting 4 scrapers in parallel for faster completion..."
echo ""

# Scraper 5: 1992 (June-December) - completes year 1992
echo "🚀 Starting Scraper 5: Year 1992 (June-December)"
nohup python3 batch_scraper.py \
    --start-year 1992 \
    --end-year 1992 \
    --batch-name "Batch 3D-1992" \
    --progress-file scraping_progress_1992.json \
    --resume \
    > scraper5.log 2>&1 &
SCRAPER5_PID=$!
echo $SCRAPER5_PID > scraper5.pid
echo "   PID: $SCRAPER5_PID (saved to scraper5.pid)"

sleep 2

# Scraper 6: 1993 (full year)
echo "🚀 Starting Scraper 6: Year 1993"
nohup python3 batch_scraper.py \
    --start-year 1993 \
    --end-year 1993 \
    --batch-name "Batch 3D-1993" \
    --progress-file scraping_progress_1993.json \
    > scraper6.log 2>&1 &
SCRAPER6_PID=$!
echo $SCRAPER6_PID > scraper6.pid
echo "   PID: $SCRAPER6_PID (saved to scraper6.pid)"

sleep 2

# Scraper 7: 1994 (full year)
echo "🚀 Starting Scraper 7: Year 1994"
nohup python3 batch_scraper.py \
    --start-year 1994 \
    --end-year 1994 \
    --batch-name "Batch 3D-1994" \
    --progress-file scraping_progress_1994.json \
    > scraper7.log 2>&1 &
SCRAPER7_PID=$!
echo $SCRAPER7_PID > scraper7.pid
echo "   PID: $SCRAPER7_PID (saved to scraper7.pid)"

sleep 2

# Scraper 8: 1995 (full year)
echo "🚀 Starting Scraper 8: Year 1995"
nohup python3 batch_scraper.py \
    --start-year 1995 \
    --end-year 1995 \
    --batch-name "Batch 3D-1995" \
    --progress-file scraping_progress_1995.json \
    > scraper8.log 2>&1 &
SCRAPER8_PID=$!
echo $SCRAPER8_PID > scraper8.pid
echo "   PID: $SCRAPER8_PID (saved to scraper8.pid)"

echo ""
echo "=============================================="
echo "  ALL 4 SCRAPERS LAUNCHED!"
echo "=============================================="
echo ""
echo "PIDs:"
echo "  Scraper 5 (1992): $SCRAPER5_PID"
echo "  Scraper 6 (1993): $SCRAPER6_PID"
echo "  Scraper 7 (1994): $SCRAPER7_PID"
echo "  Scraper 8 (1995): $SCRAPER8_PID"
echo ""
echo "Monitor progress with:"
echo "  ./monitor_remaining_years.sh"
echo ""
echo "View live logs with:"
echo "  tail -f scraper5.log scraper6.log scraper7.log scraper8.log"
echo ""
echo "Stop all scrapers with:"
echo "  pkill -f batch_scraper.py"
echo ""
