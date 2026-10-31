"""Tìm kiếm theo chữ cho tiếng Việt — cổng Python của src/lib/textSearch.js ở bản front-end 02
(tìm theo tên, Sprint 1). Thuần Python (chỉ dùng thư viện chuẩn), không phụ thuộc FastAPI hay
Qdrant nên kiểm thử được ở mọi máy.

Quy tắc giữ đúng như bản 02 để người dùng thấy cùng một kết quả:
  * cả từ khóa lẫn nội dung sản phẩm đều được bỏ dấu, đ → d, chữ thường, gộp khoảng trắng;
  * từ khóa tách thành các từ; sản phẩm khớp khi MỌI từ đều xuất hiện trong chuỗi
    "tên + nhãn danh mục + mã SKU" (so khớp chuỗi con).
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from app.config import settings
from app.core.catalog_labels import category_label

_SPACES = re.compile(r"\s+")


def normalize_vi(text: object) -> str:
    """Bỏ dấu (tách dấu bằng Unicode NFD rồi xóa các ký tự dấu), đ → d, chữ thường, gộp
    khoảng trắng. Tương đương normalizeVi() phía front-end."""
    s = unicodedata.normalize("NFD", "" if text is None else str(text))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")  # Mn = dấu kết hợp
    s = s.replace("đ", "d").replace("Đ", "d").lower()
    return _SPACES.sub(" ", s).strip()


def clean_query(q: str | None) -> str:
    """Từ khóa người dùng gửi lên: bỏ khoảng trắng thừa, cắt ở độ dài tối đa."""
    return ("" if q is None else str(q)).strip()[: settings.MAX_QUERY_LEN]


def to_terms(q: str | None) -> list[str]:
    norm = normalize_vi(clean_query(q))
    return norm.split(" ") if norm else []


# NFR-03: duyệt/tìm theo tên trên danh mục 100.000+ sản phẩm gọi hai hàm dưới cho MỌI sản phẩm ở
# mỗi request — nhớ kết quả theo chuỗi đầu vào (tên sản phẩm ít khi đổi) để lần sau gần như miễn phí.
_CACHE_SIZE = 1 << 18  # ~262.000 mục


@lru_cache(maxsize=_CACHE_SIZE)
def _haystack(name: str, category: str, sku: str) -> str:
    return normalize_vi(f"{name} {category_label(category)} {sku}")


def haystack(payload: dict) -> str:
    return _haystack(str(payload.get("name", "")), str(payload.get("category", "")), str(payload.get("sku", "")))


def matches_terms(payload: dict, terms: list[str] | None) -> bool:
    if not terms:
        return True
    text = haystack(payload)
    return all(t in text for t in terms)


# --- Sắp xếp tên theo bảng chữ cái tiếng Việt ----------------------------------------------
# Python không có sẵn bộ so sánh chuỗi theo ngôn ngữ (như Intl.Collator('vi') phía trình duyệt),
# nên tự dựng khóa sắp xếp: chữ cái chính theo đúng thứ tự a ă â b c d đ e ê … (ă, â, ê, ô, ơ, ư,
# đ là chữ cái riêng), dấu thanh chỉ dùng để phân định khi mọi chữ cái giống nhau.
_ALPHABET = "a ă â b c d đ e ê f g h i j k l m n o ô ơ p q r s t u ư v w x y z".split()
_LETTER_RANK = {ch: i for i, ch in enumerate(_ALPHABET)}
# Dấu thanh (khác với dấu tạo chữ cái ă â ê ô ơ ư): không dấu < huyền < hỏi < ngã < sắc < nặng
_TONE_RANK = {"̀": 1, "̉": 2, "̃": 3, "́": 4, "̣": 5}


def _letter_key(ch: str) -> tuple[int, int, int]:
    """(hạng chữ cái, hạng dấu thanh, mã ký tự gốc) cho một ký tự đã viết thường."""
    decomposed = unicodedata.normalize("NFD", ch)
    tone = 0
    base = []
    for c in decomposed:
        if c in _TONE_RANK:
            tone = _TONE_RANK[c]
        else:
            base.append(c)
    letter = unicodedata.normalize("NFC", "".join(base))
    if letter in _LETTER_RANK:
        return (100 + _LETTER_RANK[letter], tone, 0)
    # Chữ số, dấu cách, ký tự khác: xếp trước chữ cái, giữ thứ tự mã Unicode
    return (0, tone, ord(letter[0]) if letter else 0)


@lru_cache(maxsize=_CACHE_SIZE)
def vi_sort_key(text: str) -> tuple:
    lowered = _SPACES.sub(" ", str(text)).strip().lower()
    letters = tuple(_letter_key(ch) for ch in lowered)
    # Khóa chính: chuỗi (chữ cái, mã ký tự) — bỏ qua dấu thanh; khóa phụ: dấu thanh lần lượt
    return (tuple((k[0], k[2]) for k in letters), tuple(k[1] for k in letters))
