"""Observer that prints a stderr timeline for pipeline debug runs."""

from __future__ import annotations

import sys
import time

from pipecat.frames.frames import (
    InputAudioRawFrame,
    InterimTranscriptionFrame,
    MetricsFrame,
    TranscriptionFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from pipecat.metrics.metrics import TTFBMetricsData
from pipecat.observers.base_observer import BaseObserver, FramePushed
from pipecat.processors.audio.vad_processor import VADProcessor
from pipecat.services.stt_service import STTService

from stt_benchmark.pipeline.synthetic_transport import SyntheticInputTransport


class DebugTraceObserver(BaseObserver):
    """Print pipeline events to stderr with wall-clock offset from first audio chunk."""

    def __init__(self) -> None:
        super().__init__()
        self._anchor: float | None = None
        self._chunk_count = 0

    def log_start(
        self,
        *,
        service: str,
        chunk_ms: int,
        vad_stop_secs: float,
        audio_bytes: int,
        duration_seconds: float,
        source_label: str,
    ) -> None:
        """Log run configuration before the pipeline starts."""
        self._anchor = None
        self._chunk_count = 0
        self._emit(
            "start",
            f"service={service} source={source_label} chunk_ms={chunk_ms} "
            f"vad_stop_secs={vad_stop_secs} audio_bytes={audio_bytes} "
            f"duration_s={duration_seconds:.2f}",
        )

    def log_done(
        self,
        *,
        transcription: str | None,
        ttfb_seconds: float | None,
        error: str | None = None,
    ) -> None:
        """Log final summary after the pipeline completes."""
        if error:
            self._emit("done", f"error={error}")
            return
        ttfb_text = f"{ttfb_seconds:.3f}s" if ttfb_seconds is not None else "N/A"
        text = transcription or ""
        self._emit(
            "done",
            f"ttfb={ttfb_text} transcription={text!r}",
        )

    def log_grpc_reply(
        self,
        raw_text: str,
        is_final: bool,
        eou_reason: int,
        processed_ms: int,
    ) -> None:
        """Log a raw gRPC ASR reply, including empty hypotheses."""
        text = raw_text.strip()
        self._emit(
            "asr",
            f"reply is_final={is_final} eou={eou_reason} processed_ms={processed_ms} "
            f"text_len={len(text)} text={text!r}",
        )

    def _offset_ms(self) -> float:
        if self._anchor is None:
            return 0.0
        return (time.perf_counter() - self._anchor) * 1000

    def _emit(self, tag: str, message: str) -> None:
        offset_ms = self._offset_ms()
        if self._anchor is not None:
            print(f"[{tag}] offset_ms={offset_ms:.1f} {message}", file=sys.stderr, flush=True)
        else:
            print(f"[{tag}] {message}", file=sys.stderr, flush=True)

    async def on_push_frame(self, data: FramePushed) -> None:
        frame = data.frame

        if isinstance(data.source, SyntheticInputTransport) and isinstance(
            frame, InputAudioRawFrame
        ):
            if self._anchor is None:
                self._anchor = time.perf_counter()
            self._chunk_count += 1
            self._emit(
                "chunk",
                f"chunk #{self._chunk_count} bytes={len(frame.audio)}",
            )
            return

        if isinstance(data.source, VADProcessor):
            if isinstance(frame, VADUserStartedSpeakingFrame):
                self._emit("vad", "started")
                return
            if isinstance(frame, VADUserStoppedSpeakingFrame):
                stop_secs = getattr(frame, "stop_secs", 0.0)
                speech_end_ms = self._offset_ms() - (stop_secs * 1000)
                self._emit(
                    "vad",
                    f"stopped stop_secs={stop_secs} speech_end_ms={speech_end_ms:.1f}",
                )
                return

        if not isinstance(data.source, STTService):
            return

        if isinstance(frame, InterimTranscriptionFrame):
            self._emit("asr", f"interim text={frame.text!r}")
            return

        if isinstance(frame, TranscriptionFrame):
            finalized = getattr(frame, "finalized", False)
            self._emit(
                "asr",
                f"final finalized={finalized} text={frame.text!r}",
            )
            return

        if isinstance(frame, MetricsFrame):
            for metrics_data in frame.data:
                if isinstance(metrics_data, TTFBMetricsData) and metrics_data.value != 0.0:
                    self._emit("ttfb", f"ttfb={metrics_data.value:.3f}s")
