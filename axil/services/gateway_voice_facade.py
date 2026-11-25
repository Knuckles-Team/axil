"""CONCEPT:MERISTEM-ECO.mcp.webui-voice-transcription-delegation
Voice dictation facade for the desktop gateway client.

Transcribes one bounded audio clip via the WebUI's voice route — the same
route the web dictation control calls (``POST /api/enhanced/voice/transcribe``
on this gateway app, delegated server-side through
``meristem.server.webui_voice_delegation`` to the governed
``audio-transcriber-mcp`` sidecar). No separate backend for the desktop
client.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from axil.services.gateway_client import GatewayClient

logger = logging.getLogger("axil.gateway")


class VoiceFacade:
    """Facade method over the gateway's voice transcription route."""

    def __init__(self, client: GatewayClient) -> None:
        self._client = client

    async def transcribe_voice(
        self, audio_bytes: bytes, *, content_type: str = "audio/wav"
    ) -> dict:
        """Transcribe one bounded audio clip via the WebUI's voice route.

        Returns ``{"text": "..."}`` on success. On failure, graceful-offline
        like the rest of the facade: ``{"error": "..."}`` for a genuine
        error, or ``{"error": "...", "unavailable": True}`` specifically
        when the route answers 404/501 (no ``transcribe_voice`` workspace
        helper registered server-side) -- distinct so a caller can tell
        "not enabled here" from "something broke" instead of collapsing
        both into one generic failure message.
        """
        try:
            if len(audio_bytes) > 25 * 1024 * 1024:
                raise ValueError("Audio clip exceeds the transcription size limit")
            files = {"file": ("clip.wav", audio_bytes, content_type)}
            async with self._client._direct_http.stream(
                "POST",
                "/api/enhanced/voice/transcribe",
                files=files,
                follow_redirects=False,
            ) as response:
                if response.status_code in (404, 501):
                    return {
                        "error": "voice transcription is not enabled on this server",
                        "unavailable": True,
                    }
                response.raise_for_status()
                body = await self._client._bounded_body(response)
            value = json.loads(body)
            if not isinstance(value, dict):
                raise RuntimeError("Gateway returned an invalid envelope")
            return value
        except Exception as e:
            logger.warning(
                "Voice transcription failed: error_type=%s", type(e).__name__
            )
            return {"error": "voice transcription failed"}
