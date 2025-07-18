# Git Analytics Dashboard

A full-stack demo project (Flask + vanilla JS) that visualises GitHub repository activity.

## Features

* Fetches commit history from any public repo (defaults to `OpenRA/OpenRA`) via GitHub GraphQL API.
* Caches raw commit data on disk, resumes partially-fetched sessions, and shows a progress bar while fetching.
* API endpoints:
  1. `/api/authors` – list authors within date range.
  2. `/api/outliers` – commits whose size (additions+deletions) is a z-score > 2.
  3. `/api/activity` – Sun-Sat aggregate for commits/additions/deletions/total_changes, optional author filter.
  4. `/api/word_frequency` – word cloud data for commit messages.
* Single-page frontend with:
  * Date pickers, metric/author filters, and a debounced **Run** button.
  * Outlier table, bar chart (Chart.js), and word cloud (wordcloud2.js).
  * LocalStorage cache so last-seen visuals persist after reload.
* One-command launch: `python backend/app.py` (frontend is served by Flask).

## Quick start

```bash
# 1. Clone repository (or copy files)
cd hackathon

# 2. Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set a GitHub personal access token (only needs `public_repo` scope)
export GITHUB_TOKEN=ghp_yourTokenHere
# Optionally override repo target
export REPO_OWNER=OpenRA
export REPO_NAME=OpenRA

# 5. Run the app (will fetch commits on first start, then use cache)
python backend/app.py

# 6. Visit the dashboard
open http://localhost:5000   # or just browse to it
```

## Notes

* **First run** may take a minute or two while commits are downloaded. Subsequent runs hit the on-disk cache.
* Cache files live in `backend/cache/`. Delete them to force a refetch.
* The progress bar prints to the terminal during data download.
* If you need to change the default date range, use the date pickers on the UI; the backend will fetch (and cache) that range on demand.

Enjoy! :rocket: 