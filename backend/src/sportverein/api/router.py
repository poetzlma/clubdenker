"""Main API router that includes all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from sportverein.api.agents import router as agents_router
from sportverein.api.audit import router as audit_router
from sportverein.api.chat import router as chat_router
from sportverein.api.dashboard import router as dashboard_router
from sportverein.api.finanzen import router as finanzen_router
from sportverein.api.mitglieder import router as mitglieder_router
from sportverein.api.setup import router as setup_router
from sportverein.api.dokumente import router as dokumente_router
from sportverein.api.training import router as training_router
from sportverein.auth.router import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(mitglieder_router)
api_router.include_router(dashboard_router)
api_router.include_router(finanzen_router)
api_router.include_router(agents_router)
api_router.include_router(chat_router)
api_router.include_router(audit_router)
api_router.include_router(setup_router)
api_router.include_router(training_router)
api_router.include_router(dokumente_router)
