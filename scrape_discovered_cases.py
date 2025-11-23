#!/usr/bin/env python3
"""
Scrape discovered missing cases from lawphil.net.
This script reads the lawphil_missing_cases.json file and attempts to scrape cases.

Due to the large number of cases (15K+), we'll focus on a subset for demonstration.
"""

import requests
import json
import re
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import logging
from html.parser import HTMLParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

class HTMLStripper(HTMLParser):
    """Simple HTML tag stripper."""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
    
    def handle_data(self, data):
        self.text.append(data)
    
    def get_data(self):
        return ''.join(self.text)

def strip_html(html_text: str) -> str:
    """Remove HTML tags from text."""
    s = HTMLStripper()
    s.feed(html_text)
    return s.get_data()

def extract_month_from_date(date_str: str) -> Optional[str]:
    """Extract month abbreviation from date string like 'December 10, 2018'."""
    months = {
        'january': 'jan', 'february': 'feb', 'march': 'mar',
        'april': 'apr', 'may': 'may', 'june': 'jun',
        'july': 'jul', 'august': 'aug', 'september': 'sep',
        'october': 'oct', 'november': 'nov', 'december': 'dec'
    }
    
    for month_name, month_abbr in months.items():
        if month_name in date_str.lower():
            return month_abbr  # Return abbreviation, not full name
    
    return None

def construct_case_urls(case_info: Dict) -> List[str]:
    """
    Construct possible URLs for a case based on known patterns.
    Returns list of URLs to try in priority order.
    """
    gr_number = case_info['gr_number']
    year = case_info['year']
    date_str = case_info.get('date', '')
    
    # Extract month from date
    month = extract_month_from_date(date_str)
    
    urls = []
    
    if month:
        # Primary pattern: /judjuris/juri{YEAR}/{MONTH}{YEAR}/gr_{GR}_{YEAR}.html
        urls.append(f"https://lawphil.net/judjuris/juri{year}/{month}{year}/gr_{gr_number}_{year}.html")
        
        # Alternative: without year suffix in filename
        urls.append(f"https://lawphil.net/judjuris/juri{year}/{month}{year}/gr_{gr_number}.html")
    
    # Fallback patterns (older structure)
    if year >= 2000:
        yy = str(year)[2:]  # Get last 2 digits
        urls.append(f"https://lawphil.net/juris/juri{yy}/gr_{gr_number}.html")
        urls.append(f"https://lawphil.net/juris/juri{yy}/juris_{gr_number}.html")
    
    return urls

def fetch_case_content(urls: List[str]) -> Optional[Dict]:
    """
    Try to fetch case content from list of URLs.
    Returns dict with content and source URL if successful.
    """
    headers = {'User-Agent': USER_AGENT}
    
    for url in urls:
        try:
            logger.debug(f"Trying {url}")
            response = requests.get(url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                # Verify it's a real case (has G.R. in content)
                if 'G.R.' in response.text or 'G. R.' in response.text:
                    logger.debug(f"✓ Found at {url}")
                    return {
                        'content': response.text,
                        'url': url
                    }
        except Exception as e:
            logger.debug(f"Error accessing {url}: {e}")
            continue
    
    return None

def extract_case_metadata(html_content: str, case_info: Dict) -> Optional[Dict]:
    """Extract metadata from HTML case content."""
    try:
        # Extract title
        title_match = re.search(r'<title>([^<]+)</title>', html_content, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else case_info.get('title', 'Unknown')
        
        # Extract GR number from content
        gr_match = re.search(r'G\.?\s*R\.?\s*No\.?\s*(\d+)', html_content)
        gr_number = gr_match.group(1) if gr_match else case_info['gr_number']
        
        # Extract decision date
        date_match = re.search(r'(\w+ \d+, \d{4})', html_content)
        decision_date = date_match.group(1) if date_match else case_info.get('date', '')
        
        # Extract year and month
        year = case_info['year']
        month = extract_month_from_date(decision_date) or 'unknown'
        
        # Clean and extract body content
        # Look for the main decision text
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            body_html = body_match.group(1)
            formatted_content = strip_html(body_html)
            # Clean up extra whitespace
            formatted_content = re.sub(r'\n\s*\n', '\n\n', formatted_content)
            formatted_content = formatted_content.strip()
        else:
            formatted_content = strip_html(html_content)
        
        return {
            'title': title,
            'gr_number': f"G.R. No. {gr_number}",
            'decision_date': decision_date,
            'year': year,
            'month': month,
            'formatted_case_content': formatted_content,
            'content_length': len(formatted_content)
        }
    
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        return None

def categorize_case(content: str, title: str) -> List[str]:
    """Simple categorization based on keywords."""
    text = (content + " " + title).lower()
    
    categories = []
    
    keywords_map = {
        'Criminal Law': ['criminal', 'murder', 'homicide', 'theft', 'robbery', 'rape', 'fraud'],
        'Civil Law': ['civil', 'damages', 'obligation', 'contract'],
        'Labor Law': ['labor', 'employee', 'employer', 'nlrc', 'termination', 'wage'],
        'Commercial Law': ['commercial', 'corporation', 'partnership', 'negotiable'],
        'Tax Law': ['tax', 'revenue', 'bir', 'commissioner of internal revenue', 'vat'],
        'Administrative Law': ['administrative', 'government', 'public officer', 'civil service'],
        'Constitutional Law': ['constitutional', 'bill of rights', 'due process', 'equal protection'],
        'Family Law': ['family', 'marriage', 'divorce', 'adoption', 'child custody'],
        'Property Law': ['property', 'land', 'ownership', 'title', 'real estate'],
        'Remedial Law': ['procedure', 'jurisdiction', 'appeal', 'motion', 'certiorari']
    }
    
    for category, keywords in keywords_map.items():
        if any(keyword in text for keyword in keywords):
            categories.append(category)
    
    if not categories:
        categories.append('Civil Law')  # Default
    
    return categories[:3]  # Limit to top 3

def extract_keywords(content: str, title: str) -> List[str]:
    """Extract keywords from case."""
    text = (title + " " + content[:2000]).lower()
    
    # Common legal keywords
    legal_terms = ['jurisdiction', 'appeal', 'damages', 'evidence', 'procedure',
                   'contract', 'liability', 'negligence', 'statutory', 'constitutional',
                   'administrative', 'criminal', 'civil', 'labor', 'tax']
    
    keywords = [term for term in legal_terms if term in text]
    
    return keywords[:10]  # Limit to 10

def save_case_to_db(case_data: Dict, db_path: str) -> bool:
    """Save case to database in proper structure."""
    try:
        year = case_data['year']
        month = case_data['month']
        gr_number = case_data['gr_number'].replace('G.R. No. ', '').replace('G.R.No.', '').strip()
        
        # Create directory structure
        year_path = Path(db_path) / str(year)
        month_path = year_path / month
        month_path.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        filename = f"{gr_number}.json"
        file_path = month_path / filename
        
        # Check if already exists
        if file_path.exists():
            logger.info(f"  Case already exists: {file_path}")
            return False
        
        # Build complete case data
        complete_data = {
            'file_path': str(file_path.relative_to(db_path)),
            'filename': filename,
            'year': year,
            'month': month,
            'case_number': gr_number,
            'gr_number': case_data['gr_number'],
            'volume_page': '',  # Not available
            'decision_date': case_data.get('decision_date', ''),
            'title': case_data['title'],
            'division': None,
            'categories': categorize_case(case_data['formatted_case_content'], case_data['title']),
            'keywords': extract_keywords(case_data['formatted_case_content'], case_data['title']),
            'title_summary': case_data['title'][:200],
            'formatted_case_content': case_data['formatted_case_content'],
            'content_length': case_data['content_length'],
            'metadata_extraction_date': datetime.utcnow().isoformat() + 'Z',
            'extraction_version': '2.0-lawphil-bulk-scrape'
        }
        
        # Save to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(complete_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"  ✓ Saved: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"  Error saving case: {e}")
        return False

def scrape_cases_batch(cases: List[Dict], db_path: str, max_cases: int = None) -> Dict:
    """Scrape a batch of cases."""
    stats = {
        'attempted': 0,
        'successful': 0,
        'failed': 0,
        'already_exists': 0
    }
    
    cases_to_process = cases[:max_cases] if max_cases else cases
    
    for i, case in enumerate(cases_to_process, 1):
        logger.info(f"\n[{i}/{len(cases_to_process)}] Processing G.R. No. {case['gr_number']}")
        logger.info(f"  Title: {case['title'][:60]}...")
        
        stats['attempted'] += 1
        
        # Construct possible URLs
        urls = construct_case_urls(case)
        
        # Try to fetch content
        result = fetch_case_content(urls)
        
        if not result:
            logger.warning(f"  ✗ Could not fetch case from any URL")
            stats['failed'] += 1
            continue
        
        # Extract metadata
        metadata = extract_case_metadata(result['content'], case)
        
        if not metadata:
            logger.warning(f"  ✗ Could not extract metadata")
            stats['failed'] += 1
            continue
        
        # Save to database
        saved = save_case_to_db(metadata, db_path)
        
        if saved:
            stats['successful'] += 1
        else:
            stats['already_exists'] += 1
        
        # Rate limiting
        time.sleep(0.5)  # Be respectful to the server
    
    return stats

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_discovered_cases.py <RESTRUCTURED_DB_path> [max_cases]")
        sys.exit(1)
    
    db_path = sys.argv[1]
    max_cases = int(sys.argv[2]) if len(sys.argv) > 2 else 100  # Default: scrape 100 cases
    
    # Load discovered cases
    with open('lawphil_missing_cases.json') as f:
        all_cases = json.load(f)
    
    logger.info("=" * 80)
    logger.info(f"SCRAPING DISCOVERED MISSING CASES")
    logger.info("=" * 80)
    logger.info(f"Total cases available: {len(all_cases)}")
    logger.info(f"Will process: {min(max_cases, len(all_cases))} cases")
    logger.info(f"Database path: {db_path}")
    logger.info("=" * 80)
    
    # Scrape cases
    stats = scrape_cases_batch(all_cases, db_path, max_cases)
    
    # Report results
    logger.info("\n" + "=" * 80)
    logger.info("SCRAPING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Cases attempted: {stats['attempted']}")
    logger.info(f"Successfully scraped: {stats['successful']}")
    logger.info(f"Already existed: {stats['already_exists']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Success rate: {stats['successful'] / stats['attempted'] * 100:.1f}%")
    logger.info("=" * 80)

if __name__ == '__main__':
    main()
