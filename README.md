# GitHub File Monitor

Скрипт отслеживает изменения файлов в репозиториях GitHub и имеет возможность отправки изменившихся файлов через Email или ВКонтакте

## Установка

```bash
git clone <repository-url>
cd github-file-monitor
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
pip install requests
```

## Настройка

1. Скопируйте пример конфигурации в рабочий файл:

   ```bash
   cp config.example.json config.json
   ```

2. Откройте `config.json` и заполните необходимые поля:

```json
{
  "repo_owner": "octocat",
  "repo_name": "hello-world",
  "branch": "main",
  "file_path": [
    "README.md",
    "src/main.py"
  ],
  "gh_api_token": "ghp_xxxxxxxxxxxxxxxxxxxx",
  "check_interval_minutes": 15,
  "email": {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "me@example.com",
    "sender_password": "app-password",
    "recipient_email": "you@example.com"
  },
  "vk": {
    "token": "vk1.a.xxxxxxxxxxxxxxxxxxxx",
    "peer_id": 123456789,
    "api_version": "5.199"
  }
}
```

- **`gh_api_token`**: Опционален для публичных репозиториев, но обязателен для приватных. Также помогает избежать жестких лимитов GitHub API (60 запросов/час без токена против 5000 с токеном).
- **Email**: Для получения уведомлений во время "белых списков" можно использовать mail.ru или yandex.
- **VK**: Токен сообщества должен иметь права на отправку сообщений и работу с документами.
*Вы можете удалить блок `email` или `vk` из конфига, если планируете использовать только один способ уведомлений.*

## Использование

Запустите главный скрипт:

```bash
python main.py
```

Скрипт перейдет в бесконечный цикл, проверяя репозиторий каждые `check_interval_minutes` минут.
Для остановки нажмите `Ctrl+C`. Все события и ошибки будут дублироваться в файл `monitor.log`.

## Структура проекта

```text
github-file-monitor/
├── config.example.json      # Пример конфигурации
├── monitor.log              # Файл логов (в .gitignore)
├── last_known_sha.json      # Кэш состояний файлов (в .gitignore)
├── updates/                 # Локальные копии измененных файлов (в .gitignore)
└── src/
    ├── __init__.py
    ├── config.py            
    ├── worker.py            # Логика GitHub API и проверки SHA
    └── notifiers/
        ├── __init__.py
        ├── email_notifier.py # Отправка Email с вложениями
        └── vk_notifier.py    # Отправка в VK с загрузкой документов
```

## Лицензия

MIT
