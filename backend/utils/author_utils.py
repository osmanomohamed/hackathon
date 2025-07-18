import numpy as np


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
