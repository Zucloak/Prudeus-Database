#!/usr/bin/env python3
"""
Generate sample case files to demonstrate the expected format
This creates example cases that match the database schema
"""

import json
from pathlib import Path
from datetime import datetime


def create_sample_cases():
    """Create sample case files in the correct format"""
    
    samples = [
        {
            'year': 1901,
            'month': 'august',
            'case_number': 'G.R. No. 1',
            'gr_number': '1',
            'title': 'SMITH vs. JONES',
            'decision_date': 'August 15, 1901',
            'volume_page': '1 Phil. 1',
            'division': 'En Banc',
            'content': '''FIRST DIVISION

[ G.R. No. 1, August 15, 1901 ]

SMITH vs. JONES

D E C I S I O N

This is a sample case to demonstrate the format.

The case involves a dispute between Smith and Jones regarding property rights.

ACCORDINGLY, the petition is GRANTED.

SO ORDERED.'''
        },
        {
            'year': 1901,
            'month': 'september',
            'case_number': 'G.R. No. 2',
            'gr_number': '2',
            'title': 'REPUBLIC OF THE PHILIPPINES vs. DOE',
            'decision_date': 'September 1, 1901',
            'volume_page': '1 Phil. 25',
            'division': None,
            'content': '''[ G.R. No. 2, September 1, 1901 ]

REPUBLIC OF THE PHILIPPINES vs. DOE

D E C I S I O N

This is another sample case demonstrating the database format.

The Supreme Court rules on an important matter of law.

WHEREFORE, the decision is AFFIRMED.

SO ORDERED.'''
        }
    ]
    
    output_dir = Path('SAMPLE_CASES')
    
    for sample in samples:
        # Create directory structure
        case_dir = output_dir / str(sample['year']) / sample['month']
        case_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate case data with all required fields
        case_data = {
            'file_path': f"/workspace/PRUDEUS_DB/WEBPAGE_VERSION/{sample['year']}/{sample['month']}/GR_{sample['gr_number']}.html",
            'filename': f"GR_{sample['gr_number']}.html",
            'year': sample['year'],
            'month': sample['month'],
            'case_number': sample['case_number'],
            'gr_number': sample['gr_number'],
            'volume_page': sample['volume_page'],
            'decision_date': sample['decision_date'],
            'title': sample['title'],
            'division': sample['division'],
            'categories': ['Civil Law', 'Property Law'],
            'keywords': ['property', 'rights', 'dispute', 'petition', 'court', 'decision'],
            'title_summary': sample['title'],
            'formatted_case_content': sample['content'],
            'content_length': len(sample['content']),
            'metadata_extraction_date': datetime.now().isoformat(),
            'extraction_version': '2.0_enhanced_full_content'
        }
        
        # Save to JSON file
        filename = f"G_R__No__{sample['gr_number']}.json"
        filepath = case_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(case_data, f, indent=2, ensure_ascii=False)
        
        print(f"Created: {filepath}")
    
    print(f"\n✅ Sample cases created in: {output_dir}")
    print("\nYou can examine these files to understand the expected format:")
    print(f"  cat {output_dir}/1901/august/G_R__No__1.json | python -m json.tool")
    print("\nThese samples show:")
    print("  - Required metadata fields")
    print("  - Proper JSON structure")
    print("  - Case content formatting")
    print("  - File naming convention")
    print("  - Directory organization")


if __name__ == '__main__':
    create_sample_cases()
