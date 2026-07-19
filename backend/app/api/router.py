from fastapi import APIRouter

from app.api.routes.candidates import router as candidates_router
from app.api.routes.collection import router as collection_router
from app.api.routes.health import router as health_router
from app.api.routes.inbound import router as inbound_router
from app.api.routes.theses import router as theses_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(candidates_router)
api_router.include_router(collection_router)
api_router.include_router(theses_router)
api_router.include_router(inbound_router)
