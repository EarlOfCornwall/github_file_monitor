import requests
import json
from pathlib import Path
from config import AppConfig

config = AppConfig.load_config()

AUTHOR = config.repo_owner
REPO = config.repo_name
TOKEN = config.gh_api_token
BRANCH = config.branch
SHA_CACHE_FILE = Path("last_known_sha.json")

GITHUB_API = "https://api.github.com"
HEADERS = {"Authorization": f"token {TOKEN}"} if TOKEN else {}


def get_latest_commit_sha():
    url = f"{GITHUB_API}/repos/{AUTHOR}/{REPO}/commits/{BRANCH}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()["sha"]


def get_file_sha(commit_sha, file_path):
    url = f"{GITHUB_API}/repos/{AUTHOR}/{REPO}/contents/{file_path}?ref={commit_sha}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()["sha"]


def download_raw_file(file_path):
    url = f"https://raw.githubusercontent.com/{AUTHOR}/{REPO}/{BRANCH}/{file_path}"
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.text


def load_cached_sha():
    if SHA_CACHE_FILE.exists():
        with open(SHA_CACHE_FILE, "r") as f:
            return json.load(f).get("file_sha")
    return None


def save_cached_sha(commit_sha, file_sha):
    with open(SHA_CACHE_FILE, "w") as f:
        json.dump({"commit_sha": commit_sha, "file_sha": file_sha}, f)
