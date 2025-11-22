# User Guide - Title Extraction and Case Scraping Tools

## Overview

This guide explains how to use the tools created for fixing case titles and scraping missing cases from lawphil.net.

## Tools Included

1. **fix_remaining_titles_enhanced.py** - Automated title extraction
2. **scrape_missing_cases_lawphil.py** - Web scraper for missing cases

---

## Tool 1: Enhanced Title Extraction

### Purpose
Automatically extracts and fixes case titles from case content for cases marked as "Untitled Case" or "Title not found".

### Usage

```bash
python3 fix_remaining_titles_enhanced.py <path_to_RESTRUCTURED_DB>
```

### Example

```bash
# Fix all cases with title issues
python3 fix_remaining_titles_enhanced.py RESTRUCTURED_DB

# Output will show:
# - Number of files found needing fixes
# - Progress updates every 100 files
# - Summary of fixes made
```

### What It Does

1. Scans all JSON files in the database
2. Identifies cases with "Untitled Case" or "Title not found"
3. Applies 11 pattern-matching algorithms to extract titles
4. Updates files with properly formatted titles
5. Generates a summary report

### Pattern Types Detected

The script recognizes these title formats:

1. **Single-line with roles**: `PARTY, COMPLAINANT, VS. PARTY, RESPONDENT`
2. **Split-line format**: Title spans multiple lines with "VS." in between
3. **Administrative cases**: `REQUEST OF...`, `IN RE:`, `RE:` formats
4. **Short "V." notation**: Using "V." instead of "VS."
5. **Multi-party cases**: Handles "ET AL." and multiple parties
6. **Clean prefixes**: Removes "HON.", "JUDGE", etc.

### Success Rate

- **Current Achievement**: 84.3% (901 out of 1,069 cases)
- **Processing Time**: ~5 minutes for 1,069 cases
- **Quality**: All extractions validated through pattern matching

### Output Example

```
================================================================================
ENHANCED TITLE EXTRACTION - Starting...
================================================================================
Database path: RESTRUCTURED_DB

Scanning for cases needing title fixes...
Found 1069 case files needing title fixes

================================================================================
PROCESSING FILES
================================================================================
  ✓ Fixed: 9209.json
    Old: Untitled Case
    New: NENITA DE GUZMAN FERGUSON vs. ATTY. SALVADOR P. RAMOS

Progress: 100/1069 files processed (85 fixed)
Progress: 200/1069 files processed (170 fixed)
...

================================================================================
SUMMARY
================================================================================
Total files checked: 1069
Files successfully fixed: 901
Files unchanged: 168
Errors: 0
================================================================================
```

---

## Tool 2: Missing Case Scraper

### Purpose
Scrapes specific missing cases from lawphil.net and adds them to the database.

### Usage

```bash
python3 scrape_missing_cases_lawphil.py <path_to_RESTRUCTURED_DB>
```

### Example

```bash
# Scrape the 8 missing cases
python3 scrape_missing_cases_lawphil.py RESTRUCTURED_DB
```

### What It Does

1. Attempts to locate each missing case on lawphil.net
2. Downloads the case HTML content
3. Extracts text and metadata
4. Formats according to database schema
5. Saves to appropriate year/month directory

### Missing Cases List

The script is configured to scrape these 8 cases:

1. Municipality of Tupi v. Faustino (G.R. No. 231896, 2019)
2. Manuel v. People (G.R. No. 165842, 2005)
3. Toyo v. Toyo (G.R. No. 213198, 2019)
4. Valeroso v. People (G.R. No. 164815, 2008)
5. San Miguel Corp. v. CIR (G.R. Nos. 257697 & 259446, 2023)
6. Otamias v. Republic (G.R. No. 189516, 2016)
7. Sanico v. Colipano (G.R. No. 209969, 2017)
8. Film Development Council v. Colon (G.R. No. 203754, 2019)

### Output Example

```
================================================================================
SCRAPING MISSING CASES FROM LAWPHIL.NET
================================================================================
Database path: RESTRUCTURED_DB
Cases to scrape: 8

================================================================================
Case: Municipality of Tupi v. Faustino (G.R. No. 231896)
================================================================================
Searching lawphil.net for G.R. No. 231896: Municipality of Tupi v. Faustino
  ✓ Found at: https://lawphil.net/juris/juri23/gr_231896.html
  ✓ Saved to: RESTRUCTURED_DB/2019/august/231896.json

[...]

================================================================================
SCRAPING SUMMARY
================================================================================
Total cases: 8
Successfully scraped: 6
Failed: 2
================================================================================
```

### Note on Manual Intervention

Some cases may not be found automatically. In such cases:
1. Search manually at https://lawphil.net
2. Note the correct URL
3. Update the `search_patterns` in the script if needed

---

## Best Practices

### Before Running Scripts

1. **Backup your database**
   ```bash
   cp -r RESTRUCTURED_DB RESTRUCTURED_DB.backup
   ```

2. **Check git status**
   ```bash
   git status
   git diff
   ```

3. **Run on a subset first** (for testing)
   - Modify script to process only a few files
   - Verify output quality
   - Then run on full database

### After Running Scripts

1. **Review changes**
   ```bash
   git status
   git diff RESTRUCTURED_DB/*/
   ```

2. **Commit in batches**
   ```bash
   # For large changes, commit in smaller groups
   git add RESTRUCTURED_DB/1901/ RESTRUCTURED_DB/1902/ ...
   git commit -m "Fix titles for cases 1901-1902"
   ```

3. **Verify data quality**
   ```bash
   # Sample check
   python3 -c "
   import json
   with open('RESTRUCTURED_DB/2024/12/9209.json') as f:
       data = json.load(f)
       print(data['title'])
   "
   ```

---

## Troubleshooting

### Issue: Script runs slowly

**Solution:**
- Expected: ~5-10 minutes for 1,000+ cases
- Ensure no other heavy processes running
- Check disk I/O performance

### Issue: Some titles not extracted

**Expected behavior:**
- ~15-20% of cases may have unusual formatting
- These require manual review
- See `TITLE_FIX_COMPLETION_REPORT.md` for details

**Solution:**
- Review remaining cases manually
- Identify new patterns
- Add patterns to script if common
- Or manually fix individual cases

### Issue: Web scraper fails

**Possible causes:**
- Network connectivity issues
- lawphil.net is down
- Case URL pattern changed

**Solution:**
1. Check internet connection
2. Try accessing lawphil.net manually
3. Update URL patterns in script
4. Manually download and format cases

### Issue: Git push fails (too large)

**Solution:**
- Already handled by batch commit strategy
- If still occurs, reduce batch size further
- Push one directory at a time

---

## Maintenance

### Periodic Tasks

1. **Monthly**: Check for new "Untitled Case" entries
   ```bash
   python3 -c "
   import json, glob
   count = 0
   for f in glob.glob('RESTRUCTURED_DB/*/*/*.json'):
       with open(f) as fp:
           if json.load(fp).get('title') == 'Untitled Case':
               count += 1
   print(f'Untitled cases: {count}')
   "
   ```

2. **Quarterly**: Run title extraction on new cases
   ```bash
   python3 fix_remaining_titles_enhanced.py RESTRUCTURED_DB
   ```

3. **As needed**: Update extraction patterns
   - Review failed extractions
   - Identify common patterns
   - Add to script

### Adding New Patterns

To add a new title extraction pattern:

1. Open `fix_remaining_titles_enhanced.py`
2. Find the `extract_title_from_content_enhanced()` function
3. Add your pattern following existing examples:

```python
# Pattern X: Your new pattern description
for i, line in enumerate(lines[:15]):
    if your_condition:
        # Extract party names
        party1 = extract_party1(line)
        party2 = extract_party2(line)
        
        if party1 and party2:
            title = f"{party1} vs. {party2}"
            candidates.append((priority, title))
```

4. Test on sample cases
5. Run on full database
6. Commit changes

---

## Support

For issues or questions:

1. Check `TITLE_FIX_COMPLETION_REPORT.md` for detailed documentation
2. Review script comments for implementation details
3. Test changes on backup database first
4. Commit changes in batches to avoid git issues

---

## Version History

- **v2.3** (2025-11-22): Enhanced extraction with 11 patterns
- **v2.2** (Previous): Title fix script  
- **v2.1** (Previous): Metadata fix script
- **v2.0** (Previous): Enhanced full content extraction

---

**Last Updated:** 2025-11-22  
**Maintainer:** Prudeus Database Team
