#!/usr/bin/env python3
"""
Extract and Remove HTML Metadata Script

Purpose: Safely extract HTML <meta> tags to sidecar JSON files and remove them
         from HTML files, only rewriting files when content actually changes.

Usage:
    python3 scripts/extract_and_remove_html_metadata.py <directory>
    python3 scripts/extract_and_remove_html_metadata.py --dry-run <directory>

Arguments:
    directory    - Directory containing HTML files to process
    --dry-run    - Preview changes without modifying files

Features:
    - Extracts all <meta> tags to sidecar JSON files (*.html.meta.json)
    - Removes <meta> tags from HTML files
    - Only rewrites files when content actually changes (reduces git churn)
    - Preserves original file modification times when no changes made
    - Handles multiple meta tag formats (name, property, http-equiv)
    - Supports Open Graph (og:) and Twitter Card metadata
    - Robust error handling and logging

Reference: Job 56105745944, Commit 345be85e7675ce5fe25b3aef5fe0c74bae445096
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extracts and manages HTML metadata."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            'files_scanned': 0,
            'files_modified': 0,
            'files_unchanged': 0,
            'metadata_extracted': 0,
            'errors': 0
        }
    
    def extract_meta_tags(self, html_content: str) -> Tuple[Dict[str, any], str]:
        """
        Extract meta tags from HTML content and return metadata dict and cleaned HTML.
        
        Args:
            html_content: HTML content as string
            
        Returns:
            Tuple of (metadata_dict, cleaned_html)
        """
        metadata = {
            'extraction_date': datetime.utcnow().isoformat() + 'Z',
            'meta_tags': []
        }
        
        # Pattern to match meta tags with various formats
        # Matches: <meta name="..." content="...">, <meta property="..." content="...">, etc.
        meta_pattern = re.compile(
            r'<meta\s+([^>]*?)/?>', 
            re.IGNORECASE | re.DOTALL
        )
        
        # Find all meta tags
        meta_matches = meta_pattern.finditer(html_content)
        
        for match in meta_matches:
            meta_attrs = match.group(1)
            meta_dict = self._parse_meta_attributes(meta_attrs)
            if meta_dict:
                metadata['meta_tags'].append(meta_dict)
        
        # Remove meta tags from HTML
        cleaned_html = meta_pattern.sub('', html_content)
        
        # Clean up any double blank lines that might result
        cleaned_html = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_html)
        
        return metadata, cleaned_html
    
    def _parse_meta_attributes(self, attrs_string: str) -> Optional[Dict[str, str]]:
        """
        Parse attributes from a meta tag string.
        
        Args:
            attrs_string: String containing meta tag attributes
            
        Returns:
            Dictionary of attributes or None if parsing fails
        """
        meta_dict = {}
        
        # Pattern to match attribute="value" or attribute='value'
        attr_pattern = re.compile(r'(\w+(?:[-:]\w+)*)\s*=\s*["\']([^"\']*)["\']')
        
        for match in attr_pattern.finditer(attrs_string):
            key = match.group(1).lower()
            value = match.group(2)
            meta_dict[key] = value
        
        return meta_dict if meta_dict else None
    
    def process_html_file(self, html_path: Path) -> bool:
        """
        Process a single HTML file: extract metadata and remove meta tags.
        
        Args:
            html_path: Path to HTML file
            
        Returns:
            True if file was modified, False otherwise
        """
        try:
            self.stats['files_scanned'] += 1
            
            # Read HTML content
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                original_content = f.read()
            
            # Extract metadata and get cleaned HTML
            metadata, cleaned_html = self.extract_meta_tags(original_content)
            
            # Check if there were any meta tags
            if not metadata['meta_tags']:
                logger.debug(f"No meta tags found in: {html_path}")
                self.stats['files_unchanged'] += 1
                return False
            
            # Check if content actually changed
            if original_content == cleaned_html:
                logger.debug(f"Content unchanged after meta removal: {html_path}")
                self.stats['files_unchanged'] += 1
                return False
            
            self.stats['metadata_extracted'] += len(metadata['meta_tags'])
            
            if self.dry_run:
                logger.info(f"[DRY-RUN] Would extract {len(metadata['meta_tags'])} meta tags from: {html_path}")
                self.stats['files_modified'] += 1
                return True
            
            # Write metadata to sidecar JSON file
            meta_json_path = Path(str(html_path) + '.meta.json')
            with open(meta_json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Extracted {len(metadata['meta_tags'])} meta tags to: {meta_json_path}")
            
            # Write cleaned HTML (only if content changed)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_html)
            
            logger.info(f"Removed meta tags from: {html_path}")
            self.stats['files_modified'] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing {html_path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def process_directory(self, directory: Path, recursive: bool = True) -> None:
        """
        Process all HTML files in a directory.
        
        Args:
            directory: Directory path to process
            recursive: Whether to process subdirectories
        """
        if not directory.exists():
            logger.error(f"Directory does not exist: {directory}")
            sys.exit(1)
        
        if not directory.is_dir():
            logger.error(f"Path is not a directory: {directory}")
            sys.exit(1)
        
        logger.info(f"Processing directory: {directory}")
        logger.info(f"Recursive: {recursive}")
        logger.info(f"Dry run: {self.dry_run}")
        
        # Find all HTML files
        pattern = '**/*.html' if recursive else '*.html'
        html_files = list(directory.glob(pattern))
        
        if not html_files:
            logger.warning(f"No HTML files found in: {directory}")
            return
        
        logger.info(f"Found {len(html_files)} HTML files to process")
        
        # Process each file
        for html_file in html_files:
            self.process_html_file(html_file)
        
        # Print summary
        self._print_summary()
    
    def _print_summary(self) -> None:
        """Print processing summary statistics."""
        logger.info("=" * 60)
        logger.info("PROCESSING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Files scanned:        {self.stats['files_scanned']}")
        logger.info(f"Files modified:       {self.stats['files_modified']}")
        logger.info(f"Files unchanged:      {self.stats['files_unchanged']}")
        logger.info(f"Meta tags extracted:  {self.stats['metadata_extracted']}")
        logger.info(f"Errors:               {self.stats['errors']}")
        logger.info("=" * 60)
        
        if self.dry_run:
            logger.info("[DRY-RUN MODE] No files were actually modified")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Extract HTML metadata to sidecar JSON files and remove from HTML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all HTML files in a directory
  python3 scripts/extract_and_remove_html_metadata.py /path/to/html/files
  
  # Dry run to preview changes
  python3 scripts/extract_and_remove_html_metadata.py --dry-run /path/to/html/files
  
  # Process non-recursively
  python3 scripts/extract_and_remove_html_metadata.py --no-recursive /path/to/html/files
        """
    )
    
    parser.add_argument(
        'directory',
        type=str,
        help='Directory containing HTML files to process'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    
    parser.add_argument(
        '--no-recursive',
        action='store_true',
        help='Do not process subdirectories'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Create extractor and process
    extractor = MetadataExtractor(dry_run=args.dry_run)
    directory = Path(args.directory).resolve()
    
    extractor.process_directory(directory, recursive=not args.no_recursive)
    
    # Exit with error code if there were errors
    if extractor.stats['errors'] > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
