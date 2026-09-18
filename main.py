import time
import sys
import logging
from pathlib import Path

# Добавляем корень проекта в sys.path для корректных импортов
sys.path.insert(0, str(Path(__file__).parent))

from src.config import AppConfig
from src.worker import MonitorWorker
from src.notifiers.email_notifier import EmailNotifier

log_file = Path("monitor.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def save_files_locally(
    updated_files: dict[str, str], base_dir: str = "updates"
) -> None:
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    for file_path, content in updated_files.items():
        safe_path = file_path.replace("/", "_").replace("\\", "_")
        local_file = Path(base_dir) / safe_path

        with open(local_file, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Файл сохранен локально: {local_file}")


def main() -> None:
    logger.info("=== Запуск скрипта мониторинга ===")

    try:
        logger.info("Загрузка конфигурации...")
        config = AppConfig.load_config()
    except FileNotFoundError as e:
        logger.error(f"{e}. Убедитесь, что файл config.json существует.")
        return
    except Exception as e:
        logger.error(
            f"Ошибка загрузки конфигурации: {e}", exc_info=True
        )  # exc_info добавит traceback в лог
        return

    logger.info("Инициализация модулей...")
    worker = MonitorWorker(config)
    notifier = EmailNotifier(config.email)

    logger.info(
        f"Мониторинг запущен. Интервал проверки: {config.check_interval_minutes} мин."
    )
    logger.info("Для остановки нажмите Ctrl+C\n")

    try:
        while True:
            logger.info("-" * 50)
            logger.info("Начало проверки обновлений...")

            updated_files = worker.check_for_updates()

            if updated_files:
                logger.warning(f"Найдено обновлений: {len(updated_files)}")

                save_files_locally(updated_files)

                logger.info("Отправка уведомления на почту...")
                success = notifier.send_notification(
                    repo_name=config.repo_name, updated_files=updated_files
                )

                if success:
                    logger.info("Уведомление успешно отправлено.")
                else:
                    logger.error(
                        "Не удалось отправить уведомление на почту. Проверьте логи выше."
                    )
            else:
                logger.info("Обновлений не найдено.")

            logger.info(
                f"Ожидание следующей проверки ({config.check_interval_minutes} мин)..."
            )
            time.sleep(config.check_interval_minutes * 60)

    except KeyboardInterrupt:
        logger.info("Мониторинг остановлен пользователем (Ctrl+C).")
    except Exception as e:
        logger.critical(f"Критическая ошибка в главном цикле: {e}", exc_info=True)


if __name__ == "__main__":
    main()
