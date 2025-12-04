from __future__ import annotations

import structlog
import logging
from typing import Dict, Any


SENSITIVE_KEYS = {"notes", "pii", "ssn", "phone", "email"}


def _mask(d: Dict[str, Any]) -> Dict[str, Any]:
    masked = {}
    for k, v in d.items():
        if k in SENSITIVE_KEYS:
            masked[k] = "***"
        elif isinstance(v, dict):
            masked[k] = _mask(v)
        else:
            masked[k] = v
    return masked


def get_logger(component: str = "app"):
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.EventRenamer("msg"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )
    return structlog.get_logger(component=component)


def log_with_mask(logger, event: str, **kwargs):
    masked_kwargs = _mask(kwargs)
    logger.info(event, **masked_kwargs)
