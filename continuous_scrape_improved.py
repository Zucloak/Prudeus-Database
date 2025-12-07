#!/usr/bin/env python3
"""
Improved continuous scraping script that:
1. Scrapes cases in batches
2. Updates lawphil_missing_cases.json to remove successfully scraped cases
3. Can be safely interrupted and resumed
"""

import requests
import json
import re
import time
import os
from pathlib import Path
from datetime import datetime, timezone
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
    """Extract month abbreviation from date string."""
    months = {
        'january': 'jan', 'february': 'feb', 'march': 'mar',
        'april': 'apr', 'may': 'may', 'june': 'jun',
        'july': 'jul', 'august': 'aug', 'september': 'sep',
        'october': 'oct', 'november': 'nov', 'december': 'dec'
    }
    
    for month_name, month_abbr in months.items():
        if month_name in date_str.lower():
            return month_abbr
    
    return None

def construct_case_urls(case_info: Dict) -> List[str]:
    """Construct possible URLs for a case based on known patterns."""
    gr_number = case_info['gr_number']
    year = case_info['year']
    date_str = case_info.get('date', '')
    
    month = extract_month_from_date(date_str)
    
    urls = []
    
    if month:
        urls.append(f"https://lawphil.net/judjuris/juri{year}/{month}{year}/gr_{gr_number}_{year}.html")
        urls.append(f"https://lawphil.net/judjuris/juri{year}/{month}{year}/gr_{gr_number}.html")
    
    if year >= 2000:
        yy = str(year)[2:]
        urls.append(f"https://lawphil.net/juris/juri{yy}/gr_{gr_number}.html")
        urls.append(f"https://lawphil.net/juris/juri{yy}/juris_{gr_number}.html")
    
    return urls

def fetch_case_content(urls: List[str]) -> Optional[Dict]:
    """Try to fetch case content from list of URLs."""
    headers = {'User-Agent': USER_AGENT}
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                if 'G.R.' in response.text or 'G. R.' in response.text:
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
        title_match = re.search(r'<title>([^<]+)</title>', html_content, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else case_info.get('title', 'Unknown')
        
        gr_match = re.search(r'G\.?\s*R\.?\s*No\.?\s*(\d+)', html_content)
        gr_number = gr_match.group(1) if gr_match else case_info['gr_number']
        
        date_match = re.search(r'(\w+ \d+, \d{4})', html_content)
        decision_date = date_match.group(1) if date_match else case_info.get('date', '')
        
        year = case_info['year']
        month = extract_month_from_date(decision_date) or 'unknown'
        
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            body_html = body_match.group(1)
            formatted_content = strip_html(body_html)
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
        categories.append('Civil Law')
    
    return categories[:3]

def extract_keywords(content: str, title: str) -> List[str]:
    """Extract keywords from case."""
    text = (title + " " + content[:2000]).lower()
    
    legal_terms = ['jurisdiction', 'appeal', 'damages', 'evidence', 'procedure',
                   'contract', 'liability', 'negligence', 'statutory', 'constitutional',
                   'administrative', 'criminal', 'civil', 'labor', 'tax']
    
    keywords = [term for term in legal_terms if term in text]
    
    return keywords[:10]

def save_case_to_db(case_data: Dict, db_path: str) -> bool:
    """Save case to database in proper structure."""
    try:
        year = case_data['year']
        month = case_data['month']
        gr_number = case_data['gr_number'].replace('G.R. No. ', '').replace('G.R.No.', '').strip()
        
        year_path = Path(db_path) / str(year)
        month_path = year_path / month
        month_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"{gr_number}.json"
        file_path = month_path / filename
        
        if file_path.exists():
            logger.info(f"  Case already exists: {file_path}")
            return False
        
        complete_data = {
            'file_path': str(file_path.relative_to(db_path)),
            'filename': filename,
            'year': year,
            'month': month,
            'case_number': gr_number,
            'gr_number': case_data['gr_number'],
            'volume_page': '',
            'decision_date': case_data.get('decision_date', ''),
            'title': case_data['title'],
            'division': None,
            'categories': categorize_case(case_data['formatted_case_content'], case_data['title']),
            'keywords': extract_keywords(case_data['formatted_case_content'], case_data['title']),
            'title_summary': case_data['title'][:200],
            'formatted_case_content': case_data['formatted_case_content'],
            'content_length': case_data['content_length'],
            'metadata_extraction_date': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'extraction_version': '2.0-lawphil-bulk-scrape'
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(complete_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"  ✓ Saved: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"  Error saving case: {e}")
        return False

def scrape_cases_batch(cases: List[Dict], db_path: str, max_cases: int = None) -> Dict:
    """Scrape a batch of cases and return list of successfully scraped case indices."""
    stats = {
        'attempted': 0,
        'successful': 0,
        'failed': 0,
        'already_exists': 0,
        'scraped_indices': []  # Track which cases were successfully scraped
    }
    
    cases_to_process = cases[:max_cases] if max_cases else cases
    
    for i, case in enumerate(cases_to_process):
        logger.info(f"\n[{i+1}/{len(cases_to_process)}] Processing G.R. No. {case['gr_number']}")
        logger.info(f"  Title: {case['title'][:60]}...")
        
        stats['attempted'] += 1
        
        urls = construct_case_urls(case)
        result = fetch_case_content(urls)
        
        if not result:
            logger.warning(f"  ✗ Could not fetch case from any URL")
            stats['failed'] += 1
            continue
        
        metadata = extract_case_metadata(result['content'], case)
        
        if not metadata:
            logger.warning(f"  ✗ Could not extract metadata")
            stats['failed'] += 1
            continue
        
        saved = save_case_to_db(metadata, db_path)
        
        if saved:
            stats['successful'] += 1
            stats['scraped_indices'].append(i)
        else:
            stats['already_exists'] += 1
        
        time.sleep(0.5)
    
    return stats

def update_missing_cases_file(missing_cases_file: str, scraped_indices: List[int]):
    """Remove successfully scraped cases from the missing cases file."""
    try:
        with open(missing_cases_file, 'r') as f:
            all_cases = json.load(f)
        
        # Remove scraped cases (in reverse order to maintain indices)
        for index in sorted(scraped_indices, reverse=True):
            if 0 <= index < len(all_cases):
                del all_cases[index]
        
        # Save updated list
        with open(missing_cases_file, 'w') as f:
            json.dump(all_cases, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\n✓ Updated {missing_cases_file}: removed {len(scraped_indices)} scraped cases")
        logger.info(f"  Remaining cases: {len(all_cases)}")
        
    except Exception as e:
        logger.error(f"Error updating missing cases file: {e}")

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 continuous_scrape_improved.py <RESTRUCTURED_DB_path> [max_cases]")
        sys.exit(1)
    
    db_path = sys.argv[1]
    max_cases = int(sys.argv[2]) if len(sys.argv) > 2 else 500
    missing_cases_file = 'lawphil_missing_cases.json'
    
    # Load discovered cases
    with open(missing_cases_file) as f:
        all_cases = json.load(f)
    
    logger.info("=" * 80)
    logger.info(f"CONTINUOUS SCRAPING SESSION")
    logger.info("=" * 80)
    logger.info(f"Total cases remaining: {len(all_cases)}")
    logger.info(f"Will process: {min(max_cases, len(all_cases))} cases")
    logger.info(f"Database path: {db_path}")
    logger.info("=" * 80)
    
    # Scrape cases
    stats = scrape_cases_batch(all_cases, db_path, max_cases)
    
    # Update missing cases file
    if stats['scraped_indices']:
        update_missing_cases_file(missing_cases_file, stats['scraped_indices'])
    
    # Report results
    logger.info("\n" + "=" * 80)
    logger.info("BATCH COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Cases attempted: {stats['attempted']}")
    logger.info(f"Successfully scraped: {stats['successful']}")
    logger.info(f"Already existed: {stats['already_exists']}")
    logger.info(f"Failed: {stats['failed']}")
    if stats['attempted'] > 0:
        logger.info(f"Success rate: {stats['successful'] / stats['attempted'] * 100:.1f}%")
    logger.info("=" * 80)

if __name__ == '__main__':
    main()
