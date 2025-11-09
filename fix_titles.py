import os
import json
import re
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_title(content):
    # More robust regex to handle variations in formatting
    match = re.search(r'.*\[\s*G\.R\. Nos?\.?\s*.*?\]\s*(.*?)\s*D E C I S I O N', content, re.DOTALL)
    if match:
        title = match.group(1).strip()
        # Remove the redundant title if it's repeated before the decision
        decision_parts = title.split('D E C I S I O N')
        if len(decision_parts) > 1:
            title = decision_parts[0].strip()

        # Remove extra newlines and create a clean, single-line title
        title = ' '.join(title.split())

        # Additional check to remove repeated titles
        half_len = len(title) // 2
        if len(title) > 20 and title[:half_len].strip() == title[half_len:].strip():
            title = title[:half_len].strip()

        summary = title
        if len(summary) > 100:
            summary = summary[:100] + "..."
        return title, summary
    return "", ""

def process_file(filepath):
    try:
        with open(filepath, 'r+') as f:
            # handle empty files
            content = f.read()
            if not content or content == '{}':
                logging.info(f"Skipping empty or basic JSON file: {filepath}")
                return

            f.seek(0)
            data = json.loads(content)

            if not data.get('title'):
                logging.info(f"Found file with missing title: {filepath}")
                formatted_case_content = data.get('formatted_case_content', '')
                if formatted_case_content:
                    title, summary = extract_title(formatted_case_content)
                    if title:
                        logging.info(f"Extracted title: '{title}' from {filepath}")
                        data['title'] = title
                        data['title_summary'] = summary
                        f.seek(0)
                        json.dump(data, f, indent=2)
                        f.truncate()
                    else:
                        logging.warning(f"Could not extract title from {filepath}")
                else:
                    logging.warning(f"No 'formatted_case_content' in {filepath}")
            else:
                logging.info(f"File already has a title: {filepath}")

    except json.JSONDecodeError:
        logging.error(f"Skipping invalid JSON file: {filepath}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 fix_titles.py <year>")
        return

    year = sys.argv[1]
    year_dir = os.path.join('RESTRUCTURED_DB', year)
    if os.path.isdir(year_dir):
        for month in os.listdir(year_dir):
            month_dir = os.path.join(year_dir, month)
            if os.path.isdir(month_dir):
                for filename in os.listdir(month_dir):
                    if filename.endswith('.json'):
                        process_file(os.path.join(month_dir, filename))

if __name__ == '__main__':
    main()
