#!/usr/bin/env python3
"""Exécuteur Oracle de DOMINUS HYPERFLUIDA.

Le script orchestre les étapes déterministes du MVP : F00/F01 localement,
F02/F03/F04/F05/F06 sur Modal, F07 intégré au remux audio, puis F10 localement.
La 4K reste désactivée par défaut et chaque étape écrit un rapport d'état.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auspex import analyze_video
from oracle import campaign_dir, load_state, save_state, state_path

# Legacy remote stages (dev6-B/C) — kept for v2 pipeline
REMOTE_STAGES_V2 = {
    "F02_MOTUS_RIFE": "F02_MOTUS_RIFE",
    "F03_APOTHECA_RESTAURA": "F03_APOTHECA_RESTAURA",
    "F04_FORGE_TEXTURA": "F04_FORGE_TEXTURA",
    "F05_LIBRARIUS_FACIES": "F05_LIBRARIUS_FACIES",
    "F06_LUMEN_IGNIS": "F06_LUMEN_IGNIS",
    "F07_CHROMA_DOMINATUS": "F07_CHROMA_DOMINATUS",
    "F08_TEMPORALIS_CONSISTENTIA": "F08_TEMPORALIS_CONSISTENTIA",
}

# F03_AI pipeline (dev6-D) — orchestrator chains 3 Modal workers
F03_AI_STAGES = {
    "F03_AI_DIFFBIR": "lac-diffbir-upscale",
    "F03_AI_VCG": "lac-vcg-color-grading",
    "F03_AI_AMT": "lac-amt-interpolation",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run(command: list[str], dry_run: bool = False) -> str:
    print("$", " ".join(command))
    if dry_run:
        return ""
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    return result.stdout


def write_stage_report(base: Path, stage: str, report: dict[str, Any]) -> Path:
    stage_dir = base / stage
    stage_dir.mkdir(parents=True, exist_ok=True)
    path = stage_dir / "stage_report.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Oracle DOMINUS HYPERFLUIDA")
    parser.add_argument("--root", default=".")
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--app", default="lacrimae-dev6-video")
    parser.add_argument("--video-volume", default="lacrimae-dev6-video")
    parser.add_argument("--profile", default="auto", choices=["auto", "fast", "balanced", "quality_ultimate", "cinematic_hyper_detail", "hdr_imperator", "realistic_aurea", "old_main_noctis", "viral_imperator"])
    parser.add_argument("--target-fps", type=int, default=120)
    parser.add_argument("--compositing-preset", default=None,
                        help="Preset F09 (clean_realistic, silver_gray, dark, warm, viral_hdr). Par défaut, mappé depuis le profil ATOM.")
    parser.add_argument("--pipeline", default="v3", choices=["v2", "v3"],
                        help="v2=legacy FFmpeg, v3=neural AI pipeline")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.target_fps != 120:
        raise SystemExit("target-fps doit être 120 pour le MVP")
    if not args.source.is_file():
        raise SystemExit(f"source absente: {args.source}")

    root = Path(args.root)
    state_file = state_path(root, args.campaign_id)
    if not state_file.exists():
        from oracle import create_campaign
        create_campaign(root, args.campaign_id, args.source, args.target_fps, args.profile)
    state = load_state(state_file)
    base = campaign_dir(root, args.campaign_id)
    selected_profile = args.profile
    if args.profile == "auto":
        analysis = analyze_video(args.source)
        analysis_path = write_stage_report(base, "F01_AUSPEX_OCULUS", analysis)
        selected_profile = analysis["recommendation"]["profile"]
        state["analysis"] = analysis
        state["artifacts"]["F01_AUSPEX_OCULUS"] = str(analysis_path)
        state["target"]["profile"] = selected_profile
        save_state(state_file, state)
    remote_root = f"campaigns/{args.campaign_id}"

    input_uri = f"{remote_root}/input.mp4"
    run(["modal", "volume", "put", args.video_volume, str(args.source), input_uri], args.dry_run)
    state["worker_profile"] = "modal"
    state["current_stage"] = "F00_PORTA_INGRESSUS"
    state["status"] = "RUNNING"
    state["artifacts"]["source_remote"] = input_uri
    save_state(state_file, state)

    report = {"status": "SUCCEEDED", "stage": "F00_PORTA_INGRESSUS", "mode": "oracle_local", "created_at": now()}
    report_path = write_stage_report(base, "F00_PORTA_INGRESSUS", report)
    state["completed_stages"].append("F00_PORTA_INGRESSUS")
    state["artifacts"]["F00_PORTA_INGRESSUS"] = str(report_path)
    if args.profile != "auto":
        report = {"status": "SUCCEEDED", "stage": "F01_AUSPEX_OCULUS", "mode": "oracle_local_legacy", "created_at": now()}
        report_path = write_stage_report(base, "F01_AUSPEX_OCULUS", report)
        state["artifacts"]["F01_AUSPEX_OCULUS"] = str(report_path)
    if "F01_AUSPEX_OCULUS" not in state["completed_stages"]:
        state["completed_stages"].append("F01_AUSPEX_OCULUS")
    state["current_stage"] = "F02_MOTUS_RIFE"
    save_state(state_file, state)

    current_input = input_uri
    for stage, remote_stage in REMOTE_STAGES.items():
        output_uri = f"{remote_root}/{stage.lower()}.mp4"
        command = [sys.executable, "modal/invoke_remote.py", "--app", args.app,
                   "--stage", remote_stage, "--input-uri", current_input,
                   "--output-uri", output_uri, "--campaign-id", args.campaign_id,
                   "--profile", selected_profile, "--target-fps", str(args.target_fps)]
        stdout = run(command, args.dry_run)
        report = json.loads(stdout.strip().splitlines()[-1]) if stdout and stdout.strip() else {
            "status": "PLANNED", "stage": stage, "output_uri": output_uri,
        }
        report_path = write_stage_report(base, stage, report)
        state["completed_stages"].append(stage)
        state["artifacts"][stage] = str(report_path)    state["current_stage"] = "F09_AETHER_COMPOSITUM"
    state["artifacts"]["latest_remote"] = output_uri
    save_state(state_file, state)
    current_input = output_uri

    # --- F09 AETHER COMPOSITUM (local FFmpeg compositing) ---
    compositing_preset = args.compositing_preset
    if not compositing_preset:
        atom_config = Path("CONFIG/atom_ic_profiles.json")
        if atom_config.is_file():
            atom_data = json.loads(atom_config.read_text(encoding="utf-8"))
            preset_map = atom_data.get("compositing_preset_map", {})
            compositing_preset = preset_map.get(selected_profile, "clean_realistic")
        else:
            compositing_preset = "clean_realistic"

    state["compositing_preset"] = compositing_preset
    save_state(state_file, state)

    # Télécharger le dernier résultat Modal pour F09
    f09_input_local = base / "F09_AETHER_COMPOSITUM" / "input_for_aether.mp4"
    f09_input_local.parent.mkdir(parents=True, exist_ok=True)
    run(["modal", "volume", "get", args.video_volume, current_input, str(f09_input_local)], args.dry_run)

    # Exécuter F09 localement
    f09_output_dir = base / "F09_AETHER_COMPOSITUM"
    f09_command = [
        sys.executable, "F09_AETHER/CODEBASE/lac_f09_aether.py",
        "--input", str(f09_input_local),
        "--output", str(f09_output_dir),
        "--preset", compositing_preset,
    ]
    f09_stdout = run(f09_command, args.dry_run)
    f09_report = json.loads(f09_stdout.strip().splitlines()[-1]) if f09_stdout and f09_stdout.strip() else {
        "status": "PLANNED", "stage": "F09_AETHER_COMPOSITUM",
    }
    f09_report_path = write_stage_report(base, "F09_AETHER_COMPOSITUM", f09_report)
    state["completed_stages"].append("F09_AETHER_COMPOSITUM")
    state["artifacts"]["F09_AETHER_COMPOSITUM"] = str(f09_report_path)
    state["current_stage"] = "F10_CUSTOS_RESTITUTIO"
    save_state(state_file, state)

    # Upload du résultat F09 vers Modal pour F10
    f09_output_file = f09_output_dir / f"aether_{compositing_preset}.mp4"
    f09_remote_uri = f"{remote_root}/f09_aether_output.mp4"
    if f09_output_file.is_file():
        run(["modal", "volume", "put", args.video_volume, str(f09_output_file), f09_remote_uri], args.dry_run)
        current_input = f09_remote_uri

    final_local = base / "F10_CUSTOS_RESTITUTIO" / f"{args.campaign_id}_final.mp4"
    final_local.parent.mkdir(parents=True, exist_ok=True)
    run(["modal", "volume", "get", args.video_volume, current_input, str(final_local)], args.dry_run)
    report = {"status": "SUCCEEDED" if not args.dry_run else "PLANNED", "stage": "F10_CUSTOS_RESTITUTIO", "local_output": str(final_local), "remote_input": current_input, "created_at": now()}
    report_path = write_stage_report(base, "F10_CUSTOS_RESTITUTIO", report)
    state["completed_stages"].append("F10_CUSTOS_RESTITUTIO")
    state["artifacts"]["final"] = str(final_local)
    state["artifacts"]["F10_CUSTOS_RESTITUTIO"] = str(report_path)
    state["current_stage"] = "SEALED"
    state["status"] = "SEALED" if not args.dry_run else "PLANNED"
    save_state(state_file, state)
    print(json.dumps({"status": state["status"], "campaign_id": args.campaign_id, "final": str(final_local)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
