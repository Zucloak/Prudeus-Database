#!/usr/bin/env python3
"""
Philippine Supreme Court Case Scraper for lawphil.net
This script scrapes historical cases from 1901-1995 and formats them according to the database schema.

Usage:
    python scraper.py --start-year 1901 --end-year 1995 --output-dir RESTRUCTURED_DB
    
Note: This script should be run in an environment with access to lawphil.net
"""

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Required packages not installed. Run:")
    print("pip install requests beautifulsoup4")
    exit(1)


class LawPhilScraper:
    """Scraper for lawphil.net Supreme Court cases"""
    
    BASE_URL = "https://lawphil.net/judjuris/"
    
    # Month mapping
    MONTHS = {
        'jan': '01', 'january': '01',
        'feb': '02', 'february': '02',
        'mar': '03', 'march': '03',
        'apr': '04', 'april': '04',
        'may': '05',
        'jun': '06', 'june': '06',
        'jul': '07', 'july': '07',
        'aug': '08', 'august': '08',
        'sep': '09', 'sept': '09', 'september': '09',
        'oct': '10', 'october': '10',
        'nov': '11', 'november': '11',
        'dec': '12', 'december': '12'
    }
    
    def __init__(self, output_dir: str, delay: float = 1.0):
        self.output_dir = Path(output_dir)
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def get_year_url(self, year: int) -> str:
        """Get the URL for a specific year's case listing"""
        return f"{self.BASE_URL}juri{year}/juri{year}.html"
    
    def get_month_url(self, year: int, month: str) -> str:
        """Get the URL for a specific month's case listing"""
        month_lower = month.lower()[:3]
        return f"{self.BASE_URL}juri{year}/{month_lower}{year}/{month_lower}{year}.html"
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with error handling and rate limiting"""
        try:
            time.sleep(self.delay)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def parse_case_links(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """Extract case links from a listing page"""
        soup = BeautifulSoup(html, 'html.parser')
        cases = []
        
        # Find all links that look like case files
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Filter for case links (typically .html files with case numbers)
            if href.endswith('.html') and not href.startswith('http'):
                full_url = urljoin(base_url, href)
                cases.append({
                    'url': full_url,
                    'link_text': text,
                    'href': href
                })
        
        return cases
    
    def extract_case_number(self, text: str) -> Optional[str]:
        """Extract G.R. number or other case numbers from text"""
        patterns = [
            r'G\.R\.?\s*No\.?\s*(\d+)',
            r'GR\s*No\.?\s*(\d+)',
            r'A\.C\.?\s*No\.?\s*(\d+)',
            r'A\.M\.?\s*No\.?\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None
    
    def extract_decision_date(self, text: str) -> Optional[str]:
        """Extract decision date from case text"""
        patterns = [
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}',
            r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return ""
    
    def extract_volume_page(self, text: str) -> str:
        """Extract volume and page information"""
        patterns = [
            r'\d+\s+Phil\.?\s+\d+',
            r'\d+\s+SCRA\s+\d+',
            r'Vol\.?\s+\d+[,\s]+p\.?\s+\d+',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return "Volume information not available"
    
    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extract case title"""
        # Try different methods to find the title
        title = ""
        
        # Method 1: Look for bold text near the beginning
        bold_tags = soup.find_all(['b', 'strong'])
        if bold_tags:
            for tag in bold_tags[:3]:
                text = tag.get_text(strip=True)
                if len(text) > 20 and 'vs' in text.lower():
                    title = text
                    break
        
        # Method 2: Look for text with "vs" or "v."
        if not title:
            text = soup.get_text()
            lines = text.split('\n')
            for line in lines[:20]:
                if ' vs ' in line.lower() or ' v. ' in line.lower():
                    title = line.strip()
                    break
        
        return title if title else "Title not found"
    
    def categorize_case(self, content: str) -> List[str]:
        """Categorize case based on content keywords"""
        categories = []
        content_lower = content.lower()
        
        category_keywords = {
            'Civil Law': ['civil', 'contract', 'property', 'obligation', 'tort', 'damages'],
            'Criminal Law': ['criminal', 'murder', 'homicide', 'theft', 'robbery', 'fraud'],
            'Labor Law': ['labor', 'employment', 'employee', 'employer', 'nlrc', 'worker'],
            'Commercial Law': ['commercial', 'corporation', 'partnership', 'banking', 'insurance'],
            'Tax Law': ['tax', 'taxation', 'bir', 'revenue', 'customs'],
            'Administrative Law': ['administrative', 'agency', 'regulation', 'license'],
            'Constitutional Law': ['constitutional', 'constitution', 'bill of rights', 'due process'],
            'Family Law': ['family', 'marriage', 'divorce', 'adoption', 'custody'],
            'Property Law': ['land', 'real property', 'title', 'ownership', 'possession'],
            'Remedial Law': ['procedure', 'jurisdiction', 'appeal', 'certiorari', 'mandamus']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                categories.append(category)
        
        # Always include at least one category
        if not categories:
            categories.append('General')
        
        return list(set(categories))[:6]  # Limit to 6 categories
    
    def extract_keywords(self, content: str, title: str) -> List[str]:
        """Extract keywords from case content"""
        text = f"{title} {content}".lower()
        
        # Remove common words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 
                      'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'that',
                      'this', 'these', 'those', 'from', 'by', 'not', 'which', 'such', 'all'}
        
        # Extract words
        words = re.findall(r'\b[a-z]{3,}\b', text)
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        return [word for word, _ in keywords]
    
    def parse_case(self, url: str, year: int, month: str) -> Optional[Dict]:
        """Parse a single case and extract all metadata"""
        html = self.fetch_page(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Get full text content
        text_content = soup.get_text()
        
        # Extract metadata
        case_number = self.extract_case_number(text_content)
        if not case_number:
            # Try to extract from URL or filename
            filename = url.split('/')[-1].replace('.html', '')
            case_number = filename
        
        title = self.extract_title(soup)
        decision_date = self.extract_decision_date(text_content)
        volume_page = self.extract_volume_page(text_content)
        
        # Generate formatted content (preserve structure)
        formatted_content = self.format_case_content(soup)
        
        # Generate filename based on case number
        safe_filename = re.sub(r'[^\w\-_]', '_', case_number)
        
        # Extract division if mentioned
        division = None
        if 'first division' in text_content.lower():
            division = 'First Division'
        elif 'second division' in text_content.lower():
            division = 'Second Division'
        elif 'third division' in text_content.lower():
            division = 'Third Division'
        elif 'en banc' in text_content.lower():
            division = 'En Banc'
        
        # Build case data
        case_data = {
            'file_path': f'/workspace/PRUDEUS_DB/WEBPAGE_VERSION/{year}/{month.lower()}/{safe_filename}.html',
            'filename': f'{safe_filename}.html',
            'year': year,
            'month': month.lower(),
            'case_number': case_number,
            'gr_number': case_number.replace('G.R. No. ', '').replace('G.R. ', ''),
            'volume_page': volume_page,
            'decision_date': decision_date if decision_date else f"Date not specified, {year}",
            'title': title,
            'division': division,
            'categories': self.categorize_case(text_content),
            'keywords': self.extract_keywords(text_content, title),
            'title_summary': title[:100] + '...' if len(title) > 100 else title,
            'formatted_case_content': formatted_content,
            'content_length': len(formatted_content),
            'metadata_extraction_date': datetime.now().isoformat(),
            'extraction_version': '2.0_enhanced_full_content'
        }
        
        return case_data
    
    def format_case_content(self, soup: BeautifulSoup) -> str:
        """Format case content to match existing database style"""
        # Preserve the HTML structure but clean it up
        content = soup.get_text(separator='\n')
        
        # Clean up excessive whitespace
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        formatted = '\n\n'.join(lines)
        
        return formatted
    
    def save_case(self, case_data: Dict) -> bool:
        """Save case to JSON file"""
        year = case_data['year']
        month = case_data['month']
        filename = case_data['filename'].replace('.html', '.json')
        
        # Create directory structure
        output_path = self.output_dir / str(year) / month
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save JSON file
        json_path = output_path / filename
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(case_data, f, indent=2, ensure_ascii=False)
            print(f"Saved: {json_path}")
            return True
        except Exception as e:
            print(f"Error saving {json_path}: {e}")
            return False
    
    def scrape_year(self, year: int, start_month: str = 'january', end_month: str = 'december'):
        """Scrape all cases for a specific year"""
        print(f"\n=== Scraping Year {year} ===")
        
        months = ['january', 'february', 'march', 'april', 'may', 'june',
                  'july', 'august', 'september', 'october', 'november', 'december']
        
        # Filter months based on start and end
        start_idx = months.index(start_month.lower())
        end_idx = months.index(end_month.lower()) + 1
        months_to_scrape = months[start_idx:end_idx]
        
        for month in months_to_scrape:
            print(f"\n--- Processing {month.title()} {year} ---")
            month_url = self.get_month_url(year, month)
            
            html = self.fetch_page(month_url)
            if not html:
                print(f"Could not fetch {month_url}")
                continue
            
            # Parse case links
            cases = self.parse_case_links(html, month_url)
            print(f"Found {len(cases)} potential cases")
            
            # Process each case
            for i, case_info in enumerate(cases, 1):
                print(f"  [{i}/{len(cases)}] Processing {case_info['href']}")
                case_data = self.parse_case(case_info['url'], year, month)
                
                if case_data:
                    self.save_case(case_data)
                else:
                    print(f"    Failed to parse case")
    
    def scrape_range(self, start_year: int, end_year: int, 
                     start_month: str = 'january', end_month: str = 'december'):
        """Scrape cases for a range of years"""
        for year in range(start_year, end_year + 1):
            # For first year, use start_month
            month_start = start_month if year == start_year else 'january'
            # For last year, use end_month
            month_end = end_month if year == end_year else 'december'
            
            self.scrape_year(year, month_start, month_end)
            
            # Take a longer break between years
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description='Scrape Philippine Supreme Court cases from lawphil.net')
    parser.add_argument('--start-year', type=int, default=1901, help='Starting year (default: 1901)')
    parser.add_argument('--end-year', type=int, default=1995, help='Ending year (default: 1995)')
    parser.add_argument('--start-month', type=str, default='august', help='Starting month (default: august)')
    parser.add_argument('--end-month', type=str, default='december', help='Ending month (default: december)')
    parser.add_argument('--output-dir', type=str, default='RESTRUCTURED_DB', help='Output directory')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests in seconds')
    parser.add_argument('--year', type=int, help='Scrape a specific year only')
    
    args = parser.parse_args()
    
    scraper = LawPhilScraper(args.output_dir, delay=args.delay)
    
    if args.year:
        scraper.scrape_year(args.year, args.start_month, args.end_month)
    else:
        scraper.scrape_range(args.start_year, args.end_year, args.start_month, args.end_month)
    
    print("\n=== Scraping Complete ===")


if __name__ == '__main__':
    main()
