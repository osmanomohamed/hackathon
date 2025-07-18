import os
from datetime import datetime, timedelta
from collections import Counter, defaultdict

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import numpy as np

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


def _get_commits():
    start = request.args.get("start_date")
    end = request.args.get("end_date")
    if not start or not end:
        start, end = _default_dates()
    commits = get_commits_between(OWNER, REPO, start, end, GITHUB_TOKEN)
    return commits, start, end


# --------------------------------------------------------------------------------------
# API Endpoints
# --------------------------------------------------------------------------------------


@app.route("/api/authors")
def api_authors():
    commits, start, end = _get_commits()
    authors = set()
    for c in commits:
        name = c["author"].get("name") or c["author"].get("login")
        if name:
            authors.add(name)
    return jsonify(sorted(authors))


@app.route("/api/outliers")
def api_outliers():
    commits, _, _ = _get_commits()
    total_changes = np.array([c["additions"] + c["deletions"] for c in commits])
    if len(total_changes) == 0:
        return jsonify([])
    mean = total_changes.mean()
    std = total_changes.std() or 1  # avoid div0
    outliers = []
    for c in commits:
        tc = c["additions"] + c["deletions"]
        z = (tc - mean) / std
        if z > 2:
            outliers.append({
                "sha": c["sha"],
                "title": c["message"].split("\n")[0],
                "total_changes": tc,
                "z_score": round(float(z), 2),
            })
    # sort descending by z_score
    outliers.sort(key=lambda x: x["z_score"], reverse=True)
    return jsonify(outliers)


DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@app.route("/api/activity")
def api_activity():
    commits, _, _ = _get_commits()
    metric_type = request.args.get("metric_type", "commits")
    author_filter = request.args.get("author")

    buckets = defaultdict(int)
    for c in commits:
        if author_filter:
            name = c["author"].get("name") or c["author"].get("login")
            if name != author_filter:
                continue
        date_obj = datetime.fromisoformat(c["date"].replace("Z", "+00:00"))
        day_name = DAY_NAMES[date_obj.weekday()]

        if metric_type == "commits":
            buckets[day_name] += 1
        elif metric_type == "additions":
            buckets[day_name] += c["additions"]
        elif metric_type == "deletions":
            buckets[day_name] += c["deletions"]
        else:  # total_changes
            buckets[day_name] += c["additions"] + c["deletions"]

    # ensure all days present
    result = {d: buckets.get(d, 0) for d in DAY_NAMES}
    return jsonify(result)


STOP_WORDS = set("""
a an the and or but if in on at for to of with a's that's it is are was were be been being this that those these i me my we our you your he she they them their commit merge fix fixed update updates updated
""".split())


@app.route("/api/word_frequency")
def api_word_frequency():
    commits, _, _ = _get_commits()
    words = Counter()
    for c in commits:
        msg = c["message"].lower()
        for w in msg.split():
            w = ''.join(ch for ch in w if ch.isalpha())  # strip punctuation
            if w and w not in STOP_WORDS and len(w) > 2:
                words[w] += 1
    most_common = [{"text": w, "value": cnt} for w, cnt in words.most_common(200)]
    return jsonify(most_common)


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
    app.run(host="0.0.0.0", port=5000, debug=True) 