# Prudeus Database - Philippine Supreme Court Cases

This repository contains Philippine Supreme Court case decisions from 1996-2025, with tools to expand coverage back to 1901.

## Database Statistics

- **Current Coverage**: 1996-2025 (30 years)
- **Total Cases**: ~9,282 cases
- **Format**: JSON files organized by year/month
- **Source**: Various legal databases

## Adding Historical Cases (1901-1995)

Due to network restrictions in automated environments, historical cases from lawphil.net must be scraped locally. This repository includes a complete toolkit for this purpose.

### Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the batch scraper (recommended):**
   ```bash
   python batch_scraper.py --start-year 1901 --end-year 1995 --output-dir RESTRUCTURED_DB
   ```

3. **Validate the results:**
   ```bash
   python validate_cases.py --directory RESTRUCTURED_DB --start-year 1901 --end-year 1995
   ```

4. **Update the case index:**
   ```bash
   python update_index.py --directory RESTRUCTURED_DB
   ```

### Available Tools

| Tool | Purpose |
|------|---------|
| `batch_scraper.py` | Scrape with progress tracking and resume capability ⭐ |
| `scraper.py` | Direct scraper for specific year ranges |
| `validate_cases.py` | Validate all cases have complete metadata |
| `update_index.py` | Update case_index.json with new cases |
| `generate_samples.py` | Create example cases showing correct format |

### Documentation

- 📖 **[QUICK_START.md](QUICK_START.md)** - Step-by-step guide to scraping
- 📚 **[SCRAPING_INSTRUCTIONS.md](SCRAPING_INSTRUCTIONS.md)** - Comprehensive documentation
- 📋 **[requirements.txt](requirements.txt)** - Python dependencies

### Features

✅ **Complete Metadata** - All required fields populated, no null values (except division/decision_date)  
✅ **Auto-Categorization** - Cases automatically classified into 10 legal categories  
✅ **Keyword Extraction** - Keywords automatically extracted from case content  
✅ **Progress Tracking** - Resume scraping after interruptions  
✅ **Validation** - Comprehensive validation of all cases  
✅ **Proper Formatting** - Preserves original case text formatting from source  

## Database Schema

Each case is stored as a JSON file with the following structure:

```json
{
  "file_path": "string",
  "filename": "string",
  "year": "integer",
  "month": "string (name or number)",
  "case_number": "string",
  "gr_number": "string",
  "volume_page": "string",
  "decision_date": "string (nullable)",
  "title": "string",
  "division": "string (nullable)",
  "categories": ["array of strings"],
  "keywords": ["array of strings"],
  "title_summary": "string",
  "formatted_case_content": "string (full case text)",
  "content_length": "integer",
  "metadata_extraction_date": "string (ISO 8601)",
  "extraction_version": "string"
}
```

### Directory Structure

```
RESTRUCTURED_DB/
├── 1996/
│   ├── january/
│   │   ├── 111401.json
│   │   └── ...
│   ├── february/
│   └── ...
├── 1997/
├── ...
├── 2025/
└── case_index.json
```

## Case Categories

Cases are automatically classified into these categories:

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

## Performance

- **Scraping Speed**: 2-3 seconds per case
- **Historical Cases (1901-1995)**: Estimated 60-90 hours total
- **Batch Processing**: Recommended to run decade by decade
- **Resume Capability**: Can be interrupted and resumed at any time

## Validation

All cases are validated to ensure:

- ✓ All required fields present
- ✓ No null values in required fields
- ✓ Proper data types (year is integer, categories/keywords are arrays)
- ✓ Valid month names or numbers
- ✓ Content length matches actual content
- ✓ Proper file organization

## Contributing

When scraping historical cases:

1. Run validation: `python validate_cases.py --directory RESTRUCTURED_DB`
2. Fix any validation errors
3. Update the index: `python update_index.py --directory RESTRUCTURED_DB`
4. Commit in batches (e.g., by decade): `git add RESTRUCTURED_DB/1901 && git commit`
5. Submit pull request with summary statistics

## Testing

Generate sample cases to test the workflow:

```bash
python generate_samples.py
python validate_cases.py --directory SAMPLE_CASES
```

## Troubleshooting

### Connection Issues
- Increase delay between requests: `--delay 3.0`
- Check internet connection
- Verify lawphil.net is accessible

### Missing Metadata
- Review case HTML on lawphil.net manually
- Update parsing logic in scraper.py if needed
- Some very old cases may have incomplete information

### Validation Errors
- Review specific error messages
- Fix issues manually if needed
- Re-run validation to confirm fixes

## Support

For issues or questions:
1. Check the documentation in `SCRAPING_INSTRUCTIONS.md`
2. Review error messages from scraper or validator
3. Examine sample cases to understand the structure
4. Update parsing logic if needed

## License

This database is for educational and research purposes. Case decisions are public domain, but please respect the source attribution requirements.

## Acknowledgments

- Case data sourced from lawphil.net and other legal databases
- Schema designed to support legal research and analysis
- Tools created to facilitate database expansion
