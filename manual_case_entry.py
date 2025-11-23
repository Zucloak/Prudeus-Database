#!/usr/bin/env python3
"""
Manual Case Entry Helper

This tool helps with manual entry of Supreme Court cases into the database.
Use this when cases cannot be scraped automatically and need to be entered manually.

Usage:
    python3 manual_case_entry.py
    
The script will prompt for case information and create properly formatted JSON files.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List


def get_input_with_default(prompt: str, default: str = "") -> str:
    """Get input with optional default value."""
    if default:
        value = input(f"{prompt} [{default}]: ").strip()
        return value if value else default
    else:
        value = input(f"{prompt}: ").strip()
        while not value:
            print("This field is required.")
            value = input(f"{prompt}: ").strip()
        return value


def get_multiline_input(prompt: str) -> str:
    """Get multi-line input for case content."""
    print(f"\n{prompt}")
    print("(Enter content below. When done, type END on a new line and press Enter)")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return '\n'.join(lines)


def get_list_input(prompt: str) -> List[str]:
    """Get comma-separated list input."""
    value = input(f"{prompt} (comma-separated): ").strip()
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def categorize_case_interactive() -> List[str]:
    """Interactive category selection."""
    categories = [
        'Civil Law',
        'Criminal Law',
        'Labor Law',
        'Commercial Law',
        'Tax Law',
        'Administrative Law',
        'Constitutional Law',
        'Family Law',
        'Property Law',
        'Remedial Law'
    ]
    
    print("\nAvailable categories:")
    for i, cat in enumerate(categories, 1):
        print(f"  {i}. {cat}")
    
    print("\nSelect categories (enter numbers separated by commas, or press Enter for Civil Law):")
    selection = input("> ").strip()
    
    if not selection:
        return ['Civil Law']
    
    try:
        selected_nums = [int(n.strip()) for n in selection.split(',')]
        selected_cats = [categories[n-1] for n in selected_nums if 1 <= n <= len(categories)]
        return selected_cats if selected_cats else ['Civil Law']
    except (ValueError, IndexError):
        print("Invalid selection, defaulting to Civil Law")
        return ['Civil Law']


def create_case_entry() -> Dict:
    """Interactive case entry."""
    print("\n" + "="*80)
    print("MANUAL CASE ENTRY")
    print("="*80)
    
    # Basic information
    gr_number = get_input_with_default("G.R. Number (digits only, e.g., 165842)")
    title = get_input_with_default("Case Title (e.g., Manuel v. People)")
    
    while True:
        try:
            year_input = get_input_with_default("Year (e.g., 2005)")
            year = int(year_input)
            if 1900 <= year <= 2100:
                break
            else:
                print("Please enter a valid year between 1900 and 2100")
        except ValueError:
            print("Please enter a valid year as a number")
    
    # Month
    print("\nMonth options:")
    months = ['january', 'february', 'march', 'april', 'may', 'june',
              'july', 'august', 'september', 'october', 'november', 'december']
    for i, month in enumerate(months, 1):
        print(f"  {i}. {month}")
    
    while True:
        try:
            month_input = get_input_with_default("Select month number (1-12)")
            month_num = int(month_input)
            if 1 <= month_num <= 12:
                month = months[month_num - 1]
                break
            else:
                print("Please enter a number between 1 and 12")
        except ValueError:
            print("Please enter a valid number")
    
    # Decision date
    decision_date = get_input_with_default("Decision Date (e.g., November 29, 2005)", "")
    
    # Volume and page
    volume_page = get_input_with_default("Volume/Page (e.g., 475 Phil. 332)", "")
    
    # Categories
    categories = categorize_case_interactive()
    
    # Keywords
    keywords = get_list_input("\nKeywords")
    
    # Case content
    print("\n" + "-"*80)
    content = get_multiline_input("Enter the full case content")
    
    # Create the case data structure
    case_data = {
        'file_path': f"/manual_entry/{year}/{month}/{gr_number}.html",
        'filename': f"{gr_number}.html",
        'year': year,
        'month': month,
        'case_number': gr_number,
        'gr_number': gr_number,
        'volume_page': volume_page,
        'decision_date': decision_date if decision_date else None,
        'title': title,
        'division': None,
        'categories': categories,
        'keywords': keywords,
        'title_summary': title,
        'formatted_case_content': content,
        'content_length': len(content),
        'metadata_extraction_date': datetime.now().isoformat(),
        'extraction_version': '3.0_manual_entry',
        'source_url': 'Manual Entry',
    }
    
    return case_data


def save_case(case_data: Dict, db_path: Path) -> bool:
    """Save case to database."""
    year = case_data['year']
    month = case_data['month']
    gr_number = case_data['gr_number']
    
    # Create directory structure
    target_dir = db_path / str(year) / month
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON file
    target_file = target_dir / f"{gr_number}.json"
    
    # Check if file already exists
    if target_file.exists():
        overwrite = input(f"\nFile {target_file} already exists. Overwrite? (yes/no): ")
        if overwrite.lower() != 'yes':
            print("Cancelled.")
            return False
    
    try:
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Case saved successfully to: {target_file}")
        return True
    except Exception as e:
        print(f"\n✗ Error saving case: {e}")
        return False


def preview_case(case_data: Dict):
    """Display case data for review."""
    print("\n" + "="*80)
    print("CASE PREVIEW")
    print("="*80)
    print(f"G.R. No.: {case_data['gr_number']}")
    print(f"Title: {case_data['title']}")
    print(f"Year: {case_data['year']}")
    print(f"Month: {case_data['month']}")
    print(f"Decision Date: {case_data['decision_date']}")
    print(f"Volume/Page: {case_data['volume_page']}")
    print(f"Categories: {', '.join(case_data['categories'])}")
    print(f"Keywords: {', '.join(case_data['keywords'])}")
    print(f"Content Length: {case_data['content_length']} characters")
    print(f"\nFirst 200 characters of content:")
    print(case_data['formatted_case_content'][:200] + "...")
    print("="*80)


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python3 manual_case_entry.py <RESTRUCTURED_DB_path>")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    
    if not db_path.exists():
        print(f"Error: {db_path} does not exist")
        sys.exit(1)
    
    print("="*80)
    print("MANUAL CASE ENTRY HELPER")
    print("="*80)
    print("\nThis tool helps you manually add cases to the database.")
    print("You'll be prompted for case information step by step.")
    
    while True:
        try:
            # Create case entry
            case_data = create_case_entry()
            
            # Preview
            preview_case(case_data)
            
            # Confirm
            confirm = input("\nSave this case? (yes/no): ")
            if confirm.lower() == 'yes':
                save_case(case_data, db_path)
            else:
                print("Case not saved.")
            
            # Continue?
            another = input("\nEnter another case? (yes/no): ")
            if another.lower() != 'yes':
                break
                
        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            break
        except Exception as e:
            print(f"\n✗ Error: {e}")
            retry = input("Try again? (yes/no): ")
            if retry.lower() != 'yes':
                break
    
    print("\n" + "="*80)
    print("Thank you for using the Manual Case Entry Helper!")
    print("="*80)


if __name__ == '__main__':
    main()
