"""Kiểm thử các endpoint HTTP thật qua FastAPI TestClient — cần cài fastapi (xem
requirements.txt). Chạy trên máy đã `pip install -r requirements.txt`:

    cd backend
    STORE_BACKEND=memory python3 -m pytest tests/test_api.py -v

STORE_BACKEND=memory để kiểm thử không cần Qdrant đang chạy. Muốn kiểm thử với Qdrant thật:
chạy `docker-compose up qdrant` ở thư mục gốc rồi bỏ biến môi trường STORE_BACKEND (mặc định
đã là 'qdrant').
"""
from __future__ import annotations

import io
import os

os.environ.setdefault("STORE_BACKEND", "memory")
os.environ.setdefault("ORDERS_DB_PATH", ":memory:")  # đơn hàng kiểm thử không ghi ra đĩa

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.deps import get_encoder, get_store  # noqa: E402
from app.main import app  # noqa: E402
from tests.synthetic_catalog import seed_store  # noqa: E402


@pytest.fixture(scope="module")
def client():
    # Dùng TestClient như một context manager để FastAPI chạy `lifespan` (app/main.py). Ứng dụng
    # không còn tự nạp dữ liệu mẫu, nên kiểm thử tự nạp 25 sản phẩm tổng hợp
    # (tests/synthetic_catalog.py) vào chính store mà API dùng.
    with TestClient(app) as c:
        c.startup_count = get_store().count()  # số sản phẩm ngay sau khởi động, trước khi nạp dữ liệu kiểm thử
        seed_store(get_store(), get_encoder())
        # PB-10: endpoint /api/v1/admin/... cần token — client dùng chung cho các test đăng nhập
        # sẵn bằng mật khẩu mặc định của bản demo; test_admin_requires_login kiểm tra khi thiếu.
        token = c.post("/api/v1/admin/login", json={"password": "stylelens-admin"}).json()["token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


def _png_bytes(color=(200, 30, 30), size=64):
    img = Image.new("RGB", (size, size), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert (res.json()["encoder"], res.json()["vector_dim"]) == ("simple", 88)  # kiểm thử dùng ENCODER=simple


def test_startup_does_not_seed_drawn_catalog(client):
    # Danh mục chỉ gồm ảnh thật H&M (app.import_hm) và sản phẩm Admin: khởi động không tự nạp ảnh vẽ
    assert client.startup_count == 0
    from app.core import catalog_data

    assert not hasattr(catalog_data, "render_item_image")


def test_list_items_returns_seeded_test_catalog(client):
    res = client.get("/api/v1/items")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 25
    assert all(it["source"] == "mock" for it in body["items"][:5])


def test_get_item_404_for_unknown_sku(client):
    res = client.get("/api/v1/items/DOES-NOT-EXIST")
    assert res.status_code == 404


def test_search_by_image_returns_ranked_results(client):
    res = client.post(
        "/api/v1/search/image",
        files={"file": ("test.png", _png_bytes(), "image/png")},
        data={"top_k": "5"},
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) <= 5
    scores = [it["score"] for it in body["items"]]
    assert scores == sorted(scores, reverse=True)


def test_search_rejects_bad_file_type(client):
    res = client.post(
        "/api/v1/search/image",
        files={"file": ("test.txt", io.BytesIO(b"not an image"), "text/plain")},
    )
    assert res.status_code == 400


def test_search_rejects_oversized_file(client):
    from app.config import settings

    oversized = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * (settings.MAX_FILE_BYTES + 1))
    res = client.post(
        "/api/v1/search/image",
        files={"file": ("big.png", oversized, "image/png")},
    )
    assert res.status_code == 400
    assert "5 MB" in res.json()["detail"] or "quá lớn" in res.json()["detail"]


def test_admin_upsert_then_delete(client):
    res = client.post(
        "/api/v1/admin/items",
        data={"sku": "TEST-001", "name": "Test Item", "category": "tee", "price": "199000"},
        files={"file": ("t.png", _png_bytes((10, 200, 10)), "image/png")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["updated"] is False
    assert body["sku"] == "TEST-001"

    # Ghi đè cùng SKU -> updated phải là True
    res2 = client.post(
        "/api/v1/admin/items",
        data={"sku": "TEST-001", "name": "Test Item 2", "category": "tee", "price": "219000"},
        files={"file": ("t2.png", _png_bytes((10, 10, 200)), "image/png")},
    )
    assert res2.json()["updated"] is True

    res3 = client.get("/api/v1/items/TEST-001")
    assert res3.status_code == 200
    assert res3.json()["name"] == "Test Item 2"

    res4 = client.delete("/api/v1/admin/items/TEST-001")
    assert res4.status_code == 200
    assert res4.json()["deleted"] is True

    res5 = client.get("/api/v1/items/TEST-001")
    assert res5.status_code == 404


def test_admin_cannot_delete_mock_item(client):
    res = client.get("/api/v1/items")
    mock_sku = next(it["sku"] for it in res.json()["items"] if it["source"] == "mock")
    res2 = client.delete(f"/api/v1/admin/items/{mock_sku}")
    assert res2.status_code == 404


def test_similar_items_excludes_itself(client):
    res = client.get("/api/v1/items")
    sku = res.json()["items"][0]["sku"]
    res2 = client.get(f"/api/v1/items/{sku}/similar?k=5")
    assert res2.status_code == 200
    skus = [it["sku"] for it in res2.json()["items"]]
    assert sku not in skus



# ---------------------------------------------------------------------------------------------
# Phần mới: đồng bộ tính năng của bản front-end 02 (tìm theo tên, sắp xếp, phân trang, đơn
# hàng, tra cứu đơn, quản trị đơn, nhận tin).

def _order_body(phone="0912 345 678", items=None, **customer):
    return {
        "customer": {"name": "Nguyễn Văn A", "phone": phone, "address": "12 Phố Huế, Hà Nội", **customer},
        "payment": "cod",
        "items": items or [{"sku": "MOCK-001", "size": "M", "qty": 2}, {"sku": "MOCK-011", "size": "L", "qty": 1}],
    }


def test_list_items_text_search_without_accents(client):
    res = client.get("/api/v1/items", params={"q": "ao khoac"})
    body = res.json()
    assert res.status_code == 200
    assert body["total"] == 5
    assert all(it["category"] == "jacket" for it in body["items"])
    same = client.get("/api/v1/items", params={"q": "ÁO KHOÁC"}).json()
    assert [it["sku"] for it in same["items"]] == [it["sku"] for it in body["items"]]
    assert client.get("/api/v1/items", params={"q": "vay soc"}).json()["total"] == 1  # mọi từ phải khớp
    assert client.get("/api/v1/items", params={"q": "mock-003"}).json()["items"][0]["sku"] == "MOCK-003"


def test_list_items_sort_and_paging(client):
    asc = client.get("/api/v1/items", params={"sort": "price-asc"}).json()["items"]
    prices = [it["price"] for it in asc]
    assert prices == sorted(prices)
    page1 = client.get("/api/v1/items", params={"limit": 10, "offset": 0}).json()
    page3 = client.get("/api/v1/items", params={"limit": 10, "offset": 20}).json()
    assert page1["total"] == page3["total"] >= 25
    assert len(page1["items"]) == 10 and len(page3["items"]) == page3["total"] - 20
    assert not {it["sku"] for it in page1["items"]} & {it["sku"] for it in page3["items"]}
    # cách sắp xếp lạ -> mặc định, không lỗi
    assert client.get("/api/v1/items", params={"sort": "constructor"}).status_code == 200


def test_list_items_newest_puts_recent_admin_items_first(client):
    skus = ("TEST-NEW-1", "TEST-NEW-2")
    try:
        for sku in skus:
            res = client.post(
                "/api/v1/admin/items",
                data={"sku": sku, "name": f"Áo {sku}", "category": "tee", "price": "100000"},
                files={"file": ("t.png", _png_bytes(), "image/png")},
            )
            assert res.status_code == 200
        body = client.get("/api/v1/items", params={"sort": "newest", "limit": 3}).json()
        assert [it["sku"] for it in body["items"][:2]] == ["TEST-NEW-2", "TEST-NEW-1"]  # mới nhất trước
        assert body["items"][2]["source"] == "mock"  # dữ liệu mẫu đứng sau
        # cập nhật lại SKU cũ không làm nó thành "mới" (giữ created_at lần đầu)
        client.post(
            "/api/v1/admin/items",
            data={"sku": "TEST-NEW-1", "name": "Áo sửa giá", "category": "tee", "price": "90000"},
            files={"file": ("t.png", _png_bytes(), "image/png")},
        )
        again = client.get("/api/v1/items", params={"sort": "newest", "limit": 2}).json()["items"]
        assert [it["sku"] for it in again] == ["TEST-NEW-2", "TEST-NEW-1"]
    finally:
        for sku in skus:
            client.delete(f"/api/v1/admin/items/{sku}")


def test_create_order_retries_when_two_orders_pick_the_same_id(client, monkeypatch):
    # Giả lập hai đơn đặt cùng lúc: lần sinh mã đầu tiên trả về đúng mã của một đơn đã có
    # (bỏ qua bước kiểm tra exists), router phải sinh mã khác thay vì báo lỗi 500.
    from app.routers import orders as orders_router

    body = {
        "customer": {"name": "An", "phone": "0912345678", "email": "", "address": "1 Tràng Tiền, Hà Nội", "note": ""},
        "payment": "cod",
        "items": [{"sku": "MOCK-001", "size": "M", "qty": 1}],
    }
    first = client.post("/api/v1/orders", json=body).json()["id"]
    real = orders_router.make_order_id
    ids = iter([first])
    monkeypatch.setattr(orders_router, "make_order_id", lambda exists: next(ids, None) or real(exists))
    res = client.post("/api/v1/orders", json=body)
    assert res.status_code == 201
    assert res.json()["id"] != first


def test_list_items_by_sku_list_for_cart(client):
    res = client.get("/api/v1/items", params={"skus": "MOCK-001,MOCK-011,KHONG-CO"})
    assert sorted(it["sku"] for it in res.json()["items"]) == ["MOCK-001", "MOCK-011"]
    too_many = ",".join(f"S{i}" for i in range(101))
    assert client.get("/api/v1/items", params={"skus": too_many}).status_code == 400


def test_search_by_image_with_keyword_and_price_sort_keeps_rank(client):
    res = client.post(
        "/api/v1/search/image",
        files={"file": ("q.png", _png_bytes((198, 45, 58)), "image/png")},
        data={"top_k": "5", "q": "vay", "sort": "price-asc"},
    )
    items = res.json()["items"]
    assert res.status_code == 200
    assert items and all(it["category"] == "dress" for it in items)
    assert [it["price"] for it in items] == sorted(it["price"] for it in items)
    assert sorted(it["rank"] for it in items) == list(range(1, len(items) + 1))
    by_rank = sorted(items, key=lambda it: it["rank"])
    assert [it["score"] for it in by_rank] == sorted((it["score"] for it in items), reverse=True)


def test_create_order_recomputes_prices_on_server(client):
    res = client.post("/api/v1/orders", json=_order_body())
    assert res.status_code == 201
    order = res.json()
    assert order["status"] == "new" and order["history"][0]["status"] == "new"
    assert order["id"].startswith("DH-")
    mock1 = client.get("/api/v1/items/MOCK-001").json()
    mock11 = client.get("/api/v1/items/MOCK-011").json()
    assert order["subtotal"] == int(mock1["price"]) * 2 + int(mock11["price"])
    assert order["total"] == order["subtotal"] + order["shipping"]
    assert {(it["sku"], it["size"], it["qty"]) for it in order["items"]} == {("MOCK-001", "M", 2), ("MOCK-011", "L", 1)}


def test_create_order_ignores_client_price_and_rejects_bad_input(client):
    sneaky = _order_body(items=[{"sku": "MOCK-001", "size": "M", "qty": 1, "price": 1}])
    assert client.post("/api/v1/orders", json=sneaky).json()["subtotal"] > 1
    cases = [
        (_order_body(phone="123"), "Số điện thoại"),
        (_order_body(name="A"), "họ tên"),
        (_order_body(email="sai"), "Email"),
        (_order_body(items=[{"sku": "MOCK-001", "size": "", "qty": 1}]), "size"),
        (_order_body(items=[{"sku": "MOCK-001", "size": "M", "qty": 0}]), "Số lượng"),
        (_order_body(items=[{"sku": "KHONG-CO", "size": "M", "qty": 1}]), "không còn bán"),
        ({**_order_body(), "items": []}, "Giỏ hàng trống"),
        ({**_order_body(), "payment": "bitcoin"}, "thanh toán"),
    ]
    for body, expected in cases:
        res = client.post("/api/v1/orders", json=body)
        assert res.status_code == 400, body
        assert expected in res.json()["detail"], res.json()


def test_lookup_requires_matching_code_and_phone(client):
    order = client.post("/api/v1/orders", json=_order_body(phone="+84 912 345 678")).json()
    ok = client.post("/api/v1/orders/lookup", json={"code": f" {order['id'].lower()} ", "phone": "0912.345.678"})
    assert ok.status_code == 200 and ok.json()["id"] == order["id"]
    wrong_phone = client.post("/api/v1/orders/lookup", json={"code": order["id"], "phone": "0999999999"})
    wrong_code = client.post("/api/v1/orders/lookup", json={"code": "DH-000000-0000", "phone": "0912345678"})
    assert wrong_phone.status_code == wrong_code.status_code == 404
    assert wrong_phone.json() == wrong_code.json()  # cùng một thông báo, không lộ mã đơn có tồn tại


def test_lookup_locks_phone_after_too_many_wrong_codes(client):
    from app.core.rate_limit import FailureLimiter
    from app.deps import get_lookup_guard

    guard = FailureLimiter(max_failures=3, window_seconds=60)
    app.dependency_overrides[get_lookup_guard] = lambda: guard
    try:
        order = client.post("/api/v1/orders", json=_order_body(phone="0987654321")).json()
        ok = {"code": order["id"], "phone": "0987 654 321"}
        for i in range(3):  # dò mã đơn với số điện thoại đã biết
            assert client.post("/api/v1/orders/lookup", json={"code": f"DH-000000-000{i}", "phone": "0987654321"}).status_code == 404
        locked = client.post("/api/v1/orders/lookup", json=ok)
        assert locked.status_code == 429 and "quá nhiều lần" in locked.json()["detail"]  # kể cả mã đúng
        # Số khác không bị ảnh hưởng; số sai định dạng không được đếm (không thể khớp đơn nào)
        assert client.post("/api/v1/orders/lookup", json={"code": "DH-1", "phone": "0912345678"}).status_code == 404
        assert client.post("/api/v1/orders/lookup", json={"code": "DH-1", "phone": "abc"}).status_code == 404
        assert len(guard) == 2
        # Trường quá dài bị từ chối trước khi xử lý
        assert client.post("/api/v1/orders/lookup", json={"code": "x" * 41, "phone": "0912345678"}).status_code == 422
    finally:
        app.dependency_overrides.pop(get_lookup_guard, None)


def test_admin_order_status_flow(client):
    order = client.post("/api/v1/orders", json=_order_body()).json()
    path = f"/api/v1/admin/orders/{order['id']}"
    assert client.patch(path, json={"status": "done"}).status_code == 409  # Mới -> Hoàn tất: sai luồng
    assert client.patch(path, json={"status": "lạ"}).status_code == 400
    assert client.patch(path, json={"status": "shipping"}).json()["status"] == "shipping"
    done = client.patch(path, json={"status": "done"}).json()
    assert [h["status"] for h in done["history"]] == ["new", "shipping", "done"]
    assert client.patch(path, json={"status": "cancelled"}).status_code == 409  # trạng thái cuối
    assert client.patch("/api/v1/admin/orders/DH-000000-0000", json={"status": "shipping"}).status_code == 404


def test_admin_list_orders_counts_and_revenue(client):
    a = client.post("/api/v1/orders", json=_order_body()).json()
    b = client.post("/api/v1/orders", json=_order_body()).json()
    client.patch(f"/api/v1/admin/orders/{b['id']}", json={"status": "cancelled"})
    data = client.get("/api/v1/admin/orders").json()
    assert data["total"] == sum(data["counts"].values())
    assert data["revenue"] == sum(o["total"] for o in data["orders"] if o["status"] != "cancelled")
    cancelled = client.get("/api/v1/admin/orders", params={"status": "cancelled"}).json()["orders"]
    assert b["id"] in [o["id"] for o in cancelled] and a["id"] not in [o["id"] for o in cancelled]
    assert client.get("/api/v1/admin/orders", params={"status": "lạ"}).status_code == 400
    assert client.delete(f"/api/v1/admin/orders/{a['id']}").json() == {"deleted": True, "id": a["id"]}
    assert client.delete(f"/api/v1/admin/orders/{a['id']}").status_code == 404


def test_newsletter_subscribe_and_duplicate(client):
    first = client.post("/api/v1/newsletter", json={"email": "  Ban@Example.com "})
    assert first.status_code == 201 and first.json() == {"status": "subscribed", "email": "ban@example.com"}
    again = client.post("/api/v1/newsletter", json={"email": "ban@example.COM"})
    assert again.status_code == 200 and again.json()["status"] == "already"
    assert client.post("/api/v1/newsletter", json={"email": "sai"}).status_code == 400


def test_admin_upsert_validates_category_name_and_price(client):
    def post(**data):
        form = {"sku": "TEST-VAL", "name": "Ten", "category": "tee", "price": "1000", **data}
        return client.post("/api/v1/admin/items", data=form, files={"file": ("t.png", _png_bytes(), "image/png")})

    assert post(category="xyz").status_code == 400
    assert post(name="x" * 81).status_code == 400
    assert post(price="nan").status_code == 400
    assert post(price="inf").status_code == 400
    assert "số nguyên" in post(price="199999.5").json()["detail"]
    assert post(price="1e12").status_code == 400
    ok = post()
    assert ok.json()["price"] == 1000
    assert ok.status_code == 200 and ok.json()["created_at"]
    again = post(name="Ten moi")
    assert again.json()["created_at"] == ok.json()["created_at"]  # cập nhật giữ thời điểm thêm lần đầu
    client.delete("/api/v1/admin/items/TEST-VAL")


def test_admin_requires_login(client):
    anon = {"Authorization": ""}
    assert client.get("/api/v1/admin/orders", headers=anon).status_code == 401
    assert client.delete("/api/v1/admin/items/MOCK-001", headers=anon).status_code == 401
    form = {"sku": "TEST-ANON", "name": "x", "category": "tee", "price": "1000"}
    files = {"file": ("t.png", _png_bytes(), "image/png")}
    assert client.post("/api/v1/admin/items", data=form, files=files, headers=anon).status_code == 401
    assert client.get("/api/v1/items/TEST-ANON").status_code == 404  # không ghi gì
    forged = {"Authorization": "Bearer 9999999999.abc"}  # tự sửa hạn dùng, chữ ký sai
    assert client.get("/api/v1/admin/me", headers=forged).status_code == 401
    assert client.get("/api/v1/admin/me").status_code == 200
    # Khách vẫn dùng được các endpoint công khai
    assert client.get("/api/v1/items", headers=anon).status_code == 200


def test_admin_login_wrong_password_and_lockout(client):
    from app.core.rate_limit import FailureLimiter
    from app.deps import get_login_guard

    guard = FailureLimiter(max_failures=2, window_seconds=60)
    app.dependency_overrides[get_login_guard] = lambda: guard
    try:
        bad = client.post("/api/v1/admin/login", json={"password": "sai"})
        assert bad.status_code == 401 and "không đúng" in bad.json()["detail"]
        client.post("/api/v1/admin/login", json={"password": "sai nữa"})
        locked = client.post("/api/v1/admin/login", json={"password": "stylelens-admin"})
        assert locked.status_code == 429  # khóa cả khi đã đoán đúng
    finally:
        app.dependency_overrides.pop(get_login_guard, None)
    ok = client.post("/api/v1/admin/login", json={"password": "stylelens-admin"}).json()
    assert ok["token"] and ok["expires_at"] > 0


def test_outfit_pairs_other_categories_with_reasons(client):
    res = client.get("/api/v1/items/MOCK-004/outfit")  # áo thun kẻ sọc
    assert res.status_code == 200
    groups = res.json()["groups"]
    assert [g["category"] for g in groups] == ["pants", "jacket"]
    assert groups[0]["label"] == "Quần"
    for g in groups:
        assert 1 <= len(g["items"]) <= 3
        assert all(it["category"] == g["category"] and it["reason"] for it in g["items"])
        assert [it["match"] for it in g["items"]] == sorted((it["match"] for it in g["items"]), reverse=True)
    # áo có họa tiết -> gợi ý đầu tiên là món trơn
    assert "Trơn" in groups[0]["items"][0]["reason"]
    assert client.get("/api/v1/items/MOCK-011/outfit").json()["groups"][0]["category"] == "jacket"  # váy -> áo khoác
    assert client.get("/api/v1/items/KHONG-CO/outfit").status_code == 404


def test_quote_and_order_with_coupon(client):
    items = [{"sku": "MOCK-011", "size": "M", "qty": 1}]  # váy 359.000 ₫
    q = client.post("/api/v1/orders/quote", json={"items": items, "coupon": "giam10"}).json()
    assert (q["subtotal"], q["shipping"], q["discount"], q["total"], q["coupon"]) == (359000, 30000, 35900, 353100, "GIAM10")
    bad = client.post("/api/v1/orders/quote", json={"items": items, "coupon": "CHAO50K"})
    assert bad.status_code == 400 and "400.000" in bad.json()["detail"]
    order = client.post("/api/v1/orders", json={**_order_body(items=items), "coupon": "GIAM10"}).json()
    assert (order["discount"], order["total"], order["coupon"]) == (35900, 353100, "GIAM10")
    found = client.post("/api/v1/orders/lookup", json={"code": order["id"], "phone": "0912345678"}).json()
    assert found["discount"] == 35900
    assert client.post("/api/v1/orders", json={**_order_body(items=items), "coupon": "KHONGCO"}).status_code == 400
