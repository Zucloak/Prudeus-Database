import os
import json
import re
import shutil
import datetime
import argparse
import sys

ROOT_DIR = "RESTRUCTURED_DB"
LOG_FILE = "standardization_log.txt"

MONTH_MAP = {
    "1": "january", "01": "january", "jan": "january", "january": "january",
    "2": "february", "02": "february", "feb": "february", "february": "february",
    "3": "march", "03": "march", "mar": "march", "march": "march",
    "4": "april", "04": "april", "apr": "april", "april": "april",
    "5": "may", "05": "may", "may": "may",
    "6": "june", "06": "june", "jun": "june", "june": "june",
    "7": "july", "07": "july", "jul": "july", "july": "july",
    "8": "august", "08": "august", "aug": "august", "august": "august",
    "9": "september", "09": "september", "sep": "september", "september": "september", "sept": "september",
    "10": "october", "oct": "october", "october": "october",
    "11": "november", "nov": "november", "november": "november",
    "12": "december", "dec": "december", "december": "december"
}

def log(message):
    print(message)
    with open(LOG_FILE, "a") as f:
        f.write(message + "\n")

def standardize_folders(start_year, end_year, limit=None):
    log(f"Standardizing folders for {start_year}-{end_year} Limit: {limit}...")
    years = sorted([y for y in os.listdir(ROOT_DIR) if y.isdigit() and start_year <= int(y) <= end_year])

    moved_count = 0

    for year in years:
        if limit and moved_count >= limit: break

        year_path = os.path.join(ROOT_DIR, year)
        if not os.path.isdir(year_path):
            continue

        subdirs = sorted([d for d in os.listdir(year_path) if os.path.isdir(os.path.join(year_path, d))])

        for d in subdirs:
            if limit and moved_count >= limit: break

            d_lower = d.lower()
            target_month = MONTH_MAP.get(d_lower)

            if not target_month:
                continue

            if d == target_month:
                continue

            src_path = os.path.join(year_path, d)
            dst_path = os.path.join(year_path, target_month)

            if not os.path.exists(dst_path):
                os.makedirs(dst_path)

            # Move files one by one to respect limit
            files = sorted(os.listdir(src_path))
            for f in files:
                if limit and moved_count >= limit: break

                src_file = os.path.join(src_path, f)
                dst_file = os.path.join(dst_path, f)

                if os.path.exists(dst_file):
                    pass

                shutil.move(src_file, dst_file)
                moved_count += 1

            # If src_path is empty, remove it
            if not os.listdir(src_path):
                os.rmdir(src_path)

    log(f"Moved {moved_count} files/folders.")

def clean_title(title):
    if not title:
        return None

    # Uppercase
    title = title.upper()

    # Cut off at "DECISION" or "D E C I S I O N"
    if "DECISION" in title:
        title = title.split("DECISION")[0]
    if "D E C I S I O N" in title:
        title = title.split("D E C I S I O N")[0]

    # Standardize "VS."
    title = re.sub(r'\s+V\.\s+', ' vs. ', title)
    title = re.sub(r'\s+VS\.\s+', ' vs. ', title)
    title = re.sub(r'\s+VS\s+', ' vs. ', title)
    title = re.sub(r'\s+VERSUS\s+', ' vs. ', title)

    # Remove Roles
    role_pattern = r'[\s,]*\b(PETITIONER|RESPONDENT|PLAINTIFF|DEFENDANT|APPELLEE|APPELLANT|ACCUSED)(-[A-Z]+)?(S)?\b[\s,]*'
    title = re.sub(role_pattern, ' ', title)

    # Clean up multiple spaces and punctuation
    title = re.sub(r'\s+', ' ', title).strip()
    title = re.sub(r'\s+\.', '.', title)
    title = re.sub(r',\s*vs\.', ' vs.', title)
    title = re.sub(r'vs\.\s*,', 'vs. ', title)

    # Remove leading/trailing punctuation
    title = title.strip('.,; ')

    return title

def extract_gr_number(content, filename):
    match = re.search(r'G\.R\. No\. ([A-Za-z0-9-]+)', content, re.IGNORECASE)
    if match:
        return match.group(1)

    match = re.search(r'(\d+)', filename)
    if match:
        return match.group(1)

    return None

def process_files(start_year, end_year, specific_month=None, limit=None):
    log(f"Processing files for {start_year}-{end_year} " + (f"(Month: {specific_month})" if specific_month else "") + f" Limit: {limit}...")
    years = sorted([y for y in os.listdir(ROOT_DIR) if y.isdigit() and start_year <= int(y) <= end_year])

    modified_count = 0

    for year in years:
        if limit and modified_count >= limit:
            break

        year_path = os.path.join(ROOT_DIR, year)
        if not os.path.isdir(year_path): continue

        months_to_process = os.listdir(year_path)
        if specific_month:
             target = MONTH_MAP.get(specific_month.lower()) or specific_month
             if target in months_to_process:
                 months_to_process = [target]
             else:
                 continue

        months_to_process.sort()

        for month in months_to_process:
            if limit and modified_count >= limit:
                break

            month_path = os.path.join(year_path, month)
            if not os.path.isdir(month_path):
                continue

            files = sorted([f for f in os.listdir(month_path) if f.endswith(".json")])
            for filename in files:
                if limit and modified_count >= limit:
                    break

                filepath = os.path.join(month_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception as e:
                    log(f"Error reading {filepath}: {e}")
                    continue

                original_json_str = json.dumps(data, sort_keys=True)

                # Standardize Metadata
                if data.get('year') != int(year):
                    data['year'] = int(year)

                if data.get('month') != month:
                    data['month'] = month

                # Content
                content = data.get('formatted_case_content') or data.get('content') or ""
                if 'formatted_case_content' not in data:
                    data['formatted_case_content'] = content

                if 'content' in data:
                    del data['content']

                # GR Number
                gr = data.get('gr_number')
                if not gr or 'gr_' in str(gr).lower() or '_' in str(gr):
                    new_gr = extract_gr_number(content, filename)
                    if new_gr:
                        data['gr_number'] = new_gr

                # Case Number
                if not data.get('case_number'):
                    if data.get('gr_number'):
                         data['case_number'] = f"G.R. No. {data['gr_number']}"

                # Title Extraction
                title = data.get('title')
                if not title or len(title) > 300 or title.lower() == "untitled":
                    lines = content.split('\n')
                    best_title = None
                    for i, line in enumerate(lines[:50]):
                        line_lower = line.lower()
                        if " vs. " in line_lower or " vs " in line_lower or " versus " in line_lower:
                            if " vs. " in line_lower:
                                best_title = line.strip()
                                break
                            clean_line = line.strip().lower()
                            if clean_line in ["vs.", "vs", "versus", "v."]:
                                prev_line = lines[i-1].strip() if i > 0 else ""
                                next_line = lines[i+1].strip() if i < len(lines)-1 else ""
                                best_title = f"{prev_line} vs. {next_line}"
                                break

                    if best_title:
                        title = best_title
                        data['title'] = title

                # Clean Title
                if data.get('title'):
                    new_title = clean_title(data['title'])
                    if new_title and new_title != data['title']:
                        data['title'] = new_title

                keys_to_ensure = ["year", "month", "case_number", "gr_number", "decision_date", "title", "division", "formatted_case_content"]
                for k in keys_to_ensure:
                    if k not in data:
                        data[k] = None

                new_json_str = json.dumps(data, sort_keys=True)

                if original_json_str != new_json_str:
                    try:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        modified_count += 1
                    except Exception as e:
                         log(f"Error writing {filepath}: {e}")

    log(f"Modified {modified_count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--action", type=str, required=True, choices=["folders", "files"])
    parser.add_argument("--month", type=str, required=False)
    parser.add_argument("--limit", type=int, required=False)
    args = parser.parse_args()

    if args.action == "folders":
        standardize_folders(args.start, args.end, args.limit)
    elif args.action == "files":
        process_files(args.start, args.end, args.month, args.limit)
