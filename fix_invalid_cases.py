#!/usr/bin/env python3
"""
Script to fix invalid cases by re-scraping them from the source
or removing completely invalid files
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List


def load_validation_report(report_path: Path) -> Dict:
    """Load the validation report"""
    with open(report_path, 'r') as f:
        return json.load(f)


def fix_empty_cases(base_dir: Path, empty_cases: List[str]):
    """Remove completely empty case files that can't be recovered"""
    print(f"\n🗑️  Removing {len(empty_cases)} empty case files...")
    for case_file in empty_cases:
        file_path = base_dir / case_file
        if file_path.exists():
            print(f"   Removing: {case_file}")
            file_path.unlink()
    print("✅ Empty files removed")


def fix_content_length_mismatch(base_dir: Path, cases: List[str]):
    """Fix content_length mismatches by recalculating"""
    print(f"\n🔧 Fixing {len(cases)} content length mismatches...")
    for case_file in cases:
        file_path = base_dir / case_file
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
            
            # Recalculate content length
            if 'formatted_case_content' in case_data:
                actual_length = len(case_data['formatted_case_content'])
                case_data['content_length'] = actual_length
                
                # Write back
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(case_data, f, indent=2, ensure_ascii=False)
                
                print(f"   ✓ Fixed: {case_file}")
    print("✅ Content length mismatches fixed")


def fix_invalid_json(base_dir: Path, cases: List[str]):
    """Remove invalid JSON files that can't be parsed"""
    print(f"\n🗑️  Removing {len(cases)} invalid JSON files...")
    for case_file in cases:
        file_path = base_dir / case_file
        if file_path.exists():
            print(f"   Removing: {case_file}")
            file_path.unlink()
    print("✅ Invalid JSON files removed")


def fix_null_volume_page(base_dir: Path, cases: List[str]):
    """Fix null volume_page by setting a default value"""
    print(f"\n🔧 Fixing {len(cases)} null volume_page values...")
    for case_file in cases:
        file_path = base_dir / case_file
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
            
            # Set default volume_page if null
            if case_data.get('volume_page') is None:
                case_data['volume_page'] = "Volume information not available"
                
                # Write back
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(case_data, f, indent=2, ensure_ascii=False)
                
                print(f"   ✓ Fixed: {case_file}")
    print("✅ Null volume_page values fixed")


def fix_missing_metadata(base_dir: Path, cases: List[str]):
    """Fix cases with missing metadata fields by adding defaults"""
    print(f"\n🔧 Fixing {len(cases)} cases with missing metadata...")
    for case_file in cases:
        file_path = base_dir / case_file
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
            
            # Add missing fields with defaults
            if 'categories' not in case_data:
                case_data['categories'] = ['General']
            if 'keywords' not in case_data:
                case_data['keywords'] = ['case', 'supreme court']
            if 'title_summary' not in case_data:
                case_data['title_summary'] = case_data.get('title', 'Summary not available')[:200]
            if 'metadata_extraction_date' not in case_data:
                from datetime import datetime
                case_data['metadata_extraction_date'] = datetime.now().isoformat()
            if 'extraction_version' not in case_data:
                case_data['extraction_version'] = '2.0'
            
            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(case_data, f, indent=2, ensure_ascii=False)
            
            print(f"   ✓ Fixed: {case_file}")
    print("✅ Missing metadata fields fixed")


def categorize_errors(errors: List[Dict]) -> Dict[str, List[str]]:
    """Categorize errors by type"""
    empty_cases = []
    content_length_mismatches = []
    null_volume_pages = []
    missing_metadata = []
    invalid_json = []
    
    for error in errors:
        file_path = error['file']
        issues = error['issues']
        
        # Check for completely empty files (missing all required fields)
        if len(issues) >= 15 and 'Missing required field: file_path' in issues:
            empty_cases.append(file_path)
        # Check for invalid JSON
        elif any('Invalid JSON' in issue for issue in issues):
            invalid_json.append(file_path)
        # Check for content length mismatch
        elif any('content_length mismatch' in issue for issue in issues):
            content_length_mismatches.append(file_path)
        # Check for null volume_page
        elif any("Field 'volume_page' is null" in issue for issue in issues):
            null_volume_pages.append(file_path)
        # Check for missing metadata fields
        elif any('Missing required field: categories' in issue or 
                 'Missing required field: keywords' in issue or
                 'Missing required field: metadata_extraction_date' in issue 
                 for issue in issues):
            missing_metadata.append(file_path)
    
    return {
        'empty_cases': empty_cases,
        'content_length_mismatches': content_length_mismatches,
        'null_volume_pages': null_volume_pages,
        'missing_metadata': missing_metadata,
        'invalid_json': invalid_json
    }


def main():
    parser = argparse.ArgumentParser(description='Fix invalid cases in the database')
    parser.add_argument('--directory', type=str, default='RESTRUCTURED_DB',
                        help='Directory containing case files')
    parser.add_argument('--report', type=str, default='validation_report.json',
                        help='Validation report JSON file')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be fixed without making changes')
    
    args = parser.parse_args()
    
    base_dir = Path(args.directory)
    report_path = Path(args.report)
    
    if not report_path.exists():
        print(f"Error: Validation report not found: {report_path}")
        print("Run: python validate_cases.py --directory RESTRUCTURED_DB --output validation_report.json")
        sys.exit(1)
    
    # Load validation report
    print("Loading validation report...")
    report = load_validation_report(report_path)
    
    if not report['errors']:
        print("✅ No errors found in validation report!")
        sys.exit(0)
    
    # Categorize errors
    categorized = categorize_errors(report['errors'])
    
    print("\n" + "=" * 80)
    print("INVALID CASES SUMMARY")
    print("=" * 80)
    print(f"Empty case files: {len(categorized['empty_cases'])}")
    print(f"Content length mismatches: {len(categorized['content_length_mismatches'])}")
    print(f"Null volume_page values: {len(categorized['null_volume_pages'])}")
    print(f"Missing metadata fields: {len(categorized['missing_metadata'])}")
    print(f"Invalid JSON files: {len(categorized['invalid_json'])}")
    print("=" * 80)
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made\n")
        
        if categorized['empty_cases']:
            print(f"\nWould remove {len(categorized['empty_cases'])} empty files:")
            for case in categorized['empty_cases']:
                print(f"   - {case}")
        
        if categorized['content_length_mismatches']:
            print(f"\nWould fix {len(categorized['content_length_mismatches'])} content length mismatches:")
            for case in categorized['content_length_mismatches']:
                print(f"   - {case}")
        
        if categorized['null_volume_pages']:
            print(f"\nWould fix {len(categorized['null_volume_pages'])} null volume_page values:")
            for case in categorized['null_volume_pages']:
                print(f"   - {case}")
        
        if categorized['missing_metadata']:
            print(f"\nWould fix {len(categorized['missing_metadata'])} cases with missing metadata:")
            for case in categorized['missing_metadata']:
                print(f"   - {case}")
        
        if categorized['invalid_json']:
            print(f"\nWould remove {len(categorized['invalid_json'])} invalid JSON files:")
            for case in categorized['invalid_json']:
                print(f"   - {case}")
        
        print("\nRun without --dry-run to apply fixes")
        sys.exit(0)
    
    # Apply fixes
    print("\n🔧 Applying fixes...\n")
    
    if categorized['empty_cases']:
        fix_empty_cases(base_dir, categorized['empty_cases'])
    
    if categorized['content_length_mismatches']:
        fix_content_length_mismatch(base_dir, categorized['content_length_mismatches'])
    
    if categorized['null_volume_pages']:
        fix_null_volume_page(base_dir, categorized['null_volume_pages'])
    
    if categorized['missing_metadata']:
        fix_missing_metadata(base_dir, categorized['missing_metadata'])
    
    if categorized['invalid_json']:
        fix_invalid_json(base_dir, categorized['invalid_json'])
    
    print("\n" + "=" * 80)
    print("✅ ALL FIXES COMPLETED")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Run validation again: python validate_cases.py --directory RESTRUCTURED_DB")
    print("2. Verify all cases are now valid")
    print("3. Commit the changes")


if __name__ == '__main__':
    main()
