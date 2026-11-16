from contextlib import aclosing

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status

from app.db import SessionLocal
from app.deps import user_from_token
from app.live import broadcaster, session_channel
from app.services import get_visible_session

router = APIRouter(tags=["live"])


@router.websocket("/ws/sessions/{session_id}")
async def live_session(websocket: WebSocket, session_id: int, token: str = "") -> None:
    """Stream a running session to the trainer's browser.

    Browsers cannot set an Authorization header on a WebSocket, so the JWT comes
    as a query parameter. We check it (and tenant access) before accepting.
    """
    async with SessionLocal() as db:
        user = await user_from_token(db, token)
        try:
            if user is None:
                raise HTTPException(status.HTTP_401_UNAUTHORIZED)
            await get_visible_session(db, session_id, user)
        except HTTPException:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await websocket.accept()
    try:
        async with aclosing(broadcaster.subscribe(session_channel(session_id))) as messages:
            async for message in messages:
                await websocket.send_json(message)
                if message["type"] == "finished":
                    break
        await websocket.close()
    except WebSocketDisconnect:
        pass  # trainer closed the tab
