import os
import json
import re
import shutil
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

DB_DIR = "RESTRUCTURED_DB"
LIMIT = 50  # Safe limit per run

def clean_gr_number_for_filename(gr_number):
    # Try to extract number from patterns like gr_l-1441_1903 or L-1441

    # Pattern 1: gr_l-1441_1903 -> 1441
    match = re.search(r'gr_l-(\d+)_', gr_number, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 2: L-1441 -> 1441
    match = re.search(r'\bL-(\d+)\b', gr_number, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 3: Just remove G.R. No. and cleanup
    gr_number = re.sub(r'G\.?R\.? ?No\.? ?', '', gr_number, flags=re.IGNORECASE)
    gr_number = gr_number.replace('/', '_')
    gr_number = re.sub(r'[<>:"\\|?*]', '', gr_number)
    gr_number = gr_number.strip()

    # If it ends up as just digits, great. If it has suffix, keep it.
    return gr_number

def standardize_title(title):
    if not title:
        return ""
    title = title.strip()
    # Remove prefix like G.R. No. ...
    match = re.match(r'^G\.?R\.? ?No\.? ?[\w\d\-\/_\.]+[ ,]+(.*)', title, re.IGNORECASE)
    if match:
        title = match.group(1).strip()

    # Clean whitespace
    title = re.sub(r'\s+', ' ', title)

    # Standardize vs.
    title = re.sub(r'\s+vs\.?\s+', ' vs. ', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+v\.?\s+', ' vs. ', title, flags=re.IGNORECASE)
    title = re.sub(r'\s+versus\s+', ' vs. ', title, flags=re.IGNORECASE)

    # Uppercase parties
    parts = title.split(" vs. ")
    parts = [p.upper() for p in parts]
    title = " vs. ".join(parts)
    return title

def process_file(filepath, year, month):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        original_data = json.dumps(data, sort_keys=True)
        modified = False
        renamed = False

        # 1. Ensure required fields
        if "year" not in data or not data["year"]:
            data["year"] = int(year)
            modified = True
        if "month" not in data or not data["month"]:
            data["month"] = month
            modified = True

        # 2. Fix GR Number and Filename
        gr_number = data.get("gr_number", "")

        # Infer GR number if missing or looks like a raw filename
        if not gr_number or "gr_l-" in gr_number.lower():
            if data.get("case_number") and "gr_l-" not in data["case_number"].lower():
                gr_number = clean_gr_number_for_filename(data["case_number"])
            else:
                # Try from filename
                base_name = os.path.splitext(os.path.basename(filepath))[0]
                gr_number = clean_gr_number_for_filename(base_name)

            # If still bad, try extraction from content
            if not gr_number or "gr_l-" in gr_number.lower():
                content = data.get("formatted_case_content", "")
                match = re.search(r'G\.?R\.? ?No\.? ?(L-)?(\d+)', content, re.IGNORECASE)
                if match:
                    gr_number = match.group(2)

            if gr_number:
                data["gr_number"] = gr_number
                modified = True
        else:
            # Even if it exists, maybe clean it?
            clean = clean_gr_number_for_filename(gr_number)
            if clean != gr_number:
                data["gr_number"] = clean
                modified = True

        # Ensure case_number
        if not data.get("case_number") or data["case_number"] == data.get("gr_number"):
             # If case_number is just the number, maybe add prefix?
             # User example had "G.R. No. 1114".
             if data["gr_number"] and str(data["gr_number"]).isdigit():
                 data["case_number"] = f"G.R. No. {data['gr_number']}"
                 modified = True

        # 3. Standardize Title
        title = data.get("title", "")
        if not title or title == "Title not found":
            if not title:
                title = "UNKNOWN TITLE"
            modified = True

        new_title = standardize_title(title)
        if new_title != title:
            data["title"] = new_title
            modified = True

        # 4. Other fields
        if "division" not in data:
            data["division"] = "En Banc"
            modified = True
        if "categories" not in data:
            data["categories"] = []
            modified = True
        if "keywords" not in data:
            data["keywords"] = []
            modified = True
        if "formatted_case_content" not in data:
            data["formatted_case_content"] = ""
            modified = True
        if "decision_date" not in data:
            data["decision_date"] = f"{year}-01-01"
            modified = True

        # 5. Filename check
        # Use the (potentially updated) gr_number for filename
        clean_gr = clean_gr_number_for_filename(data.get("gr_number", ""))

        # Make sure we have a valid filename
        if not clean_gr:
             clean_gr = f"unknown_{os.path.basename(filepath)}"

        expected_filename = f"{clean_gr}.json"

        content_changed = json.dumps(data, sort_keys=True) != original_data

        if content_changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            modified = True

        current_filename = os.path.basename(filepath)
        if current_filename != expected_filename:
            new_filepath = os.path.join(os.path.dirname(filepath), expected_filename)
            if not os.path.exists(new_filepath):
                os.rename(filepath, new_filepath)
                renamed = True
            else:
                # collision, don't overwrite if it's a different file
                if new_filepath != filepath:
                    pass

        return modified or renamed
    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")
        return False

def main():
    count = 0
    # No state file, just scan

    logger.info("Scanning for files to standardize...")

    years = sorted([y for y in os.listdir(DB_DIR) if y.isdigit()])

    for year in years:
        year_path = os.path.join(DB_DIR, year)
        months = sorted(os.listdir(year_path))

        for month in months:
            month_path = os.path.join(year_path, month)
            if not os.path.isdir(month_path): continue

            # Handle directory rename (uppercase to lowercase)
            if month != month.lower():
                new_month_path = os.path.join(year_path, month.lower())
                if os.path.exists(new_month_path) and new_month_path != month_path:
                    # Move files
                    for f in os.listdir(month_path):
                        shutil.move(os.path.join(month_path, f), os.path.join(new_month_path, f))
                    os.rmdir(month_path)
                    month_path = new_month_path
                    count += 1
                else:
                    os.rename(month_path, new_month_path)
                    month_path = new_month_path
                    count += 1

                if count >= LIMIT:
                    print(f"PAUSED: Renamed folder {month} -> {month.lower()}")
                    return

            files = sorted([f for f in os.listdir(month_path) if f.endswith(".json")])

            for filename in files:
                filepath = os.path.join(month_path, filename)

                if process_file(filepath, int(year), month.lower()):
                    count += 1

                if count >= LIMIT:
                    print(f"PAUSED: Modified {count} files. Last: {year}/{month}/{filename}")
                    return

    if count == 0:
        print("COMPLETED")
    else:
        print(f"Finished scan with {count} modifications (below limit)")

if __name__ == "__main__":
    main()
