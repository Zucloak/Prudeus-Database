#!/usr/bin/env python3
"""
Script to scrape missing cases from lawphil.net

Missing cases to scrape:
1. Municipality of Tupi v. Faustino, G.R. No. 231896, Aug. 20, 2019
2. Manuel v. People, G.R. 165842, Nov. 29, 2005
3. Toyo v. Toyo, GR. No. 213198, July 1, 2019
4. Valeroso v. People, G.R. No. 164815, Feb. 22, 2008
5. San Miguel Corp. v. Commissioner of Internal Revenue, G.R. Nos. 257697 & 259446, April 12, 2023
6. Otamias v. Republic, G.R. 189516, Jun. 8, 2016
7. Sanico v. Colipano, G.R. No. 209969, Sept. 27, 2017
8. Film Devt. Council v. Colon, G.R. 203754, Oct 15, 2019
"""

import requests
import json
import re
import time
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

# Define the missing cases
MISSING_CASES = [
    {
        'title': 'Municipality of Tupi v. Faustino',
        'gr_number': '231896',
        'date': '2019-08-20',
        'year': 2019,
        'month': 'august'
    },
    {
        'title': 'Manuel v. People',
        'gr_number': '165842',
        'date': '2005-11-29',
        'year': 2005,
        'month': 'november'
    },
    {
        'title': 'Toyo v. Toyo',
        'gr_number': '213198',
        'date': '2019-07-01',
        'year': 2019,
        'month': 'july'
    },
    {
        'title': 'Valeroso v. People',
        'gr_number': '164815',
        'date': '2008-02-22',
        'year': 2008,
        'month': 'february'
    },
    {
        'title': 'San Miguel Corp. v. Commissioner of Internal Revenue',
        'gr_number': '257697',  # Note: also 259446 - consolidated
        'date': '2023-04-12',
        'year': 2023,
        'month': 'april'
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
        'title': 'Film Development Council v. Colon',
        'gr_number': '203754',
        'date': '2019-10-15',
        'year': 2019,
        'month': 'october'
    }
]


def search_lawphil_for_case(gr_number: str, title: str) -> Optional[str]:
    """
    Search lawphil.net for a case by GR number and title.
    Returns the URL if found, None otherwise.
    """
    logger.info(f"Searching lawphil.net for G.R. No. {gr_number}: {title}")
    
    # Try different search patterns
    search_patterns = [
        f"https://lawphil.net/juris/juri{gr_number[0:2]}/juris_{gr_number}.html",  # Common pattern
        f"https://lawphil.net/juris/juri{gr_number[0:2]}/gr_{gr_number}.html",
        f"https://www.lawphil.net/juris/juri{gr_number[0:2]}/gr_{gr_number}.html",
    ]
    
    for url in search_patterns:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logger.info(f"  ✓ Found at: {url}")
                return url
        except Exception as e:
            continue
    
    logger.warning(f"  ✗ Not found automatically for G.R. No. {gr_number}")
    return None


def extract_case_content_from_html(html_content: str) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Extract case content and metadata from HTML.
    Returns (formatted_content, metadata_dict)
    """
    # Remove HTML tags but preserve structure
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Extract metadata
    metadata = {}
    
    # Extract G.R. number
    gr_match = re.search(r'G\.R\.\s+No\.?\s+(\d+)', text, re.IGNORECASE)
    if gr_match:
        metadata['gr_number'] = gr_match.group(1)
    
    # Extract decision date
    date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,\s+\d{4}', text)
    if date_match:
        metadata['decision_date'] = date_match.group(0)
    
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
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    # Clean up whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = text.strip()
    
    if len(text) > 100:
        return text, metadata
    
    return None, None


def create_case_json(case_info: Dict, content: str, metadata: Dict) -> Dict:
    """
    Create a properly formatted case JSON object.
    """
    case_data = {
        'file_path': f"/scraped_from_lawphil/{case_info['year']}/{case_info['month']}/{case_info['gr_number']}.html",
        'filename': f"{case_info['gr_number']}.html",
        'year': case_info['year'],
        'month': case_info['month'],
        'case_number': case_info['gr_number'],
        'gr_number': case_info['gr_number'],
        'volume_page': metadata.get('volume_page', ''),
        'decision_date': case_info['date'],
        'title': case_info['title'],
        'division': None,
        'categories': ['Civil Law'],  # Default category, can be enhanced
        'keywords': [],  # Can be enhanced with keyword extraction
        'title_summary': case_info['title'],
        'formatted_case_content': content,
        'content_length': len(content),
        'metadata_extraction_date': datetime.now().isoformat(),
        'extraction_version': '2.3_scraped_from_lawphil'
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


def main():
    """
    Main function to scrape missing cases from lawphil.net
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_missing_cases_lawphil.py <RESTRUCTURED_DB_path>")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    
    if not db_path.exists():
        print(f"Error: {db_path} does not exist")
        sys.exit(1)
    
    logger.info("="*80)
    logger.info("SCRAPING MISSING CASES FROM LAWPHIL.NET")
    logger.info("="*80)
    logger.info(f"Database path: {db_path}")
    logger.info(f"Cases to scrape: {len(MISSING_CASES)}")
    
    scraped_count = 0
    failed_count = 0
    
    for case in MISSING_CASES:
        logger.info(f"\n{'='*80}")
        logger.info(f"Case: {case['title']} (G.R. No. {case['gr_number']})")
        logger.info(f"{'='*80}")
        
        # Search for the case
        url = search_lawphil_for_case(case['gr_number'], case['title'])
        
        if not url:
            logger.warning(f"Could not find case automatically. Manual intervention needed.")
            logger.warning(f"Please search manually at: https://lawphil.net")
            failed_count += 1
            continue
        
        # Fetch the case
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                logger.error(f"Failed to fetch case: HTTP {response.status_code}")
                failed_count += 1
                continue
            
            # Extract content
            content, metadata = extract_case_content_from_html(response.text)
            
            if not content:
                logger.error(f"Failed to extract content from case")
                failed_count += 1
                continue
            
            # Create case JSON
            case_data = create_case_json(case, content, metadata)
            
            # Save to database
            if save_case_to_db(case_data, db_path):
                scraped_count += 1
            else:
                failed_count += 1
            
            # Be polite to the server
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error scraping case: {e}")
            failed_count += 1
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("SCRAPING SUMMARY")
    logger.info("="*80)
    logger.info(f"Total cases: {len(MISSING_CASES)}")
    logger.info(f"Successfully scraped: {scraped_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info("="*80)
    
    if failed_count > 0:
        logger.warning("\nSome cases could not be scraped automatically.")
        logger.warning("Please review the logs and scrape them manually from lawphil.net")


if __name__ == '__main__':
    main()
