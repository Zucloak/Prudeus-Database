# Batch 3 Preparation Guide

## 🎯 Current Status

✅ **Batch 2 Complete!** (1930-1959, 6,700 cases)  
📊 **Repository Size**: 798MB  
⏳ **Next**: Batch 3 (1960-1995, ~8,280 cases)

---

## 📋 Decision Required

You need to choose one of the following options to proceed with Batch 3:

### Option 1: Clean Up + Proceed (Recommended) 🛠️

**What it does:**
- Removes unnecessary files (logs, cache) - saves ~1MB
- Optimizes git repository - saves ~50-100MB
- Reduces size to approximately 700-750MB
- Then proceed with Batch 3 scraping

**Final projected size:** ~1.0-1.05GB (right at limit)

**How to do it:**
```bash
# Run the cleanup script
./cleanup_repo.sh

# Then start Batch 3
python batch_scraper.py --start-year 1960 --end-year 1995 --output-dir RESTRUCTURED_DB
```

**Pros:**
- ✅ Keeps everything in one repository
- ✅ Reduces current bloat
- ✅ Likely stays under/at 1GB
- ✅ Can monitor during scraping

**Cons:**
- ⚠️ Might still exceed 1GB slightly
- ⚠️ Need to monitor closely during scraping

---

### Option 2: Create New Repository (Safest) 🆕

**What it does:**
- Keeps current repo at 798MB (1901-1959 complete)
- Creates new repo: `Prudeus-Database-Historical-1960-1995`
- Scrapes Batch 3 in the new repo

**Final size:**
- Current repo: 798MB ✅
- New repo: ~300-400MB ✅

**How to do it:**
```bash
# On GitHub: Create new repository "Prudeus-Database-Historical-1960-1995"

# Clone and set up
cd ..
git clone https://github.com/Zucloak/Prudeus-Database-Historical-1960-1995.git
cd Prudeus-Database-Historical-1960-1995

# Copy scraper files (not data)
cp ../Prudeus-Database/batch_scraper.py .
cp ../Prudeus-Database/scraper.py .
cp ../Prudeus-Database/requirements.txt .
cp ../Prudeus-Database/validate_cases.py .

# Start scraping
python batch_scraper.py --start-year 1960 --end-year 1995 --output-dir RESTRUCTURED_DB
```

**Pros:**
- ✅ Both repos stay well under 1GB
- ✅ No size concerns
- ✅ Better git performance
- ✅ Future-proof

**Cons:**
- ⚠️ Split database across repos
- ⚠️ Need to manage two repositories
- ⚠️ Cross-referencing more complex

---

### Option 3: Proceed As-Is (Risky) ⚠️

**What it does:**
- Start Batch 3 scraping immediately
- No cleanup, no new repo

**Final projected size:** ~1.09GB (exceeds 1GB by 90MB)

**How to do it:**
```bash
# Just start scraping
python batch_scraper.py --start-year 1960 --end-year 1995 --output-dir RESTRUCTURED_DB
```

**Pros:**
- ✅ Fastest to start
- ✅ No additional setup

**Cons:**
- ⚠️ Will exceed 1GB limit
- ⚠️ GitHub warnings
- ⚠️ Slower git operations
- ⚠️ Risk of hitting hard limits later

---

## 💡 My Recommendation

### 🎯 Go with **Option 1: Clean Up + Proceed**

**Reasoning:**
1. Your expectation was ~700MB (currently 798MB)
2. Cleanup can get you close to that expectation
3. Proceeding after cleanup should keep you at ~1.0-1.05GB
4. GitHub tolerates slightly over 1GB (hard limit is 5GB)
5. Can still create new repo if needed partway through

**Timeline:**
```
1. Run cleanup script: 2-3 minutes
2. Verify new size: ~700-750MB
3. Start Batch 3 scraping: 6-8 hours
4. Monitor at checkpoints:
   - 1965 (5 years in)
   - 1975 (15 years in)
   - 1985 (25 years in)
5. If exceeding 1.1GB at any checkpoint: pause and create new repo
```

---

## 📊 Size Breakdown

### Current Repository (798MB)
```
Historical Cases (1901-1959): 11,287 cases
├─ Batch 1 (1901-1929): 4,587 cases (~138MB)
└─ Batch 2 (1930-1959): 6,700 cases (~202MB)

Modern Cases (1996-2025): 9,278 cases (~280MB)

Git history: 162MB
Other files: ~16MB
```

### After Batch 3 (Projected)
```
Historical Cases (1901-1995): ~19,567 cases
├─ Batch 1 (1901-1929): 4,587 cases (~138MB)
├─ Batch 2 (1930-1959): 6,700 cases (~202MB)
└─ Batch 3 (1960-1995): 8,280 cases (~236MB)

Modern Cases (1996-2025): 9,278 cases (~280MB)

Git history: ~221MB
Other files: ~16MB

TOTAL: ~1,093MB (~1.07GB)
```

---

## 🚀 Quick Start Commands

### If you choose Option 1 (Clean Up + Proceed):
```bash
cd /home/runner/work/Prudeus-Database/Prudeus-Database

# Step 1: Clean up
./cleanup_repo.sh

# Step 2: Verify size
du -sh .

# Step 3: Start Batch 3 (if size is good)
nohup python batch_scraper.py \
  --start-year 1960 \
  --end-year 1995 \
  --output-dir RESTRUCTURED_DB \
  > batch3_scraper.log 2>&1 &

# Step 4: Monitor
tail -f batch3_scraper.log

# Step 5: Check size periodically
watch -n 3600 'du -sh .'  # Every hour
```

### If you choose Option 2 (New Repository):
```bash
# Create repo on GitHub first, then:
cd ..
git clone https://github.com/Zucloak/Prudeus-Database-Historical-1960-1995.git
cd Prudeus-Database-Historical-1960-1995

# Copy necessary files
cp ../Prudeus-Database/*.py .
cp ../Prudeus-Database/requirements.txt .

# Install dependencies
pip install -r requirements.txt

# Start scraping
nohup python batch_scraper.py \
  --start-year 1960 \
  --end-year 1995 \
  --output-dir RESTRUCTURED_DB \
  > batch3_scraper.log 2>&1 &
```

---

## 📈 Monitoring During Batch 3

### Size Checkpoints
```bash
# At 1965 (5 years in, ~1/7 complete)
# Expected: ~795-845MB
du -sh .

# At 1975 (15 years in, ~3/7 complete)
# Expected: ~845-920MB
du -sh .

# At 1985 (25 years in, ~5/7 complete)
# Expected: ~920-1000MB
du -sh .
```

### Decision Points
- **If < 900MB at 1975**: ✅ On track, continue
- **If 900-950MB at 1975**: ⚠️ Close, monitor closely
- **If > 950MB at 1975**: 🛑 Consider stopping and creating new repo

---

## 📞 What to Do Next

### Tell me your choice:

1. **"Clean up and proceed"** - I'll run the cleanup script and start Batch 3
2. **"Create new repository"** - I'll guide you through setting up the new repo
3. **"Proceed as-is"** - I'll start Batch 3 immediately (not recommended)
4. **"I need more information"** - I'll provide additional analysis

---

## 📄 Reference Documents

- `BATCH_3_SIZE_ANALYSIS.md` - Detailed technical analysis
- `SIZE_STATUS_QUICK_ANSWER.md` - Quick TL;DR summary
- `cleanup_repo.sh` - Automated cleanup script
- `SCRAPING_PROGRESS_REPORT.md` - Previous batch history
- `REPOSITORY_SIZE_ANALYSIS.md` - Earlier size analysis

---

## ❓ FAQ

**Q: What happens if we exceed 1GB?**  
A: GitHub shows warnings but allows it. Hard limit is 5GB. Operations may be slower.

**Q: Can we split later if needed?**  
A: Yes! We can stop scraping partway through and create a new repo for remaining years.

**Q: How accurate are the projections?**  
A: Based on actual data from Batch 2. Should be accurate ±10%.

**Q: Can we clean up even more?**  
A: Yes, but these are the safe, obvious items. Further cleanup risks losing useful data.

---

**Ready to proceed when you give the word!** 🚀
