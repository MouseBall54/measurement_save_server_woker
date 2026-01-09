import json
import logging
import os
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logging(level: int = logging.INFO) -> None:
    log_file = os.getenv("LOG_FILE", os.path.join("logs", "app.log"))
    error_log_file = os.getenv("ERROR_LOG_FILE", os.path.join("logs", "error.log"))
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JsonFormatter())

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(JsonFormatter())

    error_handler = logging.FileHandler(error_log_file)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [console_handler, file_handler, error_handler]
