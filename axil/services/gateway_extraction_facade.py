"""CONCEPT:MERISTEM-ECO.connector.git-task-resolver
Fact-extraction facade for the desktop gateway client.

Submits extraction jobs and consumes their SSE event streams over the
client's direct HTTP transport. Each event is forwarded to the caller's
progress callback as a JSON string so the Qt panel can render facts live
on the main thread; stream sizes and event counts are capped so a hostile
or misbehaving gateway cannot exhaust the desktop process.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from axil.services.gateway_envelope import (
    MAX_STREAM_EVENTS,
    MAX_STREAM_LINE_BYTES,
    SAFE_JOB_ID,
)

if TYPE_CHECKING:
    from axil.services.gateway_client import GatewayClient

logger = logging.getLogger("axil.gateway")


def validate_extraction_request(text: str, url: str, rounds: int) -> None:
    """Refuse an extraction request before it touches the network."""
    if len(text.encode("utf-8")) > 4 * 1024 * 1024 or len(url) > 8_192:
        raise ValueError("Extraction request exceeded its size limit")
    if not 1 <= int(rounds) <= 100:
        raise ValueError("Extraction rounds are outside the allowed range")


def check_extraction_stream_limits(event_count: int, line: str) -> None:
    """Enforce the per-stream event and line-size caps while consuming."""
    if event_count > MAX_STREAM_EVENTS:
        raise RuntimeError("Gateway event stream exceeded its limit")
    if len(line.encode("utf-8")) > MAX_STREAM_LINE_BYTES:
        raise RuntimeError("Gateway event exceeded its size limit")


def parse_extraction_event(payload: str) -> dict[str, Any] | None:
    """Parse one ``data:`` SSE payload, or None when it is not a JSON object."""
    try:
        ev = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return ev if isinstance(ev, dict) else None


class ExtractionFacade:
    """Facade methods over the gateway's fact-extraction routes."""

    def __init__(self, client: GatewayClient) -> None:
        self._client = client

    async def _consume_extraction_stream(self, job_id: str, progress_cb) -> int:
        """Stream one submitted job's SSE events, forwarding each ``data:``
        payload to ``progress_cb``. Returns the count of kept (non-duplicate)
        facts seen."""
        kept = 0
        event_count = 0
        async with self._client._direct_http.stream(
            "GET",
            f"/api/enhanced/extract/stream/{job_id}",
            follow_redirects=False,
        ) as stream:
            stream.raise_for_status()
            async for line in stream.aiter_lines():
                event_count += 1
                check_extraction_stream_limits(event_count, line)
                if not line.startswith("data: "):
                    continue
                payload = line[6:]
                ev = parse_extraction_event(payload)
                if ev is None:
                    continue
                if ev.get("type") == "fact" and not ev.get("is_duplicate"):
                    kept += 1
                if progress_cb:
                    progress_cb(payload)
                if ev.get("type") == "job_done":
                    break
        return kept

    async def submit_and_stream_extraction(
        self,
        *,
        text: str = "",
        url: str = "",
        rounds: int = 1,
        dedup: bool = True,
        progress_cb=None,
    ):
        """Submit a fact-extraction job and stream its events (MERISTEM-ECO.connector.git-task-resolver).

        Each event (round_start|fact|…|job_done) is forwarded to ``progress_cb``
        as a JSON string so the Qt panel can render facts live on the main thread.
        Returns a summary dict; graceful-offline like every facade method.
        """
        try:
            validate_extraction_request(text, url, rounds)
            sub = await self._client._json_request(
                "POST",
                "/api/enhanced/extract/submit",
                payload={
                    "text": text,
                    "url": url,
                    "rounds": int(rounds),
                    "dedup": bool(dedup),
                },
            )
            job_id = sub.get("job_id")
            if (
                sub.get("status") != "submitted"
                or not isinstance(job_id, str)
                or not SAFE_JOB_ID.fullmatch(job_id)
            ):
                return {"status": "unavailable", "message": "Request unavailable"}

            kept = await self._consume_extraction_stream(job_id, progress_cb)
            return {"status": "done", "job_id": job_id, "facts": kept}
        except Exception as e:
            logger.warning("Extraction stream failed: error_type=%s", type(e).__name__)
            return {"status": "error", "message": "Extraction stream failed"}

    async def fetch_extraction_jsonl(self, job_id: str) -> str:
        """Fetch a finished job's facts as JSONL text (upstream parity)."""
        try:
            if not SAFE_JOB_ID.fullmatch(str(job_id)):
                raise ValueError("Extraction job id is invalid")
            async with self._client._direct_http.stream(
                "GET",
                f"/api/enhanced/extract/jsonl/{job_id}",
                follow_redirects=False,
            ) as response:
                response.raise_for_status()
                body = await self._client._bounded_body(response)
            return body.decode("utf-8")
        except Exception as e:
            logger.warning("JSONL fetch failed: error_type=%s", type(e).__name__)
            return ""
