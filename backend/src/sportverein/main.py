from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sportverein.api.router import api_router

app = FastAPI(title="Sportverein API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
