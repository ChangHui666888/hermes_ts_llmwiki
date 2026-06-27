#!/bin/bash
# ==========================================
# Hermes Wiki Auto-Sync
# 
# Triggered by Hermes cron. 
# 1. Checks for uncommitted changes
# 2. Auto-commits with meaningful message
# 3. Rebuilds graph data
# 4. Pushes to GitHub
# ==========================================

WIKI=/c/Users/ChangHui/wiki
cd "$WIKI" || exit 1

# Step 1: Check for changes
if ! git diff --quiet HEAD 2>/dev/null && ! git ls-files --others --exclude-standard --quiet; then
    HAS_CHANGES=true
else
    HAS_CHANGES=false
fi

# Step 2: Rebuild graph data (always)
python scripts/wiki-graph.py 2>/dev/null

# If no changes, we're done
if [ "$HAS_CHANGES" = false ]; then
    # But still need to commit graph data if it changed
    if git diff --quiet data.json 2>/dev/null; then
        echo "✅ Wiki up-to-date, graph rebuilt"
        exit 0
    fi
fi

# Step 3: Auto-commit
git add -A
git commit -m "auto-sync: wiki updates [$(date '+%Y-%m-%d %H:%M')]" 2>/dev/null || true

# Step 4: Push to GitHub
git push 2>&1
echo "✅ Wiki auto-sync complete at $(date)"
