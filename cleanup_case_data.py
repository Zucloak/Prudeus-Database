#!/usr/bin/env python3
"""
Script to clean and standardize Philippine Supreme Court case JSON files.

This script performs the following operations:
1. Standardizes JSON filenames based on case identifiers (gr_number or case_number)
2. Fixes character encoding issues (UTF-8 misinterpretations)
3. Removes redundant table text blocks
4. Extracts and populates missing title and date metadata
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Common UTF-8 encoding fixes
ENCODING_FIXES = {
    'â': "'",  # Common apostrophe misencoding
    'â€™': "'",
    'â€œ': '"',
    'â€': '"',
    'â€"': '—',
    'â€"': '–',
    'â€¢': '•',
    'Ã©': 'é',
    'Ã±': 'ñ',
    'Ã¡': 'á',
    'Ã³': 'ó',
    'Ãº': 'ú',
    'Ã': 'í',
    'Ã': 'Ñ',
}


def fix_encoding(text: str) -> str:
    """Fix common UTF-8 encoding issues in text."""
    if not isinstance(text, str):
        return text
    
    for wrong, correct in ENCODING_FIXES.items():
        text = text.replace(wrong, correct)
    
    return text


def remove_table_blocks(text: str) -> str:
    """Remove redundant table text blocks from content."""
    if not isinstance(text, str):
        return text
    
    # Remove [TABLE_CONTENT]...[END_TABLE] blocks
    text = re.sub(
        r'\[TABLE_CONTENT\].*?\[END_TABLE\]',
        '',
        text,
        flags=re.DOTALL
    )
    
    return text


def extract_title(text: str) -> Optional[str]:
    """
    Extract title from case text.
    Looks for case party names (plaintiff vs. defendant pattern).
    """
    if not isinstance(text, str) or not text.strip():
        return None
    
    # First, try to find a simple one-line case title
    lines = [l.strip() for l in text.strip().split('\n')]
    
    # Look for single-line titles with "vs." in the first 100 lines
    for i, line in enumerate(lines[:100]):
        if not line or len(line) < 20:
            continue
            
        # Simple case: line contains "vs." directly with substantial content
        if (' vs. ' in line.lower() or ' v. ' in line.lower()):
            # Skip lines that seem to be references or citations
            if re.search(r'CA-G\.R\.|G\.R\. No\.|Case No\.|Docket|L-\d+|See\s+', line, re.IGNORECASE):
                continue
            if re.search(r'\d{4},\s+\d+\s+SCRA', line):  # Skip citations like "1973, 54 SCRA"
                continue
                
            title = line
            # Remove common trailing phrases that are roles
            title = re.sub(r',?\s*(PETITIONER|RESPONDENT|DEFENDANT|PLAINTIFF|ACCUSED|APPELLANT).*$', '', title, flags=re.IGNORECASE)
            # Clean up excess whitespace
            title = re.sub(r'\s+', ' ', title).strip()
            if len(title) > 200:
                title = title[:197] + '...'
            if len(title) > 20:  # Ensure it's substantial
                return title
    
    # Multi-line case title extraction
    # Look for pattern:
    # PARTY NAME,
    # [role description],
    # vs.
    # PARTY NAME,
    # [role description].
    
    for i in range(min(100, len(lines))):
        line = lines[i]
        
        # Skip empty lines
        if not line:
            continue
        
        # Check if this looks like a case party (all caps or title case with comma)
        # Must not be a section header or G.R. reference
        if re.search(r'G\.R\.\s*No\.|DECISION|RESOLUTION|OPINION', line, re.IGNORECASE):
            continue
        
        # Look for a line that ends with comma and looks like a name (contains caps)
        if ',' in line and re.search(r'[A-Z]{2,}', line):
            # This might be a plaintiff/petitioner
            plaintiff = line.rstrip(',').strip()
            
            # Look ahead for "vs." within next 5 non-empty lines
            j = i + 1
            found_vs_idx = -1
            while j < min(i + 6, len(lines)):
                if lines[j].strip().lower() in ['vs.', 'vs', 'v.', 'v']:
                    found_vs_idx = j
                    break
                # Skip role description lines
                if lines[j].strip() and not re.match(r'^\s*(plaintiff|petitioner|appellee|appellant|respondent|defendant|accused)[-,\s]*(plaintiff|petitioner|appellee|appellant|respondent|defendant|accused)?[,\s-]*\.?$', lines[j].strip(), re.IGNORECASE):
                    # Not a role line and not empty, so not part of title structure
                    break
                j += 1
            
            if found_vs_idx > 0:
                # Found "vs.", now look for defendant in next few lines
                j = found_vs_idx + 1
                defendant = None
                
                while j < min(found_vs_idx + 6, len(lines)):
                    curr = lines[j].strip()
                    if not curr:
                        j += 1
                        continue
                    
                    # Skip role-only lines
                    if re.match(r'^\s*(plaintiff|petitioner|appellee|appellant|respondent|defendant|accused)[-,\s]*(plaintiff|petitioner|appellee|appellant|respondent|defendant|accused)?[,\s-]*\.?$', curr, re.IGNORECASE):
                        j += 1
                        continue
                    
                    # This should be the defendant line
                    if ',' in curr or re.search(r'[A-Z]{2,}', curr):
                        # Remove trailing role descriptions
                        defendant = re.sub(r',?\s*(defendants?|respondents?|appellants?|accused).*$', '', curr, flags=re.IGNORECASE).strip(' ,.')
                        break
                    j += 1
                
                if defendant and plaintiff:
                    # Clean up names
                    plaintiff = plaintiff.strip(' ,.')
                    defendant = defendant.strip(' ,.')
                    
                    # Make sure they're substantial
                    if len(plaintiff) > 5 and len(defendant) > 5:
                        title = f"{plaintiff} vs. {defendant}"
                        if len(title) > 200:
                            title = title[:197] + '...'
                        return title
    
    return None


def extract_date(text: str) -> Optional[str]:
    """
    Extract decision date from case text.
    Returns date in YYYY-MM-DD format.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    
    # Common date patterns
    date_patterns = [
        # January 1, 2020
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
        # Jan. 1, 2020
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(\d{1,2}),?\s+(\d{4})',
    ]
    
    month_map = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12,
    }
    
    # Search in first 2000 characters for efficiency
    search_text = text[:2000]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, search_text, re.IGNORECASE)
        if matches:
            for match in matches:
                month_str, day_str, year_str = match
                month = month_map.get(month_str.lower())
                if month:
                    try:
                        day = int(day_str)
                        year = int(year_str)
                        # Validate date
                        if 1900 <= year <= 2030 and 1 <= day <= 31:
                            return f"{year:04d}-{month:02d}-{day:02d}"
                    except (ValueError, TypeError):
                        continue
    
    return None


def get_case_identifier(data: Dict) -> Optional[str]:
    """
    Extract the primary case identifier to use as filename.
    Prioritizes gr_number, then case_number.
    """
    # Try gr_number first
    gr_number = data.get('gr_number', '')
    if gr_number and isinstance(gr_number, str):
        # Clean up the gr_number to use as filename
        # Extract just the number part if possible
        match = re.search(r'(\d+)', gr_number)
        if match:
            return match.group(1)
        # Otherwise use cleaned version
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', gr_number)
        return cleaned
    
    # Try case_number
    case_number = data.get('case_number', '')
    if case_number and isinstance(case_number, str):
        # Extract number if available
        match = re.search(r'(\d+)', case_number)
        if match:
            return match.group(1)
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', case_number)
        return cleaned
    
    return None


def clean_json_file(filepath: Path, rename: bool = True) -> Tuple[bool, str]:
    """
    Clean a single JSON file.
    
    Args:
        filepath: Path to the JSON file
        rename: Whether to rename the file based on case identifier
    
    Returns:
        Tuple of (success, message)
    """
    try:
        # Read the JSON file
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modified = False
        
        # Fix encoding in all string fields
        for key, value in data.items():
            if isinstance(value, str):
                fixed_value = fix_encoding(value)
                if fixed_value != value:
                    data[key] = fixed_value
                    modified = True
        
        # Remove table blocks from formatted_case_content
        if 'formatted_case_content' in data:
            content = data['formatted_case_content']
            cleaned_content = remove_table_blocks(content)
            if cleaned_content != content:
                data['formatted_case_content'] = cleaned_content
                data['content_length'] = len(cleaned_content)
                modified = True
        
        # Extract and populate missing title
        if 'title' not in data or not data['title'] or data['title'] == 'Title not found':
            if 'formatted_case_content' in data:
                extracted_title = extract_title(data['formatted_case_content'])
                if extracted_title:
                    data['title'] = extracted_title
                    # Also update title_summary if it's missing
                    if 'title_summary' not in data or not data['title_summary'] or data['title_summary'] == 'Title not found':
                        # Truncate for summary
                        summary = extracted_title[:97] + '...' if len(extracted_title) > 100 else extracted_title
                        data['title_summary'] = summary
                    modified = True
                    logger.info(f"Extracted title for {filepath.name}: {extracted_title[:50]}...")
        
        # Extract and populate missing date
        if 'decision_date' not in data or not data['decision_date'] or data['decision_date'] == 'null':
            if 'formatted_case_content' in data:
                extracted_date = extract_date(data['formatted_case_content'])
                if extracted_date:
                    data['decision_date'] = extracted_date
                    modified = True
                    logger.info(f"Extracted date for {filepath.name}: {extracted_date}")
        
        # Write back if modified
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Handle file renaming
        if rename:
            case_id = get_case_identifier(data)
            if case_id:
                new_filename = f"{case_id}.json"
                new_filepath = filepath.parent / new_filename
                
                # Only rename if different and new name doesn't exist
                if filepath.name != new_filename:
                    if new_filepath.exists():
                        # File with this name already exists
                        return True, f"Cleaned but not renamed (target exists): {filepath.name} -> {new_filename}"
                    else:
                        filepath.rename(new_filepath)
                        return True, f"Cleaned and renamed: {filepath.name} -> {new_filename}"
        
        if modified:
            return True, f"Cleaned: {filepath.name}"
        else:
            return True, f"No changes needed: {filepath.name}"
    
    except json.JSONDecodeError as e:
        return False, f"JSON decode error in {filepath.name}: {e}"
    except Exception as e:
        return False, f"Error processing {filepath.name}: {e}"


def process_directory(directory: Path, rename: bool = True, max_files: Optional[int] = None) -> Dict[str, int]:
    """
    Process all JSON files in directory recursively.
    
    Args:
        directory: Root directory to process
        rename: Whether to rename files
        max_files: Maximum number of files to process (for testing)
    
    Returns:
        Dictionary with statistics
    """
    stats = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'renamed': 0,
        'cleaned': 0,
        'unchanged': 0,
    }
    
    failed_files = []
    
    # Find all JSON files
    json_files = list(directory.rglob('*.json'))
    
    if max_files:
        json_files = json_files[:max_files]
    
    logger.info(f"Found {len(json_files)} JSON files to process")
    
    for i, filepath in enumerate(json_files, 1):
        if i % 100 == 0:
            logger.info(f"Processing file {i}/{len(json_files)}...")
        
        stats['total'] += 1
        success, message = clean_json_file(filepath, rename=rename)
        
        if success:
            stats['success'] += 1
            if 'renamed' in message.lower():
                stats['renamed'] += 1
            elif 'cleaned' in message.lower():
                stats['cleaned'] += 1
            else:
                stats['unchanged'] += 1
        else:
            stats['failed'] += 1
            failed_files.append(message)
            logger.warning(message)
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("PROCESSING SUMMARY")
    logger.info("="*60)
    logger.info(f"Total files processed: {stats['total']}")
    logger.info(f"Successfully processed: {stats['success']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Renamed: {stats['renamed']}")
    logger.info(f"Cleaned (not renamed): {stats['cleaned']}")
    logger.info(f"No changes needed: {stats['unchanged']}")
    
    if failed_files:
        logger.info(f"\n{len(failed_files)} files failed:")
        for msg in failed_files[:10]:  # Show first 10
            logger.info(f"  - {msg}")
        if len(failed_files) > 10:
            logger.info(f"  ... and {len(failed_files) - 10} more")
    
    return stats


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Clean and standardize case JSON files'
    )
    parser.add_argument(
        'directory',
        type=str,
        help='Directory containing JSON files to process'
    )
    parser.add_argument(
        '--no-rename',
        action='store_true',
        help='Skip file renaming, only clean content'
    )
    parser.add_argument(
        '--test',
        type=int,
        metavar='N',
        help='Test mode: process only first N files'
    )
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        sys.exit(1)
    
    if not directory.is_dir():
        logger.error(f"Not a directory: {directory}")
        sys.exit(1)
    
    logger.info(f"Processing directory: {directory}")
    logger.info(f"Rename files: {not args.no_rename}")
    if args.test:
        logger.info(f"TEST MODE: Processing only first {args.test} files")
    
    stats = process_directory(
        directory,
        rename=not args.no_rename,
        max_files=args.test
    )
    
    if stats['failed'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
