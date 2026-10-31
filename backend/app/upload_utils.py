"""Tiện ích đọc UploadFile — cố ý tách khỏi app/core/ vì app/core/ chỉ chứa logic THUẦN
PYTHON, không phụ thuộc FastAPI (xem README.md). Import kiểu UploadFile được đặt sau
TYPE_CHECKING nên module này KHÔNG cần cài fastapi để import lúc chạy (hàm chỉ cần đối
tượng có sẵn phương thức async read(n) — đúng interface của UploadFile, nhưng không ép kiểu
cụ thể) — nhờ vậy có thể kiểm thử bằng unittest thuần, không cần fastapi (xem
tests/test_core.py, lớp UploadUtilsTests)."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import UploadFile

_CHUNK_SIZE = 1024 * 1024  # 1 MB mỗi lần đọc


async def read_capped(file: "UploadFile", max_bytes: int) -> bytes:
    """Đọc nội dung tệp tải lên theo từng đoạn, DỪNG SỚM ngay khi đã đọc vượt quá max_bytes
    thay vì luôn đọc hết toàn bộ tệp vào bộ nhớ trước rồi mới kiểm tra dung lượng (như
    `await file.read()` không tham số). Với FR-01 (giới hạn 5 MB), điều này tránh việc một
    tệp lớn bất thường (gửi nhầm hoặc cố ý) chiếm dụng bộ nhớ máy chủ trước khi bị từ chối.

    Kết quả trả về vẫn tương thích với validate_upload(): nếu tệp vượt max_bytes, phần bytes
    trả về cũng có độ dài > max_bytes (chỉ là không nhất thiết đọc HẾT phần còn lại của tệp),
    nên validate_upload() vẫn phát hiện và báo lỗi "quá lớn" đúng như trước."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            break
    return b"".join(chunks)
