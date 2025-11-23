#!/usr/bin/env python3
"""
Discover additional cases available on lawphil.net that are not in our database.
This script scrapes the lawphil judjuris index page to find available cases.
"""

import requests
import json
import re
import glob
from bs4 import BeautifulSoup
from collections import defaultdict
from typing import Set, Dict, List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_existing_gr_numbers(year_start=2005, year_end=2024) -> Dict[int, Set[str]]:
    """Get GR numbers already in database for specified year range."""
    existing = defaultdict(set)
    
    for file in glob.glob('RESTRUCTURED_DB/*/*/*.json'):
        if 'case_index' in file:
            continue
        try:
            with open(file) as f:
                data = json.load(f)
                year = data.get('year')
                gr_num = data.get('gr_number', '')
                
                if year and year_start <= year <= year_end and gr_num:
                    # Extract numeric part
                    match = re.search(r'(\d+)', gr_num)
                    if match:
                        existing[year].add(match.group(1))
        except Exception as e:
            pass
    
    return existing

def scrape_lawphil_index() -> List[Dict]:
    """Scrape lawphil judjuris main page to find available cases."""
    url = "https://lawphil.net/judjuris/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    logger.info(f"Fetching lawphil index from {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        cases = []
        # Look for G.R. No. pattern with dates
        for row in soup.find_all('tr', class_='xy'):
            try:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    # First cell has GR number and date
                    first_cell_text = cells[0].get_text()
                    # Second cell has title
                    title_text = cells[1].get_text()
                    
                    # Extract GR number
                    gr_match = re.search(r'G\.R\.?\s*No\.?\s*(\d+)', first_cell_text)
                    # Extract date
                    date_match = re.search(r'(\w+ \d+, \d{4})', first_cell_text)
                    
                    if gr_match and date_match:
                        gr_num = gr_match.group(1)
                        date_str = date_match.group(1)
                        
                        # Extract year from date
                        year_match = re.search(r'(\d{4})', date_str)
                        if year_match:
                            year = int(year_match.group(1))
                            
                            # Only include 2005-2024
                            if 2005 <= year <= 2024:
                                cases.append({
                                    'gr_number': gr_num,
                                    'title': title_text.strip(),
                                    'date': date_str,
                                    'year': year
                                })
            except Exception as e:
                logger.debug(f"Error parsing row: {e}")
                continue
        
        logger.info(f"Found {len(cases)} cases from 2005-2024 on lawphil index")
        return cases
        
    except Exception as e:
        logger.error(f"Error fetching lawphil index: {e}")
        return []

def main():
    logger.info("=" * 80)
    logger.info("DISCOVERING ADDITIONAL CASES ON LAWPHIL")
    logger.info("=" * 80)
    
    # Get existing cases in database
    logger.info("Scanning database for existing GR numbers...")
    existing = get_existing_gr_numbers(2005, 2024)
    
    total_existing = sum(len(v) for v in existing.values())
    logger.info(f"Found {total_existing} cases in database (2005-2024)")
    
    # Scrape lawphil index
    logger.info("\nScraping lawphil.net/judjuris/ for available cases...")
    available_cases = scrape_lawphil_index()
    
    if not available_cases:
        logger.warning("No cases found on lawphil index. The website might be unavailable.")
        return
    
    # Find missing cases
    logger.info("\nAnalyzing gaps...")
    missing_cases = []
    
    for case in available_cases:
        year = case['year']
        gr_num = case['gr_number']
        
        if gr_num not in existing.get(year, set()):
            missing_cases.append(case)
    
    # Report results
    logger.info("\n" + "=" * 80)
    logger.info(f"RESULTS: Found {len(missing_cases)} cases on lawphil NOT in our database")
    logger.info("=" * 80)
    
    if missing_cases:
        # Group by year
        by_year = defaultdict(list)
        for case in missing_cases:
            by_year[case['year']].append(case)
        
        for year in sorted(by_year.keys()):
            logger.info(f"\n{year}: {len(by_year[year])} missing cases")
            for case in by_year[year][:5]:  # Show first 5
                logger.info(f"  - G.R. No. {case['gr_number']}: {case['title'][:60]}...")
            if len(by_year[year]) > 5:
                logger.info(f"  ... and {len(by_year[year]) - 5} more")
        
        # Save to file
        output_file = 'lawphil_missing_cases.json'
        with open(output_file, 'w') as f:
            json.dump(missing_cases, f, indent=2)
        logger.info(f"\nFull list saved to: {output_file}")
        logger.info(f"Total missing cases that can be scraped: {len(missing_cases)}")
    else:
        logger.info("\nNo additional cases found on lawphil that aren't in our database.")
        logger.info("The database appears to have all publicly available cases from lawphil.")
    
    logger.info("\n" + "=" * 80)

if __name__ == '__main__':
    main()
