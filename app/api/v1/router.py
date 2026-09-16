from fastapi import APIRouter

from app.api.v1.endpoints import redemptions, system

api_v1_router = APIRouter()

# Register endpoints under /api/v1
api_v1_router.include_router(system.router, tags=["System Health & Operating Gate"])
api_v1_router.include_router(redemptions.router, tags=["Autonomous Redemption"])
