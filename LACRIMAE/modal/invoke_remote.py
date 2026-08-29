from __future__ import annotations

import argparse
import json
import modal


parser = argparse.ArgumentParser(description="Invoke an already deployed LACRIMAE Modal function")
parser.add_argument("--app", default="lacrimae-dev6-video")
parser.add_argument("--stage", required=True)
parser.add_argument("--input-uri", required=True)
parser.add_argument("--output-uri", required=True)
parser.add_argument("--campaign-id", required=True)
parser.add_argument("--profile", default="balanced")
parser.add_argument("--target-fps", type=int, default=120)
args = parser.parse_args()

function = modal.Function.from_name(args.app, "run_stage")
result = function.remote(
    args.stage,
    args.input_uri,
    args.output_uri,
    args.campaign_id,
    args.profile,
    args.target_fps,
)
print(json.dumps(result, ensure_ascii=False))
