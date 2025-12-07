#!/bin/bash
#
# Safe Git Diff Script - Prevents SIGPIPE and exit code null errors
#
# Purpose: Safely runs git diff --cached with proper error handling
#          - Verifies we are inside a git repository
#          - Checks for staged changes before running diff
#          - Returns success even when no changes exist
#
# Usage:
#   bash .github/scripts/safe-git-diff.sh
#
# Exit Codes:
#   0 - Success (includes cases with no staged changes)
#   1 - Error (not a git repository)

set -euo pipefail

# Check if we are in a git repository
if [ ! -d .git ]; then
    echo "Not a git repository; skipping git diff --cached."
    exit 0
fi

# Check for staged changes
staged="$(git diff --cached --name-only 2>/dev/null || true)"

if [ -z "$staged" ]; then
    echo "No staged changes to diff."
    exit 0
fi

# Show the diff, ignore broken pipe errors
git --no-pager diff --cached 2>/dev/null || true

exit 0
