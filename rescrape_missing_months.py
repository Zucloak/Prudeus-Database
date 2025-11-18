#!/usr/bin/env python3
"""
Script to rescrape specific missing months for years 1909, 1910, and 1913
"""

import sys
from pathlib import Path

# Import the scraper
from scraper import LawPhilScraper

def rescrape_missing_months():
    """Rescrape missing months for specific years"""
    
    # Define missing months per year
    missing_data = {
        1909: ['february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november'],
        1910: ['march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'],
        1913: ['may', 'june']
    }
    
    print("=" * 80)
    print("RESCRAPING MISSING MONTHS")
    print("=" * 80)
    
    scraper = LawPhilScraper(output_dir='RESTRUCTURED_DB', delay=2.0)
    
    for year, months in missing_data.items():
        print(f"\n{'=' * 80}")
        print(f"YEAR {year} - Scraping {len(months)} missing months")
        print(f"{'=' * 80}")
        
        for month in months:
            print(f"\n--- Processing {month.title()} {year} ---")
            month_url = scraper.get_month_url(year, month)
            
            html = scraper.fetch_page(month_url)
            if not html:
                print(f"  ⚠️  Could not fetch {month_url}")
                continue
            
            # Parse case links
            cases = scraper.parse_case_links(html, month_url)
            print(f"  Found {len(cases)} potential cases")
            
            if len(cases) == 0:
                print(f"  ⚠️  No cases found for {month} {year}")
                continue
            
            # Process each case
            success_count = 0
            for i, case_info in enumerate(cases, 1):
                print(f"    [{i}/{len(cases)}] Processing {case_info['href']}")
                case_data = scraper.parse_case(case_info['url'], year, month)
                
                if case_data:
                    if scraper.save_case(case_data):
                        success_count += 1
                else:
                    print(f"      ⚠️  Failed to parse case")
            
            print(f"  ✅ Successfully scraped {success_count}/{len(cases)} cases for {month} {year}")
    
    print("\n" + "=" * 80)
    print("RESCRAPING COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Run validation: python validate_cases.py --directory RESTRUCTURED_DB --start-year 1909 --end-year 1913")
    print("2. Check completeness: python check_lawphil_completeness.py")

if __name__ == '__main__':
    rescrape_missing_months()
