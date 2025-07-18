import os
import json
import time
from datetime import datetime
from typing import List, Dict, Optional

import requests
from tqdm import tqdm

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

GITHUB_API_URL = "https://api.github.com/graphql"


def _cache_path(owner: str, repo: str, start: str, end: str) -> str:
    fname = f"commits_{owner}_{repo}_{start}_{end}.json"
    return os.path.join(CACHE_DIR, fname)


def _run_query(query: str, variables: dict, token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(GITHUB_API_URL, json={"query": query, "variables": variables}, headers=headers, timeout=30)
    if response.status_code == 200:
        return response.json()
    else:
        raise RuntimeError(f"GitHub API error {response.status_code}: {response.text}")


HISTORY_QUERY = """
query($owner: String!, $name: String!, $since: GitTimestamp, $until: GitTimestamp, $cursor: String) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 10, since: $since, until: $until, after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                oid
                committedDate
                message
                additions
                deletions
                author {
                  name
                  email
                  user { login }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


def get_commits_between(owner: str, repo: str, start: str, end: str, token: str) -> List[Dict]:
    """Fetch commits between ISO8601 date strings start and end inclusive. Uses local cache if available."""
    cache_file = _cache_path(owner, repo, start, end)
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            data = json.load(f)
        print(f"[github_fetcher] Using cached data from {cache_file} (commits: {len(data)})")
        return data

    print(f"[github_fetcher] No cache found. Fetching commits for {owner}/{repo} {start}->{end}")
    all_commits: List[Dict] = []
    cursor: Optional[str] = None

    pbar = tqdm(total=None, desc="Fetching pages")
    while True:
        variables = {
            "owner": owner,
            "name": repo,
            "since": f"{start}T00:00:00Z",
            "until": f"{end}T23:59:59Z",
            "cursor": cursor,
        }
        result = _run_query(HISTORY_QUERY, variables, token)
        if "errors" in result:
            raise RuntimeError(result["errors"])

        edges = result["data"]["repository"]["defaultBranchRef"]["target"]["history"]["edges"]
        for edge in edges:
            node = edge["node"]
            commit = {
                "sha": node["oid"],
                "date": node["committedDate"],
                "message": node["message"],
                "additions": node["additions"],
                "deletions": node["deletions"],
                "author": {
                    "name": node["author"]["name"],
                    "email": node["author"]["email"],
                    "login": node["author"]["user"]["login"] if node["author"]["user"] else None,
                },
            }
            all_commits.append(commit)

        page_info = result["data"]["repository"]["defaultBranchRef"]["target"]["history"]["pageInfo"]
        cursor = page_info["endCursor"]
        pbar.update(1)
        # persist after each page
        with open(cache_file, "w") as f:
            json.dump(all_commits, f)

        if not page_info["hasNextPage"]:
            break
        # minor throttle to respect secondary rate limits
        time.sleep(0.8)
    pbar.close()
    print(f"[github_fetcher] Fetched {len(all_commits)} commits. Cached at {cache_file}")
    return all_commits 