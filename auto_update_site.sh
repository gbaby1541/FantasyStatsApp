#!/bin/bash

# Navigate to the app directory
cd /Users/garybalkus/AntiGravity/fantasy-stats-app || exit 1

# Export environment variables from .env
set -a
source .env
set +a

# Export ESPN_SWID specifically since fetch_espn.py expects it
export ESPN_SWID=$SWID

# Run the python script to pull fresh data
echo "Fetching latest ESPN data..."
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 fetch_espn.py

# Check if data.js actually changed
if git diff --quiet data.js; then
    echo "No new data to commit."
else
    # Stage, commit, and push
    echo "Committing and pushing to GitHub..."
    git add data.js
    git commit -m "Automated weekly data update for Current Season"
    git push origin main
    echo "Successfully updated and pushed new data to GitHub!"
fi
