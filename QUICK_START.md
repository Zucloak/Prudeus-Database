# Quick Start Guide: Adding Historical Cases

## Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

## Step 2: Test the Scraper
Test with a single year first to make sure everything works:
```bash
python scraper.py --year 1901 --start-month august --output-dir RESTRUCTURED_DB
```

## Step 3: Validate Test Results
```bash
python validate_cases.py --directory RESTRUCTURED_DB --start-year 1901 --end-year 1901
```

If validation passes, proceed to full scraping.

## Step 4: Run Full Scrape
Scrape all historical cases from 1901-1995:
```bash
# This will take 2-4 days to complete
python scraper.py --start-year 1901 --end-year 1995 --start-month august --delay 2.0 --output-dir RESTRUCTURED_DB
```

### Recommended: Scrape in Batches
Instead of running all at once, scrape decade by decade:

```bash
# 1901-1910
python scraper.py --start-year 1901 --end-year 1910 --start-month august --delay 2.0 --output-dir RESTRUCTURED_DB

# Validate
python validate_cases.py --directory RESTRUCTURED_DB --start-year 1901 --end-year 1910

# 1911-1920
python scraper.py --start-year 1911 --end-year 1920 --delay 2.0 --output-dir RESTRUCTURED_DB

# And so on...
```

## Step 5: Final Validation
After all scraping is complete:
```bash
python validate_cases.py --directory RESTRUCTURED_DB --start-year 1901 --end-year 1995 --output validation_report.json
```

## Step 6: Commit to Repository
```bash
git add RESTRUCTURED_DB/
git commit -m "Add historical cases from 1901-1995"
git push
```

## Troubleshooting

### Scraper hangs or times out
- Increase the delay: `--delay 3.0`
- Check your internet connection
- Try scraping a smaller range

### Missing metadata
- Review the case on lawphil.net manually
- Update the scraper's parsing logic if needed
- Some very old cases may have incomplete information

### Validation errors
- Review the specific error messages
- Fix issues manually if needed
- Re-run validation to confirm fixes

## Progress Tracking

Check progress at any time:
```bash
# Count cases by year
for year in RESTRUCTURED_DB/*; do
    if [ -d "$year" ]; then
        count=$(find "$year" -name "*.json" | wc -l)
        echo "$(basename $year): $count cases"
    fi
done
```

## Resuming After Interruption

If scraping is interrupted, resume from where it stopped:
```bash
# Check what years are complete
ls RESTRUCTURED_DB/

# Resume from next year (e.g., if 1901-1905 are done, start from 1906)
python scraper.py --start-year 1906 --end-year 1995 --delay 2.0 --output-dir RESTRUCTURED_DB
```

## Best Practices

1. **Start Small**: Test with one year before running the full range
2. **Validate Often**: Run validation after each decade
3. **Be Respectful**: Use a reasonable delay (2+ seconds) between requests
4. **Monitor Progress**: Check logs periodically
5. **Backup**: Keep backups of successfully scraped data
6. **Version Control**: Commit data in batches (by decade) rather than all at once

## Expected Results

After completion, you should have:
- ~15,000-25,000 new case files
- Cases organized in `RESTRUCTURED_DB/{year}/{month}/` structure
- All cases with complete metadata (no null values)
- All validation checks passing

## Need Help?

- Check `SCRAPING_INSTRUCTIONS.md` for detailed information
- Review error messages from scraper or validator
- Manually inspect a few cases to understand the data structure
- Update parsing logic in `scraper.py` if needed
