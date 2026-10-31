"""FR-05: thêm/cập nhật SKU. Mở rộng ngoài đặc tả gốc: xóa SKU do Admin thêm (để dọn dữ liệu
demo) — không cho xóa dữ liệu mẫu (seed) của hệ thống."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.core.catalog_data import image_to_data_url
from app.core.embedding import ImageEncoder
from app.core.encoder import load_image
from app.core.orders import now_iso
from app.core.validate import validate_category, validate_name, validate_price, validate_sku, validate_upload
from app.deps import get_encoder, get_store, require_admin
from app.schemas import DeleteResult, UpsertResult
from app.store.base import VectorStore
from app.upload_utils import read_capped

router = APIRouter(prefix="/api/v1/admin/items", tags=["admin"], dependencies=[Depends(require_admin)])

_THUMBNAIL_SIZE = (256, 256)


def _decode_and_encode(data: bytes, encoder: ImageEncoder):
    # Giải mã ảnh MỘT lần, dùng chung cho cả vector đặc trưng lẫn ảnh thu nhỏ hiển thị
    # (trước đây Image.open() được gọi lần hai riêng cho ảnh thu nhỏ — lãng phí vì phải
    # giải mã cùng một tệp hai lần).
    img = load_image(data)
    vector = encoder.encode_image(img)  # mã hóa từ ảnh GỐC, trước khi thu nhỏ để lưu hiển thị
    img.thumbnail(_THUMBNAIL_SIZE)
    return img, vector


def _save(store: VectorStore, sku: str, name: str, category: str, price: int, img, vector) -> tuple[dict, bool]:
    # Nhập trùng SKU (kể cả SKU mẫu) thì ghi đè — giống bản 02: Admin có thể thay ảnh vẽ của
    # sản phẩm mẫu bằng ảnh thật mà vẫn giữ mã SKU.
    existing = store.get(sku)
    payload = {
        "name": name,
        "category": category,
        "price": price,  # số nguyên (đồng), đã kiểm tra bằng validate_price
        "image": image_to_data_url(img),
        "source": "admin",
        # Giữ thời điểm thêm lần đầu khi cập nhật — dùng để xếp "Hàng mới về" (sort=newest).
        # Lấy tới micro giây để hai SKU thêm trong cùng một giây vẫn phân định được thứ tự.
        "created_at": (existing or {}).get("created_at") or now_iso(timespec="microseconds"),
    }
    return payload, store.upsert(sku, vector, payload)


@router.post("", response_model=UpsertResult)
async def upsert_item(
    sku: str = Form(...),
    name: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    file: UploadFile = File(...),
    store: VectorStore = Depends(get_store),
    encoder: ImageEncoder = Depends(get_encoder),
) -> UpsertResult:
    sku = sku.strip().upper()
    name = name.strip()

    err = validate_sku(sku) or validate_name(name) or validate_category(category) or validate_price(price)
    if err:
        raise HTTPException(status_code=400, detail=err)

    # Đọc theo đoạn, dừng sớm nếu vượt dung lượng cho phép (xem app/upload_utils.py).
    data = await read_capped(file, settings.MAX_FILE_BYTES)
    err = validate_upload(file.filename, file.content_type, len(data))
    if err:
        raise HTTPException(status_code=400, detail=err)

    try:
        # Giải mã + mã hóa ảnh tốn CPU: chạy trong threadpool để không chặn event loop (endpoint
        # là async vì phải `await` đọc tệp) — nếu không, mọi request khác phải chờ.
        img, vector = await run_in_threadpool(_decode_and_encode, data, encoder)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Không đọc được ảnh này. Hãy thử một tệp khác.") from e

    # Qdrant client là đồng bộ, tạo ảnh thu nhỏ PNG tốn CPU -> cũng chạy trong threadpool
    payload, updated = await run_in_threadpool(_save, store, sku, name, category, int(price), img, vector)
    return UpsertResult(sku=sku, updated=updated, **payload)


@router.delete("/{sku}", response_model=DeleteResult)
def delete_item(sku: str, store: VectorStore = Depends(get_store)) -> DeleteResult:
    item = store.get(sku)
    if item is None or item.get("source") != "admin":
        raise HTTPException(status_code=404, detail=f"Không tìm thấy SKU {sku} do Admin thêm.")
    store.delete(sku)
    return DeleteResult(deleted=True, sku=sku)
