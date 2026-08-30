#!/bin/bash
# LACRIMAE F03_AI — Setup & Clean Test
# Usage: bash F03_AI/setup_and_test.sh
#
# This script:
# 1. Verifies Modal auth
# 2. Deploys all 3 workers (one image build each)
# 3. Runs a single clean pipeline test
# 4. Shows results and cost
#
# Prerequisites:
#   - Modal account with credits
#   - modal token set (run: modal token set --token-id <ID> --token-secret <SECRET>)

set -e

echo "================================================================"
echo "  LACRIMAE F03_AI — Setup & Clean Test"
echo "================================================================"
echo ""

# ── Step 0: Check Modal auth ──────────────────────────────────────
echo "▶ Checking Modal auth..."
PROFILE=$(modal profile current 2>&1)
if [ $? -ne 0 ]; then
    echo "❌ Modal not authenticated. Run:"
    echo "   modal token set --token-id <YOUR_ID> --token-secret <YOUR_SECRET>"
    exit 1
fi
echo "  ✅ Modal profile: $PROFILE"
echo ""

# ── Step 1: Deploy all workers ────────────────────────────────────
echo "▶ Deploying workers (this builds 3 GPU images, ~3-5 min)..."
echo "  [1/3] lac-upscale (Real-ESRGAN x4plus)..."
modal deploy LACRIMAE/F03_AI/workers/diffbir_pipeline.py 2>&1 | tail -3
echo ""

echo "  [2/3] lac-vcg-color-grading (L-Diffuser)..."
modal deploy LACRIMAE/F03_AI/workers/vcg_pipeline.py 2>&1 | tail -3
echo ""

echo "  [3/3] lac-amt-interpolation (AMT-G)..."
modal deploy LACRIMAE/F03_AI/workers/amt_pipeline.py 2>&1 | tail -3
echo ""

echo "  ✅ All 3 workers deployed"
echo ""

# ── Step 2: Prepare test inputs ───────────────────────────────────
echo "▶ Preparing test inputs..."
cd LACRIMAE

# Download test video from Modal volume (or use local)
if [ ! -f /tmp/test_input.mp4 ]; then
    modal volume get lacrimae-dev6-video rife_input_5s.mp4 /tmp/test_input.mp4 2>&1 | tail -1
fi

# Extract reference frame for color grading
if [ ! -f /tmp/ref_frame.png ]; then
    ffmpeg -y -i /tmp/test_input.mp4 -vf "select=eq(n\,60)" -vframes 1 /tmp/ref_frame.png 2>/dev/null
fi

echo "  ✅ Test video: $(ls -lh /tmp/test_input.mp4 | awk '{print $5}')"
echo "  ✅ Reference frame extracted"
echo ""

# ── Step 3: Run clean pipeline test ───────────────────────────────
echo "▶ Running clean pipeline test (single pass, no debug)..."
echo "  Input: 1920x1080 @ 30fps, 5s"
echo "  Output target: 1920x1080 @ 120fps, style=crunchy"
echo ""

python3 F03_AI/run_real_test.py

echo ""
echo "================================================================"
echo "  DONE — Check the output in .test/f03_ai_modal_test/"
echo "================================================================"
