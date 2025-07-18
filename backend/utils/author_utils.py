def get_authors_from_commit(commits: set):
    authors = set()
    for c in commits:
        name = c["author"].get("name") or c["author"].get("login")
        if name:
            authors.add(name)
    return authors
