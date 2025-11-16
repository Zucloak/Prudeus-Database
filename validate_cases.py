#!/usr/bin/env python3
"""
Case Validation Script for Prudeus Database
Validates that all cases have complete metadata with no null values
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class CaseValidator:
    """Validates case JSON files for completeness and correctness"""
    
    REQUIRED_FIELDS = [
        'file_path',
        'filename',
        'year',
        'month',
        'case_number',
        'gr_number',
        'volume_page',
        'decision_date',
        'title',
        'categories',
        'keywords',
        'title_summary',
        'formatted_case_content',
        'content_length',
        'metadata_extraction_date',
        'extraction_version'
    ]
    
    # Fields that can be null
    NULLABLE_FIELDS = ['division', 'decision_date']
    
    VALID_MONTHS = [
        'january', 'february', 'march', 'april', 'may', 'june',
        'july', 'august', 'september', 'october', 'november', 'december',
        '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12',
        '1', '2', '3', '4', '5', '6', '7', '8', '9'
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.cases_validated = 0
        
    def validate_case(self, case_path: Path) -> Tuple[bool, List[str]]:
        """Validate a single case file"""
        issues = []
        
        # Check file can be opened and is valid JSON
        try:
            with open(case_path, 'r', encoding='utf-8') as f:
                case_data = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]
        except Exception as e:
            return False, [f"Cannot read file: {e}"]
        
        # Check all required fields are present
        for field in self.REQUIRED_FIELDS:
            if field not in case_data:
                issues.append(f"Missing required field: {field}")
        
        # Check for null values in required fields (excluding nullable fields)
        for field in self.REQUIRED_FIELDS:
            if field in case_data and case_data[field] is None:
                if field not in self.NULLABLE_FIELDS:
                    issues.append(f"Field '{field}' is null but should have a value")
            elif field in case_data and field not in ['categories', 'keywords'] and field not in self.NULLABLE_FIELDS:
                # Check for empty strings in non-array fields
                if isinstance(case_data[field], str) and case_data[field].strip() == '':
                    issues.append(f"Field '{field}' is empty")
        
        # Check array fields are not empty
        if 'categories' in case_data:
            if not isinstance(case_data['categories'], list):
                issues.append("Field 'categories' must be an array")
            elif len(case_data['categories']) == 0:
                issues.append("Field 'categories' is empty")
        
        if 'keywords' in case_data:
            if not isinstance(case_data['keywords'], list):
                issues.append("Field 'keywords' must be an array")
            elif len(case_data['keywords']) == 0:
                issues.append("Field 'keywords' is empty")
        
        # Validate year is an integer
        if 'year' in case_data:
            if not isinstance(case_data['year'], int):
                issues.append(f"Field 'year' must be an integer, got {type(case_data['year']).__name__}")
            elif case_data['year'] < 1900 or case_data['year'] > 2100:
                issues.append(f"Field 'year' has invalid value: {case_data['year']}")
        
        # Validate month
        if 'month' in case_data:
            month_str = str(case_data['month']).lower()
            if month_str not in self.VALID_MONTHS:
                issues.append(f"Invalid month: {case_data['month']}")
        
        # Validate content_length matches actual content length
        if 'content_length' in case_data and 'formatted_case_content' in case_data:
            actual_length = len(case_data['formatted_case_content'])
            if case_data['content_length'] != actual_length:
                issues.append(f"content_length mismatch: declared {case_data['content_length']}, actual {actual_length}")
        
        # Validate file path structure matches actual location
        if 'year' in case_data and 'month' in case_data:
            expected_path_part = f"{case_data['year']}/{case_data['month']}"
            actual_path = str(case_path)
            if expected_path_part not in actual_path:
                issues.append(f"File location doesn't match year/month: expected {expected_path_part} in path")
        
        return len(issues) == 0, issues
    
    def validate_directory(self, directory: Path, start_year: int = None, end_year: int = None) -> Dict:
        """Validate all cases in a directory"""
        print(f"Validating cases in: {directory}")
        print("=" * 80)
        
        results = {
            'total_cases': 0,
            'valid_cases': 0,
            'invalid_cases': 0,
            'cases_by_year': {},
            'errors': []
        }
        
        # Find all JSON files
        json_files = list(directory.rglob('*.json'))
        
        # Filter out index and report files
        case_files = [
            f for f in json_files 
            if not any(x in f.name.lower() for x in ['index', 'report', 'progress'])
        ]
        
        print(f"Found {len(case_files)} case files to validate\n")
        
        for case_file in sorted(case_files):
            # Extract year from path
            parts = case_file.parts
            year_str = None
            for part in parts:
                if part.isdigit() and len(part) == 4:
                    year_str = part
                    break
            
            if year_str:
                year = int(year_str)
                if start_year and year < start_year:
                    continue
                if end_year and year > end_year:
                    continue
                
                if year not in results['cases_by_year']:
                    results['cases_by_year'][year] = {'valid': 0, 'invalid': 0}
            
            results['total_cases'] += 1
            is_valid, issues = self.validate_case(case_file)
            
            if is_valid:
                results['valid_cases'] += 1
                if year_str:
                    results['cases_by_year'][int(year_str)]['valid'] += 1
            else:
                results['invalid_cases'] += 1
                if year_str:
                    results['cases_by_year'][int(year_str)]['invalid'] += 1
                
                error_info = {
                    'file': str(case_file.relative_to(directory)),
                    'issues': issues
                }
                results['errors'].append(error_info)
                
                # Print error immediately
                print(f"❌ {case_file.relative_to(directory)}")
                for issue in issues:
                    print(f"   - {issue}")
                print()
            
            # Progress indicator
            if results['total_cases'] % 100 == 0:
                print(f"Validated {results['total_cases']} cases... ({results['valid_cases']} valid, {results['invalid_cases']} invalid)")
        
        return results
    
    def print_summary(self, results: Dict):
        """Print validation summary"""
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Total cases validated: {results['total_cases']}")
        print(f"Valid cases: {results['valid_cases']} ({results['valid_cases']/results['total_cases']*100:.1f}%)")
        print(f"Invalid cases: {results['invalid_cases']} ({results['invalid_cases']/results['total_cases']*100:.1f}%)")
        
        if results['cases_by_year']:
            print("\nCases by year:")
            print("-" * 80)
            for year in sorted(results['cases_by_year'].keys()):
                stats = results['cases_by_year'][year]
                total = stats['valid'] + stats['invalid']
                print(f"  {year}: {total:4d} cases ({stats['valid']:4d} valid, {stats['invalid']:4d} invalid)")
        
        if results['invalid_cases'] > 0:
            print(f"\n⚠️  Found {results['invalid_cases']} cases with issues")
            print("   Review the errors above and fix the issues")
            return False
        else:
            print("\n✅ All cases are valid!")
            return True


def main():
    parser = argparse.ArgumentParser(description='Validate Prudeus Database case files')
    parser.add_argument('--directory', type=str, default='RESTRUCTURED_DB',
                        help='Directory containing case files (default: RESTRUCTURED_DB)')
    parser.add_argument('--start-year', type=int, help='Validate only from this year onwards')
    parser.add_argument('--end-year', type=int, help='Validate only up to this year')
    parser.add_argument('--output', type=str, help='Save validation report to JSON file')
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    if not directory.exists():
        print(f"Error: Directory {directory} does not exist")
        sys.exit(1)
    
    validator = CaseValidator()
    results = validator.validate_directory(directory, args.start_year, args.end_year)
    
    # Print summary
    all_valid = validator.print_summary(results)
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nValidation report saved to: {args.output}")
    
    # Exit with error code if validation failed
    sys.exit(0 if all_valid else 1)


if __name__ == '__main__':
    main()
