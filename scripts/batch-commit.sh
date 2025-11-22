#!/bin/bash
#
# Batch Commit Script - Safe Git Operations for Large File Changes
#
# Purpose: Prevents git operation failures (SIGPIPE, exit code null) when
#          committing large numbers of modified files by splitting them into
#          manageable batches.
#
# Usage:
#   BRANCH=main BATCH_SIZE=500 COMMIT_MSG="Update files" ./scripts/batch-commit.sh
#
# Environment Variables:
#   BRANCH       - Target branch name (required, default: main)
#   BATCH_SIZE   - Number of files per commit batch (default: 500)
#   COMMIT_MSG   - Commit message prefix (default: "Batch commit")
#
# Reference: Job 56105745944, Commit 345be85e7675ce5fe25b3aef5fe0c74bae445096
#

set -euo pipefail

# Configuration
BRANCH="${BRANCH:-main}"
BATCH_SIZE="${BATCH_SIZE:-500}"
COMMIT_MSG="${COMMIT_MSG:-Batch commit}"
MODIFIED_FILES="/tmp/modified_files.txt"
BATCH_DIR="/tmp/batch_files"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f "${MODIFIED_FILES}"
    rm -rf "${BATCH_DIR}"
}

trap cleanup EXIT

# Disable git pagers to avoid interactive prompts
export GIT_PAGER=cat
git config --local core.pager cat

log_info "Starting batch commit process..."
log_info "Branch: ${BRANCH}"
log_info "Batch size: ${BATCH_SIZE}"
log_info "Commit message: ${COMMIT_MSG}"

# Step 1: Fetch and checkout target branch
log_info "Fetching origin and checking out branch: ${BRANCH}"
git fetch --no-tags --prune origin "+refs/heads/${BRANCH}:refs/remotes/origin/${BRANCH}" || {
    log_warn "Branch ${BRANCH} does not exist on remote, will be created"
}

# Check if local branch exists
if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
    log_info "Checking out existing local branch: ${BRANCH}"
    git checkout "${BRANCH}"
else
    # Check if remote branch exists
    if git show-ref --verify --quiet "refs/remotes/origin/${BRANCH}"; then
        log_info "Creating local branch from remote: ${BRANCH}"
        git checkout -B "${BRANCH}" "origin/${BRANCH}"
    else
        log_info "Creating new branch: ${BRANCH}"
        git checkout -b "${BRANCH}"
    fi
fi

# Step 2: Collect modified files
log_info "Collecting modified files..."
git status -s -uall | awk '{print $2}' > "${MODIFIED_FILES}" || true

# Count total files
TOTAL_FILES=$(wc -l < "${MODIFIED_FILES}" | tr -d ' ')
log_info "Found ${TOTAL_FILES} modified files"

if [ "${TOTAL_FILES}" -eq 0 ]; then
    log_info "No modified files to commit. Exiting."
    exit 0
fi

# Step 3: Split into batches
log_info "Splitting files into batches of ${BATCH_SIZE}..."
mkdir -p "${BATCH_DIR}"
cd "${BATCH_DIR}"
split -l "${BATCH_SIZE}" -d "${MODIFIED_FILES}" batch_

# Count batches
BATCH_COUNT=$(ls -1 batch_* 2>/dev/null | wc -l | tr -d ' ')
log_info "Created ${BATCH_COUNT} batches"

# Step 4: Process each batch
cd - > /dev/null
BATCH_NUM=0
COMMITTED_BATCHES=0

for batch_file in "${BATCH_DIR}"/batch_*; do
    BATCH_NUM=$((BATCH_NUM + 1))
    BATCH_SIZE_ACTUAL=$(wc -l < "${batch_file}" | tr -d ' ')
    
    log_info "Processing batch ${BATCH_NUM}/${BATCH_COUNT} (${BATCH_SIZE_ACTUAL} files)..."
    
    # Stage files from this batch using xargs with null delimiter handling
    # Use -r to handle empty input, -d '\n' for newline delimiter
    if [ -s "${batch_file}" ]; then
        # Add files one at a time to avoid argument list too long
        while IFS= read -r file; do
            if [ -n "${file}" ] && [ -e "${file}" ]; then
                git add -- "${file}" 2>/dev/null || log_warn "Could not add file: ${file}"
            fi
        done < "${batch_file}"
        
        # Check if there are staged changes
        if git diff --cached --quiet; then
            log_warn "Batch ${BATCH_NUM}: No changes to commit (files may have been deleted or unchanged)"
            continue
        fi
        
        # Commit the batch
        BATCH_COMMIT_MSG="${COMMIT_MSG} - Batch ${BATCH_NUM}/${BATCH_COUNT}"
        git commit -m "${BATCH_COMMIT_MSG}" --quiet
        COMMITTED_BATCHES=$((COMMITTED_BATCHES + 1))
        log_info "Batch ${BATCH_NUM}: Committed successfully"
    else
        log_warn "Batch ${BATCH_NUM}: Empty batch file, skipping"
    fi
done

# Step 5: Push all commits
if [ "${COMMITTED_BATCHES}" -gt 0 ]; then
    log_info "Pushing ${COMMITTED_BATCHES} batch commits to origin/${BRANCH}..."
    git push origin "${BRANCH}"
    log_info "Push completed successfully"
else
    log_warn "No batches were committed, nothing to push"
fi

# Summary
log_info "======================================"
log_info "Batch commit completed successfully!"
log_info "Total files processed: ${TOTAL_FILES}"
log_info "Total batches: ${BATCH_COUNT}"
log_info "Batches committed: ${COMMITTED_BATCHES}"
log_info "======================================"

exit 0
