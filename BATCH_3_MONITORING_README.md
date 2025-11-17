# Batch 3 Scraping - Monitoring Guide

## Current Status

**Status**: ✅ RUNNING  
**Started**: November 17, 2025 at 06:52 UTC  
**Target**: Years 1960-1995 (36 years)  
**Expected Duration**: 6-8 hours  
**Expected Completion**: ~14:00-15:00 UTC

## Active Processes

1. **Scraper** (PID in `scraper.pid`)
   - Command: `python3 batch_scraper.py --start-year 1960 --end-year 1995 --batch-name "Batch 3"`
   - Output: `batch3_scraper.log`

2. **Continuous Monitor** (PID in `monitor.pid`)
   - Command: `./batch3_continuous_monitor.sh`
   - Output: `batch3_monitor.log`
   - Auto-commits every 30 minutes

## Quick Status Check

```bash
# Quick progress check
./batch3_monitor.sh

# View live log
tail -f batch3_scraper.log

# Check if processes are running
ps aux | grep -E "(batch3_continuous|batch_scraper)" | grep -v grep

# View progress JSON
cat scraping_progress.json | python3 -m json.tool
```

## Progress Tracking

The scraper saves progress in `scraping_progress.json`:
- `total_cases_scraped`: Total number of cases scraped
- `current_year`: Year currently being processed
- `completed_years`: List of completed years
- `completed_months`: Months completed in current year
- `last_updated`: Timestamp of last update

## Automatic Commits

The continuous monitor automatically commits progress every 30 minutes. You can also manually commit at any time:

```bash
./batch3_commit.sh
```

## What to Expect

### Timeline (Estimated)
- **1960s** (1960-1969): ~2,300 cases, ~1.5 hours
- **1970s** (1970-1979): ~2,300 cases, ~1.5 hours
- **1980s** (1980-1989): ~2,300 cases, ~1.5 hours
- **1990-1995**: ~1,380 cases, ~1 hour
- **Total**: 36 years, ~8,280 cases, ~6 hours

### Repository Size
- **Starting**: 796MB (after cleanup)
- **Current**: ~803MB (increasing)
- **Expected Final**: ~1,030MB (~1.01GB)

### Progress Indicators
- 🧀 "cheese" printed after each year completes
- 🍝 "macaroni - Batch 3 COMPLETE!" when all done

## Checkpoints

Monitor at these milestones:
- **1965**: ~825-850MB (✅ OK if < 900MB)
- **1975**: ~900-950MB (⚠️ Monitor if > 900MB)
- **1985**: ~975-1000MB (🛑 Consider stopping if > 1000MB)
- **1995**: ~1030-1050MB (🎯 Target)

## If Something Goes Wrong

### Scraper Stopped
The scraper saves progress automatically. Resume with:
```bash
python3 batch_scraper.py --resume --start-year 1960 --end-year 1995 --batch-name "Batch 3"
```

### Check for Errors
```bash
# View log file
cat batch3_scraper.log

# Check last 50 lines
tail -50 batch3_scraper.log

# Search for errors
grep -i error batch3_scraper.log
```

### Restart Monitoring
```bash
# Kill old monitor
kill $(cat monitor.pid)

# Start new monitor
nohup ./batch3_continuous_monitor.sh > batch3_monitor.log 2>&1 &
echo $! > monitor.pid
```

## After Completion

When scraping finishes (all 36 years complete):

1. **Validate the data**:
   ```bash
   python3 validate_cases.py --directory RESTRUCTURED_DB --start-year 1960 --end-year 1995
   ```

2. **Update the index**:
   ```bash
   python3 update_index.py --directory RESTRUCTURED_DB
   ```

3. **Check final size**:
   ```bash
   du -sh .
   du -sh RESTRUCTURED_DB
   ```

4. **Final commit** (if not auto-committed):
   ```bash
   ./batch3_commit.sh
   ```

## Files Created

- `batch3_scraper.log` - Scraper output log
- `batch3_monitor.log` - Monitor output log
- `scraping_progress.json` - Progress tracking data
- `scraper.pid` - Scraper process ID
- `monitor.pid` - Monitor process ID
- `batch3_monitor.sh` - Manual progress check script
- `batch3_commit.sh` - Manual commit script
- `batch3_continuous_monitor.sh` - Continuous monitoring script

## Notes

- The scraper uses a 2-second delay between requests to be respectful to lawphil.net
- Progress is saved after each month, so interruptions are safe
- The continuous monitor checks every 5 minutes and commits every 30 minutes
- All processes run in the background and persist across session disconnects
