"""Main API router that includes all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from sportverein.api.dashboard import router as dashboard_router
from sportverein.api.mitglieder import router as mitglieder_router
from sportverein.auth.router import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(mitglieder_router)
api_router.include_router(dashboard_router)
