#!/usr/bin/env python3
"""
Enhanced Supreme Court Case Scraper with Multiple Sources

This script attempts to scrape cases from multiple sources in order:
1. Supreme Court E-Library (https://elibrary.judiciary.gov.ph/)
2. ChanRobles Virtual Law Library (https://www.chanrobles.com/)
3. Lawphil.net (fallback)

Includes batch commit support, deduplication, and comprehensive error handling.
"""

import json
import requests
import re
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import logging
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Priority cases to scrape
SCRAPING_TARGETS = [
    {
        'gr_number': '231896',
        'title': 'Municipality of Tupi v. Faustino',
        'year': 2019,
        'month': 'august',
        'decision_date': '2019-08-20'
    },
    {
        'gr_number': '165842',
        'title': 'Manuel v. People',
        'year': 2005,
        'month': 'november',
        'decision_date': '2005-11-29'
    },
    {
        'gr_number': '213198',
        'title': 'Toyo v. Toyo',
        'year': 2019,
        'month': 'july',
        'decision_date': '2019-07-01'
    },
    {
        'gr_number': '164815',
        'title': 'Valeroso v. People',
        'year': 2008,
        'month': 'february',
        'decision_date': '2008-02-22'
    },
    {
        'gr_number': '257697',
        'title': 'San Miguel v. Commissioner',
        'year': 2023,
        'month': 'april',
        'decision_date': '2023-04-12'
    },
    {
        'gr_number': '189516',
        'title': 'Otamias v. Republic',
        'year': 2016,
        'month': 'june',
        'decision_date': '2016-06-08'
    },
    {
        'gr_number': '209969',
        'title': 'Sanico v. Colipano',
        'year': 2017,
        'month': 'september',
        'decision_date': '2017-09-27'
    },
    {
        'gr_number': '203754',
        'title': 'Film Devt. Council v. Colon',
        'year': 2019,
        'month': 'october',
        'decision_date': '2019-10-15'
    }
]


class MultiSourceScraper:
    """Scrapes cases from multiple sources with fallback support"""
    
    def __init__(self, db_path: Path, batch_size: int = 250):
        self.db_path = db_path
        self.batch_size = batch_size
        self.scraped_files: List[Path] = []
        self.failed_cases: List[Dict] = []
        self.sources_tried: Dict[str, int] = {
            'sc_elibrary': 0,
            'chanrobles': 0,
            'lawphil': 0
        }
        
    def search_sc_elibrary(self, gr_number: str, title: str) -> Optional[str]:
        """Search Supreme Court E-Library for a case"""
        logger.info(f"Searching SC E-Library for G.R. No. {gr_number}")
        self.sources_tried['sc_elibrary'] += 1
        
        try:
            # Try direct search URL patterns
            search_urls = [
                f"https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/{gr_number}",
                f"https://elibrary.judiciary.gov.ph/thebookshelf/showdocsfulltext/{gr_number}",
            ]
            
            for url in search_urls:
                try:
                    response = requests.get(url, timeout=15, allow_redirects=True)
                    if response.status_code == 200 and len(response.text) > 500:
                        logger.info(f"  ✓ Found at: {url}")
                        return response.text
                    time.sleep(0.5)
                except Exception as e:
                    logger.debug(f"  Failed URL {url}: {e}")
                    continue
            
            # Try search interface
            search_url = "https://elibrary.judiciary.gov.ph/thebookshelf/search"
            try:
                response = requests.post(
                    search_url,
                    data={'q': f'G.R. No. {gr_number}'},
                    timeout=15
                )
                if response.status_code == 200 and len(response.text) > 500:
                    # Parse search results to find case link
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.find_all('a', href=True)
                    for link in links:
                        if gr_number in link.get('href', '') or gr_number in link.text:
                            case_url = link['href']
                            if not case_url.startswith('http'):
                                case_url = f"https://elibrary.judiciary.gov.ph{case_url}"
                            
                            case_response = requests.get(case_url, timeout=15)
                            if case_response.status_code == 200:
                                logger.info(f"  ✓ Found via search at: {case_url}")
                                return case_response.text
            except Exception as e:
                logger.debug(f"  Search interface failed: {e}")
            
            logger.warning(f"  ✗ Not found on SC E-Library")
            return None
            
        except Exception as e:
            logger.error(f"  ✗ SC E-Library error: {e}")
            return None
    
    def search_chanrobles(self, gr_number: str, title: str) -> Optional[str]:
        """Search ChanRobles Virtual Law Library for a case"""
        logger.info(f"Searching ChanRobles for G.R. No. {gr_number}")
        self.sources_tried['chanrobles'] += 1
        
        try:
            # Try different ChanRobles URL patterns
            patterns = [
                f"https://www.chanrobles.com/scdecisions/jurisprudence{gr_number[:2]}/gr_{gr_number}.php",
                f"https://www.chanrobles.com/cralaw/decisions/gr_{gr_number}.html",
                f"https://chanrobles.com/scdecisions/jurisprudence{gr_number[:2]}/gr_{gr_number}.php",
            ]
            
            for url in patterns:
                try:
                    response = requests.get(url, timeout=15, allow_redirects=True)
                    if response.status_code == 200 and len(response.text) > 500:
                        logger.info(f"  ✓ Found at: {url}")
                        return response.text
                    time.sleep(0.5)
                except Exception as e:
                    continue
            
            # Try search
            search_url = "https://www.chanrobles.com/search"
            try:
                response = requests.get(
                    search_url,
                    params={'q': f'G.R. No. {gr_number}'},
                    timeout=15
                )
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    links = soup.find_all('a', href=True)
                    for link in links:
                        if gr_number in link.get('href', ''):
                            case_url = link['href']
                            if not case_url.startswith('http'):
                                case_url = f"https://www.chanrobles.com{case_url}"
                            
                            case_response = requests.get(case_url, timeout=15)
                            if case_response.status_code == 200:
                                logger.info(f"  ✓ Found via search at: {case_url}")
                                return case_response.text
            except Exception as e:
                logger.debug(f"  Search failed: {e}")
            
            logger.warning(f"  ✗ Not found on ChanRobles")
            return None
            
        except Exception as e:
            logger.error(f"  ✗ ChanRobles error: {e}")
            return None
    
    def search_lawphil(self, gr_number: str) -> Optional[str]:
        """Search lawphil.net for a case (fallback)"""
        logger.info(f"Searching lawphil.net for G.R. No. {gr_number}")
        self.sources_tried['lawphil'] += 1
        
        patterns = [
            f"https://lawphil.net/juris/juri{gr_number[:2]}/juris_{gr_number}.html",
            f"https://lawphil.net/juris/juri{gr_number[:2]}/gr_{gr_number}.html",
            f"https://www.lawphil.net/juris/juri{gr_number[:2]}/juris_{gr_number}.html",
            f"https://www.lawphil.net/juris/juri{gr_number[:2]}/gr_{gr_number}.html",
        ]
        
        for url in patterns:
            try:
                response = requests.get(url, timeout=15, allow_redirects=True)
                if response.status_code == 200 and len(response.text) > 500:
                    logger.info(f"  ✓ Found at: {url}")
                    return response.text
                time.sleep(0.5)
            except:
                continue
        
        logger.warning(f"  ✗ Not found on lawphil.net")
        return None
    
    def extract_case_from_html(self, html: str, case_info: Dict, source: str) -> Optional[Dict]:
        """Extract case content and metadata from HTML"""
        try:
            # Remove script and style tags
            text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            
            # Extract metadata
            metadata = {}
            
            # Extract volume and page
            vol_match = re.search(r'(\d+)\s+Phil\.?\s+(\d+)', text)
            if vol_match:
                metadata['volume_page'] = vol_match.group(0)
            
            # Convert HTML to text
            text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
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
            
            # Clean whitespace
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            text = text.strip()
            
            # Validate content length
            if len(text) < 500:
                logger.warning(f"  Content too short: {len(text)} chars")
                return None
            
            # Build case data
            case_data = {
                'file_path': f"/scraped_from_{source}/{case_info['year']}/{case_info['month']}/{case_info['gr_number']}.html",
                'filename': f"{case_info['gr_number']}.html",
                'year': case_info['year'],
                'month': case_info['month'],
                'case_number': f"G.R. No. {case_info['gr_number']}",
                'gr_number': case_info['gr_number'],
                'volume_page': metadata.get('volume_page', ''),
                'decision_date': case_info['decision_date'],
                'title': case_info['title'],
                'division': None,
                'categories': ['Civil Law'],  # Default - can be enhanced
                'keywords': self._extract_keywords(text),
                'title_summary': case_info['title'],
                'formatted_case_content': text,
                'content_length': len(text),
                'metadata_extraction_date': datetime.now().isoformat(),
                'extraction_version': f'2.5_scraped_from_{source}'
            }
            
            return case_data
            
        except Exception as e:
            logger.error(f"  Error extracting case: {e}")
            return None
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from case text"""
        common_legal_terms = [
            'plaintiff', 'defendant', 'petitioner', 'respondent',
            'court', 'appeal', 'judgment', 'evidence', 'testimony',
            'contract', 'damages', 'liability', 'negligence', 'fraud'
        ]
        
        keywords = []
        text_lower = text.lower()
        
        for term in common_legal_terms:
            if term in text_lower:
                keywords.append(term)
                if len(keywords) >= max_keywords:
                    break
        
        return keywords[:max_keywords]
    
    def check_duplicate(self, case_data: Dict) -> bool:
        """Check if case already exists in database"""
        gr_number = case_data['gr_number']
        year = case_data['year']
        month = case_data['month']
        
        # Check standard location
        target_file = self.db_path / str(year) / month / f"{gr_number}.json"
        if target_file.exists():
            logger.info(f"  ⚠ Case already exists: {target_file}")
            return True
        
        # Check all month directories for this year
        year_path = self.db_path / str(year)
        if year_path.exists():
            for month_dir in year_path.iterdir():
                if month_dir.is_dir():
                    check_file = month_dir / f"{gr_number}.json"
                    if check_file.exists():
                        logger.info(f"  ⚠ Case already exists: {check_file}")
                        return True
        
        return False
    
    def save_case(self, case_data: Dict) -> Optional[Path]:
        """Save scraped case to database"""
        if self.check_duplicate(case_data):
            return None
        
        year = case_data['year']
        month = case_data['month']
        gr_number = case_data['gr_number']
        
        # Create directory structure
        target_dir = self.db_path / str(year) / month
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON file
        target_file = target_dir / f"{gr_number}.json"
        
        try:
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(case_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  ✓ Saved: {target_file}")
            return target_file
        except Exception as e:
            logger.error(f"  ✗ Failed to save: {e}")
            return None
    
    def scrape_case(self, case_info: Dict) -> bool:
        """Scrape a single case from multiple sources"""
        logger.info(f"\n{'='*80}")
        logger.info(f"Scraping: {case_info['title']} (G.R. No. {case_info['gr_number']})")
        logger.info(f"{'='*80}")
        
        # Try sources in order: SC E-Library -> ChanRobles -> Lawphil
        sources = [
            ('sc_elibrary', lambda: self.search_sc_elibrary(case_info['gr_number'], case_info['title'])),
            ('chanrobles', lambda: self.search_chanrobles(case_info['gr_number'], case_info['title'])),
            ('lawphil', lambda: self.search_lawphil(case_info['gr_number']))
        ]
        
        html = None
        source_used = None
        
        for source_name, search_func in sources:
            logger.info(f"Trying source: {source_name}")
            try:
                html = search_func()
                if html:
                    source_used = source_name
                    break
            except Exception as e:
                logger.error(f"  Error with {source_name}: {e}")
                continue
            time.sleep(1)  # Rate limiting between sources
        
        if not html:
            self.failed_cases.append({
                'case': case_info,
                'reason': 'Not found on any source (SC E-Library, ChanRobles, Lawphil)'
            })
            return False
        
        # Extract case data
        case_data = self.extract_case_from_html(html, case_info, source_used)
        
        if not case_data:
            self.failed_cases.append({
                'case': case_info,
                'reason': f'Failed to extract content from {source_used}'
            })
            return False
        
        # Save case
        saved_file = self.save_case(case_data)
        
        if saved_file:
            self.scraped_files.append(saved_file)
            return True
        else:
            return False
    
    def scrape_all(self, cases: List[Dict]):
        """Scrape all cases with rate limiting"""
        logger.info(f"Starting scraping for {len(cases)} cases...")
        logger.info(f"Sources: SC E-Library → ChanRobles → Lawphil (fallback)")
        
        success_count = 0
        for i, case in enumerate(cases, 1):
            logger.info(f"\nProgress: {i}/{len(cases)}")
            
            if self.scrape_case(case):
                success_count += 1
            
            # Rate limiting between cases
            if i < len(cases):
                time.sleep(3)
        
        logger.info(f"\nScraping complete: {success_count}/{len(cases)} successful")
        return success_count
    
    def generate_report(self) -> Dict:
        """Generate scraping report"""
        return {
            'scraping_date': datetime.now().isoformat(),
            'total_cases_attempted': len(SCRAPING_TARGETS),
            'successful_scrapes': len(self.scraped_files),
            'failed_scrapes': len(self.failed_cases),
            'files_saved': len(self.scraped_files),
            'failed_cases': self.failed_cases,
            'sources_tried': self.sources_tried,
            'sources_order': ['SC E-Library', 'ChanRobles', 'Lawphil'],
            'batch_size': self.batch_size
        }


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_enhanced.py <RESTRUCTURED_DB_path> [batch_size]")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 250
    
    if not db_path.exists():
        logger.error(f"Database path does not exist: {db_path}")
        sys.exit(1)
    
    logger.info("="*80)
    logger.info("ENHANCED SUPREME COURT CASE SCRAPER")
    logger.info("="*80)
    logger.info(f"Database: {db_path}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Cases to scrape: {len(SCRAPING_TARGETS)}")
    logger.info(f"Sources: SC E-Library → ChanRobles → Lawphil")
    logger.info("")
    
    # Initialize scraper
    scraper = MultiSourceScraper(db_path, batch_size)
    
    # Scrape all cases
    success_count = scraper.scrape_all(SCRAPING_TARGETS)
    
    # Generate report
    report = scraper.generate_report()
    
    # Save report
    report_file = 'SCRAPING_REPORT_ENHANCED.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Print summary
    logger.info("\n" + "="*80)
    logger.info("SCRAPING SUMMARY")
    logger.info("="*80)
    logger.info(f"Total cases attempted: {report['total_cases_attempted']}")
    logger.info(f"Successful scrapes: {report['successful_scrapes']}")
    logger.info(f"Failed scrapes: {report['failed_scrapes']}")
    logger.info(f"Sources tried: {report['sources_tried']}")
    logger.info(f"Report saved to: {report_file}")
    logger.info("="*80)
    
    if report['failed_cases']:
        logger.warning("\nFailed cases:")
        for failed in report['failed_cases']:
            logger.warning(f"  - G.R. {failed['case']['gr_number']}: {failed['reason']}")
    
    return 0 if success_count > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
