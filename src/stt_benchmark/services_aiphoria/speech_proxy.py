"""Pipecat STT service for speech-proxy (gRPC v2).

Speech-proxy exposes the same platform_proto v2 gRPC API as asr-backend-service.
The proxy signals end-of-turn via `is_final=True` only; `eou_reason` is always
0 (UNSPECIFIED). We finalize on the FIRST is_final with non-empty text,
eou_reason-agnostic.

TTFS instrumentation is unchanged: Pipecat base STTService TTFB, started on the
shared local Silero VADUserStoppedSpeaking - 0.2s, stopped when we push the one
finalized TranscriptionFrame -> identical clock/anchor as every other setup.
"""

from __future__ import annotations

from pipecat.frames.frames import InterimTranscriptionFrame
from pipecat.transcriptions.language import Language
from pipecat.utils.time import time_now_iso8601

from stt_benchmark.services_aiphoria.asr_backend import AsrBackendService


class SpeechProxyService(AsrBackendService):
    """ASR via speech-proxy (gRPC v2)."""

    def __init__(
        self,
        *,
        url: str = "speech-proxy.main.stage.aiphoria.pro:443",
        use_ssl: bool = True,
        recognizer: str = "asr_deepgram_en_nova3",
        **kwargs,
    ) -> None:
        super().__init__(
            url=url,
            use_ssl=use_ssl,
            language=recognizer,
            mode="native_eou",
            **kwargs,
        )

    async def _on_reply(self, resp):
        text = (getattr(resp, "raw_text", "") or "").strip()
        is_final = bool(getattr(resp, "is_final", False))
        if is_final and text:
            await self._push_final(text)
        elif text:
            await self.push_frame(
                InterimTranscriptionFrame(
                    text, self._user_id, time_now_iso8601(), Language.EN
                )
            )
