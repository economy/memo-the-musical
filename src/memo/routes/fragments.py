from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from memo.domain.message_dna.readiness import assess_readiness
from memo.services.message_dna_service import MessageDNAService


def build_fragments_router(
    message_service: MessageDNAService,
    templates: Jinja2Templates,
) -> APIRouter:
    """Build HTMX fragment routes for server-authoritative Message DNA panels."""
    router = APIRouter(prefix="/fragments", tags=["fragments"])

    async def message_dna_fragment(request: Request, project_id: str) -> HTMLResponse:
        project = message_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        readiness = assess_readiness(project.message_dna)
        return templates.TemplateResponse(
            request=request,
            name="fragments/message_dna.html",
            context={
                "project": project,
                "readiness": readiness,
                "is_replay": project_id.endswith("-replay"),
            },
        )

    router.add_api_route(
        "/dna/{project_id}",
        message_dna_fragment,
        methods=["GET"],
        response_class=HTMLResponse,
    )
    return router
