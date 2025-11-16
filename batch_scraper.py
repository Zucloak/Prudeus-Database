#!/usr/bin/env python3
"""
Batch scraper with progress tracking and resume capability
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


class ProgressTracker:
    """Track scraping progress and enable resume"""
    
    def __init__(self, progress_file: str = 'scraping_progress.json'):
        self.progress_file = Path(progress_file)
        self.progress = self.load_progress()
    
    def load_progress(self) -> dict:
        """Load progress from file"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            'completed_years': [],
            'current_year': None,
            'completed_months': [],
            'last_updated': None,
            'total_cases_scraped': 0
        }
    
    def save_progress(self):
        """Save progress to file"""
        self.progress['last_updated'] = datetime.now().isoformat()
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def mark_year_complete(self, year: int):
        """Mark a year as completed"""
        if year not in self.progress['completed_years']:
            self.progress['completed_years'].append(year)
            self.progress['completed_years'].sort()
        self.progress['current_year'] = None
        self.progress['completed_months'] = []
        self.save_progress()
    
    def mark_month_complete(self, year: int, month: str):
        """Mark a month as completed"""
        self.progress['current_year'] = year
        if month not in self.progress['completed_months']:
            self.progress['completed_months'].append(month)
        self.save_progress()
    
    def is_year_complete(self, year: int) -> bool:
        """Check if a year is already completed"""
        return year in self.progress['completed_years']
    
    def is_month_complete(self, year: int, month: str) -> bool:
        """Check if a month is already completed"""
        return (self.progress['current_year'] == year and 
                month in self.progress['completed_months'])
    
    def get_resume_point(self, start_year: int, end_year: int) -> tuple:
        """Get the point to resume scraping from"""
        # Find the first uncompleted year
        for year in range(start_year, end_year + 1):
            if not self.is_year_complete(year):
                return year, 'january'
        return None, None


def get_months():
    """Get list of months"""
    return ['january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december']


def count_cases_in_directory(directory: Path, year: int, month: str) -> int:
    """Count cases in a specific year/month directory"""
    path = directory / str(year) / month
    if not path.exists():
        return 0
    return len(list(path.glob('*.json')))


def main():
    parser = argparse.ArgumentParser(description='Batch scraper with progress tracking')
    parser.add_argument('--start-year', type=int, default=1901, help='Starting year')
    parser.add_argument('--end-year', type=int, default=1995, help='Ending year')
    parser.add_argument('--output-dir', type=str, default='RESTRUCTURED_DB', help='Output directory')
    parser.add_argument('--progress-file', type=str, default='scraping_progress.json',
                        help='Progress tracking file')
    parser.add_argument('--resume', action='store_true', help='Resume from last position')
    parser.add_argument('--reset', action='store_true', help='Reset progress and start over')
    parser.add_argument('--status', action='store_true', help='Show current status')
    
    args = parser.parse_args()
    
    tracker = ProgressTracker(args.progress_file)
    output_dir = Path(args.output_dir)
    
    # Show status and exit
    if args.status:
        print("=== Scraping Progress Status ===")
        print(f"Completed years: {len(tracker.progress['completed_years'])}")
        if tracker.progress['completed_years']:
            print(f"  Years: {', '.join(map(str, tracker.progress['completed_years']))}")
        print(f"Current year: {tracker.progress['current_year']}")
        if tracker.progress['current_year']:
            print(f"Completed months in current year: {', '.join(tracker.progress['completed_months'])}")
        print(f"Total cases scraped: {tracker.progress['total_cases_scraped']}")
        print(f"Last updated: {tracker.progress['last_updated']}")
        
        if args.resume:
            resume_year, resume_month = tracker.get_resume_point(args.start_year, args.end_year)
            if resume_year:
                print(f"\nWould resume from: {resume_month.title()} {resume_year}")
            else:
                print("\nAll years completed!")
        return 0
    
    # Reset progress
    if args.reset:
        print("Resetting progress...")
        tracker.progress = {
            'completed_years': [],
            'current_year': None,
            'completed_months': [],
            'last_updated': None,
            'total_cases_scraped': 0
        }
        tracker.save_progress()
        print("Progress reset complete")
        return 0
    
    # Determine starting point
    if args.resume:
        resume_year, resume_month = tracker.get_resume_point(args.start_year, args.end_year)
        if resume_year:
            print(f"Resuming from {resume_month.title()} {resume_year}")
            start_year = resume_year
            start_month = resume_month
        else:
            print("All years already completed!")
            return 0
    else:
        start_year = args.start_year
        start_month = 'august' if start_year == 1901 else 'january'
    
    print("\n=== Batch Scraping Configuration ===")
    print(f"Years: {start_year} to {args.end_year}")
    print(f"Starting from: {start_month.title()} {start_year}")
    print(f"Output directory: {output_dir}")
    print(f"Progress file: {args.progress_file}")
    print("\nThis will take a long time. Press Ctrl+C to stop at any time.")
    print("You can resume later using --resume flag.\n")
    
    # Import scraper
    try:
        from scraper import LawPhilScraper
    except ImportError:
        print("Error: scraper.py not found or cannot be imported")
        return 1
    
    # Create scraper instance
    scraper = LawPhilScraper(str(output_dir), delay=2.0)
    months = get_months()
    
    # Process each year
    for year in range(start_year, args.end_year + 1):
        if tracker.is_year_complete(year):
            print(f"\n=== Skipping {year} (already completed) ===")
            continue
        
        print(f"\n=== Processing Year {year} ===")
        
        # Determine month range for this year
        if year == start_year:
            month_start_idx = months.index(start_month)
        else:
            month_start_idx = 0
        
        if year == args.end_year:
            month_end_idx = 12  # December
        else:
            month_end_idx = 12
        
        # Process each month
        year_total_cases = 0
        for month in months[month_start_idx:month_end_idx]:
            if tracker.is_month_complete(year, month):
                existing_cases = count_cases_in_directory(output_dir, year, month)
                print(f"  Skipping {month.title()} (already completed, {existing_cases} cases)")
                year_total_cases += existing_cases
                continue
            
            print(f"\n  --- {month.title()} {year} ---")
            
            try:
                # Scrape this month
                scraper.scrape_year(year, month, month)
                
                # Count cases
                month_cases = count_cases_in_directory(output_dir, year, month)
                print(f"  Completed {month.title()}: {month_cases} cases")
                year_total_cases += month_cases
                
                # Mark month complete
                tracker.mark_month_complete(year, month)
                tracker.progress['total_cases_scraped'] += month_cases
                tracker.save_progress()
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Progress saved.")
                print(f"Resume with: python batch_scraper.py --resume --start-year {args.start_year} --end-year {args.end_year}")
                return 0
            except Exception as e:
                print(f"  Error processing {month} {year}: {e}")
                print("  Continuing to next month...")
        
        # Mark year complete
        tracker.mark_year_complete(year)
        print(f"\n  Year {year} completed: {year_total_cases} total cases")
    
    print("\n=== Batch Scraping Complete ===")
    print(f"Total cases scraped: {tracker.progress['total_cases_scraped']}")
    print("\nRun validation:")
    print(f"  python validate_cases.py --directory {output_dir} --start-year {args.start_year} --end-year {args.end_year}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
