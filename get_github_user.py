import os
import re
import time
import base64
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()   

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28"
}

def get_user_named_repo_readme(username):
    url = f"https://api.github.com/repos/{username}/{username}/readme"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        content = resp.json().get("content")
        if content:
            try:
                return base64.b64decode(content).decode("utf-8", errors="ignore")
            except Exception:
                return None
    return None

def collect_github_profile(username):
    user_url = f"https://api.github.com/users/{username}"
    user_resp = requests.get(user_url, headers=HEADERS)
    if user_resp.status_code != 200:
        raise Exception(f"GitHub user {username} not found ({user_resp.status_code})")
    user_data = user_resp.json()

    repos_url = f"https://api.github.com/users/{username}/repos"
    repos_resp = requests.get(repos_url, headers=HEADERS, params={"per_page": 100})
    repos = repos_resp.json() if repos_resp.status_code == 200 else []

    # Combine repo name and description into a single list of dicts
    repos_list = [
        {
            "repo_name": r.get("name"),
            "repo_description": r.get("description") or ""
        }
        for r in repos if r.get("name")
    ]

    recent_commits = []
    count = 0
    for repo in repos:
        if count >= 3:
            break
        if repo.get("fork"):
            continue
        commits_url = f"https://api.github.com/repos/{username}/{repo['name']}/commits"
        commits_resp = requests.get(commits_url, headers=HEADERS, params={"per_page": 5})
        if commits_resp.status_code == 200:
            commits = commits_resp.json()
            for c in commits:
                if "commit" in c and "message" in c["commit"]:
                    recent_commits.append(c["commit"]["message"])
        count += 1
        time.sleep(0.2)

    readme_content = get_user_named_repo_readme(username)

    return {
        "platform": "github",
        "user_id": str(user_data.get("id")),
        "username": user_data.get("login"),
        "name": user_data.get("name") or user_data.get("login"),
        "bio": user_data.get("bio") or "",
        "location": user_data.get("location") or "",
        "email": user_data.get("email") or "",
        "company": user_data.get("company") or "",
        "website": user_data.get("blog") or "",
        "repos": repos_list,  # <-- combined field
        "user_named_repo_readme": readme_content,
    }

def collect_profile_from_github_url(url):
    match = re.search(r"github\.com/([\w\-\d]+)", url)
    if not match:
        raise ValueError("Invalid GitHub URL")
    username = match.group(1)
    return collect_github_profile(username)
