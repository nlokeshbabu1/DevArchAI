"""Access to the uvicorn/FastAPI main event loop for cross-thread scheduling."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Record the running application event loop (call from FastAPI lifespan)."""
    global _main_loop
    _main_loop = loop


def get_main_event_loop() -> asyncio.AbstractEventLoop | None:
    return _main_loop


def schedule_coroutine(
    coro: Coroutine[Any, Any, T],
    *,
    on_error: Callable[[Exception], None] | None = None,
) -> asyncio.Future[T] | None:
    """Schedule ``coro`` on the main loop from a worker/background thread."""
    loop = get_main_event_loop()
    if loop is None or not loop.is_running():
        return None

    future = asyncio.run_coroutine_threadsafe(coro, loop)

    def _done(done_future: asyncio.Future[T]) -> None:
        try:
            done_future.result()
        except Exception as exc:
            if on_error is not None:
                on_error(exc)

    future.add_done_callback(_done)
    return future
