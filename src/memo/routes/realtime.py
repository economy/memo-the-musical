from fastapi import APIRouter, HTTPException, Request, Response, status

from memo.adapters.realtime.openai_call_client import RealtimeUpstreamError
from memo.domain.realtime.constants import CALL_ID_HEADER, MAX_SDP_BYTES, SDP_MEDIA_TYPE
from memo.domain.realtime.ports import RealtimeCallPort
from memo.services.message_dna_service import MessageDNAService
from memo.services.sideband_registry import (
    SidebandRegistryError,
    SidebandSessionRegistry,
    SidebandTimeoutError,
)


def build_realtime_router(
    call_client: RealtimeCallPort,
    registry: SidebandSessionRegistry,
    message_service: MessageDNAService,
) -> APIRouter:
    """Build the realtime router with explicit transport dependencies."""
    router = APIRouter(prefix="/api/realtime", tags=["realtime"])

    async def create_realtime_call(request: Request, project_id: str) -> Response:
        if message_service.get_project(project_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        media_type = request.headers.get("content-type", "").partition(";")[0].strip().casefold()
        if media_type != SDP_MEDIA_TYPE:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Expected application/sdp",
            )
        offer_sdp = await _read_sdp(request)
        try:
            call = await call_client.create_call(offer_sdp)
            await registry.start(call.call_id, project_id)
        except RealtimeUpstreamError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(error),
            ) from error
        except SidebandTimeoutError as error:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Realtime sideband attachment timed out",
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
            headers={CALL_ID_HEADER: call.call_id},
        )

    async def delete_realtime_call(call_id: str) -> Response:
        await registry.stop(call_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    router.add_api_route(
        "/calls",
        create_realtime_call,
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
    )
    router.add_api_route(
        "/calls/{call_id}",
        delete_realtime_call,
        methods=["DELETE"],
        status_code=status.HTTP_204_NO_CONTENT,
    )
    return router


async def _read_sdp(request: Request) -> str:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_SDP_BYTES:
                raise _sdp_too_large()
        except ValueError:
            pass
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_SDP_BYTES:
            raise _sdp_too_large()
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SDP offer must be UTF-8",
        ) from error


def _sdp_too_large() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail=f"SDP offer exceeds {MAX_SDP_BYTES} bytes",
    )
