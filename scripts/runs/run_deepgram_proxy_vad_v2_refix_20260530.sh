#!/usr/bin/env bash
# Re-measure speech_proxy with asr_deepgram_en_nova3_vad_v2 after refix.
set -u
cd /home/mle/asr-junk/danil-andreev/tasks/deepgram_vs_ours_latency/stt-benchmark
TASK=/home/mle/asr-junk/danil-andreev/tasks/deepgram_vs_ours_latency
ts() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(ts)] START dgvs_proxy_vad_v2_refix_100 (speech_proxy + vad_v2, 100 samples)"
uv run stt-benchmark run --services speech_proxy \
  --recognizer asr_deepgram_en_nova3_vad_v2 \
  --limit 100 --no-skip-existing \
  > "$TASK/run_deepgram_proxy_vad_v2_refix_100.log" 2>&1
rc=$?
echo "[$(ts)] DONE dgvs_proxy_vad_v2_refix_100 rc=$rc"
touch "$TASK/.proxy_vad_v2_refix_run_done"
