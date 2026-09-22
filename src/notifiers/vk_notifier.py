import requests
import logging
import random
from pathlib import Path
from src.config import VKConfig

logger = logging.getLogger(__name__)


class VKNotifier:
    def __init__(self, config: VKConfig):
        self.config = config
        self.api_url = "https://api.vk.com/method"

    def _upload_document(self, file_path: str, content: str) -> str | None:
        try:
            upload_url_resp = requests.get(
                f"{self.api_url}/docs.getMessagesUploadServer",
                params={
                    "access_token": self.config.token,
                    "v": self.config.api_version,
                    "type": "doc",
                },
                timeout=10,
            )
            upload_url_resp.raise_for_status()
            upload_url = upload_url_resp.json()["response"]["upload_url"]

            safe_filename = Path(file_path).name or "file.txt"
            files = {"file": (safe_filename, content.encode("utf-8"))}
            upload_resp = requests.post(upload_url, files=files, timeout=15)
            upload_resp.raise_for_status()

            uploaded_file = upload_resp.json().get("file")
            if not uploaded_file:
                logger.error(f"Не удалось загрузить файл {file_path} на сервер ВК.")
                return None

            save_resp = requests.post(
                f"{self.api_url}/docs.save",
                data={
                    "file": uploaded_file,
                    "title": safe_filename,
                    "access_token": self.config.token,
                    "v": self.config.api_version,
                },
                timeout=10,
            )
            save_resp.raise_for_status()
            doc_info = save_resp.json()["response"]

            return f"doc{doc_info['owner_id']}_{doc_info['id']}"

        except requests.exceptions.RequestException as e:
            logger.error(f"Сетевая ошибка при загрузке документа ВК: {e}")
            return None
        except KeyError as e:
            logger.error(
                f"Неожиданный ответ API ВК при загрузке документа: отсутствует ключ {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Неизвестная ошибка при загрузке документа ВК: {e}", exc_info=True
            )
            return None

    def send_notification(self, repo_name: str, updated_files: dict[str, str]) -> bool:
        body = f"🔔 Обновление файлов в репозитории {repo_name}\n\n"
        body += "Измененные файлы:\n"
        for file_path in updated_files.keys():
            body += f"📄 {file_path}\n"
        body += "\nПолное содержимое измененных файлов прикреплено в виде документов."

        attachments = []
        for file_path, content in updated_files.items():
            attachment_str = self._upload_document(file_path, content)
            if attachment_str:
                attachments.append(attachment_str)

        try:
            params = {
                "peer_id": self.config.peer_id,
                "message": body,
                "random_id": random.randint(0, 2147483647),
                "access_token": self.config.token,
                "v": self.config.api_version,
            }
            if attachments:
                params["attachment"] = ",".join(attachments)

            resp = requests.post(
                f"{self.api_url}/messages.send", data=params, timeout=10
            )
            resp.raise_for_status()
            resp_data = resp.json()

            if "response" in resp_data:
                logger.info("Уведомление успешно отправлено в VK.")
                return True
            else:
                error_msg = resp_data.get("error", {}).get(
                    "error_msg", "Неизвестная ошибка API"
                )
                logger.error(f"Ошибка API VK при отправке сообщения: {error_msg}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Сетевая ошибка при отправке сообщения в VK: {e}")
            return False
        except Exception as e:
            logger.error(f"Критическая ошибка при отправке в VK: {e}", exc_info=True)
            return False
