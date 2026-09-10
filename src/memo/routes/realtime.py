from fastapi import APIRouter, HTTPException, Request, Response, status

from memo.adapters.realtime.openai_call_client import RealtimeUpstreamError
from memo.domain.realtime.ports import RealtimeCallPort
from memo.services.sideband_registry import SidebandRegistryError, SidebandSessionRegistry

SDP_MEDIA_TYPE = "application/sdp"


def build_realtime_router(
    call_client: RealtimeCallPort,
    registry: SidebandSessionRegistry,
) -> APIRouter:
    """Build the realtime router with explicit transport dependencies."""
    router = APIRouter(prefix="/api/realtime", tags=["realtime"])

    async def create_realtime_call(request: Request, project_id: str) -> Response:
        if request.headers.get("content-type", "").split(";", 1)[0] != SDP_MEDIA_TYPE:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Expected application/sdp",
            )
        offer_sdp = (await request.body()).decode("utf-8")
        try:
            call = await call_client.create_call(offer_sdp)
            await registry.start(call.call_id, project_id)
        except RealtimeUpstreamError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(error),
            ) from error
        except SidebandRegistryError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Realtime sideband attachment failed",
            ) from error
        return Response(
            content=call.answer_sdp,
            media_type=SDP_MEDIA_TYPE,
            status_code=status.HTTP_201_CREATED,
        )

    router.add_api_route(
        "/calls",
        create_realtime_call,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
    )
    return router
