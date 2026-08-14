import logging
import json
import sys
from datetime import datetime, timezone
from src.core.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = getattr(record, "correlation_id")
        if hasattr(record, "user_id"):
            log_data["user_id"] = getattr(record, "user_id")
        if hasattr(record, "home_id"):
            log_data["home_id"] = getattr(record, "home_id")
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


def setup_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    
    # Avoid duplicate handlers
    root_logger.handlers = [handler]


logger = logging.getLogger("ozhzo_verse")
