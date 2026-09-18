import smtplib
import logging
from email.message import EmailMessage
from src.config import EmailConfig

logger = logging.getLogger(__name__)


class EmailNotifier:
    def __init__(self, config: EmailConfig):
        self.config = config

    def send_notification(self, repo_name: str, updated_files: dict[str, str]) -> bool:
        """
        Отправляет письмо с обновлениями.
        Возвращает True при успехе, False при ошибке.
        """
        msg = EmailMessage()
        msg["Subject"] = f"🔔 Обновление файлов в репозитории {repo_name}"
        msg["From"] = self.config.sender_email
        msg["To"] = self.config.recipient_email

        body = "Здравствуйте!\n\n"
        body += f"В репозитории {repo_name} были обнаружены изменения в следующих файлах:\n\n"
        for file_path in updated_files.keys():
            body += f"📄 {file_path}\n"
        body += "\nПолное содержимое измененных файлов прикреплено к этому письму."
        msg.set_content(body)

        for file_path, content in updated_files.items():
            safe_filename = file_path.replace("/", "_").replace("\\", "_")
            msg.add_attachment(
                content, filename=safe_filename, subtype="plain", charset="utf-8"
            )

        try:
            logger.info(
                f"Подключение к SMTP: {self.config.smtp_server}:{self.config.smtp_port}"
            )

            # === КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: выбор класса по порту ===
            if self.config.smtp_port == 465:
                # Неявный SSL — сразу защищенное соединение
                server_class = smtplib.SMTP_SSL
                use_starttls = False
            else:
                # Порт 587 (или другой) — обычное соединение + STARTTLS
                server_class = smtplib.SMTP
                use_starttls = True

            with server_class(
                self.config.smtp_server, self.config.smtp_port, timeout=15
            ) as server:
                if use_starttls:
                    server.starttls()

                server.login(self.config.sender_email, self.config.sender_password)
                server.send_message(msg)

            logger.info("Письмо успешно отправлено через SMTP.")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "Ошибка аутентификации SMTP. Проверьте логин и пароль приложения."
            )
            return False
        except smtplib.SMTPException as e:
            logger.error(f"Ошибка SMTP-протокола: {e}")
            return False
        except Exception as e:
            logger.error(f"Неизвестная ошибка при отправке письма: {e}", exc_info=True)
            return False
