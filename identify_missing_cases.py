#!/usr/bin/env python3
"""
Identify potentially missing cases by checking for gaps in GR numbers.
"""

import json
import glob
import re
from collections import defaultdict

def main():
    # Collect all GR numbers by year
    gr_by_year = defaultdict(set)
    
    print("Scanning database for GR numbers...")
    for file in glob.glob('RESTRUCTURED_DB/*/*/*.json'):
        if 'case_index' in file:
            continue
        
        try:
            with open(file) as f:
                data = json.load(f)
                gr_num = data.get('gr_number', '')
                year = data.get('year')
                
                # Extract numeric GR number
                match = re.search(r'(\d+)', gr_num)
                if match and year:
                    gr_by_year[year].add(int(match.group(1)))
        except:
            pass
    
    # Check for gaps in each year
    print("\n" + "="*80)
    print("MISSING CASE ANALYSIS")
    print("="*80)
    
    recent_years = [2005, 2008, 2016, 2017, 2019, 2023, 2024]
    
    for year in sorted(recent_years):
        if year not in gr_by_year or len(gr_by_year[year]) == 0:
            print(f"\n{year}: NO CASES FOUND")
            continue
        
        gr_nums = sorted(gr_by_year[year])
        min_gr = min(gr_nums)
        max_gr = max(gr_nums)
        
        # Find gaps
        all_expected = set(range(min_gr, max_gr + 1))
        missing = all_expected - gr_by_year[year]
        
        print(f"\n{year}:")
        print(f"  Cases in DB: {len(gr_nums)}")
        print(f"  GR Range: {min_gr:,} - {max_gr:,}")
        print(f"  Expected total: {len(all_expected):,}")
        print(f"  Missing: {len(missing):,} cases")
        
        if len(missing) > 0:
            # Show sample of missing
            missing_list = sorted(missing)
            if len(missing_list) <= 20:
                print(f"  Missing GR Nos: {', '.join(str(x) for x in missing_list)}")
            else:
                print(f"  Sample missing: {', '.join(str(x) for x in missing_list[:10])}...")
    
    # Check for specific cases mentioned by user
    print("\n" + "="*80)
    print("SPECIFIC CASES FROM USER REQUEST")
    print("="*80)
    
    specific_cases = [
        (231896, 2019, "Municipality of Tupi v. Faustino"),
        (165842, 2005, "Manuel v. People"),
        (213198, 2019, "Toyo v. Toyo"),
        (232269, 2024, "Asilo v. Gonzales-Betic"),
        (164815, 2008, "Valeroso v. People"),
        (257697, 2023, "San Miguel v. Commissioner"),
        (189516, 2016, "Otamias v. Republic"),
        (209969, 2017, "Sanico v. Colipano"),
        (203754, 2019, "Film Devt. Council v. Colon"),
    ]
    
    for gr_num, year, title in specific_cases:
        found = gr_num in gr_by_year.get(year, set())
        status = "✓ FOUND" if found else "✗ MISSING"
        print(f"  {status} - G.R. No. {gr_num} ({year}): {title}")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    main()
