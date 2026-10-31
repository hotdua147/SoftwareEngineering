from fastapi import APIRouter, Depends

from app.config import settings
from app.core.embedding import ImageEncoder
from app.deps import get_encoder, get_store
from app.schemas import HealthResult
from app.store.base import VectorStore

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResult)
def health(store: VectorStore = Depends(get_store), encoder: ImageEncoder = Depends(get_encoder)) -> HealthResult:
    ok = store.health()
    return HealthResult(
        status="ok" if ok else "degraded", store_backend=settings.STORE_BACKEND, encoder=encoder.name, vector_dim=encoder.dim
    )
