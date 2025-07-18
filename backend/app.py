import os
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import List, Dict

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import numpy as np

from utils.service import get_api_outliers_stdev, get_authors_from_commit, filter_by_metric_type_and_author, \
    get_most_frequent_words
from github_fetcher import get_commits_between

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------
OWNER = os.getenv("REPO_OWNER", "OpenRA")
REPO = os.getenv("REPO_NAME", "OpenRA")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("Please set GITHUB_TOKEN environment variable with a personal access token")

BACKEND_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.abspath(os.path.join(BACKEND_DIR, "..", "frontend"))

# --------------------------------------------------------------------------------------
# Flask app
# --------------------------------------------------------------------------------------
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/")
CORS(app)


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------

def _default_dates():
    end = datetime.utcnow().date() - timedelta(days=1)
    start = end - timedelta(days=365)
    return start.isoformat(), end.isoformat()


def _get_commits(start: str, end: str) -> List[Dict]:
    if not start or not end:
        start, end = _default_dates()
    commits = get_commits_between(OWNER, REPO, start, end, GITHUB_TOKEN)
    return commits


# --------------------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------------------


@app.route("/api/authors")
def api_authors():
    start = request.args.get("start_date")
    end = request.args.get("end_date")

    commits = _get_commits(start=start, end=end)
    authors = get_authors_from_commit(commits)
    return jsonify(authors)


@app.route("/api/outliers")
def api_outliers():
    start = request.args.get("start_date")
    end = request.args.get("end_date")

    commits = _get_commits(start=start, end=end)

    outliers = get_api_outliers_stdev(commits)
    return jsonify(outliers)





@app.route("/api/activity")
def api_activity():
    start = request.args.get("start_date")
    end = request.args.get("end_date")

    commits = _get_commits(start=start, end=end)

    metric_type = request.args.get("metric_type", "commits")
    author_filter = request.args.get("author")

    result = filter_by_metric_type_and_author(commits, metric_type, author_filter)
    return jsonify(result)


STOP_WORDS = set("""
a an the and or but if in on at for to of with a's that's it is are was were be been being this that those these i me my we our you your he she they them their commit merge fix fixed update updates updated
""".split())


@app.route("/api/word_frequency")
def api_word_frequency():
    start = request.args.get("start_date")
    end = request.args.get("end_date")

    commits = _get_commits(start=start, end=end)

    results = get_most_frequent_words(commits, STOP_WORDS)
    return jsonify(results)


# --------------------------------------------------------------------------------------
# Frontend routes (serves built or raw files)
# --------------------------------------------------------------------------------------


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    # if file exists in frontend folder, serve it; otherwise return index.html for SPA routing
    requested = os.path.join(FRONTEND_DIR, path)
    if path and os.path.exists(requested):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')


# --------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------


if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)