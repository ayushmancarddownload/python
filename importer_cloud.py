import os
import time
import requests
import urllib.parse

# Configurations from Environment Variables (GitHub Secrets)
GL_TOKEN = os.getenv("GITLAB_TOKEN")
GH_TARGET = os.getenv("GH_TARGET", "gameinclassroom")
GH_TOKEN = os.getenv("GITHUB_TOKEN", "")  # Optional
NAMESPACE_ID = os.getenv("GITLAB_NAMESPACE", "")  # Optional
DELAY = float(os.getenv("IMPORT_DELAY", "2.0"))

if not GL_TOKEN:
    print("❌ Error: GITLAB_TOKEN environment variable missing!")
    exit(1)

gl_headers = {"PRIVATE-TOKEN": GL_TOKEN}

# 1. GitLab Verify
print("🔍 Checking GitLab Authentication...")
user_res = requests.get("https://gitlab.com/api/v4/user", headers=gl_headers, timeout=15)
if user_res.status_code != 200:
    print(f"❌ GitLab Token Invalid (HTTP {user_res.status_code})")
    exit(1)
gl_username = user_res.json().get("username")
print(f"👤 Logged in as GitLab: @{gl_username}")

# 2. Fast Pre-Cache: Fetch existing projects from GitLab
existing_projects = set()
print("⚡ Fetching existing projects from GitLab to avoid duplicates...")
try:
    if NAMESPACE_ID:
        encoded_ns = urllib.parse.quote_plus(NAMESPACE_ID)
        fetch_url = f"https://gitlab.com/api/v4/groups/{encoded_ns}/projects?per_page=100&include_subgroups=true"
    else:
        fetch_url = "https://gitlab.com/api/v4/projects?membership=true&per_page=100"

    p_page = 1
    while True:
        r = requests.get(f"{fetch_url}&page={p_page}", headers=gl_headers, timeout=15)
        if r.status_code != 200:
            if NAMESPACE_ID and p_page == 1:
                fetch_url = "https://gitlab.com/api/v4/projects?membership=true&per_page=100"
                continue
            break
        data = r.json()
        if not data or not isinstance(data, list):
            break
        for p in data:
            existing_projects.add(p.get("path", "").lower())
            existing_projects.add(p.get("name", "").lower())
        p_page += 1
    print(f"📋 GitLab par {len(existing_projects)//2} projects pehle se maujud hain.")
except Exception as e:
    print(f"⚠️ Pre-cache error: {e}")

# 3. Fetch GitHub Repositories
print(f"📦 Fetching repositories from GitHub user: '{GH_TARGET}'...")
gh_headers = {"Authorization": f"Bearer {GH_TOKEN}"} if GH_TOKEN else {}

repos = []
page = 1
while True:
    url = f"https://api.github.com/users/{GH_TARGET}/repos?per_page=100&page={page}"
    try:
        r = requests.get(url, headers=gh_headers, timeout=15)
        if r.status_code != 200:
            break
        data = r.json()
        if not data or not isinstance(data, list):
            break
        for item in data:
            repos.append(item["name"])
        page += 1
    except Exception as e:
        print(f"❌ Error fetching GitHub repos: {e}")
        break

total_repos = len(repos)
print(f"🚀 Total {total_repos} repos found. Starting import...\n")

gl_api_url = "https://gitlab.com/api/v4/projects"
imported_count = 0
skipped_count = 0

# 4. Import Loop
for i, repo_name in enumerate(repos, start=1):
    repo_clean = repo_name.strip()
    repo_lower = repo_clean.lower()

    # Fast 0-second skip
    if repo_lower in existing_projects:
        print(f"[{i}/{total_repos}] ⚡ Skipped: {repo_clean} (Already on GitLab)")
        skipped_count += 1
        continue

    print(f"[{i}/{total_repos}] ⏳ Importing NEW: {repo_clean}...")
    payload = {
        "name": repo_clean,
        "path": repo_clean,
        "import_url": f"https://github.com/{GH_TARGET}/{repo_clean}.git",
        "visibility": "public"
    }
    if NAMESPACE_ID:
        payload["namespace_id"] = NAMESPACE_ID

    try:
        res = requests.post(gl_api_url, headers=gl_headers, json=payload, timeout=25)

        if res.status_code in [200, 201]:
            print(f"[{i}/{total_repos}] ✅ Success: {res.json().get('web_url')}")
            existing_projects.add(repo_lower)
            imported_count += 1
            time.sleep(DELAY)

        elif res.status_code == 400 and ("already exists" in res.text or "has already been taken" in res.text):
            print(f"[{i}/{total_repos}] ⚡ Already Exists: {repo_clean}")
            existing_projects.add(repo_lower)

        elif res.status_code == 429:
            print("🚨 [Rate Limit / Daily Limit Hit!] GitLab limit poori ho chuki hai.")
            print("🛑 Aaj ka batch complete. Agle schedule run (24 ghante baad) me baaki ka import hoga.")
            break

        else:
            print(f"[{i}/{total_repos}] ❌ Failed: {repo_clean} (HTTP {res.status_code}) -> {res.text[:80]}")

    except Exception as e:
        print(f"[{i}/{total_repos}] ❌ Error: {e}")

print("\n" + "="*35)
print(f"🎉 Run Finished! Newly Imported: {imported_count} | Skipped: {skipped_count}")
print("="*35)
