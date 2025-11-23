# Instructions for Continuing the Scraping Process

## Current Status

**Completed:**
- 1,189 cases scraped and committed in batches
- Database grew from ~41,375 to ~42,625 cases  
- Years covered: 2024, 2007, 2006, 2022, 2023

**Remaining:**
- ~13,621 cases in the discovery list
- Many recent 2024 cases not yet published on lawphil (will fail to scrape)
- Estimated viable cases: ~10,000-12,000
- Estimated time: ~2.5-3 hours of continuous running
- Success rate: 85-93% for older cases, 0% for very recent cases

## How to Continue

### Option 1: Run Continuously (Recommended for unattended operation)

```bash
cd /home/runner/work/Prudeus-Database/Prudeus-Database

# Run batches continuously with auto-commit every 1000 cases
for i in {1..45}; do
    echo "=== Batch Group $i ==="
    
    # Run 3 batches (900 cases)
    python3 scrape_discovered_cases.py RESTRUCTURED_DB 300
    python3 scrape_discovered_cases.py RESTRUCTURED_DB 300
    python3 scrape_discovered_cases.py RESTRUCTURED_DB 300
    
    # Commit
    git add RESTRUCTURED_DB/
    git commit -m "Batch group $i: Scraped ~900 cases"
    git push origin copilot/scrape-missing-cases-data
    
    echo "Committed batch group $i"
    sleep 5
done
```

### Option 2: Run Individual Batches (More control)

```bash
cd /home/runner/work/Prudeus-Database/Prudeus-Database

# Run single batch of 300 cases
python3 scrape_discovered_cases.py RESTRUCTURED_DB 300

# Check progress
python3 -c "import json; print(f'Remaining: {len(json.load(open(\"lawphil_missing_cases.json\")))} cases')"

# Commit when ready (every 500-1000 cases recommended)
git add RESTRUCTURED_DB/
git commit -m "Scraped additional cases"
git push origin copilot/scrape-missing-cases-data
```

### Option 3: Background Processing with tmux/screen

```bash
# Start a persistent session
tmux new -s scraping

# Run the continuous script
cd /home/runner/work/Prudeus-Database/Prudeus-Database
bash continuous_scrape.sh

# Detach: Ctrl+b then d
# Reattach later: tmux attach -t scraping
```

## File Structure

- `lawphil_missing_cases.json` - Current list of cases to scrape (updated automatically)
- `scrape_discovered_cases.py` - Main scraper (processes from beginning of list)
- `batch*.txt` - Log files from each batch
- `RESTRUCTURED_DB/YYYY/MMM/GRNUM.json` - Scraped case files

## Notes

- The scraper automatically skips cases that already exist
- Each batch of 300 cases takes ~4-5 minutes
- Rate limited to 0.5 seconds between requests
- Success rate typically 85-95% (some cases unavailable on lawphil)
- Safe to interrupt and resume anytime

## Troubleshooting

### If scraper seems stuck or finds 0 cases:

```bash
# Rebuild the missing cases list (filters out already-scraped cases)
cd /home/runner/work/Prudeus-Database/Prudeus-Database
python3 discover_additional_cases.py
```

### If getting many "Could not fetch" errors:

This is normal for very recent cases (especially 2024). Lawphil has a publishing delay of 2-3 months. The scraper will skip these and move to older cases that are available. Continue running - it will eventually reach years 2005-2021 where success rates are 90%+.

### If git push fails (too large):

```bash
# Use smaller batches
python3 scrape_discovered_cases.py RESTRUCTURED_DB 100  # Instead of 300
```

### Check database growth:

```bash
find RESTRUCTURED_DB -name "*.json" -type f | wc -l
```

## Completion

When complete, you'll have:
- ~15,000 total cases from 2005-2024 period
- Significantly improved database coverage (from 11% to ~100% of available cases)
- All cases properly categorized and indexed
