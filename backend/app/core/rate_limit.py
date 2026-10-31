"""Giới hạn số lần thất bại theo khóa trong một cửa sổ thời gian — thuần Python, có thể kiểm thử
bằng đồng hồ giả (tham số `clock`).

Dùng cho tra cứu đơn hàng (POST /api/v1/orders/lookup): mã đơn chỉ có 4 chữ số ngẫu nhiên
mỗi ngày (DH-260926-4821), nên người biết số điện thoại của khách có thể thử lần lượt ~10.000
mã để xem tên, địa chỉ của họ. Giới hạn số lần tra cứu SAI cho cùng một số điện thoại khiến
việc dò này không khả thi (10 lần / 15 phút ≈ 1.000 lần / ngày, cần ~10 ngày cho 1 ngày đơn).

Lưu trong bộ nhớ của tiến trình: đủ cho bản demo chạy một tiến trình uvicorn; chạy nhiều
tiến trình/máy chủ thì cần chuyển sang kho dùng chung (ví dụ Redis) — xem README, "Giới hạn".
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable


class FailureLimiter:
    def __init__(
        self,
        max_failures: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ) -> None:
        self.max_failures = max_failures
        self.window = window_seconds
        self.max_keys = max_keys  # chặn bộ nhớ phình ra khi bị gửi rất nhiều khóa khác nhau
        self._clock = clock
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()  # endpoint đồng bộ của FastAPI chạy trên nhiều luồng

    def _recent(self, key: str, now: float) -> deque[float]:
        q = self._failures.get(key)
        if q is None:
            return deque()
        while q and now - q[0] >= self.window:
            q.popleft()
        if not q:
            del self._failures[key]  # không giữ khóa cũ mãi trong bộ nhớ
        return q

    def blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._recent(key, self._clock())) >= self.max_failures

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            self._recent(key, now)
            if key not in self._failures and len(self._failures) >= self.max_keys:
                self._sweep(now)
            self._failures.setdefault(key, deque()).append(now)

    def _sweep(self, now: float) -> None:
        # Bỏ các khóa đã hết hạn; nếu vẫn đầy thì bỏ khóa có lần sai gần nhất cũ nhất
        for key in list(self._failures):
            self._recent(key, now)
        while len(self._failures) >= self.max_keys:
            oldest = min(self._failures, key=lambda k: self._failures[k][-1])
            del self._failures[oldest]

    def __len__(self) -> int:
        return len(self._failures)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
