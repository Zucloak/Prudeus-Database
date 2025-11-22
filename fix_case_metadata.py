#!/usr/bin/env python3
"""
Fix case metadata issues:
1. Standardize filenames where possible
2. Extract and standardize titles from case content
3. Ensure consistent metadata across all cases
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_title_from_content(content: str) -> Optional[str]:
    """
    Extract proper title from case content.
    Handles various case title formats including:
    - Party vs. Party format
    - In re: cases
    - Administrative cases
    """
    if not content or not isinstance(content, str):
        return None
    
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    # Pattern 1: Look for "IN RE:" cases (disbarment, impeachment, etc.)
    for i, line in enumerate(lines[:20]):
        if re.match(r'^IN RE:?\s+', line, re.IGNORECASE):
            # Extract the subject of the "In re" case
            title = re.sub(r'^IN RE:?\s+', '', line, flags=re.IGNORECASE).strip()
            # Clean up title
            title = re.sub(r',\s*Municipal Judge.*$', '', title)
            title = re.sub(r',\s*Judge of First Instance.*$', '', title)
            return title if title and len(title) < 200 else None
    
    # Pattern 2: Look for "In the matter of" cases
    for i, line in enumerate(lines[:20]):
        if re.match(r'^In the matter of', line, re.IGNORECASE):
            title = re.sub(r'^In the matter of\s+', '', line, flags=re.IGNORECASE).strip()
            # Clean up
            title = re.sub(r',\s*attorney.*$', '', title, flags=re.IGNORECASE)
            return title if title and len(title) < 200 else None
    
    # Pattern 3: Look for multi-line "PARTY, role, vs. PARTY, role" format
    # This handles cases like:
    # ENGRACIA CANTORNE,
    # complainant,
    # vs.
    # EUGENIANO DUCUSIN,
    # respondent.
    for i in range(len(lines) - 4):
        if re.match(r'^vs\.?$', lines[i + 2], re.IGNORECASE):
            # Check if we have party names around the "vs."
            party1_line = lines[i]
            party1_desc = lines[i + 1]
            party2_line = lines[i + 3]
            
            # Check if these look like party names (proper case, comma at end)
            if (re.search(r'^[A-Z]', party1_line) and 
                len(party1_line) < 100 and len(party1_line) > 3 and
                re.search(r'^[A-Z]', party2_line) and
                len(party2_line) < 100 and len(party2_line) > 3):
                
                # Clean up party names
                party1 = re.sub(r',\s*$', '', party1_line).strip()
                party2 = re.sub(r',\s*$', '', party2_line).strip()
                party2 = re.sub(r'\.$', '', party2).strip()
                
                # Skip if they look like section headers or other metadata
                skip_patterns = [r'^EN BANC$', r'^SUPREME COURT$', r'^Republic', r'^Manila$']
                if any(re.match(pat, party1, re.IGNORECASE) for pat in skip_patterns):
                    continue
                if any(re.match(pat, party2, re.IGNORECASE) for pat in skip_patterns):
                    continue
                
                title = f"{party1} vs. {party2}"
                return title
    
    # Pattern 4: Look for single-line "PARTY vs. PARTY" format
    for i, line in enumerate(lines[:30]):
        # Check for vs. pattern (case insensitive)
        if re.search(r'\bvs?\.?\b', line, re.IGNORECASE):
            # Skip if line is just "vs." or similar
            if re.match(r'^vs\.?$', line, re.IGNORECASE):
                continue
            
            # Clean up the line
            title = line.strip()
            # Remove common prefixes
            title = re.sub(r'^(complainant|petitioner|plaintiff):\s*', '', title, flags=re.IGNORECASE)
            # Remove trailing case number references
            title = re.sub(r',\s*G\.R\.\s*No\..*$', '', title)
            # Remove comma-separated role descriptions
            title = re.sub(r',\s*(complainant|petitioner|plaintiff|respondent|defendant)\s*,', ' vs. ', title, flags=re.IGNORECASE)
            title = re.sub(r',\s*(complainant|petitioner|plaintiff|respondent|defendant)\s*$', '', title, flags=re.IGNORECASE)
            # Clean up extra spaces
            title = re.sub(r'\s+', ' ', title).strip()
            
            # Only accept if it looks like a proper title
            if (len(title) < 200 and len(title) > 10 and 
                re.search(r'\bvs?\.?\b', title, re.IGNORECASE) and
                not re.match(r'^vs\.?$', title, re.IGNORECASE)):
                return title
    
    return None


def extract_gr_number_from_content(content: str) -> Optional[str]:
    """
    Try to extract a G.R. number or case number from content.
    """
    if not content or not isinstance(content, str):
        return None
    
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    # Look for G.R. No. patterns in first 30 lines
    for line in lines[:30]:
        # Pattern: G.R. No. 12345
        match = re.search(r'G\.?\s*R\.?\s*No\.?\s*(\d+)', line, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Pattern: L-12345 (old format)
        match = re.search(r'\bL-(\d+)\b', line)
        if match:
            return match.group(1)
    
    return None


def standardize_case_title(title: str) -> str:
    """
    Standardize case title format.
    - Capitalize properly
    - Clean up extra whitespace
    - Standardize "vs." notation
    """
    if not title or title == "Title not found":
        return title
    
    # Standardize vs. notation
    title = re.sub(r'\s+v\.?\s+', ' vs. ', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+versus\s+', ' vs. ', title, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    title = re.sub(r'\s+', ' ', title).strip()
    
    # Remove trailing periods
    title = title.rstrip('.')
    
    return title


def should_rename_file(filename: str, gr_number: str) -> bool:
    """
    Determine if a file should be renamed based on its current name and gr_number.
    """
    # Don't rename if filename already matches numeric pattern
    if re.match(r'^\d+\.json$', filename):
        return False
    
    # Rename if we have a numeric gr_number and current filename is non-standard
    if gr_number and re.match(r'^\d+$', gr_number):
        return True
    
    return False


def fix_case_file(file_path: Path) -> Tuple[bool, str, Optional[Path]]:
    """
    Fix a single case file's metadata and potentially rename it.
    Returns: (modified, message, new_path)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modified = False
        rename_to = None
        
        # Extract title from content if needed
        current_title = data.get('title', '')
        if current_title == 'Title not found' or not current_title:
            content = data.get('formatted_case_content', '')
            extracted_title = extract_title_from_content(content)
            if extracted_title:
                data['title'] = standardize_case_title(extracted_title)
                data['title_summary'] = standardize_case_title(extracted_title)
                modified = True
                logger.info(f"  Extracted title: {data['title']}")
        else:
            # Standardize existing title
            standardized = standardize_case_title(current_title)
            if standardized != current_title:
                data['title'] = standardized
                if data.get('title_summary') == current_title:
                    data['title_summary'] = standardized
                modified = True
                logger.info(f"  Standardized title: {data['title']}")
        
        # Try to extract GR number from content if current one is non-numeric
        current_gr = data.get('gr_number', '')
        if current_gr and not re.match(r'^\d+$', current_gr):
            content = data.get('formatted_case_content', '')
            extracted_gr = extract_gr_number_from_content(content)
            if extracted_gr and re.match(r'^\d+$', extracted_gr):
                # Check if file with this number already exists
                new_filename = f"{extracted_gr}.json"
                new_path = file_path.parent / new_filename
                if not new_path.exists():
                    data['gr_number'] = extracted_gr
                    data['case_number'] = extracted_gr
                    rename_to = new_path
                    modified = True
                    logger.info(f"  Will rename to: {new_filename} (extracted GR: {extracted_gr})")
        
        # Update metadata extraction date
        if modified:
            data['metadata_extraction_date'] = datetime.now().isoformat()
            data['extraction_version'] = '2.1_metadata_fix'
            
            # Write back the modified data
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True, "Modified", rename_to
        
        return False, "No changes needed", None
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False, f"Error: {e}", None


def main():
    """Main function to process all case files."""
    if len(sys.argv) < 2:
        print("Usage: python3 fix_case_metadata.py <RESTRUCTURED_DB_path>")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    if not db_path.exists():
        print(f"Error: {db_path} does not exist")
        sys.exit(1)
    
    logger.info("Starting case metadata fix...")
    logger.info(f"Database path: {db_path}")
    
    # Find all JSON files (excluding case_index.json)
    json_files = []
    for root, dirs, files in os.walk(db_path):
        for file in files:
            if file.endswith('.json') and file != 'case_index.json':
                json_files.append(Path(root) / file)
    
    logger.info(f"Found {len(json_files)} case files")
    
    # Process files
    modified_count = 0
    error_count = 0
    renamed_count = 0
    files_to_rename = []
    
    for i, file_path in enumerate(json_files, 1):
        if i % 1000 == 0:
            logger.info(f"Progress: {i}/{len(json_files)} files processed")
        
        modified, message, new_path = fix_case_file(file_path)
        
        if modified:
            modified_count += 1
            if new_path:
                files_to_rename.append((file_path, new_path))
        
        if "Error" in message:
            error_count += 1
    
    # Perform renames after all modifications
    logger.info(f"\nRenaming {len(files_to_rename)} files...")
    for old_path, new_path in files_to_rename:
        try:
            old_path.rename(new_path)
            renamed_count += 1
            logger.info(f"  Renamed: {old_path.name} -> {new_path.name}")
        except Exception as e:
            logger.error(f"  Failed to rename {old_path}: {e}")
            error_count += 1
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    logger.info(f"Total files processed: {len(json_files)}")
    logger.info(f"Files modified: {modified_count}")
    logger.info(f"Files renamed: {renamed_count}")
    logger.info(f"Errors: {error_count}")
    logger.info("="*60)


if __name__ == '__main__':
    main()
