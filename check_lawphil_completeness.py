#!/usr/bin/env python3
"""
Script to check lawphil.net for available months and cases for specific years
"""

import requests
from bs4 import BeautifulSoup
import time
import sys
from pathlib import Path

BASE_URL = "https://lawphil.net/judjuris/"

def get_available_months(year):
    """Get available months for a specific year from lawphil.net"""
    url = f"{BASE_URL}juri{year}/juri{year}.html"
    print(f"\nChecking {year}: {url}")
    
    try:
        time.sleep(1)  # Be respectful to the server
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links
        links = soup.find_all('a', href=True)
        months = set()
        
        for link in links:
            href = link.get('href', '')
            # Month links typically look like: jan1909/jan1909.html
            if f"{year}" in href and '/' in href:
                parts = href.split('/')
                if len(parts) > 0:
                    month_folder = parts[0]
                    # Extract month name (first 3 chars usually)
                    if month_folder.startswith(('jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                                'jul', 'aug', 'sep', 'oct', 'nov', 'dec')):
                        month_name = month_folder[:3]
                        months.add(month_name)
        
        return sorted(months)
        
    except requests.RequestException as e:
        print(f"Error fetching {year}: {e}")
        return None

def get_cases_in_month(year, month):
    """Get number of cases available for a specific month"""
    url = f"{BASE_URL}juri{year}/{month}{year}/{month}{year}.html"
    print(f"  Checking {month} {year}: {url}")
    
    try:
        time.sleep(1)  # Be respectful to the server
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Count case links (typically .html files)
        links = soup.find_all('a', href=True)
        case_count = 0
        
        for link in links:
            href = link.get('href', '')
            if href.endswith('.html') and not href.startswith('http'):
                case_count += 1
        
        return case_count
        
    except requests.RequestException as e:
        print(f"    Error: {e}")
        return 0

def check_local_data(year):
    """Check what we have locally"""
    base_dir = Path(f"RESTRUCTURED_DB/{year}")
    if not base_dir.exists():
        return {}, 0
    
    months_data = {}
    total_cases = 0
    
    for month_dir in base_dir.iterdir():
        if month_dir.is_dir():
            month_name = month_dir.name
            case_files = list(month_dir.glob('*.json'))
            months_data[month_name] = len(case_files)
            total_cases += len(case_files)
    
    return months_data, total_cases

def main():
    years_to_check = [1909, 1910, 1913, 1979]
    
    print("=" * 80)
    print("CHECKING LAWPHIL.NET FOR COMPLETENESS")
    print("=" * 80)
    
    for year in years_to_check:
        print(f"\n{'=' * 80}")
        print(f"YEAR {year}")
        print(f"{'=' * 80}")
        
        # Check what's available on lawphil
        available_months = get_available_months(year)
        
        if available_months is None:
            print(f"  Could not fetch data from lawphil.net for {year}")
            continue
        
        print(f"\n  Available months on lawphil.net: {len(available_months)}")
        print(f"  Months: {', '.join(available_months)}")
        
        # Check local data
        local_months, local_total = check_local_data(year)
        print(f"\n  Local months: {len(local_months)}")
        print(f"  Local months: {', '.join(sorted(local_months.keys()))}")
        print(f"  Local total cases: {local_total}")
        
        # Compare
        month_map = {
            'jan': 'january', 'feb': 'february', 'mar': 'march', 'apr': 'april',
            'may': 'may', 'jun': 'june', 'jul': 'july', 'aug': 'august',
            'sep': 'september', 'oct': 'october', 'nov': 'november', 'dec': 'december'
        }
        
        missing_months = []
        for short_month in available_months:
            full_month = month_map.get(short_month, short_month)
            if full_month not in local_months:
                missing_months.append(full_month)
        
        if missing_months:
            print(f"\n  ⚠️  MISSING MONTHS: {', '.join(missing_months)}")
        else:
            print(f"\n  ✅ All available months are present locally")
        
        # Detail for each month
        print(f"\n  Month-by-month breakdown:")
        for short_month in available_months:
            full_month = month_map.get(short_month, short_month)
            local_count = local_months.get(full_month, 0)
            
            # Get count from lawphil (this is slow, so commented out by default)
            # lawphil_count = get_cases_in_month(year, short_month)
            # print(f"    {full_month:12s}: Local={local_count:3d}, Lawphil={lawphil_count:3d}")
            
            print(f"    {full_month:12s}: Local={local_count:3d} cases")

    print("\n" + "=" * 80)
    print("CHECK COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
