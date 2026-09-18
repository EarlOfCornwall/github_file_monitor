import requests
import json
import logging
from pathlib import Path
from src.config import AppConfig

logger = logging.getLogger(__name__)


class MonitorWorker:
    def __init__(self, config: AppConfig):
        self.config = config
        self.cache_file = Path("last_known_sha.json")
        self.headers = (
            {"Authorization": f"token {config.gh_api_token}"}
            if config.gh_api_token
            else {}
        )
        self.api_base = "https://api.github.com"

    def _load_cache(self) -> dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Файл кэша был поврежден.")
                return {}
        return {}

    def _save_cache(self, cache_data: dict):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)

    def get_latest_commit_sha(self) -> str:
        url = f"{self.api_base}/repos/{self.config.repo_owner}/{self.config.repo_name}/commits/{self.config.branch}"
        resp = requests.get(url, headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()["sha"]

    def get_file_sha(self, commit_sha: str, file_path: str) -> str:
        url = f"{self.api_base}/repos/{self.config.repo_owner}/{self.config.repo_name}/contents/{file_path}?ref={commit_sha}"
        resp = requests.get(url, headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()["sha"]

    def download_raw_file(self, file_path: str, commit_sha: str) -> str:
        url = f"https://raw.githubusercontent.com/{self.config.repo_owner}/{self.config.repo_name}/{commit_sha}/{file_path}"
        r = requests.get(url, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.text

    def check_for_updates(self) -> dict[str, str]:
        latest_commit = self.get_latest_commit_sha()
        cache = self._load_cache()

        if cache.get("commit_sha") == latest_commit:
            logger.debug("Хэш коммита не изменился, подробная проверка не требуется.")
            return {}

        updated_files = {}
        files_cache = cache.get("files", {})

        for file_path in self.config.file_path:
            try:
                current_file_sha = self.get_file_sha(latest_commit, file_path)
                cached_file_sha = files_cache.get(file_path)

                if cached_file_sha != current_file_sha:
                    logger.info(f"Изменён: {file_path}")
                    content = self.download_raw_file(
                        file_path, commit_sha=latest_commit
                    )
                    updated_files[file_path] = content
                    files_cache[file_path] = current_file_sha
                else:
                    logger.debug(f"Без изменений: {file_path}")

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    logger.warning(f"Файл не найден или удалён: {file_path}")
                    files_cache.pop(file_path, None)
                else:
                    logger.error(f"HTTP ошибка при проверке {file_path}: {e}")
                    raise e

        if updated_files:
            cache["commit_sha"] = latest_commit
            cache["files"] = files_cache
            self._save_cache(cache)
            logger.info(f"Кэш обновлён для коммита {latest_commit[:7]}")

        return updated_files
