#!/usr/bin/env bash
# younggeul live demo — ingest → snapshot → baseline against real APIs
#
# Requires KPUBDATA_DATAGO_API_KEY, KPUBDATA_BOK_API_KEY, KPUBDATA_KOSIS_API_KEY
# in the environment (load from .env via: set -a; source .env; set +a).
#
# Override defaults via env vars:
#   GU=11680               (single 5-digit MOLIT sigungu code)
#   GUS=11680,11440        (multi-gu CSV; takes precedence over GU)
#   MONTHS=202403,202503   (multi-month CSV; populates YoY in Gold)
#   DEMO_DIR=./demo_output_live

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -x "${REPO_ROOT}/.venv/bin/younggeul" ]; then
    YG="${REPO_ROOT}/.venv/bin/younggeul"
elif command -v younggeul >/dev/null 2>&1; then
    YG="younggeul"
else
    echo "Error: 'younggeul' CLI not found. Install with: pip install -e '.[dev,kr-seoul-apartment]'" >&2
    exit 1
fi

echo "=== Younggeul Live Demo (ingest → snapshot → baseline) ==="

for var in KPUBDATA_DATAGO_API_KEY KPUBDATA_BOK_API_KEY KPUBDATA_KOSIS_API_KEY; do
    if [ -z "${!var:-}" ]; then
        echo "Error: $var is not set. Load .env first: set -a; source .env; set +a" >&2
        exit 1
    fi
done

DEMO_DIR="${DEMO_DIR:-./demo_output_live}"
GU="${GU:-11680}"
GUS="${GUS:-}"
MONTHS="${MONTHS:-202403,202503}"
mkdir -p "$DEMO_DIR"

if [ -n "$GUS" ]; then
    GU_ARGS=(--gus "$GUS")
    echo "  gus=$GUS  months=$MONTHS"
else
    GU_ARGS=(--gu "$GU")
    echo "  gu=$GU   months=$MONTHS"
fi

echo "[1/3] Ingesting live data..."
"$YG" ingest \
    --source live "${GU_ARGS[@]}" --months "$MONTHS" \
    --output-dir "$DEMO_DIR/pipeline"

echo "[2/3] Publishing snapshot..."
"$YG" snapshot publish \
    --data-dir "$DEMO_DIR/pipeline" --snapshot-dir "$DEMO_DIR/snapshots"

echo "[3/3] Running baseline forecast..."
"$YG" baseline \
    --snapshot-dir "$DEMO_DIR/snapshots" --output-dir "$DEMO_DIR/baseline"

echo ""
echo "=== Live Demo Complete ==="
echo "Output directory: $DEMO_DIR"
echo ""
echo "Artifacts:"
find "$DEMO_DIR" -type f | sort | sed 's/^/  /'
