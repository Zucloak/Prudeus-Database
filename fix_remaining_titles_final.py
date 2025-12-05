#!/usr/bin/env python3
"""
Final title extraction for remaining 137 cases with title issues.
This script uses enhanced patterns to extract titles from administrative cases and special formats.
"""

import json
import glob
import re
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_title_from_content(content: str) -> Optional[str]:
    """
    Extract title from case content using multiple strategies.
    Focuses on administrative cases and special formats.
    """
    if not content:
        return None
    
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    # Strategy 1: Look for title before DECISION marker (administrative cases)
    for i, line in enumerate(lines[:100]):
        if 'DECISION' in line and i > 5:
            # Check a few lines before DECISION
            for j in range(max(0, i-10), i):
                candidate = lines[j]
                
                # Skip common headers
                if any(skip in candidate for skip in ['DIVISION', 'Phil.', '[ ', 'View printer']):
                    continue
                
                # Look for administrative case patterns
                if any(pattern in candidate for pattern in ['REPORT ON', 'IN RE', 'REQUEST OF', 'REQUEST FOR', 'PETITION']):
                    # Clean up if DECISION is concatenated
                    if 'DECISION' in candidate:
                        candidate = candidate.split('DECISION')[0].strip()
                    
                    if len(candidate) > 20:  # Must be substantial
                        return clean_title(candidate)
                
                # Look for regular case titles (Party vs. Party)
                if ' VS. ' in candidate.upper() or ' V. ' in candidate:
                    if 'DECISION' in candidate:
                        candidate = candidate.split('DECISION')[0].strip()
                    if len(candidate) > 20:
                        return clean_title(candidate)
            break
    
    # Strategy 2: Look for title after case number markers
    for i, line in enumerate(lines[:50]):
        if re.search(r'\[ [AG]\.?[RM]\.? No\.', line):
            # Title might be on next few lines
            for j in range(i+1, min(i+5, len(lines))):
                candidate = lines[j]
                
                if any(skip in candidate for skip in ['DIVISION', 'DECISION', 'RESOLUTION', 'Phil.']):
                    continue
                
                if len(candidate) > 20 and (' VS. ' in candidate.upper() or ' V. ' in candidate or 'REPORT ON' in candidate or 'IN RE' in candidate):
                    if 'DECISION' in candidate:
                        candidate = candidate.split('DECISION')[0].strip()
                    return clean_title(candidate)
    
    # Strategy 3: Look for G.R. number patterns in content
    gr_match = re.search(r'G\.?R\.? No\.? (\d+)', content[:2000], re.IGNORECASE)
    if gr_match:
        gr_num = gr_match.group(1)
        # Use G.R. number as title
        return f"G.R. No. {gr_num}"
    
    return None


def clean_title(title: str) -> str:
    """Clean and standardize extracted title."""
    # Remove "D E C I S I O N" and similar suffixes
    title = re.sub(r'D\s*E\s*C\s*I\s*S\s*I\s*O\s*N\s*$', '', title, flags=re.IGNORECASE).strip()
    title = re.sub(r'R\s*E\s*S\s*O\s*L\s*U\s*T\s*I\s*O\s*N\s*$', '', title, flags=re.IGNORECASE).strip()
    
    # Remove extra whitespace
    title = ' '.join(title.split())
    
    # Remove trailing punctuation except period
    title = title.rstrip(',;:')
    
    # Standardize vs.
    title = re.sub(r'\s+[Vv][Ss]?\.?\s+', ' vs. ', title)
    
    # Remove duplicate "VS."
    title = re.sub(r'(\bvs\.\s+)+', 'vs. ', title, flags=re.IGNORECASE)
    
    # Capitalize properly
    if title.isupper() and len(title) > 50:
        # Keep as-is if all caps (common in legal documents)
        pass
    
    return title.strip()


def fix_titles_batch(db_path: Path):
    """Fix all remaining title issues."""
    logger.info("="*80)
    logger.info("FINAL TITLE EXTRACTION - Enhanced Edition")
    logger.info("="*80)
    
    # Find files with title issues
    files_to_fix = []
    
    for file_path in glob.glob(str(db_path / '*' / '*' / '*.json')):
        if 'case_index' in file_path:
            continue
        
        try:
            with open(file_path) as f:
                data = json.load(f)
                title = data.get('title', '')
                
                if title in ['Untitled Case', 'Title not found', '', None]:
                    files_to_fix.append(file_path)
        except:
            continue
    
    logger.info(f"Found {len(files_to_fix)} files needing title fixes\n")
    
    fixed_count = 0
    unchanged_count = 0
    errors = 0
    
    for i, file_path in enumerate(files_to_fix, 1):
        try:
            with open(file_path) as f:
                data = json.load(f)
            
            old_title = data.get('title', '')
            content = data.get('formatted_case_content', '')
            
            # Try to extract title
            new_title = extract_title_from_content(content)
            
            if new_title and new_title != old_title:
                data['title'] = new_title
                data['title_summary'] = new_title
                
                # Save updated file
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✓ Fixed: {Path(file_path).name}")
                logger.info(f"  Old: {old_title}")
                logger.info(f"  New: {new_title}")
                fixed_count += 1
            else:
                unchanged_count += 1
                if (i % 25) == 0:
                    logger.info(f"Progress: {i}/{len(files_to_fix)} processed ({fixed_count} fixed)")
        
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            errors += 1
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Total files checked: {len(files_to_fix)}")
    logger.info(f"Successfully fixed: {fixed_count}")
    logger.info(f"Unchanged: {unchanged_count}")
    logger.info(f"Errors: {errors}")
    logger.info("="*80)
    
    return fixed_count, unchanged_count, errors


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 fix_remaining_titles_final.py <RESTRUCTURED_DB_path>")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    
    if not db_path.exists():
        print(f"Error: {db_path} does not exist")
        sys.exit(1)
    
    fixed, unchanged, errors = fix_titles_batch(db_path)
    
    if fixed > 0:
        logger.info(f"\n✓ Successfully fixed {fixed} titles!")
    if unchanged > 0:
        logger.warning(f"\n⚠ {unchanged} files could not be automatically fixed - may need manual review")


if __name__ == '__main__':
    main()
