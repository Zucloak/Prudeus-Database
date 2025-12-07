#!/usr/bin/env python3
"""
Cleanup script to remove already-scraped cases from lawphil_missing_cases.json

This script:
1. Scans the RESTRUCTURED_DB directory for all existing case files
2. Removes those case numbers from lawphil_missing_cases.json
3. Creates a backup of the original file
4. Updates the file with only truly missing cases
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

def get_existing_case_numbers(db_path):
    """Scan RESTRUCTURED_DB and collect all existing case numbers."""
    existing_cases = set()
    
    print(f"Scanning {db_path} for existing cases...")
    
    # Walk through all directories
    for root, dirs, files in os.walk(db_path):
        for file in files:
            if file.endswith('.json'):
                # Extract case number from filename (e.g., "12345.json" -> "12345")
                case_num = file.replace('.json', '')
                existing_cases.add(case_num)
    
    print(f"Found {len(existing_cases):,} existing cases in database")
    return existing_cases

def cleanup_missing_cases(missing_cases_file, db_path):
    """Remove already-scraped cases from the missing cases list."""
    
    # Create backup
    backup_file = f"{missing_cases_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\nCreating backup: {backup_file}")
    
    # Read current missing cases
    print(f"Reading {missing_cases_file}...")
    with open(missing_cases_file, 'r') as f:
        missing_cases = json.load(f)
    
    original_count = len(missing_cases)
    print(f"Original missing cases count: {original_count:,}")
    
    # Save backup
    with open(backup_file, 'w') as f:
        json.dump(missing_cases, f, indent=2)
    print(f"Backup saved successfully")
    
    # Get existing case numbers
    existing_cases = get_existing_case_numbers(db_path)
    
    # Filter out cases that already exist
    print("\nFiltering out existing cases...")
    filtered_cases = []
    removed_count = 0
    
    for case in missing_cases:
        case_num = str(case['gr_number'])
        if case_num not in existing_cases:
            filtered_cases.append(case)
        else:
            removed_count += 1
    
    print(f"Removed {removed_count:,} cases that already exist")
    print(f"Remaining truly missing cases: {len(filtered_cases):,}")
    
    # Save cleaned file
    print(f"\nSaving cleaned file to {missing_cases_file}...")
    with open(missing_cases_file, 'w') as f:
        json.dump(filtered_cases, f, indent=2)
    
    print("\n" + "="*80)
    print("CLEANUP COMPLETE")
    print("="*80)
    print(f"Original count:     {original_count:,}")
    print(f"Existing in DB:     {removed_count:,}")
    print(f"Truly missing:      {len(filtered_cases):,}")
    print(f"Completion rate:    {(removed_count/original_count*100):.1f}%")
    print(f"Backup saved to:    {backup_file}")
    print("="*80)
    
    return len(filtered_cases)

if __name__ == "__main__":
    # Default paths
    missing_cases_file = "lawphil_missing_cases.json"
    db_path = "RESTRUCTURED_DB"
    
    # Allow override from command line
    if len(sys.argv) > 1:
        missing_cases_file = sys.argv[1]
    if len(sys.argv) > 2:
        db_path = sys.argv[2]
    
    # Validate paths
    if not os.path.exists(missing_cases_file):
        print(f"Error: Missing cases file not found: {missing_cases_file}")
        sys.exit(1)
    
    if not os.path.exists(db_path):
        print(f"Error: Database path not found: {db_path}")
        sys.exit(1)
    
    # Run cleanup
    remaining = cleanup_missing_cases(missing_cases_file, db_path)
    
    print(f"\nReady to resume scraping with {remaining:,} truly missing cases!")
    print(f"Run: python3 continuous_scrape_improved.py {db_path} 2500")
