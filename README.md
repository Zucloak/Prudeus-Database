# Prudeus Database - Philippine Supreme Court Cases

This repository contains Philippine Supreme Court case decisions from 1901-2025, providing comprehensive legal research data.

## Database Statistics

- **Coverage**: 1901-2025 (125 years)
- **Total Cases**: ~41,578 cases
- **Format**: JSON files organized by year/month
- **Source**: Various legal databases

## Features

✅ **Complete Historical Coverage** - Cases from 1901 to 2025  
✅ **Complete Metadata** - All required fields populated, no null values (except division/decision_date)  
✅ **Auto-Categorization** - Cases classified into 10 legal categories  
✅ **Keyword Extraction** - Keywords extracted from case content  
✅ **Proper Formatting** - Preserves original case text formatting from source  

## Using the Database

The database is organized in a hierarchical structure:

```
RESTRUCTURED_DB/
├── 1901/
│   ├── january/
│   │   ├── 111401.json
│   │   └── ...
│   ├── february/
│   └── ...
├── 1902/
├── ...
├── 2025/
└── case_index.json
```

Each case file contains comprehensive metadata and the full case text. The `case_index.json` file provides a quick reference to all cases in the database.

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

## Case Categories

Cases are classified into these categories:

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

## Data Quality

All cases include:

- ✓ All required fields present
- ✓ No null values in required fields (except division/decision_date)
- ✓ Proper data types (year is integer, categories/keywords are arrays)
- ✓ Valid month names or numbers
- ✓ Content length matches actual content
- ✓ Proper file organization

## License

This database is for educational and research purposes. Case decisions are public domain, but please respect the source attribution requirements.

## Acknowledgments

- Case data sourced from lawphil.net and other legal databases
- Schema designed to support legal research and analysis
