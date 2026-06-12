#!/usr/bin/env bash
# Setup 4c launcher -- run name: dgvs_proxy_vad_v2_100
# Speech-proxy with recognizer asr_deepgram_en_nova3_vad_v2 (faster VAD endpointing).
set -u
cd /home/mle/asr-junk/danil-andreev/tasks/deepgram_vs_ours_latency/stt-benchmark
LOG=/home/mle/asr-junk/danil-andreev/tasks/deepgram_vs_ours_latency
ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(ts)] START dgvs_proxy_vad_v2_100 (speech_proxy + vad_v2 recognizer, 100 samples)"
uv run stt-benchmark run --services speech_proxy \
  --recognizer asr_deepgram_en_nova3_vad_v2 \
  --limit 100 --no-skip-existing \
  > "$LOG/run_deepgram_proxy_vad_v2_100.log" 2>&1
rc=$?
echo "[$(ts)] DONE dgvs_proxy_vad_v2_100 rc=$rc"
touch "$LOG/.proxy_vad_v2_run_done"
