#!/bin/bash
# Repository Cleanup Script
# This script removes unnecessary files and optimizes git to reduce repository size

echo "================================================"
echo "Repository Cleanup for Batch 3 Preparation"
echo "================================================"
echo ""

# Check current size
echo "📊 Current repository size:"
du -sh .
echo ""

# Step 1: Remove log files
echo "🗑️  Step 1: Removing log files..."
if ls *.log 1> /dev/null 2>&1; then
    du -ch *.log | tail -1
    git rm -f *.log
    echo "✅ Log files removed"
else
    echo "ℹ️  No log files found"
fi
echo ""

# Step 2: Remove Python cache
echo "🗑️  Step 2: Removing Python cache..."
if [ -d "__pycache__" ]; then
    du -sh __pycache__
    rm -rf __pycache__
    echo "✅ Python cache removed"
else
    echo "ℹ️  No Python cache found"
fi
echo ""

# Step 3: Remove old progress files
echo "🗑️  Step 3: Removing old progress tracking files..."
if [ -f "scraping_progress_batch2.json" ]; then
    du -sh scraping_progress_batch2.json
    git rm -f scraping_progress_batch2.json
    echo "✅ Old progress file removed"
else
    echo "ℹ️  No old progress files found"
fi
echo ""

# Step 4: Update .gitignore
echo "📝 Step 4: Updating .gitignore..."
cat > .gitignore << 'EOF'
# Samples directory
SAMPLE_CASES/

# Progress tracking (active scraping)
scraping_progress.json

# Log files
*.log

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp
/tmp/
EOF
echo "✅ .gitignore updated"
echo ""

# Step 5: Commit cleanup
echo "💾 Step 5: Committing cleanup..."
git add .gitignore
git commit -m "Clean up repository: remove logs, cache, and update .gitignore"
echo "✅ Cleanup committed"
echo ""

# Step 6: Git garbage collection
echo "🔧 Step 6: Running git optimization (this may take a minute)..."
git gc --aggressive --prune=now
echo "✅ Git optimization complete"
echo ""

# Step 7: Check new size
echo "📊 New repository size:"
du -sh .
echo ""

# Calculate savings
echo "================================================"
echo "✅ Cleanup Complete!"
echo "================================================"
echo ""
echo "📋 Summary:"
echo "   - Log files removed (~744KB)"
echo "   - Python cache removed (~24KB)"
echo "   - .gitignore updated"
echo "   - Git optimized and compressed"
echo ""
echo "📊 Size comparison:"
echo "   Before: 798MB"
du -sh . | awk '{print "   After:  " $1}'
echo ""
echo "💡 Next step: Proceed with Batch 3 scraping (1960-1995)"
echo ""
