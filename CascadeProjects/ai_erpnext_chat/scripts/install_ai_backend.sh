#!/usr/bin/env bash
set -euo pipefail

# Skeleton installer for local llama.cpp llama-server
# NOTE: This is a placeholder. It echos steps to perform and sets up directories.

PORT=${1:-8081}
ROOT=/opt/erpnext-ai
BIN="$ROOT/bin"
MODELS="$ROOT/models"
LOGS="$ROOT/logs"
SERVICE="/etc/systemd/system/erpnext-gemma.service"
TEMPLATE_DIR="$(dirname "$0")/../deployment"

sudo mkdir -p "$BIN" "$MODELS" "$LOGS"

echo "[ai-installer] Checking hardware..."
RAM_GB=$(awk '/MemTotal/ {printf "%.0f", $2/1024/1024}' /proc/meminfo)
CPU_FLAGS=$(lscpu | awk -F: '/Flags/ {print $2}' | xargs || true)
GPU=""
if command -v nvidia-smi >/dev/null 2>&1; then GPU="nvidia"; fi

MODEL_FILE="gemma-2-2b-it.Q2_K.gguf"
NGL=0
CTX=2048
NPRED=700
if [ "$RAM_GB" -ge 12 ]; then MODEL_FILE="gemma-2-7b-it.Q4_K_M.gguf"; fi
MODEL_PATH="$MODELS/$MODEL_FILE"

echo "[ai-installer] Expecting model at $MODEL_PATH (place file if offline)."

echo "[ai-installer] Installing llama-server (placeholder). Please place compiled binary at $BIN/llama-server"

if [ ! -f "$BIN/llama-server" ]; then
  echo "[WARN] $BIN/llama-server not found. Place the binary and re-run."
fi

# Build systemd unit from template
UNIT_TEMPLATE="$TEMPLATE_DIR/erpnext-gemma.service.template"
if [ -f "$UNIT_TEMPLATE" ]; then
  sudo bash -c "sed -e 's/{{PORT}}/'$PORT'/g' \
    -e 's#{{MODEL_PATH}}#'$MODEL_PATH'#g' \
    -e 's/{{CTX_SIZE}}/'$CTX'/g' \
    -e 's/{{N_PREDICT}}/'$NPRED'/g' \
    -e 's/{{NGL}}/'$NGL'/g' \"$UNIT_TEMPLATE\" > \"$SERVICE\""
  sudo systemctl daemon-reload || true
  echo "[ai-installer] Created $SERVICE (not enabling in skeleton)."
else
  echo "[ERROR] Unit template not found: $UNIT_TEMPLATE"
fi

echo "[ai-installer] Done (skeleton)."
