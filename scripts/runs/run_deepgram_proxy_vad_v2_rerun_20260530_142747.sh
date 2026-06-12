#!/usr/bin/env bash
# Rerun speech_proxy with asr_deepgram_en_nova3_vad_v2 recognizer.
set -u
cd /home/mle/asr-junk/danil-andreev/tasks/deepgram_vs_ours_latency/stt-benchmark
TASK=/home/mle/asr-junk/danil-andreev/tasks/deepgram_vs_ours_latency
RUN_NAME=dgvs_proxy_vad_v2_rerun_20260530_142747_100
LOG="$TASK/run_deepgram_proxy_vad_v2_rerun_20260530_142747_100.log"
ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(ts)] START $RUN_NAME (speech_proxy + vad_v2, 100 samples)"
uv run stt-benchmark run --services speech_proxy \
  --recognizer asr_deepgram_en_nova3_vad_v2 \
  --limit 100 --no-skip-existing \
  > "$LOG" 2>&1
rc=$?
echo "[$(ts)] DONE $RUN_NAME rc=$rc"
touch "$TASK/.proxy_vad_v2_rerun_done"
