import contextvars
import json
import logging
import re
import sys
from datetime import datetime, timezone

request_id_var = contextvars.ContextVar("request_id", default="-")

SENSITIVE = re.compile(r"(token|secret|password|passwd|authorization|cookie|signature|hmac|api[-_]?key)", re.I)


def redact(value):
    if isinstance(value, dict):
        return {k: ("***" if SENSITIVE.search(str(k)) else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": getattr(record, "service", "-"),
            "request_id": request_id_var.get(),
            "event": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if fields:
            data.update(redact(fields))
        return json.dumps(data, ensure_ascii=False, default=str)


_logger = logging.getLogger("mariachi")


def setup_logging():
    if not any(getattr(h, "_mariachi", False) for h in _logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        handler._mariachi = True
        _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def log(service, event, level=logging.INFO, **fields):
    _logger.log(level, event, extra={"service": service, "fields": fields})
