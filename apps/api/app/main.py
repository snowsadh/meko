from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.activity.router import router as activity_router
from app.agent.router import router as agent_router
from app.auth.router import router as auth_router
from app.channel_assignments.router import router as channel_router
from app.core.config import settings
from app.core.database import engine
from app.core.meko import MekoError
from app.documents.router import router as document_router
from app.employees.router import router as employee_router
from app.health.router import router as health_router
from app.memory.router import router as memory_router
from app.memory_sources.router import router as source_router
from app.mcp.router import router as mcp_router
from app.organizations.router import router as organization_router
from app.gateway.slack_oauth import router as slack_oauth_router
from app.gateway.slack_bot import SlackGateway
from app.gateway.router import router as slack_routing_router


@asynccontextmanager
async def lifespan(_app):
    gateway = SlackGateway()
    if settings.gateway_enabled:
        await gateway.start()
    yield
    await gateway.stop()
    await engine.dispose()


app = FastAPI(title="OpenHuman API", version="0.2.0", lifespan=lifespan)
origins = list(settings.cors_origins)
parsed = urlparse(settings.frontend_url)
origin = f"{parsed.scheme}://{parsed.netloc}"
if origin not in origins:
    origins.append(origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(MekoError)
async def meko_failure(request: Request, error: MekoError):
    return JSONResponse(status_code=502, content={"detail": str(error)})


for router in (
    health_router,
    activity_router,
    auth_router,
    organization_router,
    employee_router,
    channel_router,
    agent_router,
    memory_router,
    source_router,
    document_router,
    slack_oauth_router,
    mcp_router,
):
    app.include_router(router)

app.include_router(slack_routing_router)
