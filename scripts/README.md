# Scripts Directory

This directory contains scripts for managing large-scale file operations in the Prudeus Database repository.

## Background

**Problem:** When processing large numbers of files (40k+), git operations can fail with SIGPIPE errors or "exit code null" due to pipe buffer overflow when attempting to commit all changes in a single operation.

**Solution:** Batch commit infrastructure that splits file operations into manageable chunks.

**Reference:** Job ID 56105745944, Commit 345be85e7675ce5fe25b3aef5fe0c74bae445096

## Scripts

### 1. batch-commit.sh

Safe git operations for large file changes. Prevents git operation failures by splitting commits into batches.

**Usage:**
```bash
# Basic usage with defaults
BRANCH=main ./scripts/batch-commit.sh

# Custom batch size
BRANCH=main BATCH_SIZE=1000 ./scripts/batch-commit.sh

# Custom commit message
BRANCH=main COMMIT_MSG="Update metadata" ./scripts/batch-commit.sh

# All options
BRANCH=main BATCH_SIZE=500 COMMIT_MSG="Process files" ./scripts/batch-commit.sh
```

**Environment Variables:**
- `BRANCH` - Target branch name (default: main)
- `BATCH_SIZE` - Number of files per commit batch (default: 500)
- `COMMIT_MSG` - Commit message prefix (default: "Batch commit")

**Features:**
- Automatically detects modified files
- Splits into configurable batch sizes
- Creates separate commit for each batch
- Single push at the end
- Prevents git pipe overflow
- Colorized output with progress tracking

**How it works:**
1. Fetches and checks out target branch
2. Collects all modified files using `git status -s -uall`
3. Splits file list into batches using `split` command
4. For each batch:
   - Stage files with `git add`
   - Commit with descriptive message
5. Push all commits at once

### 2. extract_and_remove_html_metadata.py

Extracts HTML `<meta>` tags to sidecar JSON files and removes them from HTML files.

**Usage:**
```bash
# Process all HTML files in a directory
python3 scripts/extract_and_remove_html_metadata.py /path/to/html/files

# Dry run to preview changes
python3 scripts/extract_and_remove_html_metadata.py --dry-run /path/to/html/files

# Process only current directory (non-recursive)
python3 scripts/extract_and_remove_html_metadata.py --no-recursive /path/to/html/files

# Verbose logging
python3 scripts/extract_and_remove_html_metadata.py --verbose /path/to/html/files
```

**Features:**
- Extracts all `<meta>` tags from HTML files
- Saves metadata to sidecar JSON files (*.html.meta.json)
- Supports various meta tag formats:
  - `<meta name="..." content="...">`
  - `<meta property="..." content="...">` (Open Graph)
  - `<meta http-equiv="..." content="...">`
- Only rewrites files when content actually changes
- Preserves metadata for future reference
- Comprehensive error handling and logging
- Dry-run mode for safety

**Output Format:**

For `example.html`, creates `example.html.meta.json`:
```json
{
  "extraction_date": "2025-11-22T05:00:00Z",
  "meta_tags": [
    {
      "name": "description",
      "content": "Case description"
    },
    {
      "property": "og:title",
      "content": "Page Title"
    }
  ]
}
```

## Workflows

### GitHub Actions Integration

Two workflow files are provided:

#### 1. `.github/workflows/process-html-metadata.yml`
Standard GitHub Actions workflow for manual metadata processing.

**Trigger:** Manual via workflow_dispatch

**Inputs:**
- `directory` - Directory to process (default: RESTRUCTURED_DB)
- `batch_size` - Files per batch (default: 500)
- `dry_run` - Preview mode (default: false)

#### 2. `dynamic/copilot-swe-agent/copilot`
Specialized workflow for GitHub Copilot SWE agents.

**Features:**
- Designed for automated agent tasks
- Uses batch commit infrastructure by default
- Prevents git operation failures
- Suitable for large-scale operations

## Best Practices

### When to Use Batch Commits

Use batch commits when:
- Processing more than 100 files
- Files are large (>1MB each)
- Running in CI/CD environments
- Risk of git pipe buffer overflow

### Recommended Batch Sizes

| File Count | Recommended Batch Size |
|------------|------------------------|
| 100-1,000  | 100-200               |
| 1,000-10,000 | 200-500             |
| 10,000-50,000 | 500-1,000           |
| 50,000+    | 1,000+                |

### Safety Measures

1. **Always dry-run first:**
   ```bash
   python3 scripts/extract_and_remove_html_metadata.py --dry-run /path
   ```

2. **Test on small subset:**
   ```bash
   # Test with one directory first
   python3 scripts/extract_and_remove_html_metadata.py --no-recursive test_dir/
   ```

3. **Use version control:**
   - Always work on a feature branch
   - Review changes before merging
   - Keep main branch protected

4. **Monitor git operations:**
   - Check logs for errors
   - Verify all batches committed
   - Confirm push succeeded

## Troubleshooting

### Common Issues

**Issue:** "No modified files to commit"
- **Cause:** No files were actually changed
- **Solution:** This is normal if files didn't need modification

**Issue:** Git push fails with authentication error
- **Cause:** Missing or invalid credentials
- **Solution:** Ensure `persist-credentials: true` in workflow checkout

**Issue:** Script exits with "argument list too long"
- **Cause:** Too many files in a single batch
- **Solution:** Reduce `BATCH_SIZE` environment variable

**Issue:** Python script fails to import modules
- **Cause:** Python version or missing dependencies
- **Solution:** Use Python 3.7+ (no external dependencies required)

## Testing

### Test Batch Commit Script

```bash
# Create test files
mkdir -p /tmp/test_batch
cd /tmp/test_batch
git init
git config user.name "Test"
git config user.email "test@test.com"

# Create many files
for i in {1..1500}; do
  echo "Test file $i" > "file_$i.txt"
done

# Test batch commit
BRANCH=main BATCH_SIZE=500 /path/to/batch-commit.sh
```

### Test Metadata Extraction

```bash
# Create test HTML file
mkdir -p /tmp/test_html
cat > /tmp/test_html/test.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <meta name="description" content="Test page">
  <meta property="og:title" content="Test Title">
  <title>Test</title>
</head>
<body>Content</body>
</html>
EOF

# Run extraction (dry-run)
python3 scripts/extract_and_remove_html_metadata.py --dry-run /tmp/test_html

# Run extraction (actual)
python3 scripts/extract_and_remove_html_metadata.py /tmp/test_html

# Verify sidecar file created
cat /tmp/test_html/test.html.meta.json
```

## Performance

### Batch Commit Performance

- **500 files/batch:** ~30-60 seconds per batch
- **1000 files/batch:** ~60-120 seconds per batch
- **Network dependent:** Push time varies with connection speed

### Metadata Extraction Performance

- **Processing speed:** ~100-500 files/second (depends on file size)
- **Memory usage:** ~50-100MB for Python process
- **Disk I/O:** Main bottleneck for large files

## Future Enhancements

Potential improvements:
- [ ] Parallel processing for metadata extraction
- [ ] Progress bars for long-running operations
- [ ] Database storage option for metadata
- [ ] Rollback capability for batch commits
- [ ] Automatic batch size optimization
- [ ] Integration with CI/CD status checks

## Support

For issues or questions:
1. Check this README for troubleshooting
2. Review workflow logs in GitHub Actions
3. Examine script output for error messages
4. Open an issue in the repository

## License

These scripts are part of the Prudeus Database project and follow the same license terms.

---

**Last Updated:** 2025-11-22  
**Reference:** Job 56105745944, Commit 345be85e7675ce5fe25b3aef5fe0c74bae445096
