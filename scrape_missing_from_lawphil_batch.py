#!/usr/bin/env python3
"""
Batch scraper for missing Philippine Supreme Court cases from lawphil.net

This script attempts to scrape the 13,663 missing cases identified in lawphil_missing_cases.json
It uses multiple URL patterns and implements batching, retry logic, and progress tracking.

Usage:
    python3 scrape_missing_from_lawphil_batch.py RESTRUCTURED_DB [--batch-size 100] [--start-year 2005] [--end-year 2024]
"""

import json
import requests
import re
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraping_batch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


class LawphilBatchScraper:
    """Scraper for missing cases from lawphil.net with batch processing"""
    
    def __init__(self, db_path: Path, batch_size: int = 100, rate_limit: float = 2.0):
        self.db_path = db_path
        self.batch_size = batch_size
        self.rate_limit = rate_limit  # Configurable delay between requests
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})
        
        self.stats = {
            'total': 0,
            'attempted': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
        }
        
    def construct_lawphil_urls(self, gr_number: str, year: int, date_str: str = '') -> List[str]:
        """
        Construct possible lawphil.net URLs for a case.
        Uses the judjuris structure: https://lawphil.net/judjuris/juri{YYYY}/{month}{YYYY}/
        """
        # Extract month from date string
        month_abbrev = self.extract_month_abbrev(date_str)
        
        # Determine case type prefix (gr, ac, am, etc.)
        # Most cases are G.R., but we'll try multiple prefixes
        case_prefixes = ['gr', 'ac', 'am', 'am_rtj', 'am_mtj', 'am_p']
        
        urls = []
        
        # Primary pattern: judjuris/juriYYYY/monthYYYY/{prefix}_{number}_{year}.html
        for prefix in case_prefixes:
            if month_abbrev:
                urls.append(
                    f"https://lawphil.net/judjuris/juri{year}/{month_abbrev}{year}/{prefix}_{gr_number}_{year}.html"
                )
        
        # Also try without month (some cases may be organized differently)
        for prefix in case_prefixes:
            urls.append(
                f"https://lawphil.net/judjuris/juri{year}/{prefix}_{gr_number}_{year}.html"
            )
        
        # Fallback: old juris structure
        yy = str(year)[-2:]
        urls.extend([
            f"https://lawphil.net/juris/juri{yy}/gr_{gr_number}_{year}.html",
            f"https://lawphil.net/juris/juri{yy}/gr_{gr_number}.html",
        ])
        
        return urls
    
    def extract_month_abbrev(self, date_str: str) -> str:
        """Extract 3-letter month abbreviation from date string"""
        if not date_str:
            return ''
        
        month_map = {
            'january': 'jan', 'february': 'feb', 'march': 'mar',
            'april': 'apr', 'may': 'may', 'june': 'jun',
            'july': 'jul', 'august': 'aug', 'september': 'sep',
            'october': 'oct', 'november': 'nov', 'december': 'dec'
        }
        
        date_lower = date_str.lower()
        for month_full, month_short in month_map.items():
            if month_full in date_lower:
                return month_short
        
        return ''
    
    def fetch_case_from_url(self, url: str, timeout: int = 15) -> Optional[str]:
        """Fetch case content from a URL"""
        try:
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            
            if response.status_code == 200 and len(response.text) > 500:
                # More robust content validation - check for multiple indicators
                text = response.text.upper()
                has_gr = 'G.R. NO' in text or 'G.R.NO' in text
                has_court = 'SUPREME COURT' in text or 'REPUBLIC OF THE PHILIPPINES' in text
                has_decision = 'DECISION' in text or 'RESOLUTION' in text
                not_error = '404' not in text and 'NOT FOUND' not in text[:500]
                
                # Must have at least 2 indicators and not be an error page
                indicators = sum([has_gr, has_court, has_decision, not_error])
                if indicators >= 2:
                    return response.text
            
            return None
            
        except Exception as e:
            logger.debug(f"  Error fetching {url}: {e}")
            return None
    
    def scrape_case(self, case_info: Dict) -> Optional[Dict]:
        """
        Attempt to scrape a single case from lawphil.net
        """
        gr_number = case_info['gr_number']
        year = case_info['year']
        title = case_info.get('title', '')
        date_str = case_info.get('date', '')
        
        logger.info(f"Scraping G.R. No. {gr_number} ({year}): {title[:50]}...")
        
        # Construct possible URLs
        urls = self.construct_lawphil_urls(gr_number, year, date_str)
        
        # Try each URL
        for url in urls:
            logger.debug(f"  Trying: {url}")
            content = self.fetch_case_from_url(url)
            
            if content:
                logger.info(f"  ✓ Found at: {url}")
                
                # Extract metadata and clean content
                case_data = self.process_case_content(content, case_info, url)
                if case_data:
                    return case_data
            
            # Small delay between attempts
            time.sleep(0.3)
        
        logger.warning(f"  ✗ Not found for G.R. No. {gr_number}")
        return None
    
    def process_case_content(self, html_content: str, case_info: Dict, source_url: str) -> Optional[Dict]:
        """
        Process HTML content and create case JSON object
        """
        try:
            # Clean HTML to plain text
            text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(r'<p[^>]*>', '\n\n', text, flags=re.IGNORECASE)
            text = re.sub(r'<[^>]+>', '', text)
            
            # Decode HTML entities
            text = text.replace('&nbsp;', ' ')
            text = text.replace('&amp;', '&')
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&quot;', '"')
            text = text.replace('&#39;', "'")
            
            # Clean whitespace
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            text = text.strip()
            
            if len(text) < 200:
                return None
            
            # Extract metadata from content
            metadata = self.extract_metadata(text)
            
            # Determine month from date
            month = self.extract_month_from_date(case_info.get('date', ''))
            
            # Create case data object
            case_data = {
                'file_path': f"/scraped/{case_info['year']}/{month}/{case_info['gr_number']}.json",
                'filename': f"{case_info['gr_number']}.json",
                'year': case_info['year'],
                'month': month,
                'case_number': case_info['gr_number'],
                'gr_number': case_info['gr_number'],
                'volume_page': metadata.get('volume_page', ''),
                'decision_date': case_info.get('date', ''),
                'title': case_info.get('title', f"G.R. No. {case_info['gr_number']}"),
                'division': None,
                'categories': self.categorize_case(text),
                'keywords': self.extract_keywords(text),
                'title_summary': case_info.get('title', f"G.R. No. {case_info['gr_number']}"),
                'formatted_case_content': text,
                'content_length': len(text),
                'metadata_extraction_date': datetime.now().isoformat(),
                'extraction_version': '3.0_lawphil_batch_scraper',
                'source_url': source_url
            }
            
            return case_data
            
        except Exception as e:
            logger.error(f"Error processing content: {e}")
            return None
    
    def extract_metadata(self, text: str) -> Dict:
        """Extract metadata like volume/page from case content"""
        metadata = {}
        
        # Extract volume and page
        vol_match = re.search(r'(\d+)\s+Phil\.?\s+(\d+)', text[:1000])
        if vol_match:
            metadata['volume_page'] = vol_match.group(0)
        
        return metadata
    
    def extract_month_from_date(self, date_str: str) -> str:
        """Extract month name from date string"""
        if not date_str:
            return 'january'
        
        months = {
            'january': 'january', 'february': 'february', 'march': 'march',
            'april': 'april', 'may': 'may', 'june': 'june',
            'july': 'july', 'august': 'august', 'september': 'september',
            'october': 'october', 'november': 'november', 'december': 'december'
        }
        
        date_lower = date_str.lower()
        for month in months:
            if month in date_lower:
                return months[month]
        
        return 'january'
    
    def categorize_case(self, text: str) -> List[str]:
        """Simple categorization based on keywords"""
        categories = []
        text_upper = text.upper()
        
        if any(kw in text_upper for kw in ['CRIMINAL', 'ACCUSED', 'ROBBERY', 'MURDER', 'THEFT']):
            categories.append('Criminal Law')
        if any(kw in text_upper for kw in ['LABOR', 'EMPLOYEE', 'EMPLOYER', 'NLRC']):
            categories.append('Labor Law')
        if any(kw in text_upper for kw in ['TAX', 'REVENUE', 'BIR', 'COMMISSIONER OF INTERNAL']):
            categories.append('Tax Law')
        if any(kw in text_upper for kw in ['CONTRACT', 'COMMERCIAL', 'CORPORATION']):
            categories.append('Commercial Law')
        
        if not categories:
            categories.append('Civil Law')
        
        return categories
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract basic keywords from case"""
        # Simple keyword extraction - just use the first few relevant words
        words = text.split()[:200]
        keywords = []
        
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word).lower()
            if len(word_clean) > 4 and word_clean.isalpha():
                keywords.append(word_clean)
                if len(keywords) >= 10:
                    break
        
        return keywords[:10]
    
    def save_case(self, case_data: Dict) -> bool:
        """Save case to database"""
        try:
            year = case_data['year']
            month = case_data['month']
            gr_number = case_data['gr_number']
            
            # Create directory structure
            target_dir = self.db_path / str(year) / month
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Save JSON file
            target_file = target_dir / f"{gr_number}.json"
            
            # Check if file already exists
            if target_file.exists():
                logger.info(f"  ⚠ File already exists: {target_file}")
                return False
            
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(case_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  ✓ Saved: {target_file}")
            return True
            
        except Exception as e:
            logger.error(f"  ✗ Error saving case: {e}")
            return False
    
    def scrape_batch(self, cases: List[Dict]) -> Dict:
        """Scrape a batch of cases"""
        batch_stats = {'successful': 0, 'failed': 0, 'skipped': 0}
        
        for case in cases:
            self.stats['attempted'] += 1
            
            # Check if case already exists
            gr_num = case['gr_number']
            year = case['year']
            month = self.extract_month_from_date(case.get('date', ''))
            
            existing_file = self.db_path / str(year) / month / f"{gr_num}.json"
            if existing_file.exists():
                logger.debug(f"Skipping G.R. No. {gr_num} - already exists")
                batch_stats['skipped'] += 1
                self.stats['skipped'] += 1
                continue
            
            # Attempt to scrape
            case_data = self.scrape_case(case)
            
            if case_data and self.save_case(case_data):
                batch_stats['successful'] += 1
                self.stats['successful'] += 1
            else:
                batch_stats['failed'] += 1
                self.stats['failed'] += 1
            
            # Rate limiting - be nice to the server (configurable)
            time.sleep(self.rate_limit)
        
        return batch_stats


def main():
    parser = argparse.ArgumentParser(description='Batch scrape missing cases from lawphil.net')
    parser.add_argument('db_path', type=Path, help='Path to RESTRUCTURED_DB directory')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of cases per batch')
    parser.add_argument('--start-year', type=int, default=2005, help='Starting year')
    parser.add_argument('--end-year', type=int, default=2024, help='Ending year')
    parser.add_argument('--max-cases', type=int, help='Maximum number of cases to scrape (for testing)')
    parser.add_argument('--rate-limit', type=float, default=2.0, help='Delay in seconds between requests (default: 2.0)')
    
    args = parser.parse_args()
    
    if not args.db_path.exists():
        logger.error(f"Database path does not exist: {args.db_path}")
        return 1
    
    # Load missing cases
    logger.info("Loading missing cases list...")
    with open('lawphil_missing_cases.json') as f:
        all_missing = json.load(f)
    
    # Filter by year range
    missing_cases = [
        case for case in all_missing
        if args.start_year <= case['year'] <= args.end_year
    ]
    
    if args.max_cases:
        missing_cases = missing_cases[:args.max_cases]
    
    logger.info("="*80)
    logger.info("LAWPHIL BATCH SCRAPER")
    logger.info("="*80)
    logger.info(f"Database path: {args.db_path}")
    logger.info(f"Cases to scrape: {len(missing_cases)}")
    logger.info(f"Year range: {args.start_year}-{args.end_year}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("="*80)
    
    # Initialize scraper
    scraper = LawphilBatchScraper(args.db_path, args.batch_size, args.rate_limit)
    scraper.stats['total'] = len(missing_cases)
    
    # Process in batches
    start_time = time.time()
    
    for i in range(0, len(missing_cases), args.batch_size):
        batch = missing_cases[i:i+args.batch_size]
        batch_num = (i // args.batch_size) + 1
        total_batches = (len(missing_cases) + args.batch_size - 1) // args.batch_size
        
        logger.info(f"\n{'='*80}")
        logger.info(f"BATCH {batch_num}/{total_batches} ({len(batch)} cases)")
        logger.info(f"{'='*80}")
        
        batch_stats = scraper.scrape_batch(batch)
        
        logger.info(f"\nBatch {batch_num} complete:")
        logger.info(f"  Successful: {batch_stats['successful']}")
        logger.info(f"  Failed: {batch_stats['failed']}")
        logger.info(f"  Skipped: {batch_stats['skipped']}")
        logger.info(f"\nOverall progress: {scraper.stats['attempted']}/{scraper.stats['total']} cases")
    
    # Final summary
    elapsed_time = time.time() - start_time
    
    logger.info("\n" + "="*80)
    logger.info("SCRAPING COMPLETE")
    logger.info("="*80)
    logger.info(f"Total cases attempted: {scraper.stats['attempted']}")
    logger.info(f"Successfully scraped: {scraper.stats['successful']}")
    logger.info(f"Failed: {scraper.stats['failed']}")
    logger.info(f"Skipped (already exist): {scraper.stats['skipped']}")
    logger.info(f"Success rate: {(scraper.stats['successful'] / max(scraper.stats['attempted'] - scraper.stats['skipped'], 1)) * 100:.1f}%")
    logger.info(f"Time elapsed: {elapsed_time/60:.1f} minutes")
    logger.info("="*80)
    
    return 0


if __name__ == '__main__':
    exit(main())
