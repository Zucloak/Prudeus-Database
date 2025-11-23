#!/usr/bin/env python3
"""
Enhanced Supreme Court Case Scraper with Batch Commit Support

This script:
1. Scrapes missing priority cases from lawphil.net and Supreme Court E-Library
2. Validates and deduplicates scraped cases
3. Implements batched commits (200-300 files per batch)
4. Generates comprehensive logs and reports
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
import subprocess
import os

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


class CaseScraper:
    """Scrapes cases from lawphil.net and Supreme Court E-Library"""
    
    def __init__(self, db_path: Path, batch_size: int = 250):
        self.db_path = db_path
        self.batch_size = batch_size
        self.scraped_files: List[Path] = []
        self.failed_cases: List[Dict] = []
        
    def search_lawphil(self, gr_number: str) -> Optional[str]:
        """Search lawphil.net for a case by GR number"""
        logger.info(f"Searching lawphil.net for G.R. No. {gr_number}")
        
        # Try different URL patterns
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
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                logger.debug(f"  Failed to fetch {url}: {e}")
                continue
        
        logger.warning(f"  ✗ Not found on lawphil.net")
        return None
    
    def extract_case_from_html(self, html: str, case_info: Dict) -> Optional[Dict]:
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
                'file_path': f"/scraped/{case_info['year']}/{case_info['month']}/{case_info['gr_number']}.html",
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
                'extraction_version': '2.4_scraped_priority_cases'
            }
            
            return case_data
            
        except Exception as e:
            logger.error(f"  Error extracting case: {e}")
            return None
    
    def _extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from case text"""
        # Simple keyword extraction - can be enhanced
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
        """Scrape a single case"""
        logger.info(f"\n{'='*80}")
        logger.info(f"Scraping: {case_info['title']} (G.R. No. {case_info['gr_number']})")
        logger.info(f"{'='*80}")
        
        # Try lawphil.net
        html = self.search_lawphil(case_info['gr_number'])
        
        if not html:
            self.failed_cases.append({
                'case': case_info,
                'reason': 'Not found on lawphil.net'
            })
            return False
        
        # Extract case data
        case_data = self.extract_case_from_html(html, case_info)
        
        if not case_data:
            self.failed_cases.append({
                'case': case_info,
                'reason': 'Failed to extract content'
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
        
        success_count = 0
        for i, case in enumerate(cases, 1):
            logger.info(f"\nProgress: {i}/{len(cases)}")
            
            if self.scrape_case(case):
                success_count += 1
            
            # Rate limiting - be polite to servers
            if i < len(cases):
                time.sleep(3)
        
        logger.info(f"\nScraping complete: {success_count}/{len(cases)} successful")
        return success_count
    
    def commit_batch(self, batch_num: int, total_batches: int):
        """Commit a batch of files using git"""
        if not self.scraped_files:
            logger.info("No files to commit")
            return False
        
        try:
            # Stage files
            for file in self.scraped_files[:self.batch_size]:
                subprocess.run(['git', 'add', str(file)], check=True, 
                             capture_output=True, text=True)
            
            # Commit
            commit_msg = f"chore(batch): scraped {len(self.scraped_files[:self.batch_size])} cases - batch {batch_num}/{total_batches}"
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True,
                         capture_output=True, text=True)
            
            logger.info(f"✓ Committed batch {batch_num}/{total_batches}")
            
            # Remove committed files from list
            self.scraped_files = self.scraped_files[self.batch_size:]
            
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e}")
            return False
    
    def commit_all_batches(self):
        """Commit all scraped files in batches"""
        if not self.scraped_files:
            logger.info("No files to commit")
            return
        
        total_files = len(self.scraped_files)
        total_batches = (total_files + self.batch_size - 1) // self.batch_size
        
        logger.info(f"\nCommitting {total_files} files in {total_batches} batches...")
        
        batch_num = 0
        while self.scraped_files:
            batch_num += 1
            self.commit_batch(batch_num, total_batches)
            time.sleep(1)  # Throttle commits
        
        logger.info("All batches committed successfully")
    
    def generate_report(self) -> Dict:
        """Generate scraping report"""
        return {
            'scraping_date': datetime.now().isoformat(),
            'total_cases_attempted': len(SCRAPING_TARGETS),
            'successful_scrapes': len(self.scraped_files) + (len(SCRAPING_TARGETS) - len(self.failed_cases) - len(self.scraped_files)),
            'failed_scrapes': len(self.failed_cases),
            'files_saved': len(self.scraped_files) + (len(SCRAPING_TARGETS) - len(self.failed_cases) - len(self.scraped_files)),
            'failed_cases': self.failed_cases,
            'batch_size': self.batch_size
        }


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_and_process_cases.py <RESTRUCTURED_DB_path> [batch_size]")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 250
    
    if not db_path.exists():
        logger.error(f"Database path does not exist: {db_path}")
        sys.exit(1)
    
    logger.info("="*80)
    logger.info("SUPREME COURT CASE SCRAPER WITH BATCH COMMIT")
    logger.info("="*80)
    logger.info(f"Database: {db_path}")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Cases to scrape: {len(SCRAPING_TARGETS)}")
    logger.info("")
    
    # Initialize scraper
    scraper = CaseScraper(db_path, batch_size)
    
    # Scrape all cases
    success_count = scraper.scrape_all(SCRAPING_TARGETS)
    
    # Generate report
    report = scraper.generate_report()
    
    # Save report
    report_file = 'SCRAPING_REPORT.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    # Print summary
    logger.info("\n" + "="*80)
    logger.info("SCRAPING SUMMARY")
    logger.info("="*80)
    logger.info(f"Total cases attempted: {report['total_cases_attempted']}")
    logger.info(f"Successful scrapes: {report['successful_scrapes']}")
    logger.info(f"Failed scrapes: {report['failed_scrapes']}")
    logger.info(f"Report saved to: {report_file}")
    logger.info("="*80)
    
    if report['failed_cases']:
        logger.warning("\nFailed cases:")
        for failed in report['failed_cases']:
            logger.warning(f"  - G.R. {failed['case']['gr_number']}: {failed['reason']}")
    
    return 0 if success_count > 0 else 1


if __name__ == '__main__':
    sys.exit(main())
