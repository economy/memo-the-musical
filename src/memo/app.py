from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from memo.adapters.realtime.agents_sideband import AgentsSDKSidebandAttacher
from memo.adapters.realtime.openai_call_client import OpenAIRealtimeCallClient
from memo.adapters.storage.sqlite_project_repository import SQLiteProjectRepository
from memo.config import Settings
from memo.domain.message_dna.models import MessagePreset, Project
from memo.domain.realtime.ports import RealtimeCallPort
from memo.routes.realtime import build_realtime_router
from memo.services.message_dna_service import MessageDNAService
from memo.services.realtime_agent import RealtimeAgentFactory
from memo.services.sideband_registry import SidebandSessionRegistry

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def create_app(
    call_client: RealtimeCallPort,
    registry: SidebandSessionRegistry,
    shutdown: Callable[[], Awaitable[None]] | None = None,
) -> FastAPI:
    """Create the application with externally supplied I/O dependencies."""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        yield
        await registry.close_all()
        if shutdown is not None:
            await shutdown()

    app = FastAPI(title="Memo: The Musical", lifespan=lifespan)
    templates = Jinja2Templates(directory=PROJECT_ROOT / "templates")
    app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "static"), name="static")
    app.include_router(build_realtime_router(call_client, registry))

    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request=request, name="index.html")

    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.add_api_route("/", index, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/health", health, methods=["GET"])
    return app


def create_default_app() -> FastAPI:
    """Wire local adapters for the one-command development server."""
    settings = Settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    repository = SQLiteProjectRepository(settings.database_path)
    service = MessageDNAService(repository)
    if service.get_project("transport-spike") is None:
        project = Project.new(title="Transport spike", preset=MessagePreset.GENERAL)
        service.create_project(project.model_copy(update={"id": "transport-spike"}))

    http_client = httpx.AsyncClient(base_url="https://api.openai.com", timeout=30)
    call_client = OpenAIRealtimeCallClient(
        http_client,
        api_key=settings.openai_api_key.get_secret_value(),
    )
    attacher = AgentsSDKSidebandAttacher(
        RealtimeAgentFactory(service),
        api_key=settings.openai_api_key.get_secret_value(),
    )
    registry = SidebandSessionRegistry(attacher)

    async def shutdown() -> None:
        await http_client.aclose()
        repository.close()

    return create_app(call_client, registry, shutdown)
