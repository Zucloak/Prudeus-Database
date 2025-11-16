#!/usr/bin/env python3
"""
Update case_index.json with newly scraped cases
"""

import argparse
import json
from pathlib import Path
from datetime import datetime


def update_case_index(directory: Path, index_file: Path, start_year: int = None, end_year: int = None):
    """Update or create case_index.json with all cases"""
    
    print("Scanning for case files...")
    
    # Load existing index if it exists
    case_index = {}
    if index_file.exists():
        with open(index_file, 'r', encoding='utf-8') as f:
            case_index = json.load(f)
        print(f"Loaded existing index with {len(case_index)} cases")
    
    # Find all JSON case files
    json_files = list(directory.rglob('*.json'))
    case_files = [
        f for f in json_files 
        if not any(x in f.name.lower() for x in ['index', 'report', 'progress', 'validation'])
    ]
    
    print(f"Found {len(case_files)} case files")
    
    # Process each case
    new_cases = 0
    updated_cases = 0
    
    for case_file in sorted(case_files):
        # Extract year from path
        parts = case_file.parts
        year_str = None
        for part in parts:
            if part.isdigit() and len(part) == 4:
                year = int(part)
                if start_year and year < start_year:
                    continue
                if end_year and year > end_year:
                    continue
                year_str = part
                break
        
        if not year_str:
            continue
        
        try:
            with open(case_file, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
            
            # Create index entry
            case_id = case_file.stem  # filename without extension
            relative_path = case_file.relative_to(directory)
            
            index_entry = {
                'case_id': case_id,
                'case_number': case_data.get('case_number', ''),
                'gr_number': case_data.get('gr_number', ''),
                'year': case_data.get('year'),
                'month': case_data.get('month'),
                'decision_date': case_data.get('decision_date', ''),
                'title': case_data.get('title', ''),
                'title_summary': case_data.get('title_summary', ''),
                'volume_page': case_data.get('volume_page', ''),
                'division': case_data.get('division'),
                'categories': case_data.get('categories', []),
                'file_path': str(relative_path),
                'content_length': case_data.get('content_length', 0)
            }
            
            if case_id in case_index:
                updated_cases += 1
            else:
                new_cases += 1
            
            case_index[case_id] = index_entry
            
        except Exception as e:
            print(f"Error processing {case_file}: {e}")
    
    # Save updated index
    print(f"\nUpdating index: {new_cases} new cases, {updated_cases} updated cases")
    print(f"Total cases in index: {len(case_index)}")
    
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(case_index, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Index saved to: {index_file}")
    
    # Print statistics
    print("\nCase statistics by year:")
    year_counts = {}
    for case_id, case in case_index.items():
        year = case.get('year')
        if year:
            year_counts[year] = year_counts.get(year, 0) + 1
    
    for year in sorted(year_counts.keys()):
        print(f"  {year}: {year_counts[year]:4d} cases")
    
    return len(case_index)


def main():
    parser = argparse.ArgumentParser(description='Update case_index.json with scraped cases')
    parser.add_argument('--directory', type=str, default='RESTRUCTURED_DB',
                        help='Directory containing case files (default: RESTRUCTURED_DB)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output index file (default: DIRECTORY/case_index.json)')
    parser.add_argument('--start-year', type=int, help='Index only from this year onwards')
    parser.add_argument('--end-year', type=int, help='Index only up to this year')
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory {directory} does not exist")
        return 1
    
    if args.output:
        index_file = Path(args.output)
    else:
        index_file = directory / 'case_index.json'
    
    total_cases = update_case_index(directory, index_file, args.start_year, args.end_year)
    
    print(f"\n✅ Successfully indexed {total_cases} cases")
    return 0


if __name__ == '__main__':
    exit(main())
