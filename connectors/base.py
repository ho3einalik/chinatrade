"""
Base connector framework with circuit breaker, timeout enforcement,
rate limiting, schema validation, and transparent status reporting.
"""

import time
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("connectors")

class ConnectorStatus(str, Enum):
    LIVE_VERIFIED = "LIVE_VERIFIED"
    GEO_BLOCKED_OR_CHALLENGED = "GEO_BLOCKED_OR_CHALLENGED"
    DECOMMISSIONED_OR_DOWN = "DECOMMISSIONED_OR_DOWN"
    MANUAL_FALLBACK = "MANUAL_FALLBACK"

class CircuitBreakerOpenException(Exception):
    """Raised when consecutive network failures trip the circuit breaker."""
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_time_sec: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_time_sec = recovery_time_sec
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.is_open = False

    def record_success(self):
        self.failure_count = 0
        self.is_open = False

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(f"Circuit breaker TRIPPED! Opened for {self.recovery_time_sec}s after {self.failure_count} failures.")

    def can_execute(self) -> bool:
        if not self.is_open:
            return True
        if time.time() - self.last_failure_time > self.recovery_time_sec:
            # Half-open attempt
            logger.info("Circuit breaker half-open: attempting single probe.")
            return True
        return False

class BaseConnector(ABC):
    def __init__(self, name: str, base_url: str, default_timeout_sec: float = 6.0):
        self.name = name
        self.base_url = base_url
        self.default_timeout_sec = default_timeout_sec
        self.circuit_breaker = CircuitBreaker()
        self.last_request_time = 0.0
        self.min_interval_sec = 0.5  # Rate limiting
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "fa,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7"
        })

    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval_sec:
            time.sleep(self.min_interval_sec - elapsed)
        self.last_request_time = time.time()

    def safe_get(self, url: str, params: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None) -> Optional[requests.Response]:
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenException(f"Circuit breaker is open for {self.name}. Requests temporarily suspended.")

        self._rate_limit()
        t = timeout or self.default_timeout_sec
        try:
            resp = self.session.get(url, params=params, timeout=t)
            if resp.status_code in (200, 201):
                self.circuit_breaker.record_success()
                return resp
            elif resp.status_code in (403, 490, 503):
                logger.warning(f"[{self.name}] Got status {resp.status_code} on {url} (anti-bot or access restricted)")
                self.circuit_breaker.record_failure()
                return resp
            else:
                logger.warning(f"[{self.name}] HTTP {resp.status_code} on {url}")
                self.circuit_breaker.record_failure()
                return resp
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.warning(f"[{self.name}] Connection/Timeout error: {type(e).__name__} on {url}")
            self.circuit_breaker.record_failure()
            return None
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error on {url}: {e}")
            self.circuit_breaker.record_failure()
            return None

    @abstractmethod
    def search(self, query: str, **kwargs) -> Any:
        pass
