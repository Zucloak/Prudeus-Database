#!/usr/bin/env python3
"""
Multi-source scraper for missing Philippine Supreme Court cases (2005-2024)

This script attempts to scrape missing cases from multiple sources:
1. https://elibrary.judiciary.gov.ph/ (Supreme Court E-Library)
2. https://lawphil.net (fallback)
3. Future: https://chanrobles.com/cralaw (if accessible)
4. Future: https://sc.judiciary.gov.ph/ (if accessible)

Priority order: elibrary > lawphil > others
"""

import requests
import json
import re
import time
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

# Define the missing cases from 2005-2024
MISSING_CASES = [
    {
        'title': 'Manuel v. People',
        'gr_number': '165842',
        'date': '2005-11-29',
        'year': 2005,
        'month': 'november'
    },
    {
        'title': 'Valeroso v. People',
        'gr_number': '164815',
        'date': '2008-02-22',
        'year': 2008,
        'month': 'february'
    },
    {
        'title': 'Otamias v. Republic',
        'gr_number': '189516',
        'date': '2016-06-08',
        'year': 2016,
        'month': 'june'
    },
    {
        'title': 'Sanico v. Colipano',
        'gr_number': '209969',
        'date': '2017-09-27',
        'year': 2017,
        'month': 'september'
    },
    {
        'title': 'Municipality of Tupi v. Faustino',
        'gr_number': '231896',
        'date': '2019-08-20',
        'year': 2019,
        'month': 'august'
    },
    {
        'title': 'Toyo v. Toyo',
        'gr_number': '213198',
        'date': '2019-07-01',
        'year': 2019,
        'month': 'july'
    },
    {
        'title': 'Film Development Council v. Colon',
        'gr_number': '203754',
        'date': '2019-10-15',
        'year': 2019,
        'month': 'october'
    },
    {
        'title': 'San Miguel Corp. v. Commissioner of Internal Revenue',
        'gr_number': '257697',
        'date': '2023-04-12',
        'year': 2023,
        'month': 'april'
    }
]

# User agent for web requests
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def try_elibrary_judiciary(gr_number: str, title: str) -> Optional[Tuple[str, str]]:
    """
    Try to fetch case from Supreme Court E-Library.
    Returns (content, source_url) if found, None otherwise.
    """
    logger.info(f"  Trying elibrary.judiciary.gov.ph for G.R. No. {gr_number}")
    
    # E-Library uses an ID system. Try various approaches:
    # 1. Direct GR number
    # 2. Try search functionality if available
    # 3. Try with/without leading zeros
    
    possible_ids = [
        gr_number,  # Direct GR number
        gr_number.lstrip('0'),  # Without leading zeros
        str(int(gr_number)),  # As integer (removes leading zeros)
    ]
    
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    for doc_id in possible_ids:
        try:
            url = f"https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/{doc_id}"
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            
            if response.status_code == 200 and len(response.text) > 1000:
                # Check if this is the correct case by looking for GR number in content
                if (f"G.R. No. {gr_number}" in response.text or 
                    f"G.R. NO. {gr_number}" in response.text or
                    f"G.R. Nos. {gr_number}" in response.text or
                    f"G.R. No.{gr_number}" in response.text):
                    logger.info(f"    ✓ Found at elibrary: {url}")
                    return (response.text, url)
        except Exception as e:
            logger.debug(f"    Error trying {url}: {e}")
            continue
    
    logger.info(f"    ✗ Not found at elibrary")
    return None


def try_lawphil(gr_number: str, title: str, year: int = None, month: str = None) -> Optional[Tuple[str, str]]:
    """
    Try to fetch case from lawphil.net.
    Returns (content, source_url) if found, None otherwise.
    """
    logger.info(f"  Trying lawphil.net for G.R. No. {gr_number}")
    
    # Try different URL patterns for lawphil
    year_prefix = gr_number[:2] if len(gr_number) >= 2 else gr_number
    
    search_patterns = []
    
    # NEW PATTERN FOUND - judjuris directory with year and month (most likely for recent cases)
    if year and month:
        year_str = str(year)
        month_names = {
            'january': 'jan', 'february': 'feb', 'march': 'mar', 'april': 'apr',
            'may': 'may', 'june': 'jun', 'july': 'jul', 'august': 'aug',
            'september': 'sep', 'october': 'oct', 'november': 'nov', 'december': 'dec'
        }
        month_abbr = month_names.get(month.lower(), month[:3].lower())
        
        # Priority patterns - try these first
        search_patterns.extend([
            f"https://lawphil.net/judjuris/juri{year_str}/{month_abbr}{year_str}/gr_{gr_number}_{year_str}.html",
            f"https://www.lawphil.net/judjuris/juri{year_str}/{month_abbr}{year_str}/gr_{gr_number}_{year_str}.html",
        ])
    
    # Standard patterns
    search_patterns.extend([
        f"https://lawphil.net/juris/juri{year_prefix}/juris_{gr_number}.html",
        f"https://lawphil.net/juris/juri{year_prefix}/gr_{gr_number}.html",
        f"https://www.lawphil.net/juris/juri{year_prefix}/gr_{gr_number}.html",
        f"https://www.lawphil.net/juris/juri{year_prefix}/juris_{gr_number}.html",
    ])
    
    # Alternative patterns - only add if gr_number is long enough
    if len(gr_number) >= 4:
        search_patterns.extend([
            f"https://lawphil.net/juris/supreme/supdec/cases{gr_number[:4]}/gr_{gr_number}.html",
            f"https://www.lawphil.net/juris/supreme/supdec/cases{gr_number[:4]}/gr_{gr_number}.html",
        ])
    
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    for url in search_patterns:
        try:
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            if response.status_code == 200 and len(response.text) > 1000:
                # Verify it's the right case
                if f"G.R. No. {gr_number}" in response.text or f"G.R. NO. {gr_number}" in response.text:
                    logger.info(f"    ✓ Found at lawphil: {url}")
                    return (response.text, url)
        except Exception as e:
            logger.debug(f"    Error trying {url}: {e}")
            continue
    
    logger.info(f"    ✗ Not found at lawphil")
    return None


def extract_case_content_from_html(html_content: str, source_url: str) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Extract case content and metadata from HTML.
    Returns (formatted_content, metadata_dict)
    """
    # Remove script and style tags (handle various whitespace and attributes in closing tags)
    # Note: This is for content extraction only, not for XSS prevention
    text = re.sub(r'<script[^>]*>.*?</script[^>]*>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style[^>]*>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Extract metadata
    metadata = {}
    
    # Extract G.R. number - handle multiple case numbers  
    gr_match = re.search(r'G\.R\.\s+No\.?s?\s+(\d+(?:\s*&\s*\d+)?)', text, re.IGNORECASE)
    if gr_match:
        # Extract first number if multiple (e.g., "123 & 456" -> "123")
        gr_text = gr_match.group(1)
        first_num = re.search(r'(\d+)', gr_text)
        if first_num:
            metadata['gr_number'] = first_num.group(1)
    
    # Extract decision date
    date_patterns = [
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,\s+\d{4}',
        r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}'
    ]
    for pattern in date_patterns:
        date_match = re.search(pattern, text)
        if date_match:
            metadata['decision_date'] = date_match.group(0)
            break
    
    # Extract volume and page
    vol_match = re.search(r'(\d+)\s+Phil\.?\s+(\d+)', text)
    if vol_match:
        metadata['volume_page'] = vol_match.group(0)
    
    # Convert HTML to plain text
    text = re.sub(r'<br\s*/?>',  '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decode HTML entities
    entities = {
        '&nbsp;': ' ',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&mdash;': '—',
        '&ndash;': '–',
        '&rsquo;': ''',
        '&lsquo;': ''',
        '&rdquo;': '"',
        '&ldquo;': '"',
    }
    for entity, char in entities.items():
        text = text.replace(entity, char)
    
    # Clean up whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = text.strip()
    
    # Add source information
    metadata['source_url'] = source_url
    
    if len(text) > 500:  # Minimum content length
        return text, metadata
    
    return None, None


def extract_keywords_from_content(content: str, title: str) -> List[str]:
    """
    Extract relevant keywords from case content.
    """
    keywords = []
    
    # Common legal terms to look for
    legal_terms = [
        'constitutional', 'criminal', 'civil', 'administrative', 'labor',
        'commercial', 'tax', 'property', 'family', 'remedial',
        'jurisdiction', 'due process', 'petition', 'appeal', 'certiorari',
        'mandamus', 'prohibition', 'habeas corpus', 'quo warranto',
        'damages', 'injunction', 'preliminary', 'temporary restraining'
    ]
    
    content_lower = content.lower()
    for term in legal_terms:
        if term in content_lower:
            keywords.append(term.title())
    
    # Limit to 10 keywords
    return keywords[:10]


def categorize_case(content: str, title: str) -> List[str]:
    """
    Categorize the case based on content analysis.
    """
    categories = []
    content_lower = content.lower() + ' ' + title.lower()
    
    # Category detection patterns
    category_patterns = {
        'Criminal Law': ['criminal', 'accused', 'prosecution', 'convicted', 'murder', 'homicide', 'theft', 'robbery'],
        'Civil Law': ['civil', 'damages', 'obligation', 'contract', 'tort'],
        'Labor Law': ['labor', 'employee', 'employer', 'nlrc', 'wages', 'termination', 'dismissal'],
        'Commercial Law': ['commercial', 'corporation', 'partnership', 'negotiable instrument', 'banking'],
        'Tax Law': ['tax', 'revenue', 'bir', 'commissioner of internal revenue', 'assessment'],
        'Administrative Law': ['administrative', 'government', 'public officer', 'ombudsman', 'civil service'],
        'Constitutional Law': ['constitutional', 'constitution', 'bill of rights', 'separation of powers'],
        'Family Law': ['family', 'marriage', 'divorce', 'custody', 'adoption', 'annulment'],
        'Property Law': ['property', 'land', 'real estate', 'ownership', 'title', 'cadastral'],
        'Remedial Law': ['remedial', 'procedure', 'jurisdiction', 'appeal', 'certiorari', 'mandamus']
    }
    
    for category, patterns in category_patterns.items():
        for pattern in patterns:
            if pattern in content_lower:
                categories.append(category)
                break
    
    # Default to Civil Law if no category found
    if not categories:
        categories = ['Civil Law']
    
    return categories


def create_case_json(case_info: Dict, content: str, metadata: Dict) -> Dict:
    """
    Create a properly formatted case JSON object matching the database schema.
    """
    # Extract keywords and categories
    keywords = extract_keywords_from_content(content, case_info['title'])
    categories = categorize_case(content, case_info['title'])
    
    case_data = {
        'file_path': f"/scraped_multi_source/{case_info['year']}/{case_info['month']}/{case_info['gr_number']}.html",
        'filename': f"{case_info['gr_number']}.html",
        'year': case_info['year'],
        'month': case_info['month'],
        'case_number': case_info['gr_number'],
        'gr_number': case_info['gr_number'],
        'volume_page': metadata.get('volume_page', ''),
        'decision_date': metadata.get('decision_date', case_info['date']),
        'title': case_info['title'],
        'division': None,
        'categories': categories,
        'keywords': keywords,
        'title_summary': case_info['title'],
        'formatted_case_content': content,
        'content_length': len(content),
        'metadata_extraction_date': datetime.now().isoformat(),
        'extraction_version': '3.0_multi_source_scraper',
        'source_url': metadata.get('source_url', ''),
    }
    
    return case_data


def save_case_to_db(case_data: Dict, db_path: Path) -> bool:
    """
    Save the scraped case to the appropriate location in the database.
    """
    year = case_data['year']
    month = case_data['month']
    gr_number = case_data['gr_number']
    
    # Create directory structure
    target_dir = db_path / str(year) / month
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON file
    target_file = target_dir / f"{gr_number}.json"
    
    try:
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"  ✓ Saved to: {target_file}")
        return True
    except Exception as e:
        logger.error(f"  ✗ Failed to save: {e}")
        return False


def scrape_case(case_info: Dict, db_path: Path) -> bool:
    """
    Attempt to scrape a case from multiple sources.
    Returns True if successful, False otherwise.
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Case: {case_info['title']} (G.R. No. {case_info['gr_number']})")
    logger.info(f"{'='*80}")
    
    # Try sources in priority order
    sources = [
        (try_elibrary_judiciary, [case_info['gr_number'], case_info['title']]),
        (try_lawphil, [case_info['gr_number'], case_info['title'], case_info['year'], case_info['month']]),
    ]
    
    for source_func, args in sources:
        try:
            result = source_func(*args)
            if result:
                html_content, source_url = result
                
                # Extract content and metadata
                content, metadata = extract_case_content_from_html(html_content, source_url)
                
                if not content:
                    logger.warning(f"  ✗ Failed to extract content from {source_url}")
                    continue
                
                logger.info(f"  ✓ Successfully extracted content ({len(content)} chars)")
                
                # Create case JSON
                case_data = create_case_json(case_info, content, metadata)
                
                # Save to database
                if save_case_to_db(case_data, db_path):
                    return True
                
        except Exception as e:
            logger.error(f"  ✗ Error with source: {e}")
            continue
    
    logger.warning(f"  ✗ Failed to scrape from all sources")
    return False


def main():
    """
    Main function to scrape missing cases from multiple sources.
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_missing_cases_multi_source.py <RESTRUCTURED_DB_path>")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    
    if not db_path.exists():
        print(f"Error: {db_path} does not exist")
        sys.exit(1)
    
    logger.info("="*80)
    logger.info("MULTI-SOURCE SCRAPER FOR MISSING CASES (2005-2024)")
    logger.info("="*80)
    logger.info(f"Database path: {db_path}")
    logger.info(f"Cases to scrape: {len(MISSING_CASES)}")
    logger.info(f"Sources: elibrary.judiciary.gov.ph, lawphil.net")
    
    scraped_count = 0
    failed_cases = []
    
    for case in MISSING_CASES:
        # Check if case already exists
        target_file = db_path / str(case['year']) / case['month'] / f"{case['gr_number']}.json"
        if target_file.exists():
            logger.info(f"\n{'='*80}")
            logger.info(f"Case: {case['title']} (G.R. No. {case['gr_number']})")
            logger.info(f"{'='*80}")
            logger.info(f"  ⊙ Already exists, skipping")
            continue
        
        # Scrape the case
        if scrape_case(case, db_path):
            scraped_count += 1
        else:
            failed_cases.append(case)
        
        # Be polite to servers
        time.sleep(3)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("SCRAPING SUMMARY")
    logger.info("="*80)
    logger.info(f"Total cases: {len(MISSING_CASES)}")
    logger.info(f"Successfully scraped: {scraped_count}")
    logger.info(f"Failed: {len(failed_cases)}")
    
    if failed_cases:
        logger.info("\nFailed cases:")
        for case in failed_cases:
            logger.info(f"  - G.R. No. {case['gr_number']}: {case['title']}")
        logger.info("\nThese cases may need to be:")
        logger.info("  1. Searched manually on the court websites")
        logger.info("  2. Obtained through official channels")
        logger.info("  3. May not be publicly available yet")
    
    logger.info("="*80)


if __name__ == '__main__':
    main()
