from __future__ import annotations

from typing import Callable, Type
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type


def default_retry(exceptions: Type[BaseException] = Exception, attempts: int = 3):
    return retry(
        reraise=True,
        stop=stop_after_attempt(attempts),
        wait=wait_exponential_jitter(),
        retry=retry_if_exception_type(exceptions),
    )


def wrap_with_retry(fn: Callable, exceptions: Type[BaseException] = Exception, attempts: int = 3):
    return default_retry(exceptions, attempts)(fn)
