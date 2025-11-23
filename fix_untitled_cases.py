#!/usr/bin/env python3
"""
Untitled Case Title Inference Tool

This script attempts to infer titles for cases marked as "Untitled Case"
by analyzing the case content and extracting party names.
"""

import json
import glob
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Dict, List
import sys


class TitleInferencer:
    """Infers titles for untitled cases"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.fixed_count = 0
        self.low_confidence_count = 0
        self.failed_count = 0
        self.fixed_files = []
        
    def infer_title_from_content(self, content: str) -> Tuple[Optional[str], float]:
        """
        Infer case title from content with confidence score
        
        Returns: (title, confidence_score)
        confidence_score: 0.0 to 1.0
        """
        if not content or len(content) < 100:
            return None, 0.0
        
        # Pattern 1: Look for party names with vs/v. near the beginning
        patterns = [
            # Standard format at beginning
            r'^([A-Z][A-Za-z\s\.,&]+?)\s+(?:vs?\.?|versus)\s+([A-Z][A-Za-z\s\.,&]+?)(?:\n|G\.R\.|,\s*G\.R\.)',
            # After GR number
            r'G\.R\.\s+No\.\s+\d+\s*[\n,]\s*([A-Z][A-Za-z\s\.,&]+?)\s+(?:vs?\.?|versus)\s+([A-Z][A-Za-z\s\.,&]+?)(?:\n|,)',
            # All caps format
            r'([A-Z][A-Z\s&,\.]+?),?\s+(?:vs?\.?|versus)\s+([A-Z][A-Z\s&,\.]+?)(?:\n|,)',
            # Petitioner/Respondent format
            r'([A-Z][A-Za-z\s\.,&]+?),\s*(?:petitioner|plaintiff)\s*(?:vs?\.?|versus)\s+([A-Z][A-Za-z\s\.,&]+?),\s*(?:respondent|defendant)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content[:2000], re.MULTILINE | re.IGNORECASE)
            if match:
                petitioner = match.group(1).strip()
                respondent = match.group(2).strip()
                
                # Clean up names
                petitioner = re.sub(r'\s+', ' ', petitioner).strip()
                respondent = re.sub(r'\s+', ' ', respondent).strip()
                
                # Remove trailing commas, periods
                petitioner = petitioner.rstrip('.,')
                respondent = respondent.rstrip('.,')
                
                # Validate names
                if self._validate_party_names(petitioner, respondent):
                    title = f"{petitioner} vs. {respondent}"
                    confidence = self._calculate_confidence(petitioner, respondent, pattern)
                    return title, confidence
        
        # Pattern 2: Look for "PEOPLE OF THE PHILIPPINES" cases
        people_pattern = r'(PEOPLE\s+OF\s+THE\s+PHILIPPINES)\s+(?:vs?\.?|versus)\s+([A-Z][A-Za-z\s\.,&]+?)(?:\n|,)'
        match = re.search(people_pattern, content[:2000], re.IGNORECASE)
        if match:
            respondent = match.group(2).strip().rstrip('.,')
            if 5 < len(respondent) < 100:
                title = f"People of the Philippines vs. {respondent}"
                return title, 0.85
        
        return None, 0.0
    
    def _validate_party_names(self, petitioner: str, respondent: str) -> bool:
        """Validate that extracted party names look reasonable"""
        # Length checks
        if not (3 < len(petitioner) < 150 and 3 < len(respondent) < 150):
            return False
        
        # Check for invalid patterns
        invalid_patterns = [
            r'^\d+$',  # Only numbers
            r'^[^A-Za-z]+$',  # No letters
            r'(?:printer|friendly|version|click|here|source|library)',  # Website artifacts
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d+,\s+\d{4}',  # Date
        ]
        
        for pattern in invalid_patterns:
            if re.search(pattern, petitioner, re.IGNORECASE) or re.search(pattern, respondent, re.IGNORECASE):
                return False
        
        return True
    
    def _calculate_confidence(self, petitioner: str, respondent: str, pattern: str) -> float:
        """Calculate confidence score for inferred title"""
        confidence = 0.6  # Base confidence
        
        # Boost confidence for certain indicators
        if re.match(r'^[A-Z][a-z]', petitioner):  # Proper capitalization
            confidence += 0.1
        if re.match(r'^[A-Z][a-z]', respondent):
            confidence += 0.1
        if len(petitioner.split()) >= 2:  # Multiple words
            confidence += 0.05
        if len(respondent.split()) >= 2:
            confidence += 0.05
        
        # Cap at 0.95 (never 100% certain without manual review)
        return min(confidence, 0.95)
    
    def process_untitled_cases(self, min_confidence: float = 0.6):
        """Process all untitled cases and attempt to infer titles"""
        print(f"Scanning for untitled cases in {self.db_path}...")
        
        untitled_files = []
        for file_path in glob.glob(f'{self.db_path}/*/*/*.json'):
            if 'case_index' in file_path:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    title = data.get('title', '').strip()
                    
                    if title in ['Untitled Case', 'Title not found', '']:
                        untitled_files.append(file_path)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        print(f"Found {len(untitled_files)} untitled cases")
        
        if not untitled_files:
            print("No untitled cases to process")
            return
        
        print(f"\nProcessing untitled cases (min confidence: {min_confidence})...")
        
        for i, file_path in enumerate(untitled_files, 1):
            if i % 10 == 0:
                print(f"Progress: {i}/{len(untitled_files)}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                content = data.get('formatted_case_content', '')
                current_title = data.get('title', '')
                
                # Attempt to infer title
                inferred_title, confidence = self.infer_title_from_content(content)
                
                if inferred_title and confidence >= min_confidence:
                    # Update title
                    data['title'] = inferred_title
                    data['title_summary'] = inferred_title
                    data['metadata_extraction_date'] = datetime.now().isoformat()
                    data['extraction_version'] = '2.5_title_inference'
                    
                    # Save updated file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    self.fixed_count += 1
                    self.fixed_files.append({
                        'file': file_path,
                        'old_title': current_title,
                        'new_title': inferred_title,
                        'confidence': confidence
                    })
                    
                    print(f"  ✓ Fixed: {Path(file_path).name} -> {inferred_title[:50]}... (confidence: {confidence:.2f})")
                    
                elif inferred_title:
                    self.low_confidence_count += 1
                    print(f"  ⚠ Low confidence ({confidence:.2f}): {Path(file_path).name}")
                else:
                    self.failed_count += 1
                    
            except Exception as e:
                print(f"  ✗ Error processing {file_path}: {e}")
                self.failed_count += 1
        
        print(f"\nProcessing complete:")
        print(f"  Fixed: {self.fixed_count}")
        print(f"  Low confidence (skipped): {self.low_confidence_count}")
        print(f"  Failed: {self.failed_count}")
    
    def generate_report(self) -> Dict:
        """Generate report of title inference results"""
        return {
            'processing_date': datetime.now().isoformat(),
            'total_fixed': self.fixed_count,
            'low_confidence_skipped': self.low_confidence_count,
            'failed': self.failed_count,
            'fixed_cases': self.fixed_files[:100],  # Sample of fixed cases
            'summary': {
                'success_rate': f"{(self.fixed_count / (self.fixed_count + self.low_confidence_count + self.failed_count) * 100):.1f}%" if (self.fixed_count + self.low_confidence_count + self.failed_count) > 0 else "0%"
            }
        }


def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Usage: python3 fix_untitled_cases.py <RESTRUCTURED_DB_path> [min_confidence]")
        print("\nmin_confidence: float between 0.0 and 1.0 (default: 0.6)")
        sys.exit(1)
    
    db_path = sys.argv[1]
    min_confidence = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
    
    print("="*80)
    print("UNTITLED CASE TITLE INFERENCE")
    print("="*80)
    print(f"Database: {db_path}")
    print(f"Minimum confidence: {min_confidence}")
    print()
    
    # Initialize inferencer
    inferencer = TitleInferencer(db_path)
    
    # Process untitled cases
    inferencer.process_untitled_cases(min_confidence)
    
    # Generate report
    report = inferencer.generate_report()
    
    # Save report
    report_file = 'TITLE_INFERENCE_REPORT.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\nReport saved to: {report_file}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
