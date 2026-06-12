#!/usr/bin/env bash
# Setup 4b launcher -- run name: dgvs_proxy_v2_100
# Same speech_proxy path, re-measured after reported server-side fix.
set -u
cd /home/mle/asr-junk/danil-andreev/tasks/deepgram_vs_ours_latency/stt-benchmark
LOG=/home/mle/asr-junk/danil-andreev/tasks/deepgram_vs_ours_latency
ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(ts)] START dgvs_proxy_v2_100 (speech_proxy, 100 samples)"
uv run stt-benchmark run --services speech_proxy --limit 100 --no-skip-existing \
  > "$LOG/run_deepgram_proxy_v2_100.log" 2>&1
rc=$?
echo "[$(ts)] DONE dgvs_proxy_v2_100 rc=$rc"
touch "$LOG/.proxy_v2_run_done"
