import json
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path("config.json")


@dataclass
class EmailConfig:
    smtp_server: str
    smtp_port: int
    sender_email: str
    sender_password: str
    recipient_email: str


@dataclass
class AppConfig:
    repo_owner: str
    repo_name: str
    file_path: list
    check_interval_minutes: int
    email: EmailConfig

    @classmethod
    def load_config(cls, path: Path = CONFIG_PATH) -> "AppConfig":
        if not path.exists():
            raise FileNotFoundError(f"Config {CONFIG_PATH} not found")

        with path.open("r", encoding="utf-8") as configfile:
            data = json.load(configfile)

        email_data = data.get("email")
        if email_data is None:
            raise ValueError("Empty email config")

        email_cfg = EmailConfig(**email_data)

        return cls(
            repo_owner=data["repo_owner"],
            repo_name=data["repo_name"],
            file_path=data["file_path"],
            check_interval_minutes=data["check_interval_minutes"],
            email=email_cfg,
        )
