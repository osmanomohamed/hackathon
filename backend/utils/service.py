from collections import defaultdict
from datetime import datetime

import numpy as np

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def get_authors_from_commit(commits: list):
    authors = set()
    for c in commits:
        name = c["author"].get("name") or c["author"].get("login")
        if name:
            authors.add(name)
    return sorted(list(authors))


def get_api_outliers_stdev(commits:list) -> list:
    """
    Identify outliers based on standard deviation from the mean.
    """
    total_changes = np.array([c["additions"] + c["deletions"] for c in commits])
    if len(total_changes) == 0:
        return []
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
    return outliers



def filter_by_metric_type_and_author(commits: list, metric_type: str, author_filter: str = None) -> dict:
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
    return result




def get_most_frequent_words(commits: list, stop_words: set) -> list:
    from collections import Counter


    words = Counter()
    for c in commits:
        msg = c["message"].lower()
        for w in msg.split():
            w = ''.join(ch for ch in w if ch.isalpha())  # strip punctuation
            if w and w not in stop_words and len(w) > 2:
                words[w] += 1
    most_common = [{"text": w, "value": cnt} for w, cnt in words.most_common(200)]
    return most_common
