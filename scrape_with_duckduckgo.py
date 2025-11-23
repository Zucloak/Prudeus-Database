#!/usr/bin/env python3
"""
Browser-based scraper using DuckDuckGo search to find Philippine Supreme Court cases.

This script uses DuckDuckGo to search for cases and then attempts to access them
from the discovered URLs. This approach helps bypass direct bot protection on
legal websites.

Usage:
    python3 scrape_with_duckduckgo.py <RESTRUCTURED_DB_path>
"""

import requests
import json
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import logging
from urllib.parse import quote_plus, urlparse

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

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def search_duckduckgo(query: str) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo for the query and return results.
    Returns list of {'title': str, 'url': str, 'snippet': str}
    
    Note: If DuckDuckGo is blocked, this falls back to constructing
    likely URLs based on known patterns.
    """
    logger.info(f"  Searching DuckDuckGo for: {query}")
    
    # Try DuckDuckGo API first
    try:
        api_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json"
        headers = {'User-Agent': USER_AGENT}
        
        response = requests.get(api_url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            results = []
            
            # Parse Related Topics
            for topic in data.get('RelatedTopics', [])[:10]:
                if isinstance(topic, dict) and 'FirstURL' in topic:
                    results.append({
                        'title': topic.get('Text', ''),
                        'url': topic.get('FirstURL', ''),
                        'snippet': topic.get('Text', '')
                    })
            
            if results:
                logger.info(f"    Found {len(results)} results from DuckDuckGo API")
                return results
                
    except Exception as e:
        logger.debug(f"    DuckDuckGo API error: {e}")
    
    # Fallback: Return empty (will use direct URL patterns instead)
    logger.info(f"    DuckDuckGo search unavailable, will try direct URLs")
    return []


def search_for_case_via_duckduckgo(case_info: Dict) -> List[str]:
    """
    Search for a case using DuckDuckGo and return potential URLs.
    Falls back to constructing likely URLs if search is unavailable.
    """
    gr_number = case_info['gr_number']
    title = case_info['title']
    year = str(case_info['year'])
    
    # Try multiple search queries
    queries = [
        f"G.R. No. {gr_number} {title} Philippines Supreme Court",
        f"{title} G.R. {gr_number} site:elibrary.judiciary.gov.ph",
        f"{title} G.R. {gr_number} site:lawphil.net",
        f"G.R. No. {gr_number} Supreme Court Philippines",
    ]
    
    all_urls = []
    seen_urls = set()
    
    # Try DuckDuckGo search
    for query in queries:
        results = search_duckduckgo(query)
        
        for result in results:
            url = result['url']
            
            # Filter for relevant legal websites
            if any(domain in url.lower() for domain in [
                'judiciary.gov.ph',
                'lawphil.net',
                'chanrobles.com',
                'supremecourt.gov.ph'
            ]):
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_urls.append(url)
                    logger.info(f"    Found potential URL: {url}")
        
        # Be polite to DuckDuckGo
        time.sleep(1)
    
    # Fallback: Construct likely URLs directly if no results from search
    if not all_urls:
        logger.info(f"  No search results, constructing direct URLs...")
        
        year_prefix = gr_number[:2] if len(gr_number) >= 2 else gr_number
        
        # E-Library patterns
        direct_urls = [
            # E-Library
            f"https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/{gr_number}",
            f"https://elibrary.judiciary.gov.ph/thebookshelf/showdocs/1/{gr_number.lstrip('0')}",
            # Lawphil patterns
            f"https://lawphil.net/juris/juri{year_prefix}/juris_{gr_number}.html",
            f"https://lawphil.net/juris/juri{year_prefix}/gr_{gr_number}.html",
            f"https://www.lawphil.net/juris/juri{year_prefix}/gr_{gr_number}.html",
            f"https://www.lawphil.net/juris/juri{year_prefix}/juris_{gr_number}.html",
            # ChanRobles patterns (may be blocked but worth trying)
            f"https://www.chanrobles.com/scdecisions/jurisprudence{year[:2]}.php?gr={gr_number}",
            # Alternative lawphil patterns
            f"https://lawphil.net/juris/supreme/supdec/cases{year}/gr_{gr_number}.html",
        ]
        
        for url in direct_urls:
            if url not in seen_urls:
                seen_urls.add(url)
                all_urls.append(url)
                logger.info(f"    Trying direct URL: {url}")
    
    return all_urls


def fetch_case_content(url: str, gr_number: str) -> Optional[Tuple[str, Dict]]:
    """
    Fetch case content from a URL.
    Returns (content, metadata) if successful, None otherwise.
    """
    logger.info(f"  Fetching content from: {url}")
    
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        
        if response.status_code != 200:
            logger.warning(f"    HTTP {response.status_code}")
            return None
        
        html_content = response.text
        
        # Verify it's the right case
        if not (f"G.R. No. {gr_number}" in html_content or 
                f"G.R. NO. {gr_number}" in html_content or
                f"G.R. Nos. {gr_number}" in html_content):
            logger.warning(f"    Case G.R. No. {gr_number} not found in content")
            return None
        
        # Extract content and metadata
        return extract_case_content_from_html(html_content, url)
        
    except Exception as e:
        logger.error(f"    Error fetching: {e}")
        return None


def extract_case_content_from_html(html_content: str, source_url: str) -> Tuple[Optional[str], Optional[Dict]]:
    """
    Extract case content and metadata from HTML.
    Returns (formatted_content, metadata_dict)
    """
    # Remove script and style tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Extract metadata
    metadata = {}
    
    # Extract G.R. number
    gr_match = re.search(r'G\.R\.\s+No\.?s?\s+(\d+(?:\s*&\s*\d+)?)', text, re.IGNORECASE)
    if gr_match:
        metadata['gr_number'] = gr_match.group(1)
    
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
    """Extract relevant keywords from case content."""
    keywords = []
    
    legal_terms = [
        'constitutional', 'criminal', 'civil', 'administrative', 'labor',
        'commercial', 'tax', 'property', 'family', 'remedial',
        'jurisdiction', 'due process', 'petition', 'appeal', 'certiorari',
        'mandamus', 'prohibition', 'habeas corpus', 'damages', 'injunction'
    ]
    
    content_lower = content.lower()
    for term in legal_terms:
        if term in content_lower:
            keywords.append(term.title())
    
    return keywords[:10]


def categorize_case(content: str, title: str) -> List[str]:
    """Categorize the case based on content analysis."""
    categories = []
    content_lower = content.lower() + ' ' + title.lower()
    
    category_patterns = {
        'Criminal Law': ['criminal', 'accused', 'prosecution', 'convicted', 'murder', 'homicide'],
        'Civil Law': ['civil', 'damages', 'obligation', 'contract', 'tort'],
        'Labor Law': ['labor', 'employee', 'employer', 'nlrc', 'wages', 'termination'],
        'Commercial Law': ['commercial', 'corporation', 'partnership', 'banking'],
        'Tax Law': ['tax', 'revenue', 'bir', 'commissioner of internal revenue'],
        'Administrative Law': ['administrative', 'government', 'public officer', 'ombudsman'],
        'Constitutional Law': ['constitutional', 'constitution', 'bill of rights'],
        'Family Law': ['family', 'marriage', 'divorce', 'custody', 'adoption'],
        'Property Law': ['property', 'land', 'real estate', 'ownership', 'title'],
        'Remedial Law': ['remedial', 'procedure', 'jurisdiction', 'appeal', 'certiorari']
    }
    
    for category, patterns in category_patterns.items():
        for pattern in patterns:
            if pattern in content_lower:
                categories.append(category)
                break
    
    return categories if categories else ['Civil Law']


def create_case_json(case_info: Dict, content: str, metadata: Dict) -> Dict:
    """Create a properly formatted case JSON object."""
    keywords = extract_keywords_from_content(content, case_info['title'])
    categories = categorize_case(content, case_info['title'])
    
    case_data = {
        'file_path': f"/scraped_via_duckduckgo/{case_info['year']}/{case_info['month']}/{case_info['gr_number']}.html",
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
        'extraction_version': '3.1_duckduckgo_scraper',
        'source_url': metadata.get('source_url', ''),
    }
    
    return case_data


def save_case_to_db(case_data: Dict, db_path: Path) -> bool:
    """Save the scraped case to the database."""
    year = case_data['year']
    month = case_data['month']
    gr_number = case_data['gr_number']
    
    target_dir = db_path / str(year) / month
    target_dir.mkdir(parents=True, exist_ok=True)
    
    target_file = target_dir / f"{gr_number}.json"
    
    try:
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"  ✓ Saved to: {target_file}")
        return True
    except Exception as e:
        logger.error(f"  ✗ Failed to save: {e}")
        return False


def scrape_case_via_duckduckgo(case_info: Dict, db_path: Path) -> bool:
    """
    Scrape a case using DuckDuckGo search to find it.
    Returns True if successful, False otherwise.
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Case: {case_info['title']} (G.R. No. {case_info['gr_number']})")
    logger.info(f"{'='*80}")
    
    # Search for the case
    urls = search_for_case_via_duckduckgo(case_info)
    
    if not urls:
        logger.warning(f"  ✗ No URLs found via DuckDuckGo")
        return False
    
    # Try each URL
    for url in urls:
        try:
            result = fetch_case_content(url, case_info['gr_number'])
            
            if result:
                content, metadata = result
                logger.info(f"  ✓ Successfully extracted content ({len(content)} chars)")
                
                # Create case JSON
                case_data = create_case_json(case_info, content, metadata)
                
                # Save to database
                if save_case_to_db(case_data, db_path):
                    return True
            
        except Exception as e:
            logger.error(f"  ✗ Error processing URL {url}: {e}")
            continue
        
        # Rate limiting
        time.sleep(3)
    
    logger.warning(f"  ✗ Failed to scrape case from any URL")
    return False


def main():
    """Main function."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 scrape_with_duckduckgo.py <RESTRUCTURED_DB_path>")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    
    if not db_path.exists():
        print(f"Error: {db_path} does not exist")
        sys.exit(1)
    
    logger.info("="*80)
    logger.info("DUCKDUCKGO-BASED SCRAPER FOR MISSING CASES (2005-2024)")
    logger.info("="*80)
    logger.info(f"Database path: {db_path}")
    logger.info(f"Cases to scrape: {len(MISSING_CASES)}")
    logger.info(f"Method: DuckDuckGo search + content extraction")
    
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
        if scrape_case_via_duckduckgo(case, db_path):
            scraped_count += 1
        else:
            failed_cases.append(case)
        
        # Be polite to servers
        time.sleep(5)
    
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
    
    logger.info("="*80)


if __name__ == '__main__':
    main()
