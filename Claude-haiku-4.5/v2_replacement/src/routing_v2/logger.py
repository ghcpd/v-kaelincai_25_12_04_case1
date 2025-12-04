"""
Structured logging with request ID tracking.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class StructuredLogger:
    """JSON-structured logger with request ID."""
    
    def __init__(self, name: str, log_file: Optional[str] = None, level: str = "INFO"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))
        
        # JSON formatter
        formatter = logging.Formatter(
            '%(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S',
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (optional)
        if log_file:
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def _format_entry(self, level: str, request_id: str, event: str, **kwargs) -> str:
        """Format log entry as JSON."""
        entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "logger": self.name,
            "request_id": request_id,
            "event": event,
        }
        entry.update(kwargs)
        return json.dumps(entry)
    
    def info(self, request_id: str, event: str, **kwargs):
        """Log info-level event."""
        msg = self._format_entry("INFO", request_id, event, **kwargs)
        self.logger.info(msg)
    
    def warning(self, request_id: str, event: str, **kwargs):
        """Log warning-level event."""
        msg = self._format_entry("WARNING", request_id, event, **kwargs)
        self.logger.warning(msg)
    
    def error(self, request_id: str, event: str, **kwargs):
        """Log error-level event."""
        msg = self._format_entry("ERROR", request_id, event, **kwargs)
        self.logger.error(msg)
    
    def debug(self, request_id: str, event: str, **kwargs):
        """Log debug-level event."""
        msg = self._format_entry("DEBUG", request_id, event, **kwargs)
        self.logger.debug(msg)


# Global logger instance
_logger: Optional[StructuredLogger] = None


def get_logger(name: str = "routing_v2", log_file: Optional[str] = None) -> StructuredLogger:
    """Get or create global logger."""
    global _logger
    if _logger is None:
        _logger = StructuredLogger(name, log_file=log_file)
    return _logger
