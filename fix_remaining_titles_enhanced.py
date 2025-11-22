#!/usr/bin/env python3
"""
Enhanced title extraction script for remaining "Untitled Case" and "Title not found" cases.
This script handles unusual content formatting that prevented automatic extraction.
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


def extract_title_from_content_enhanced(content: str) -> Optional[str]:
    """
    Enhanced title extraction that handles various unusual formats.
    """
    if not content or not isinstance(content, str):
        return None
    
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    if len(lines) < 5:
        return None
    
    candidates = []
    
    # Pattern 0: Look for single-line party format with roles on same line and "D E C I S I O N" appended
    # Example: "NENITA DE GUZMAN FERGUSON, COMPLAINANT, ATTY. SALVADOR P. RAMOS, RESPONDENT.D E C I S I O N"
    for i, line in enumerate(lines[:15]):
        # Remove "D E C I S I O N" suffix if present
        clean_line = re.sub(r'\.?\s*D\s+E\s+C\s+I\s+S\s+I\s+O\s+N.*$', '', line, flags=re.IGNORECASE)
        
        # Match pattern: PARTY, role, PARTY, role
        match = re.search(
            r'^([A-ZÑ][A-ZÑA-Z\s.,&\'-]+?),\s*(complainant|petitioner|plaintiff|accused)[\-,\s]*(appellee|appellant)?,?\s*([A-ZÑ][A-ZÑA-Z\s.,&\'-]+?),\s*(respondent|defendant|accused)[\-,\s]*(appellant|appellee)?\.?$',
            clean_line,
            re.IGNORECASE
        )
        if match:
            party1 = match.group(1).strip()
            party2 = match.group(4).strip()
            
            if len(party1) > 3 and len(party2) > 3 and len(party1) < 150 and len(party2) < 150:
                # Skip headers
                if not re.match(r'^(EN BANC|FIRST DIVISION|SUPREME COURT)', party1, re.IGNORECASE):
                    title = f"{party1} vs. {party2}"
                    candidates.append((1, title))
    
    # Pattern 0b: Look for "PARTY, ROLE-ROLE, VS. PARTY, ROLE-ROLE." format on one line
    # Example: "PEOPLE OF THE PHILIPPINES, PLAINTIFF-APPELLEE, VS. GODOFREDO RUIZ, JR. Y SALAMANCA, ACCUSED-APPELLANT."
    for i, line in enumerate(lines[:15]):
        if re.search(r',\s*(plaintiff|petitioner|complainant|people)[\-\s]+(appellee|appellant)', line, re.IGNORECASE):
            if re.search(r'\bvs\.?\b', line, re.IGNORECASE):
                # Clean the line
                clean_line = re.sub(r'\.?\s*D\s+E\s+C\s+I\s+S\s+I\s+O\s+N.*$', '', line, flags=re.IGNORECASE)
                
                # Try to extract parties
                match = re.search(
                    r'^(.+?),\s*(plaintiff|petitioner|complainant|people)[\-\s]+(appellee|appellant),?\s+vs\.?\s+(.+?),\s*(respondent|defendant|accused)[\-\s]+(appellant|appellee)\.?$',
                    clean_line,
                    re.IGNORECASE
                )
                if match:
                    party1 = match.group(1).strip()
                    party2 = match.group(4).strip()
                    
                    if len(party1) > 3 and len(party2) > 3 and len(party1) < 150 and len(party2) < 150:
                        if not re.match(r'^(EN BANC|FIRST DIVISION)', party1, re.IGNORECASE):
                            title = f"{party1} vs. {party2}"
                            candidates.append((1, title))
    
    # Pattern 0c: Handle split lines where "VS." ends one line and party2 starts next line
    # Example: Line 1: "PEOPLE OF THE PHILIPPINES, PLAINTIFF-APPELLEE, VS."
    #          Line 2: "GODOFREDO RUIZ, JR. Y SALAMANCA, ACCUSED-APPELLANT."
    for i in range(len(lines) - 1):
        if re.search(r',\s+VS\.?\s*$', lines[i], re.IGNORECASE):
            # This line ends with VS., check next line for party2
            combined = lines[i] + ' ' + lines[i+1]
            # Remove "D E C I S I O N" if present
            combined = re.sub(r'\.?\s*D\s+E\s+C\s+I\s+S\s+I\s+O\s+N.*$', '', combined, flags=re.IGNORECASE)
            
            match = re.search(
                r'^(.+?),\s*(plaintiff|petitioner|complainant|people)[\-\s]+(appellee|appellant),?\s+vs\.?\s+(.+?),\s*(respondent|defendant|accused)[\-\s]+(appellant|appellee)\.?$',
                combined,
                re.IGNORECASE
            )
            if match:
                party1 = match.group(1).strip()
                party2 = match.group(4).strip()
                
                if len(party1) > 3 and len(party2) > 3 and len(party1) < 150 and len(party2) < 150:
                    if not re.match(r'^(EN BANC|FIRST DIVISION)', party1, re.IGNORECASE):
                        title = f"{party1} vs. {party2}"
                        candidates.append((1, title))
    
    # Pattern 1: Administrative cases starting with "REQUEST OF" or "IN RE:"
    for i, line in enumerate(lines[:25]):
        # Match administrative cases like "REQUEST OF THE PUBLIC ATTORNEY'S OFFICE..."
        if re.match(r'^REQUEST OF', line, re.IGNORECASE):
            # This is the title itself
            title = line.strip()
            if len(title) > 10 and len(title) < 250:
                candidates.append((1, title))
        
        # Match "IN RE:" cases
        if re.match(r'^IN RE:?\s+', line, re.IGNORECASE):
            title = re.sub(r'^IN RE:?\s+', '', line, flags=re.IGNORECASE).strip()
            # Clean up common suffixes
            title = re.sub(r',\s*(Municipal Judge|Judge of First Instance|respondent|attorney).*$', '', title, flags=re.IGNORECASE)
            if title and len(title) > 5 and len(title) < 200:
                candidates.append((1, f"In Re: {title}"))
    
    # Pattern 2: Look for single-line "PARTY, role, VS. PARTY, role" format (BEST QUALITY)
    for i, line in enumerate(lines[:40]):
        # Enhanced pattern to catch more variations including Spanish characters
        match = re.search(
            r'([A-ZÑ][A-ZÑA-Z\s.,&\'-]+),?\s*(complainant|petitioner|plaintiff|accused)[\-,\s]*(appellee|appellant)?,?\s+(vs?\.?)\s+([A-ZÑ][A-ZÑA-Z\s.,&\'-]+),?\s*(respondent|defendant|accused)[\-,\s]*(appellant|appellee)?',
            line, 
            re.IGNORECASE
        )
        if match:
            party1 = match.group(1).strip()
            party2 = match.group(5).strip()
            
            # Clean up party names
            party1 = re.sub(r',\s*$', '', party1).strip()
            party2 = re.sub(r',\s*$', '', party2).strip()
            
            # Skip if too short or too long
            if len(party1) > 3 and len(party2) > 3 and len(party1) < 150 and len(party2) < 150:
                # Skip common non-party terms
                skip_patterns = [
                    r'^EN BANC$', r'^SUPREME COURT$', r'^FIRST DIVISION$', 
                    r'^SECOND DIVISION$', r'^THIRD DIVISION$', r'^PRINTER FRIENDLY',
                    r'^\d+\s+Phil', r'^G\.R\. No', r'^Manila$'
                ]
                if any(re.match(pat, party1, re.IGNORECASE) for pat in skip_patterns):
                    continue
                if any(re.match(pat, party2, re.IGNORECASE) for pat in skip_patterns):
                    continue
                
                title = f"{party1} vs. {party2}"
                candidates.append((1, title))
    
    # Pattern 3: Multi-line party format with standalone "vs." line
    for i in range(len(lines)):
        # Check for standalone "vs." line
        if re.match(r'^vs\.?$', lines[i], re.IGNORECASE):
            # Look backwards for party1 (up to 5 lines back)
            party1_line = None
            party1_idx = -1
            for j in range(i-1, max(i-6, -1), -1):
                if lines[j] and len(lines[j]) > 3 and len(lines[j]) < 150:
                    # Skip role descriptors
                    if re.match(r'^(complainant|plaintiff|petitioner|respondent|defendant)s?[,\.]?$', lines[j], re.IGNORECASE):
                        continue
                    # Check if it looks like a party name (starts with capital)
                    if re.match(r'^[A-ZÑ]', lines[j]):
                        party1_line = lines[j]
                        party1_idx = j
                        break
            
            # Look forward for party2 (up to 5 lines ahead)
            party2_line = None
            for j in range(i+1, min(i+6, len(lines))):
                if lines[j] and len(lines[j]) > 3 and len(lines[j]) < 150:
                    # Skip role descriptors
                    if re.match(r'^(complainant|plaintiff|petitioner|respondent|defendant)s?[,\.]?$', lines[j], re.IGNORECASE):
                        continue
                    # Check if it looks like a party name
                    if re.match(r'^[A-ZÑ]', lines[j]):
                        party2_line = lines[j]
                        break
            
            if party1_line and party2_line:
                # Clean up party names
                party1 = re.sub(r',\s*$', '', party1_line).strip()
                party2 = re.sub(r',\s*$', '', party2_line).strip()
                party2 = re.sub(r'\.$', '', party2).strip()
                
                # Skip section headers and metadata
                skip_patterns = [
                    r'^EN BANC$', r'^SUPREME COURT$', r'^FIRST DIVISION$',
                    r'^Republic', r'^Manila$', r'^\d+$', r'^G\.R\. No\.',
                    r'^for (plaintiff|defendant|complainant|respondent)',
                    r'^\d+\s+Phil', r'^PRINTER FRIENDLY'
                ]
                if any(re.match(pat, party1, re.IGNORECASE) for pat in skip_patterns):
                    continue
                if any(re.match(pat, party2, re.IGNORECASE) for pat in skip_patterns):
                    continue
                
                title = f"{party1} vs. {party2}"
                candidates.append((2, title))
    
    # Pattern 4: Look for general "vs." pattern in a line (lower priority)
    for i, line in enumerate(lines[:40]):
        # Must have "vs." or "v." in the line
        if re.search(r'\bvs?\.?\b', line, re.IGNORECASE):
            # Skip standalone "vs." lines (already handled)
            if re.match(r'^vs\.?$', line, re.IGNORECASE):
                continue
            
            # Skip lines that are clearly not titles
            if re.match(r'^(EN BANC|FIRST DIVISION|SECOND DIVISION|THIRD DIVISION|Manila|G\.R\. No)', line, re.IGNORECASE):
                continue
            
            # Check if line has actual party names (not just "vs.")
            parts = re.split(r'\s+vs?\.?\s+', line, flags=re.IGNORECASE)
            if len(parts) >= 2 and len(parts[0].strip()) > 3 and len(parts[1].strip()) > 3:
                # Clean up the line
                title = line.strip()
                
                # Remove common prefixes
                title = re.sub(r'^(complainant|petitioner|plaintiff):\s*', '', title, flags=re.IGNORECASE)
                
                # Remove trailing case number references and dates
                title = re.sub(r',\s*G\.R\.\s*No\..*$', '', title)
                title = re.sub(r',?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,?\s*\d{4}.*$', '', title, flags=re.IGNORECASE)
                
                # Remove role descriptions
                title = re.sub(r',\s*(complainant|petitioner|plaintiff|respondent|defendant)[\s,]*$', '', title, flags=re.IGNORECASE)
                
                # Clean up extra spaces
                title = re.sub(r'\s+', ' ', title).strip()
                
                # Only accept if it looks like a proper title
                if (len(title) >= 10 and len(title) < 200 and 
                    re.search(r'\bvs?\.?\b', title, re.IGNORECASE)):
                    candidates.append((3, title))
    
    # Pattern 5: Look for cases with named parties as petitioners/respondents
    # Format: "GREGORIO LORENO and FELISA LAVILLA,\npetitioners,\nvs.\n..."
    for i in range(len(lines) - 4):
        if re.match(r'^(petitioners?|plaintiffs?|complainants?)[,\.]?$', lines[i+1], re.IGNORECASE):
            if re.match(r'^vs\.?$', lines[i+2], re.IGNORECASE):
                party1_line = lines[i]
                # Find party2
                party2_line = None
                for j in range(i+3, min(i+7, len(lines))):
                    if re.match(r'^(respondents?|defendants?)[,\.]?$', lines[j], re.IGNORECASE):
                        if j > 0:
                            party2_line = lines[j-1]
                            break
                
                if party1_line and party2_line and len(party1_line) > 3 and len(party2_line) > 3:
                    party1 = re.sub(r',\s*$', '', party1_line).strip()
                    party2 = re.sub(r',\s*$', '', party2_line).strip()
                    
                    # Skip if they look like headers
                    skip_patterns = [r'^EN BANC$', r'^SUPREME COURT$', r'^\d+\s+Phil']
                    if not any(re.match(pat, party1, re.IGNORECASE) for pat in skip_patterns):
                        if not any(re.match(pat, party2, re.IGNORECASE) for pat in skip_patterns):
                            if len(party1) < 150 and len(party2) < 150:
                                title = f"{party1} vs. {party2}"
                                candidates.append((2, title))
    
    # Return the best candidate (lowest priority number = highest quality)
    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    
    return None


def clean_title(title: str) -> str:
    """
    Clean and standardize a title.
    """
    if not title or title in ["Title not found", "Untitled Case"]:
        return title
    
    # Standardize vs. notation
    title = re.sub(r'\s+v\.?\s+', ' vs. ', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+versus\s+', ' vs. ', title, flags=re.IGNORECASE)
    
    # Remove dates from titles
    title = re.sub(r',?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,?\s*\d{4}.*$', '', title, flags=re.IGNORECASE)
    
    # Remove "D E C I S I O N" and similar patterns
    title = re.sub(r'\s*[.,]\s*D\s+E\s+C\s+I\s+S\s+I\s+O\s+N.*$', '', title, flags=re.IGNORECASE)
    title = re.sub(r',?\s*RESPONDENT\s*\.\s*D\s+E\s+C\s+I\s+S\s+I\s+O\s+N.*$', '', title, flags=re.IGNORECASE)
    
    # Clean up extra spaces
    title = re.sub(r'\s+', ' ', title).strip()
    
    # Remove trailing periods and commas
    title = title.rstrip('.').rstrip(',')
    
    # Capitalize "vs." properly
    title = re.sub(r'\bvs\b\.?', 'vs.', title, flags=re.IGNORECASE)
    
    return title


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
        if current_title in ['Untitled Case', 'Title not found', '']:
            content = data.get('formatted_case_content', '')
            
            # Try to extract title from content
            extracted_title = extract_title_from_content_enhanced(content)
            
            if extracted_title:
                new_title = clean_title(extracted_title)
                
                # Only update if we got a valid title
                if new_title and new_title not in ["Title not found", "Untitled Case", ""]:
                    data['title'] = new_title
                    data['title_summary'] = new_title
                    data['metadata_extraction_date'] = datetime.now().isoformat()
                    data['extraction_version'] = '2.3_enhanced_title_fix'
                    modified = True
                    
                    # Write back the modified data
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    logger.info(f"  ✓ Fixed: {file_path.name}")
                    logger.info(f"    Old: {current_title}")
                    logger.info(f"    New: {new_title[:100]}")
                    return True, f"Fixed: {current_title} -> {new_title[:50]}"
        
        return False, "No changes needed"
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}")
        return False, f"Error: {e}"


def main():
    """Main function to process all case files needing title fixes."""
    if len(sys.argv) < 2:
        print("Usage: python3 fix_remaining_titles_enhanced.py <RESTRUCTURED_DB_path>")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    
    if not db_path.exists():
        print(f"Error: {db_path} does not exist")
        sys.exit(1)
    
    logger.info("="*80)
    logger.info("ENHANCED TITLE EXTRACTION - Starting...")
    logger.info("="*80)
    logger.info(f"Database path: {db_path}")
    
    # Find all JSON files that need fixing
    logger.info("\nScanning for cases needing title fixes...")
    json_files = []
    
    for root, dirs, files in os.walk(db_path):
        for file in files:
            if file.endswith('.json') and file != 'case_index.json':
                file_path = Path(root) / file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        title = data.get('title', '')
                        if title in ['Untitled Case', 'Title not found', '']:
                            json_files.append(file_path)
                except Exception as e:
                    logger.warning(f"Could not read {file_path}: {e}")
    
    logger.info(f"Found {len(json_files)} case files needing title fixes")
    logger.info(f"  - Untitled Case: checking...")
    logger.info(f"  - Title not found: checking...")
    
    if len(json_files) == 0:
        logger.info("No files need fixing. Exiting.")
        return
    
    # Process files
    logger.info("\n" + "="*80)
    logger.info("PROCESSING FILES")
    logger.info("="*80)
    
    total_modified = 0
    total_errors = 0
    total_unchanged = 0
    
    for i, file_path in enumerate(json_files, 1):
        if i % 100 == 0:
            logger.info(f"Progress: {i}/{len(json_files)} files processed ({total_modified} fixed)")
        
        modified, message = fix_case_file(file_path)
        
        if modified:
            total_modified += 1
        elif "Error" in message:
            total_errors += 1
        else:
            total_unchanged += 1
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Total files checked: {len(json_files)}")
    logger.info(f"Files successfully fixed: {total_modified}")
    logger.info(f"Files unchanged: {total_unchanged}")
    logger.info(f"Errors: {total_errors}")
    logger.info("="*80)
    
    if total_modified > 0:
        logger.info(f"\n✓ Successfully fixed {total_modified} case titles!")
    else:
        logger.info("\n⚠ No titles could be extracted. Manual review may be needed.")


if __name__ == '__main__':
    main()
