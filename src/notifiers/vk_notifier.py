import requests
import logging
import random
import time
from pathlib import Path
from src.config import VKConfig

logger = logging.getLogger(__name__)


class VKNotifier:
    def __init__(self, config: VKConfig):
        self.config = config
        self.api_url = "https://api.vk.com/method"

    def _upload_document(
        self, file_path: str, content: str, max_retries: int = 3
    ) -> str | None:
        safe_filename = Path(file_path).name or "file.txt"
        content_bytes = content.encode("utf-8")
        logger.debug(
            f"Загрузка документа '{safe_filename}' ({len(content_bytes)} байт)..."
        )

        last_error = "Неизвестная ошибка"

        for attempt in range(1, max_retries + 1):
            try:
                upload_url_resp = requests.get(
                    f"{self.api_url}/docs.getMessagesUploadServer",
                    params={
                        "access_token": self.config.token,
                        "v": self.config.api_version,
                        "type": "doc",
                        "peer_id": self.config.peer_id,
                    },
                    timeout=10,
                )
                upload_url_resp.raise_for_status()
                upload_url_data = upload_url_resp.json()

                if "response" not in upload_url_data:
                    last_error = f"Ошибка получения сервера: {upload_url_data}"
                    logger.warning(last_error)
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                    return None

                upload_url = upload_url_data["response"]["upload_url"]

                files = {"file": (safe_filename, content_bytes, "text/plain")}
                upload_resp = requests.post(upload_url, files=files, timeout=60)
                upload_resp.raise_for_status()
                upload_data = upload_resp.json()
                uploaded_file = upload_data.get("file")

                if not uploaded_file:
                    last_error = (
                        upload_data.get("error_descr")
                        or upload_data.get("error")
                        or str(upload_data)
                    )
                    logger.warning(
                        f"Сервер ВК не принял файл (попытка {attempt}/{max_retries}): {last_error}"
                    )
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
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
                save_data = save_resp.json()

                if "response" not in save_data:
                    last_error = f"Ошибка сохранения: {save_data}"
                    logger.warning(last_error)
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                    return None

                doc_container = save_data["response"]
                doc_info = doc_container.get("doc", doc_container)

                if "owner_id" not in doc_info or "id" not in doc_info:
                    last_error = f"Неожиданный формат ответа: {save_data}"
                    logger.warning(last_error)
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                    return None

                attachment_str = f"doc{doc_info['owner_id']}_{doc_info['id']}"

                if attempt > 1:
                    logger.info(
                        f"Документ '{safe_filename}' успешно загружен с {attempt}-й попытки -> {attachment_str}"
                    )
                else:
                    logger.info(
                        f"Документ загружен в ВК: {safe_filename} -> {attachment_str}"
                    )
                return attachment_str

            except requests.exceptions.Timeout:
                last_error = "Таймаут загрузки"
                logger.warning(
                    f"Таймаут при загрузке '{safe_filename}' (попытка {attempt}/{max_retries})."
                )
                if attempt < max_retries:
                    time.sleep(3)
                    continue
            except requests.exceptions.RequestException as e:
                last_error = f"Сетевая ошибка: {e}"
                logger.warning(last_error)
                if attempt < max_retries:
                    time.sleep(2)
                    continue
            except Exception as e:
                logger.error(f"Неожиданная ошибка при загрузке: {e}", exc_info=True)
                return None

        logger.error(
            f"Не удалось загрузить '{safe_filename}' после {max_retries} попыток. "
            f"Последняя ошибка: {last_error}"
        )
        return None

    def send_notification(self, repo_name: str, updated_files: dict[str, str]) -> bool:
        body = f"🔔 Обновление файлов в репозитории {repo_name}\n\n"
        body += "Измененные файлы:\n"
        for file_path in updated_files.keys():
            body += f"📄 {file_path}\n"

        attachments = []
        failed_files = []
        for file_path, content in updated_files.items():
            attachment_str = self._upload_document(file_path, content)
            if attachment_str:
                attachments.append(attachment_str)
            else:
                failed_files.append(file_path)

        if failed_files:
            body += "\n⚠️ Не удалось прикрепить следующие файлы (см. логи):\n"
            for f in failed_files:
                body += f"❌ {f}\n"
        elif attachments:
            body += (
                "\nПолное содержимое измененных файлов прикреплено в виде документов."
            )

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
            elif updated_files:
                logger.warning(
                    "Ни один файл не удалось прикрепить. Сообщение уйдёт без вложений."
                )

            resp = requests.post(
                f"{self.api_url}/messages.send", data=params, timeout=10
            )
            resp.raise_for_status()
            resp_data = resp.json()

            if "response" in resp_data:
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
