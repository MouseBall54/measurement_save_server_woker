import os

from dotenv import load_dotenv


def get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class Settings:
    def __init__(self) -> None:
        load_dotenv()
        self.rabbitmq_host = get_env("RABBITMQ_HOST", "localhost")
        self.rabbitmq_port = int(get_env("RABBITMQ_PORT", "5672"))
        self.rabbitmq_user = get_env("RABBITMQ_USER", "guest")
        self.rabbitmq_password = get_env("RABBITMQ_PASSWORD", "guest")
        self.rabbitmq_queue_name = get_env("RABBITMQ_QUEUE_NAME", "measurement_ingest")
        self.database_url = get_env(
            "DATABASE_URL", "mysql+pymysql://user:password@localhost:3306/measure_system_3"
        )


def get_settings() -> Settings:
    return Settings()
