#!/usr/bin/env python3
"""
Batched version of the case data cleanup script.
Processes files in year-based batches and commits changes after each batch.
This prevents git failures with large numbers of files.
"""

import json
import os
import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
from multiprocessing import Pool, cpu_count

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


def configure_git_for_large_operations():
    """Configure git settings for handling large operations."""
    logger.info("Configuring git for large operations...")
    try:
        # Disable preload index for better performance with many files
        subprocess.run(['git', 'config', 'core.preloadIndex', 'false'], check=False)
        # Increase auto gc limit
        subprocess.run(['git', 'config', 'gc.auto', '10000'], check=False)
        # Increase pack size limit
        subprocess.run(['git', 'config', 'pack.windowMemory', '256m'], check=False)
        subprocess.run(['git', 'config', 'pack.packSizeLimit', '2g'], check=False)
        logger.info("Git configuration updated successfully")
    except Exception as e:
        logger.warning(f"Could not configure git: {e}")


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


def normalize_date_format(date_str: str) -> Optional[str]:
    """
    Normalize date from various formats to YYYY-MM-DD.
    """
    if not date_str or date_str == 'null':
        return None
    
    # If already in YYYY-MM-DD format, return as-is
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    
    # Try to parse and reformat common date formats
    date_patterns = [
        # January 1, 2020
        (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', 'month_day_year'),
        # Jan. 1, 2020
        (r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(\d{1,2}),?\s+(\d{4})', 'month_day_year'),
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
    
    for pattern, format_type in date_patterns:
        match = re.search(pattern, date_str, re.IGNORECASE)
        if match:
            if format_type == 'month_day_year':
                month_str, day_str, year_str = match.groups()
                month = month_map.get(month_str.lower())
                if month:
                    try:
                        day = int(day_str)
                        year = int(year_str)
                        if 1900 <= year <= 2030 and 1 <= day <= 31:
                            return f"{year:04d}-{month:02d}-{day:02d}"
                    except (ValueError, TypeError):
                        continue
    
    return None


def get_case_identifier(data: Dict) -> Optional[str]:
    """
    Extract the primary case identifier to use as filename.
    Extracts numeric part from gr_number, case_number, or various formats.
    """
    # Try gr_number first - extract numeric part
    gr_number = data.get('gr_number', '')
    if gr_number and isinstance(gr_number, str):
        # Extract numeric digits
        match = re.search(r'(\d+)', gr_number)
        if match:
            return match.group(1)
    
    # Try case_number - look for various formats
    case_number = data.get('case_number', '')
    if case_number and isinstance(case_number, str):
        # Extract numeric part from formats like "G.R. No. 123456", "A.M. No. 1234", etc.
        match = re.search(r'(\d+)', case_number)
        if match:
            return match.group(1)
    
    return None


def clean_json_file(filepath: Path, rename: bool = True) -> Tuple[bool, str, bool]:
    """
    Clean a single JSON file.
    
    Args:
        filepath: Path to the JSON file
        rename: Whether to rename the file based on case identifier
    
    Returns:
        Tuple of (success, message, was_renamed)
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
        
        # Normalize decision_date format to YYYY-MM-DD
        if 'decision_date' in data and data['decision_date']:
            current_date = data['decision_date']
            normalized_date = normalize_date_format(current_date)
            if normalized_date and normalized_date != current_date:
                data['decision_date'] = normalized_date
                modified = True
        # Extract and populate missing date
        elif 'decision_date' not in data or not data['decision_date'] or data['decision_date'] == 'null':
            if 'formatted_case_content' in data:
                extracted_date = extract_date(data['formatted_case_content'])
                if extracted_date:
                    data['decision_date'] = extracted_date
                    modified = True
        
        # Write back if modified
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Handle file renaming
        was_renamed = False
        if rename:
            case_id = get_case_identifier(data)
            if case_id:
                new_filename = f"{case_id}.json"
                new_filepath = filepath.parent / new_filename
                
                # Only rename if different and new name doesn't exist
                if filepath.name != new_filename:
                    if new_filepath.exists():
                        # File with this name already exists
                        return True, f"cleaned:{filepath.name}", False
                    else:
                        filepath.rename(new_filepath)
                        was_renamed = True
                        return True, f"renamed:{filepath.name}->{new_filename}", True
        
        if modified:
            return True, f"cleaned:{filepath.name}", False
        else:
            return True, f"unchanged:{filepath.name}", False
    
    except json.JSONDecodeError as e:
        return False, f"error:{filepath.name}:JSON decode error", False
    except Exception as e:
        return False, f"error:{filepath.name}:{str(e)}", False


def process_file_wrapper(args):
    """Wrapper function for multiprocessing."""
    filepath, rename = args
    return clean_json_file(filepath, rename)


def process_years_batch(directory: Path, years: List[int], rename: bool = True, num_workers: Optional[int] = None) -> Dict[str, int]:
    """
    Process JSON files for a specific batch of years.
    
    Args:
        directory: Root directory (e.g., RESTRUCTURED_DB)
        years: List of years to process
        rename: Whether to rename files
        num_workers: Number of worker processes
    
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
    
    # Collect JSON files for the specified years
    json_files = []
    for year in years:
        year_dir = directory / str(year)
        if year_dir.exists() and year_dir.is_dir():
            json_files.extend(list(year_dir.rglob('*.json')))
    
    if not json_files:
        logger.info(f"No files found for years {years}")
        return stats
    
    stats['total'] = len(json_files)
    logger.info(f"Found {len(json_files)} JSON files for years {years[0]}-{years[-1]}")
    
    # Determine number of workers
    if num_workers is None:
        num_workers = cpu_count()
    
    logger.info(f"Using {num_workers} worker processes")
    
    # Prepare arguments for each file
    file_args = [(filepath, rename) for filepath in json_files]
    
    # Process files in parallel
    with Pool(processes=num_workers) as pool:
        # Use imap_unordered for better progress tracking
        results = pool.imap_unordered(process_file_wrapper, file_args, chunksize=50)
        
        # Process results as they complete
        for i, (success, message, was_renamed) in enumerate(results, 1):
            if i % 100 == 0:
                logger.info(f"  Processing file {i}/{len(json_files)}... ({i*100//len(json_files)}%)")
            
            if success:
                stats['success'] += 1
                if was_renamed:
                    stats['renamed'] += 1
                elif message.startswith('cleaned:'):
                    stats['cleaned'] += 1
                else:
                    stats['unchanged'] += 1
            else:
                stats['failed'] += 1
                failed_files.append(message)
    
    # Print batch summary
    logger.info(f"\nBatch {years[0]}-{years[-1]} Summary:")
    logger.info(f"  Total: {stats['total']}, Success: {stats['success']}, Renamed: {stats['renamed']}, Cleaned: {stats['cleaned']}, Unchanged: {stats['unchanged']}, Failed: {stats['failed']}")
    
    if failed_files:
        logger.warning(f"  {len(failed_files)} files failed in this batch")
        for msg in failed_files[:5]:
            logger.warning(f"    - {msg}")
    
    return stats


def git_commit_batch(years: List[int], stats: Dict[str, int]) -> bool:
    """
    Commit changes for a batch of years.
    
    Args:
        years: List of years processed
        stats: Statistics for the batch
    
    Returns:
        True if commit succeeded, False otherwise
    """
    try:
        year_range = f"{years[0]}-{years[-1]}"
        
        # Stage changes for this batch
        logger.info(f"Staging changes for years {year_range}...")
        for year in years:
            year_path = f"RESTRUCTURED_DB/{year}"
            result = subprocess.run(['git', 'add', year_path], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Git add had issues for {year}: {result.stderr}")
        
        # Check if there are changes to commit
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True)
        if result.returncode == 0:
            logger.info(f"No changes to commit for years {year_range}")
            return True
        
        # Create commit message
        commit_msg = f"""Apply case data cleanup for years {year_range}

- Processed {stats['total']} files
- Renamed {stats['renamed']} files to standardized format
- Fixed encoding/content in {stats['cleaned']} files
- {stats['unchanged']} files unchanged
- {stats['failed']} failures

Standardized filenames to numeric ID format (e.g., 12345.json)
Fixed character encoding issues
Normalized decision dates to YYYY-MM-DD format
Extracted missing titles where possible"""
        
        # Commit
        logger.info(f"Committing changes for years {year_range}...")
        result = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Git commit failed: {result.stderr}")
            return False
        
        logger.info(f"✓ Successfully committed changes for years {year_range}")
        return True
        
    except Exception as e:
        logger.error(f"Error committing batch: {e}")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Clean and standardize case JSON files in batches by year'
    )
    parser.add_argument(
        'directory',
        type=str,
        help='Directory containing JSON files to process (e.g., RESTRUCTURED_DB)'
    )
    parser.add_argument(
        '--no-rename',
        action='store_true',
        help='Skip file renaming, only clean content'
    )
    parser.add_argument(
        '--workers',
        type=int,
        metavar='N',
        help='Number of worker processes (default: CPU count)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=5,
        help='Number of years per batch (default: 5)'
    )
    parser.add_argument(
        '--no-commit',
        action='store_true',
        help='Skip git commits (for testing)'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=1901,
        help='Start year (default: 1901)'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        default=2025,
        help='End year (default: 2025)'
    )
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        sys.exit(1)
    
    if not directory.is_dir():
        logger.error(f"Not a directory: {directory}")
        sys.exit(1)
    
    # Configure git
    if not args.no_commit:
        configure_git_for_large_operations()
    
    logger.info("="*80)
    logger.info("BATCHED CASE DATA CLEANUP")
    logger.info("="*80)
    logger.info(f"Directory: {directory}")
    logger.info(f"Rename files: {not args.no_rename}")
    logger.info(f"Batch size: {args.batch_size} years")
    logger.info(f"Year range: {args.start_year}-{args.end_year}")
    logger.info(f"Workers: {args.workers or cpu_count()}")
    logger.info(f"Git commits: {not args.no_commit}")
    logger.info("="*80)
    
    # Create year batches
    all_years = range(args.start_year, args.end_year + 1)
    batches = [list(all_years[i:i + args.batch_size]) for i in range(0, len(all_years), args.batch_size)]
    
    logger.info(f"\nProcessing {len(batches)} batches of years...")
    
    # Track overall statistics
    overall_stats = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'renamed': 0,
        'cleaned': 0,
        'unchanged': 0,
    }
    
    failed_batches = []
    
    # Process each batch
    for batch_num, years in enumerate(batches, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"BATCH {batch_num}/{len(batches)}: Years {years[0]}-{years[-1]}")
        logger.info(f"{'='*80}")
        
        # Process the batch
        batch_stats = process_years_batch(
            directory,
            years,
            rename=not args.no_rename,
            num_workers=args.workers
        )
        
        # Update overall stats
        for key in overall_stats:
            overall_stats[key] += batch_stats[key]
        
        # Commit changes for this batch
        if not args.no_commit and batch_stats['total'] > 0:
            if not git_commit_batch(years, batch_stats):
                failed_batches.append(f"Years {years[0]}-{years[-1]}")
                logger.error(f"Failed to commit batch {batch_num}")
        
        logger.info(f"✓ Completed batch {batch_num}/{len(batches)}")
    
    # Print final summary
    logger.info("\n" + "="*80)
    logger.info("FINAL SUMMARY")
    logger.info("="*80)
    logger.info(f"Total files processed: {overall_stats['total']}")
    logger.info(f"Successfully processed: {overall_stats['success']}")
    logger.info(f"Failed: {overall_stats['failed']}")
    logger.info(f"Renamed: {overall_stats['renamed']}")
    logger.info(f"Cleaned (not renamed): {overall_stats['cleaned']}")
    logger.info(f"No changes needed: {overall_stats['unchanged']}")
    
    if failed_batches:
        logger.error(f"\n{len(failed_batches)} batches had commit failures:")
        for batch in failed_batches:
            logger.error(f"  - {batch}")
    
    logger.info("="*80)
    
    if overall_stats['failed'] > 0 or failed_batches:
        sys.exit(1)


if __name__ == '__main__':
    main()
