import json
import logging
from datetime import datetime, timezone

from server.core.config import Settings


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class LoggingConfigurator:
    def configure(self, settings: Settings) -> None:
        root = logging.getLogger()
        root.handlers.clear()
        handler = logging.StreamHandler()
        if settings.log_format.lower() == "json":
            handler.setFormatter(JsonLogFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("%(levelname)s %(name)s: %(message)s")
            )
        root.addHandler(handler)
        root.setLevel(logging.INFO)
