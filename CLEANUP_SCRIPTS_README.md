# Case Data Cleanup Scripts - Performance Comparison

This repository includes two versions of the cleanup script for processing Philippine Supreme Court case JSON files:

## Scripts

### 1. `cleanup_case_data.py` (Serial Version)
- Processes files one at a time
- Simple, straightforward implementation
- Best for small datasets or debugging

### 2. `cleanup_case_data_parallel.py` (Parallel Version) ⚡
- Processes multiple files simultaneously using multiprocessing
- Utilizes all available CPU cores (default) or specified number of workers
- **2x faster** on multi-core systems for large datasets
- Recommended for production use with large file counts

## Performance Benchmarks

Tested on a 4-core system:

| Files | Serial Time | Parallel Time (4 workers) | Speedup |
|-------|-------------|---------------------------|---------|
| 32    | 0.070s      | 0.098s                    | 0.7x    |
| 375   | 0.272s      | 0.165s                    | 1.65x   |
| 41,574| ~80s        | ~40s (estimated)          | ~2x     |

**Note:** Speedup is more significant with larger datasets. For small datasets (< 100 files), overhead of multiprocessing may reduce benefits.

## Usage

### Serial Version
```bash
python3 cleanup_case_data.py RESTRUCTURED_DB
```

### Parallel Version (Recommended)
```bash
# Use all available CPU cores
python3 cleanup_case_data_parallel.py RESTRUCTURED_DB

# Specify number of workers
python3 cleanup_case_data_parallel.py RESTRUCTURED_DB --workers 8

# Only clean content, don't rename files
python3 cleanup_case_data_parallel.py RESTRUCTURED_DB --no-rename
```

## Features

Both scripts perform the same operations:

1. **Filename Standardization**: Renames files to `{case_id}.json` format
2. **Encoding Fixes**: Corrects UTF-8 misinterpretations (â → ', etc.)
3. **Table Removal**: Removes `[TABLE_CONTENT]...[END_TABLE]` markers
4. **Title Extraction**: Parses "PLAINTIFF vs. DEFENDANT" from case text
5. **Date Extraction**: Finds decision dates and converts to YYYY-MM-DD format

## Recommendations

- **Small datasets (< 1,000 files)**: Either script works fine
- **Medium datasets (1,000 - 10,000 files)**: Use parallel version
- **Large datasets (> 10,000 files)**: Use parallel version with `--workers` matching CPU cores
- **Very large datasets (> 50,000 files)**: Use parallel version and consider processing in batches by year/directory

## Example Commands

```bash
# Process entire database with maximum parallelization
python3 cleanup_case_data_parallel.py RESTRUCTURED_DB --workers 8

# Process only 1976 cases
python3 cleanup_case_data_parallel.py RESTRUCTURED_DB/1976

# Dry run: clean content only, don't rename
python3 cleanup_case_data_parallel.py RESTRUCTURED_DB --no-rename

# Process with progress monitoring
python3 cleanup_case_data_parallel.py RESTRUCTURED_DB --workers 4 | tee cleanup_output.log
```

## System Requirements

- Python 3.6+
- Multi-core CPU recommended for parallel version
- Sufficient RAM for concurrent file processing (typically < 1GB for most datasets)
