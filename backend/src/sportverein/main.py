from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sportverein.api.router import api_router
from sportverein.mcp.server import mcp

app = FastAPI(title="Sportverein API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Mount the MCP server at /mcp
app.mount("/mcp", mcp.http_app())


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
