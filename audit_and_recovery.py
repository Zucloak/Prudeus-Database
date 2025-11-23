#!/usr/bin/env python3
"""
Supreme Court Case Data Audit & Recovery Tool (2005-2024)

This script performs:
1. Priority case assessment (9 specific cases)
2. Data gap analysis for 2005-2024
3. Untitled case resolution
4. Structured JSON report generation
"""

import json
import glob
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import sys


# Priority cases requested by user
PRIORITY_CASES = [
    {
        'gr_number': '231896',
        'title': 'Municipality of Tupi v. Faustino',
        'year': 2019,
        'expected_status': 'MISSING'
    },
    {
        'gr_number': '165842',
        'title': 'Manuel v. People',
        'year': 2005,
        'expected_status': 'MISSING'
    },
    {
        'gr_number': '213198',
        'title': 'Toyo v. Toyo',
        'year': 2019,
        'expected_status': 'MISSING'
    },
    {
        'gr_number': '232269',
        'title': 'Asilo v. Gonzales-Betic',
        'year': 2024,
        'expected_status': 'FOUND_WITH_ERRORS'
    },
    {
        'gr_number': '164815',
        'title': 'Valeroso v. People',
        'year': 2008,
        'expected_status': 'MISSING'
    },
    {
        'gr_number': '257697',
        'title': 'San Miguel v. Commissioner',
        'year': 2023,
        'expected_status': 'MISSING'
    },
    {
        'gr_number': '189516',
        'title': 'Otamias v. Republic',
        'year': 2016,
        'expected_status': 'MISSING'
    },
    {
        'gr_number': '209969',
        'title': 'Sanico v. Colipano',
        'year': 2017,
        'expected_status': 'MISSING'
    },
    {
        'gr_number': '203754',
        'title': 'Film Devt. Council v. Colon',
        'year': 2019,
        'expected_status': 'MISSING'
    }
]


TARGET_YEARS = [2005, 2008, 2016, 2017, 2019, 2023, 2024]


class DatabaseAuditor:
    """Audits the Supreme Court case database"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.gr_by_year: Dict[int, Set[int]] = defaultdict(set)
        self.case_files: Dict[str, List[Path]] = defaultdict(list)
        self.untitled_cases: List[Dict] = []
        self.total_files = 0
        
    def scan_database(self):
        """Scan the entire database and collect statistics"""
        print("Scanning database...")
        
        for file_path in glob.glob(f'{self.db_path}/*/*/*.json'):
            if 'case_index' in file_path:
                continue
            
            self.total_files += 1
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Extract GR number
                gr_num = data.get('gr_number', '')
                year = data.get('year')
                title = data.get('title', '').strip()
                
                # Track GR numbers by year
                match = re.search(r'(\d+)', gr_num)
                if match and year:
                    gr_int = int(match.group(1))
                    self.gr_by_year[year].add(gr_int)
                    self.case_files[f"{year}_{gr_int}"].append(Path(file_path))
                
                # Track untitled cases
                if title in ['Untitled Case', 'Title not found', '']:
                    self.untitled_cases.append({
                        'file_path': file_path,
                        'gr_number': gr_num,
                        'year': year,
                        'content_length': data.get('content_length', 0)
                    })
                    
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        print(f"Scanned {self.total_files} case files")
        print(f"Found {len(self.untitled_cases)} untitled cases")
    
    def check_priority_cases(self) -> List[Dict]:
        """Check status of priority cases"""
        print("\nChecking priority cases...")
        results = []
        
        for case in PRIORITY_CASES:
            gr_num = int(case['gr_number'])
            year = case['year']
            
            # Check if case exists
            found_files = self.case_files.get(f"{year}_{gr_num}", [])
            
            if found_files:
                # Case found - check for issues
                status = 'FOUND'
                issues = []
                
                # Check all instances (might be duplicates)
                for file_path in found_files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            title = data.get('title', '').strip()
                            
                            # Check for title issues
                            if 'VS. VS.' in title.upper() or 'V. V.' in title.upper():
                                issues.append('Duplicate VS in title')
                                status = 'FOUND_WITH_ERRORS'
                            if title in ['Untitled Case', 'Title not found', '']:
                                issues.append('Missing title')
                                status = 'FOUND_WITH_ERRORS'
                            if not data.get('formatted_case_content'):
                                issues.append('Missing case content')
                                status = 'FOUND_WITH_ERRORS'
                    except Exception as e:
                        issues.append(f'File read error: {e}')
                        status = 'FOUND_WITH_ERRORS'
                
                results.append({
                    'gr_number': case['gr_number'],
                    'title': case['title'],
                    'year': year,
                    'status': status,
                    'file_paths': [str(f) for f in found_files],
                    'issues': issues if issues else None
                })
            else:
                # Case not found
                results.append({
                    'gr_number': case['gr_number'],
                    'title': case['title'],
                    'year': year,
                    'status': 'MISSING',
                    'file_paths': [],
                    'issues': ['Case not in database']
                })
        
        return results
    
    def analyze_coverage_gaps(self) -> Dict[int, Dict]:
        """Analyze coverage gaps for target years"""
        print("\nAnalyzing coverage gaps...")
        gaps = {}
        
        for year in TARGET_YEARS:
            if year not in self.gr_by_year or len(self.gr_by_year[year]) == 0:
                gaps[year] = {
                    'cases_in_db': 0,
                    'min_gr': None,
                    'max_gr': None,
                    'coverage_percent': 0.0,
                    'sample_missing': []
                }
                continue
            
            gr_nums = sorted(self.gr_by_year[year])
            min_gr = min(gr_nums)
            max_gr = max(gr_nums)
            expected_count = max_gr - min_gr + 1
            
            # Find missing cases
            all_expected = set(range(min_gr, max_gr + 1))
            missing = all_expected - self.gr_by_year[year]
            
            gaps[year] = {
                'cases_in_db': len(gr_nums),
                'min_gr': min_gr,
                'max_gr': max_gr,
                'expected_total': expected_count,
                'missing_count': len(missing),
                'coverage_percent': (len(gr_nums) / expected_count * 100) if expected_count > 0 else 0,
                'sample_missing': sorted(missing)[:20]  # First 20 missing
            }
        
        return gaps
    
    def infer_titles_for_untitled_cases(self) -> List[Dict]:
        """Attempt to infer titles from case content"""
        print("\nInferring titles for untitled cases...")
        results = []
        
        for case in self.untitled_cases[:20]:  # Process first 20 as sample
            try:
                with open(case['file_path'], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    content = data.get('formatted_case_content', '')
                    
                    # Try to extract title from content
                    inferred_title, confidence = self._infer_title_from_content(content)
                    
                    results.append({
                        'file_path': case['file_path'],
                        'gr_number': case['gr_number'],
                        'year': case['year'],
                        'current_title': data.get('title', ''),
                        'inferred_title': inferred_title,
                        'confidence': confidence,
                        'requires_manual_review': confidence < 0.7
                    })
            except Exception as e:
                print(f"Error inferring title for {case['file_path']}: {e}")
        
        return results
    
    def _infer_title_from_content(self, content: str) -> Tuple[Optional[str], float]:
        """Infer case title from content with confidence score"""
        if not content or len(content) < 100:
            return None, 0.0
        
        # Pattern 1: Look for "X vs. Y" or "X v. Y" at the start
        patterns = [
            r'^([A-Z][A-Za-z\s\.,]+?)\s+(?:vs?\.?|versus)\s+([A-Z][A-Za-z\s\.,]+?)(?:\n|,|\.|G\.R\.)',
            r'G\.R\.\s+No\.\s+\d+\s*\n+([A-Z][A-Za-z\s\.,]+?)\s+(?:vs?\.?|versus)\s+([A-Z][A-Za-z\s\.,]+?)(?:\n|,|\.)',
            r'([A-Z][A-Z\s]+?),?\s+(?:vs?\.?|versus)\s+([A-Z][A-Z\s]+?)(?:\n|,|\.)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content[:1000], re.MULTILINE | re.IGNORECASE)
            if match:
                petitioner = match.group(1).strip()
                respondent = match.group(2).strip()
                
                # Clean up names
                petitioner = re.sub(r'\s+', ' ', petitioner).strip()
                respondent = re.sub(r'\s+', ' ', respondent).strip()
                
                # Validate names (not too long, not too short)
                if 5 < len(petitioner) < 100 and 5 < len(respondent) < 100:
                    title = f"{petitioner} vs. {respondent}"
                    confidence = 0.8
                    return title, confidence
        
        return None, 0.0
    
    def generate_report(self, priority_results: List[Dict], 
                       coverage_gaps: Dict, 
                       untitled_analysis: List[Dict]) -> Dict:
        """Generate comprehensive JSON report"""
        
        # Count status types
        found_count = sum(1 for r in priority_results if r['status'] == 'FOUND')
        found_with_errors = sum(1 for r in priority_results if r['status'] == 'FOUND_WITH_ERRORS')
        missing_count = sum(1 for r in priority_results if r['status'] == 'MISSING')
        
        # Calculate total missing across target years
        total_missing = sum(gaps['missing_count'] for gaps in coverage_gaps.values())
        
        report = {
            'report_date': datetime.now().isoformat(),
            'report_version': '1.0',
            'summary': {
                'total_files_scanned': self.total_files,
                'untitled_cases': len(self.untitled_cases),
                'priority_cases_requested': len(PRIORITY_CASES),
                'priority_cases_found': found_count,
                'priority_cases_found_with_errors': found_with_errors,
                'priority_cases_missing': missing_count,
                'target_years_coverage': TARGET_YEARS,
                'estimated_total_missing': total_missing
            },
            'priority_cases_status': priority_results,
            'coverage_analysis_by_year': coverage_gaps,
            'untitled_cases_sample': untitled_analysis[:20],
            'recommended_actions': [
                {
                    'priority': 'HIGH',
                    'action': 'Scrape missing priority cases',
                    'details': f'{missing_count} priority cases need to be scraped from lawphil.net or Supreme Court E-Library'
                },
                {
                    'priority': 'HIGH',
                    'action': 'Fix cases found with errors',
                    'details': f'{found_with_errors} cases found but have issues that need correction'
                },
                {
                    'priority': 'MEDIUM',
                    'action': 'Systematic scraping for 2005-2024',
                    'details': f'Coverage is extremely sparse (<1%) for target years. Estimated {total_missing:,} cases missing in range.'
                },
                {
                    'priority': 'LOW',
                    'action': 'Resolve untitled cases',
                    'details': f'{len(self.untitled_cases)} cases have "Untitled Case" label and need title inference or manual review'
                }
            ],
            'scraping_targets': [
                {
                    'gr_number': r['gr_number'],
                    'title': r['title'],
                    'year': r['year']
                }
                for r in priority_results if r['status'] == 'MISSING'
            ]
        }
        
        return report


def main():
    """Main execution function"""
    if len(sys.argv) < 2:
        print("Usage: python3 audit_and_recovery.py <RESTRUCTURED_DB_path> [output_file]")
        sys.exit(1)
    
    db_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'AUDIT_REPORT.json'
    
    print("="*80)
    print("SUPREME COURT CASE DATA AUDIT & RECOVERY")
    print("="*80)
    print(f"Database path: {db_path}")
    print(f"Target years: {', '.join(map(str, TARGET_YEARS))}")
    print(f"Priority cases: {len(PRIORITY_CASES)}")
    print()
    
    # Initialize auditor
    auditor = DatabaseAuditor(db_path)
    
    # Step 1: Scan database
    auditor.scan_database()
    
    # Step 2: Check priority cases
    priority_results = auditor.check_priority_cases()
    
    # Step 3: Analyze coverage gaps
    coverage_gaps = auditor.analyze_coverage_gaps()
    
    # Step 4: Infer titles for untitled cases
    untitled_analysis = auditor.infer_titles_for_untitled_cases()
    
    # Step 5: Generate comprehensive report
    report = auditor.generate_report(priority_results, coverage_gaps, untitled_analysis)
    
    # Save report
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*80)
    print("AUDIT SUMMARY")
    print("="*80)
    print(f"Total files scanned: {report['summary']['total_files_scanned']:,}")
    print(f"Untitled cases: {report['summary']['untitled_cases']}")
    print(f"\nPriority Cases Status:")
    print(f"  ✓ Found: {report['summary']['priority_cases_found']}")
    print(f"  ⚠ Found with errors: {report['summary']['priority_cases_found_with_errors']}")
    print(f"  ✗ Missing: {report['summary']['priority_cases_missing']}")
    print(f"\nReport saved to: {output_file}")
    print("="*80)
    
    # Print priority case details
    print("\nPriority Cases Details:")
    print("-" * 80)
    for case in priority_results:
        status_symbol = {
            'FOUND': '✓',
            'FOUND_WITH_ERRORS': '⚠',
            'MISSING': '✗'
        }.get(case['status'], '?')
        
        print(f"{status_symbol} G.R. {case['gr_number']} ({case['year']}): {case['title']}")
        print(f"  Status: {case['status']}")
        if case.get('issues'):
            print(f"  Issues: {', '.join(case['issues'])}")
        if case.get('file_paths'):
            print(f"  Files: {len(case['file_paths'])}")
    
    # Print coverage summary
    print("\n" + "="*80)
    print("COVERAGE BY YEAR")
    print("="*80)
    for year, data in sorted(coverage_gaps.items()):
        print(f"{year}:")
        print(f"  Cases in DB: {data['cases_in_db']}")
        if data['min_gr']:
            print(f"  GR Range: {data['min_gr']:,} - {data['max_gr']:,}")
            print(f"  Coverage: {data['coverage_percent']:.2f}%")
            print(f"  Missing: {data['missing_count']:,} cases")
        else:
            print(f"  NO CASES FOUND")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
