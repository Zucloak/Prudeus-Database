# Instructions for Adding Historical Cases (1901-1995)

## Overview
This document provides instructions for adding historical Philippine Supreme Court cases from lawphil.net to the Prudeus Database. Due to network restrictions in the automated environment, this process requires manual execution.

## Approach Options

### Option 1: Run Scraper Locally (Recommended)

The provided `scraper.py` script automates the entire process of downloading and formatting cases from lawphil.net.

#### Prerequisites
```bash
pip install requests beautifulsoup4
```

#### Usage

**Scrape all years from 1901-1995:**
```bash
python scraper.py --start-year 1901 --end-year 1995 --start-month august --output-dir RESTRUCTURED_DB
```

**Scrape a specific year:**
```bash
python scraper.py --year 1901 --start-month august --output-dir RESTRUCTURED_DB
```

**Scrape with custom delay (to be respectful to the server):**
```bash
python scraper.py --start-year 1901 --end-year 1995 --delay 2.0 --output-dir RESTRUCTURED_DB
```

#### What the scraper does:
1. Navigates to lawphil.net case listings for each year/month
2. Extracts case links from listing pages
3. Downloads each case HTML
4. Parses and extracts metadata:
   - Case number (G.R., A.C., A.M., etc.)
   - Decision date
   - Volume and page references
   - Case title and parties
   - Division (First, Second, Third, En Banc)
   - Categories (automatically classified)
   - Keywords (extracted from content)
5. Formats content to match existing database style
6. Saves each case as a JSON file in `RESTRUCTURED_DB/{year}/{month}/{case}.json`

#### Expected Output Structure
```
RESTRUCTURED_DB/
├── 1901/
│   ├── august/
│   │   ├── G_R__No__1.json
│   │   ├── G_R__No__2.json
│   │   └── ...
│   ├── september/
│   └── ...
├── 1902/
│   ├── january/
│   └── ...
└── ...
```

### Option 2: Manual Download and Process

If the scraper doesn't work perfectly, you can manually download cases and process them:

1. **Download cases manually from lawphil.net**
   - Visit: https://lawphil.net/judjuris/juri1901/aug1901/aug1901.html
   - Save individual case HTML files

2. **Use the case processor script** (to be created)
   ```bash
   python process_cases.py --input-dir downloaded_cases --output-dir RESTRUCTURED_DB
   ```

### Option 3: Import from Alternative Sources

If you have cases in a different format (PDF, DOC, CSV), create a converter script following the schema requirements.

## Database Schema Requirements

Each case JSON file must contain ALL of the following fields with NO null values:

### Required Metadata Fields
```json
{
  "file_path": "string - original file path",
  "filename": "string - filename with extension",
  "year": "integer - year of decision",
  "month": "string - month name (lowercase)",
  "case_number": "string - full case number (e.g., 'G.R. No. 123456')",
  "gr_number": "string - numeric part only (e.g., '123456')",
  "volume_page": "string - volume and page reference (e.g., '331 Phil. 590')",
  "decision_date": "string - full date (e.g., 'October 17, 1996')",
  "title": "string - full case title with parties",
  "division": "string or null - court division (First Division, En Banc, etc.)",
  "categories": ["array of strings - legal categories"],
  "keywords": ["array of strings - extracted keywords"],
  "title_summary": "string - truncated title (max 100 chars)",
  "formatted_case_content": "string - full formatted case text",
  "content_length": "integer - length of formatted content",
  "metadata_extraction_date": "string - ISO 8601 timestamp",
  "extraction_version": "string - version identifier (e.g., '2.0_enhanced_full_content')"
}
```

### Category Options
Common categories to use:
- Civil Law
- Criminal Law
- Labor Law
- Commercial Law
- Tax Law
- Administrative Law
- Constitutional Law
- Family Law
- Property Law
- Remedial Law

### Division Options
- First Division
- Second Division
- Third Division
- En Banc
- null (if not specified)

## Validation

After scraping, validate the data:

```bash
python validate_cases.py --directory RESTRUCTURED_DB --start-year 1901 --end-year 1995
```

This will check:
- ✓ All required fields are present
- ✓ No null values in required fields
- ✓ Proper file organization (year/month structure)
- ✓ Valid JSON syntax
- ✓ Content length matches actual content
- ✓ Dates are properly formatted

## Performance Considerations

### Scraping Speed
- Estimated time per case: 2-3 seconds
- Estimated cases per year: 100-300 (varies by year)
- Total estimated time: 
  - 1901-1920: ~8-12 hours
  - 1921-1950: ~15-25 hours
  - 1951-1995: ~35-50 hours
  - **Total: 60-90 hours** (2.5-4 days continuous)

### Recommendations
1. Run overnight or over multiple days
2. Start with recent years (more complete data)
3. Use `--delay 2.0` to be respectful to lawphil.net
4. Monitor progress and resume if interrupted
5. Validate data periodically during scraping

## Resuming Interrupted Scraping

The scraper creates files as it goes. To resume:

1. Check which years/months are already completed
2. Run scraper starting from the next month/year:
   ```bash
   python scraper.py --start-year 1905 --start-month march --end-year 1995
   ```

## Troubleshooting

### Common Issues

**Issue: Connection errors or timeouts**
- Solution: Increase delay between requests (`--delay 3.0`)
- Solution: Check internet connection
- Solution: Verify lawphil.net is accessible

**Issue: Missing metadata fields**
- Solution: Review the case HTML structure
- Solution: Update parsing logic in scraper.py
- Solution: Manually fill in missing data

**Issue: Incorrect date parsing**
- Solution: Check date format in source
- Solution: Add date pattern to `extract_decision_date()` method

**Issue: Categories not assigned**
- Solution: Review keyword matching in `categorize_case()`
- Solution: Manually categorize edge cases

## Post-Processing

After scraping, you may need to:

1. **Update case_index.json**
   ```bash
   python update_index.py --directory RESTRUCTURED_DB
   ```

2. **Generate validation report**
   ```bash
   python generate_validation_report.py --directory RESTRUCTURED_DB
   ```

3. **Fix any cases with issues**
   - Review validation report
   - Manually correct problematic cases
   - Re-run validation

## Testing Before Full Run

Test the scraper on a single year first:

```bash
# Test with just 1901
python scraper.py --year 1901 --start-month august --output-dir TEST_OUTPUT

# Verify the output
ls -R TEST_OUTPUT/1901/

# Check a sample case
cat TEST_OUTPUT/1901/august/G_R__No__1.json | python -m json.tool
```

## Contributing Back

Once cases are scraped and validated:

1. Commit the new cases to the repository
2. Update the main README with new date range
3. Submit a pull request with:
   - Case count summary
   - Years covered
   - Any issues encountered
   - Validation report summary

## Support

If you encounter issues:
1. Check the error message carefully
2. Review the lawphil.net HTML structure
3. Update the scraper's parsing logic
4. Document any changes made

## Future Improvements

Potential enhancements to the scraper:
- [ ] Parallel processing for faster scraping
- [ ] Better error recovery and retry logic
- [ ] Progress tracking and persistence
- [ ] Automatic duplicate detection
- [ ] Enhanced metadata extraction using NLP
- [ ] PDF export functionality
- [ ] Search index generation
