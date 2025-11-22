#!/usr/bin/env python3
"""
Comprehensive title fix script for Philippine Supreme Court cases.
Fixes:
1. "Untitled Case" entries
2. Titles with dates embedded (e.g., "MONTES VS RINCON August 8, 1911")
3. Titles starting with "vs." (incomplete party names)
4. Other malformed titles
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List
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
    Handles various case title formats.
    """
    if not content or not isinstance(content, str):
        return None
    
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    candidates = []
    
    # Pattern 1: Look for single-line "PARTY, role, VS. PARTY, role" format (best quality)
    # This is the most structured format
    for i, line in enumerate(lines[:40]):
        # Look for proper title format with roles - including Spanish characters
        match = re.search(r'([A-ZÑ][A-ZÑ\s.,&]+),\s*(complainant|petitioner|plaintiff),?\s+(vs\.?)\s+([A-ZÑ][A-ZÑ\s.,&]+),\s*(respondent|defendant)', line, re.IGNORECASE)
        if match:
            party1 = match.group(1).strip()
            party2 = match.group(4).strip()
            # Remove trailing punctuation
            party1 = re.sub(r',\s*$', '', party1).strip()
            party2 = re.sub(r',\s*$', '', party2).strip()
            
            if len(party1) > 3 and len(party2) > 3 and len(party1) < 150 and len(party2) < 150:
                title = f"{party1} vs. {party2}"
                candidates.append((1, title))  # Priority 1 (highest)
    
    # Pattern 2: Look for multi-line "PARTY, role, vs. PARTY, role" format
    for i in range(len(lines)):
        # Check for standalone "vs." line
        if re.match(r'^vs\.?$', lines[i], re.IGNORECASE):
            # Look backwards for party1
            party1_line = None
            party1_role = None
            for j in range(i-1, max(i-5, -1), -1):
                if lines[j] and len(lines[j]) > 3:
                    if re.match(r'^(complainant|plaintiff|petitioner)s?[,\.]?$', lines[j], re.IGNORECASE):
                        party1_role = lines[j]
                        continue
                    elif party1_role or (j == i-2):  # Direct line before vs. or after role
                        party1_line = lines[j]
                        break
            
            # Look forward for party2
            party2_line = None
            party2_role = None
            for j in range(i+1, min(i+5, len(lines))):
                if lines[j] and len(lines[j]) > 3:
                    if re.match(r'^(respondent|defendant)s?[,\.]?$', lines[j], re.IGNORECASE):
                        party2_role = lines[j]
                        continue
                    elif party2_role or (j == i+1):  # Direct line after vs. or after role
                        party2_line = lines[j]
                        break
            
            # If we found both parties
            if party1_line and party2_line:
                # Check if these look like party names
                if (re.search(r'^[A-Z]', party1_line) and 
                    len(party1_line) < 150 and
                    re.search(r'^[A-Z]', party2_line) and
                    len(party2_line) < 150):
                    
                    # Clean up party names
                    party1 = re.sub(r',\s*$', '', party1_line).strip()
                    party2 = re.sub(r',\s*$', '', party2_line).strip()
                    party2 = re.sub(r'\.$', '', party2).strip()
                    
                    # Skip if they look like section headers or other metadata
                    skip_patterns = [r'^EN BANC$', r'^SUPREME COURT$', r'^Republic', r'^Manila$', 
                                   r'^\d+$', r'^G\.R\. No\.', r'^for (plaintiff|defendant|complainant|respondent)']
                    if any(re.match(pat, party1, re.IGNORECASE) for pat in skip_patterns):
                        continue
                    if any(re.match(pat, party2, re.IGNORECASE) for pat in skip_patterns):
                        continue
                    
                    title = f"{party1} vs. {party2}"
                    candidates.append((2, title))  # Priority 2
    
    # Pattern 3: Look for "IN RE:" cases (disbarment, impeachment, etc.)
    for i, line in enumerate(lines[:20]):
        if re.match(r'^IN RE:?\s+', line, re.IGNORECASE):
            # Extract the subject of the "In re" case
            title = re.sub(r'^IN RE:?\s+', '', line, flags=re.IGNORECASE).strip()
            # Clean up title
            title = re.sub(r',\s*Municipal Judge.*$', '', title)
            title = re.sub(r',\s*Judge of First Instance.*$', '', title)
            title = re.sub(r',\s*respondent.*$', '', title, flags=re.IGNORECASE)
            if title and len(title) < 200 and len(title) > 5:
                candidates.append((3, title))  # Priority 3
    
    # Pattern 4: Look for general vs. pattern (case insensitive) - lower priority
    for i, line in enumerate(lines[:30]):
        # Check for vs. pattern
        if re.search(r'\bvs?\.?\b', line, re.IGNORECASE):
            # Skip if line is just "vs." or similar
            if re.match(r'^vs\.?$', line, re.IGNORECASE):
                continue
            
            # Check if line contains actual party names (not just "vs.")
            parts = re.split(r'\s+vs?\.?\s+', line, flags=re.IGNORECASE)
            if len(parts) >= 2:
                # Clean up the line
                title = line.strip()
                # Remove common prefixes
                title = re.sub(r'^(complainant|petitioner|plaintiff):\s*', '', title, flags=re.IGNORECASE)
                # Remove trailing case number references and dates
                title = re.sub(r',\s*G\.R\.\s*No\..*$', '', title)
                title = re.sub(r',?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,\s*\d{4}.*$', '', title, flags=re.IGNORECASE)
                # Remove comma-separated role descriptions
                title = re.sub(r',\s*(complainant|petitioner|plaintiff|respondent|defendant)\s*,', ' vs. ', title, flags=re.IGNORECASE)
                title = re.sub(r',\s*(complainant|petitioner|plaintiff|respondent|defendant)\s*$', '', title, flags=re.IGNORECASE)
                # Clean up extra spaces
                title = re.sub(r'\s+', ' ', title).strip()
                
                # Only accept if it looks like a proper title
                if (len(title) < 200 and len(title) > 10 and 
                    re.search(r'\bvs?\.?\b', title, re.IGNORECASE) and
                    not re.match(r'^vs\.?$', title, re.IGNORECASE)):
                    candidates.append((4, title))  # Priority 4
    
    # Pattern 5: Look for "In the matter of" cases - lowest priority due to verbosity
    for i, line in enumerate(lines[:20]):
        if re.match(r'^In the matter of', line, re.IGNORECASE):
            title = re.sub(r'^In the matter of\s+', '', line, flags=re.IGNORECASE).strip()
            # Clean up
            title = re.sub(r',\s*attorney.*$', '', title, flags=re.IGNORECASE)
            # Only include if reasonably short
            if title and len(title) < 150 and len(title) > 10:
                candidates.append((5, title))  # Priority 5 (lowest)
    
    # Return the best candidate (lowest priority number)
    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    
    return None


def clean_title(title: str, content: str = None) -> str:
    """
    Clean and standardize a title.
    Removes dates, fixes incomplete titles, standardizes format.
    """
    if not title or title == "Title not found":
        return title
    
    original_title = title
    
    # Fix titles starting with "vs." by extracting from content
    if re.match(r'^vs\.', title, re.IGNORECASE):
        if content:
            extracted = extract_title_from_content(content)
            if extracted:
                title = extracted
            else:
                # Try to find party name before "vs." in content
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                for i in range(len(lines) - 1):
                    if re.match(r'^vs\.', lines[i+1], re.IGNORECASE):
                        party1 = lines[i].rstrip(',').strip()
                        # Find party2 after vs.
                        if i + 2 < len(lines):
                            party2 = lines[i+2].rstrip(',').strip().rstrip('.')
                            if len(party1) > 3 and len(party2) > 3:
                                title = f"{party1} vs. {party2}"
                                break
    
    # Remove dates from titles (e.g., "August 8, 1911")
    title = re.sub(r',?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,?\s*\d{4}.*$', '', title, flags=re.IGNORECASE)
    
    # Remove things like "D E C I S I O N" or "RESPONDENT.D E C I S I O N"
    title = re.sub(r'\s*[.,]\s*D\s+E\s+C\s+I\s+S\s+I\s+O\s+N.*$', '', title, flags=re.IGNORECASE)
    title = re.sub(r',?\s*RESPONDENT\s*\.\s*D\s+E\s+C\s+I\s+S\s+I\s+O\s+N.*$', '', title, flags=re.IGNORECASE)
    
    # Remove duplicate "VS." patterns
    title = re.sub(r'\bvs\.\s+vs\.\b', 'vs.', title, flags=re.IGNORECASE)
    title = re.sub(r'\b(complainant|plaintiff|petitioner),?\s+(vs\.)\s+vs\.\b', r'\1 \2', title, flags=re.IGNORECASE)
    
    # Standardize vs. notation
    title = re.sub(r'\s+v\.?\s+', ' vs. ', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+versus\s+', ' vs. ', title, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    title = re.sub(r'\s+', ' ', title).strip()
    
    # Remove trailing periods
    title = title.rstrip('.')
    
    # Remove trailing commas
    title = title.rstrip(',')
    
    return title


def needs_title_fix(title: str) -> bool:
    """
    Determine if a title needs fixing.
    """
    if not title:
        return True
    
    # Check for "Untitled Case"
    if title == "Untitled Case" or title == "Title not found":
        return True
    
    # Check for dates in title
    if re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,?\s*\d{4}', title):
        return True
    
    # Check for titles starting with "vs."
    if re.match(r'^vs\.', title, re.IGNORECASE):
        return True
    
    return False


def fix_case_file(file_path: Path) -> Tuple[bool, str]:
    """
    Fix a single case file's title if needed.
    Returns: (modified, message)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modified = False
        current_title = data.get('title', '')
        
        # Check if title needs fixing
        if needs_title_fix(current_title):
            content = data.get('formatted_case_content', '')
            
            # First, try to extract title from content
            extracted_title = extract_title_from_content(content)
            
            if extracted_title:
                new_title = clean_title(extracted_title, content)
            else:
                # If extraction failed, try to clean existing title
                new_title = clean_title(current_title, content)
            
            # Only update if we got a better title
            if new_title and new_title != current_title and new_title not in ["Title not found", "Untitled Case"]:
                data['title'] = new_title
                data['title_summary'] = new_title
                modified = True
                logger.info(f"  Fixed title: {current_title[:50]}... -> {new_title[:50]}...")
        
        # Update metadata extraction date if modified
        if modified:
            data['metadata_extraction_date'] = datetime.now().isoformat()
            data['extraction_version'] = '2.2_title_fix'
            
            # Write back the modified data
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True, f"Fixed: {current_title[:30]} -> {new_title[:30]}"
        
        return False, "No changes needed"
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False, f"Error: {e}"


def process_batch(files: List[Path], batch_num: int) -> Tuple[int, int]:
    """
    Process a batch of files.
    Returns: (modified_count, error_count)
    """
    modified_count = 0
    error_count = 0
    
    logger.info(f"\nProcessing batch {batch_num} ({len(files)} files)...")
    
    for i, file_path in enumerate(files, 1):
        if i % 100 == 0:
            logger.info(f"  Progress: {i}/{len(files)} files in batch")
        
        modified, message = fix_case_file(file_path)
        
        if modified:
            modified_count += 1
        
        if "Error" in message:
            error_count += 1
    
    return modified_count, error_count


def main():
    """Main function to process all case files in batches."""
    if len(sys.argv) < 2:
        print("Usage: python3 fix_titles_comprehensive.py <RESTRUCTURED_DB_path> [batch_size]")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    
    if not db_path.exists():
        print(f"Error: {db_path} does not exist")
        sys.exit(1)
    
    logger.info("Starting comprehensive title fix...")
    logger.info(f"Database path: {db_path}")
    logger.info(f"Batch size: {batch_size}")
    
    # Find all JSON files that need fixing
    json_files = []
    for root, dirs, files in os.walk(db_path):
        for file in files:
            if file.endswith('.json') and file != 'case_index.json':
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        title = data.get('title', '')
                        if needs_title_fix(title):
                            json_files.append(file_path)
                except:
                    pass
    
    logger.info(f"Found {len(json_files)} case files needing title fixes")
    
    if len(json_files) == 0:
        logger.info("No files need fixing. Exiting.")
        return
    
    # Process files in batches
    total_modified = 0
    total_errors = 0
    
    for i in range(0, len(json_files), batch_size):
        batch = json_files[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        modified, errors = process_batch(batch, batch_num)
        total_modified += modified
        total_errors += errors
        
        logger.info(f"Batch {batch_num} complete: {modified} modified, {errors} errors")
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    logger.info(f"Total files checked: {len(json_files)}")
    logger.info(f"Files modified: {total_modified}")
    logger.info(f"Errors: {total_errors}")
    logger.info("="*60)


if __name__ == '__main__':
    main()
