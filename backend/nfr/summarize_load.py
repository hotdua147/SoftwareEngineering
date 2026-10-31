"""Gom kết quả Locust (các tệp *_stats.csv do --csv tạo) thành một bảng Markdown cho báo cáo.

    python -m nfr.summarize_load nfr_results/load_u10_stats.csv nfr_results/load_u25_stats.csv nfr_results/load_u50_stats.csv
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path


def rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(v, digits: int = 0) -> str:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return "—"
    return f"{x:.{digits}f}".replace(".", ",")


def summarize(paths: list[Path]) -> str:
    """Một dòng cho mỗi thao tác. Dòng "Aggregated" của Locust bị bỏ vì nó cộng cả các dòng SERVER
    (số đo phía máy chủ, không phải request) — thay bằng dòng tổng tự tính chỉ trên request thật."""
    out = ["| Lượt đo | Thao tác | Số request | Lỗi | p50 (ms) | p95 (ms) | Request/giây |", "|---|---|---|---|---|---|---|"]
    for p in paths:
        label = p.name.replace("_stats.csv", "")
        count = fails = 0
        rps = 0.0
        for r in rows(p):
            name, kind = r.get("Name", ""), r.get("Type", "")
            if name.startswith("(chuẩn bị)") or name == "Aggregated":
                continue
            server = kind == "SERVER"
            out.append(f"| {label} | {'máy chủ đo: ' + name if server else name} | {r.get('Request Count')} | "
                       f"{'—' if server else r.get('Failure Count')} | {_num(r.get('50%'))} | {_num(r.get('95%'))} | "
                       f"{'—' if server else _num(r.get('Requests/s'), 1)} |")
            if not server:
                count += int(float(r.get("Request Count") or 0))
                fails += int(float(r.get("Failure Count") or 0))
                rps += float(r.get("Requests/s") or 0)
        out.append(f"| {label} | **Tổng** | {count} | {fails} | | | **{_num(rps, 1)}** |")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    print(summarize([Path(a) for a in sys.argv[1:]]))
