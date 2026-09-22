import argparse
import sys
from pathlib import Path

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from docstudio.pipeline import DocumentaryPipeline
from docstudio.config import DEFAULT_VOICE, DEFAULT_CAPTION_STYLE, RUNS_DIR, DOCSTUDIO_TTS_ENGINE
from docstudio.timeline import DocumentaryTimeline

def main():
    parser = argparse.ArgumentParser(
        prog="docstudio",
        description="DocStudio: Autonomous High-Retention Documentary Video Production Studio"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Produce a complete documentary video from a topic or project.yaml")
    run_parser.add_argument("--project", "-p", default=None, type=str, help="Path to project.yaml configuration file")
    run_parser.add_argument("--topic", "-t", required=False, default=None, type=str, help="Documentary topic, headline, or mystery")
    run_parser.add_argument("--voice", "-v", default=DEFAULT_VOICE, type=str, help="Edge-TTS narrator voice")
    run_parser.add_argument("--tts-engine", default=DOCSTUDIO_TTS_ENGINE, choices=["voxcpm", "edge_tts"], help="TTS engine: voxcpm (OpenBMB VoxCPM2) or edge_tts")
    run_parser.add_argument("--style", "-s", default=DEFAULT_CAPTION_STYLE, choices=["documentary", "hormozi", "mrbeast"], help="Subtitle animation style")
    run_parser.add_argument("--aspect-ratio", "-a", default="16:9", choices=["16:9", "9:16"], help="Output aspect ratio (16:9 landscape or 9:16 portrait)")
    run_parser.add_argument("--run-id", default=None, type=str, help="Custom folder name for this production run")
    run_parser.add_argument("--runtime", "-r", default="5m", choices=["45s", "50s", "60s", "90s", "1m", "1.5m", "3m", "5m", "8m", "10m"], help="Target documentary runtime duration (default: 5m)")
    run_parser.add_argument("--force", default=None, type=str, help="Comma-separated stages to force rebuild: script,audio,captions,visuals,mix,render")

    # Command: server (InVideo Web Studio)
    server_parser = subparsers.add_parser("server", help="Launch the InVideo AI Documentary Studio Web App")
    server_parser.add_argument("--port", "-p", default=8000, type=int, help="Port to bind server (default: 8000)")
    server_parser.add_argument("--host", default="127.0.0.1", type=str, help="Host to bind server (default: 127.0.0.1)")

    # Command: timeline (inspired by Palmier Pro)
    timeline_parser = subparsers.add_parser("timeline", help="Agent-programmable timeline operations (inspect, swap b-roll, trim, export)")
    timeline_sub = timeline_parser.add_subparsers(dest="timeline_action", help="Timeline action")

    # timeline inspect
    inspect_p = timeline_sub.add_parser("inspect", help="Inspect timeline tracks, clips, and durations")
    inspect_p.add_argument("--run-id", required=True, type=str, help="Run ID of the project")

    # timeline swap
    swap_p = timeline_sub.add_parser("swap", help="Swap B-roll asset for a scene")
    swap_p.add_argument("--run-id", required=True, type=str, help="Run ID of the project")
    swap_p.add_argument("--scene", required=True, type=str, help="Scene ID (e.g. act1_s1)")
    swap_p.add_argument("--asset", required=True, type=str, help="New image/video file path")

    # timeline trim
    trim_p = timeline_sub.add_parser("trim", help="Ripple trim a scene duration")
    trim_p.add_argument("--run-id", required=True, type=str, help="Run ID of the project")
    trim_p.add_argument("--scene", required=True, type=str, help="Scene ID")
    trim_p.add_argument("--delta", required=True, type=float, help="Duration delta in seconds (+1.5 or -0.8)")

    # timeline export-fcpxml
    fcpxml_p = timeline_sub.add_parser("export-fcpxml", help="Export timeline to Final Cut Pro XML / DaVinci Resolve")
    fcpxml_p.add_argument("--run-id", required=True, type=str, help="Run ID of the project")

    # timeline mcp-status
    status_p = timeline_sub.add_parser("mcp-status", help="Check Palmier Pro OS compatibility and MCP connection")
    status_p.add_argument("--run-id", default=None, type=str, help="Optional run ID")

    # timeline sync-palmier
    sync_p = timeline_sub.add_parser("sync-palmier", help="Sync timeline to live Palmier Pro instance via MCP")
    sync_p.add_argument("--run-id", required=True, type=str, help="Run ID of the project")

    # Command: status
    status_parser = subparsers.add_parser("status", help="Inspect pipeline progress, checkpoints, and execution state")
    status_parser.add_argument("--run-id", default=None, type=str, help="Specific run ID to inspect")
    status_parser.add_argument("--all", action="store_true", help="List all production runs with state and render times")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        force_stages = [s.strip() for s in args.force.split(",")] if args.force else []
        topic = args.topic
        runtime = args.runtime
        aspect_ratio = args.aspect_ratio
        voice = args.voice
        style = args.style
        tts_engine = args.tts_engine
        color_grade_preset = "kodak_2383"
        project_config = None

        if args.project:
            from docstudio.project_config import load_project_config
            project_config = load_project_config(args.project)
            topic = project_config.topic
            runtime = project_config.runtime
            aspect_ratio = project_config.aspect_ratio
            tts_engine = project_config.tts_engine
            color_grade_preset = project_config.color_grade_preset
            if project_config.style_profile.caption_style:
                style = project_config.style_profile.caption_style

        if not topic:
            print("Error: Either --topic or --project with a valid topic must be provided.")
            sys.exit(1)

        pipeline = DocumentaryPipeline(
            voice=voice,
            caption_style=style,
            aspect_ratio=aspect_ratio,
            tts_engine=tts_engine,
        )
        pipeline.run(
            topic=topic,
            run_id=args.run_id,
            force_stages=force_stages,
            runtime=runtime,
            color_grade_preset=color_grade_preset,
            project_config=project_config,
        )

    elif args.command == "server":
        from docstudio.server import start_server
        start_server(host=args.host, port=args.port)

    elif args.command == "timeline":
        if args.timeline_action == "mcp-status":
            from docstudio.palmier_bridge import PalmierBridge
            bridge = PalmierBridge()
            status = bridge.get_status()
            compat = status["system_compatibility"]
            print(f"\n--- PALMIER PRO INTEGRATION STATUS ---")
            print(f"Host OS: {compat['os_name']} {compat['os_release']}")
            print(f"Architecture: {compat['machine']}")
            print(f"Compatible with Palmier Pro: {'YES' if compat['is_compatible'] else 'NO (Requires macOS 26 Tahoe on Apple Silicon)'}")
            print(f"Status Note: {compat['reason']}")
            print(f"MCP Endpoint: {status['mcp_endpoint']}")
            print(f"MCP Active: {'CONNECTED' if status['mcp_active'] else 'DISCONNECTED / OFFLINE'}")
            print(f"Architectural Role: {status['role']}")
            print(f"Primary Autonomous Engine: {status['primary_engine']}")
            print("--------------------------------------\n")
            return

        if not args.run_id:
            print("Error: --run-id is required for this action.")
            sys.exit(1)

        run_path = RUNS_DIR / args.run_id
        if not run_path.exists():
            print(f"Error: Run folder '{run_path}' does not exist.")
            sys.exit(1)

        timeline = DocumentaryTimeline(run_dir=run_path)

        if args.timeline_action == "inspect":
            print(f"\n--- TIMELINE INSPECTION: {args.run_id} ---")
            print(f"Total Video Clips: {len(timeline.video_clips)}")
            print(f"Master Audio Track: {timeline.audio_track_path}")
            print(f"Subtitle Track: {timeline.subtitle_track_path}")
            print("\nClips:")
            for c in timeline.video_clips:
                print(f"  [{c.clip_id}] {c.start_time}s -> {c.end_time}s ({c.duration}s) | Motion: {c.motion} | Asset: {Path(c.asset_path).name if c.asset_path else 'None'}")
            print("------------------------------------------\n")

        elif args.timeline_action == "swap":
            success = timeline.swap_clip(args.scene, args.asset)
            if success:
                print(f"✅ Successfully swapped clip for scene '{args.scene}' to: {args.asset}")
            else:
                print(f"❌ Failed to find scene '{args.scene}' in timeline.")

        elif args.timeline_action == "trim":
            success = timeline.trim_clip(args.scene, args.delta)
            if success:
                print(f"✅ Successfully trimmed scene '{args.scene}' by {args.delta}s (rippled subsequent shots).")
            else:
                print(f"❌ Failed to find scene '{args.scene}' in timeline.")

        elif args.timeline_action == "export-fcpxml":
            out_file = run_path / "timeline.fcpxml"
            timeline.export_fcpxml(out_file)
            print(f"✅ Exported Apple Final Cut Pro XML: {out_file}")

        elif args.timeline_action == "sync-palmier":
            success = timeline.sync_to_palmier_mcp()
            if success:
                print(f"✅ Successfully synchronized timeline to Palmier Pro MCP!")
            else:
                print(f"⚠️ Palmier Pro MCP synchronization skipped (system incompatible or server not reachable).")
                print(f"   The timeline remains fully accessible via 'timeline.json' and 'timeline.fcpxml'.")

    elif args.command == "status":
        from docstudio.progress_tracker import ProgressTracker, PROGRESS_FILE
        if args.all:
            runs = ProgressTracker.list_all_runs()
            print("\n" + "=" * 75)
            print("  DOCSTUDIO PRODUCTION RUNS (ALL)")
            print("=" * 75)
            if not runs:
                print("  No runs found in workspace/runs/.")
            else:
                print(f"  {'RUN ID':<26} {'STATUS':<12} {'DURATION':<12} {'TOPIC'}")
                print("  " + "-" * 71)
                for r in runs:
                    dur_val = r.get("total_duration_seconds", 0.0)
                    dur_str = f"{dur_val:.1f}s" if dur_val else "N/A"
                    topic_str = r.get("topic", "") or ""
                    print(f"  {r['run_id']:<26} {r['overall_status']:<12} {dur_str:<12} {topic_str[:30]}")
            print("=" * 75 + "\n")
        else:
            run_id = args.run_id
            if run_id:
                info = ProgressTracker.get_run_status(run_id)
                if not info:
                    print(f"Error: Run '{run_id}' not found in {RUNS_DIR}.")
                    sys.exit(1)
                print("\n" + "=" * 75)
                print(f"  DOCSTUDIO RUN STATUS: {run_id}")
                print("=" * 75)
                print(f"  Topic:           {info.get('topic', 'N/A')}")
                print(f"  Overall Status:  {info.get('overall_status', 'UNKNOWN')}")
                print(f"  Started At:      {info.get('started_at', 'N/A')}")
                dur_val = info.get("total_duration_seconds", 0.0)
                dur_str = f"{dur_val:.1f}s" if dur_val else "N/A"
                print(f"  Total Duration:  {dur_str}")
                print("  " + "-" * 71)
                print("  Core Checkpoints:")
                run_p = RUNS_DIR / run_id
                for fname, desc in [
                    ("01_script.json", "Script & Storyboard Cues"),
                    ("02_narration.wav", "Master Voiceover Narration"),
                    ("03_captions.ass", "Word-Aligned Subtitles"),
                    ("04_visuals", "Visual B-Roll & Manifest"),
                    ("05_audio_mix.wav", "Ducked Audio Bed & SFX Mix"),
                    ("06_final_render.mp4", "Composited 1080p Video"),
                ]:
                    cp_path = run_p / fname
                    status_icon = "✅ Exists" if cp_path.exists() else "⏳ Missing / In Progress"
                    size_info = ""
                    if cp_path.exists():
                        if cp_path.is_file():
                            kb = cp_path.stat().st_size / 1024
                            size_info = f" ({kb:.1f} KB)" if kb < 1024 else f" ({kb/1024:.2f} MB)"
                        elif cp_path.is_dir():
                            cnt = len(list(cp_path.glob("*")))
                            size_info = f" ({cnt} files)"
                    print(f"    [{status_icon}] {fname:<22} {desc}{size_info}")

                stages = info.get("stages", {})
                if stages:
                    print("  " + "-" * 71)
                    print("  Stage Execution Log:")
                    for s_idx in sorted([int(k) for k in stages.keys()]):
                        st = stages[str(s_idx)]
                        dur_s = f"{st.get('duration_s', 0)}s" if st.get('duration_s', 0) > 0 else "-"
                        print(f"    Stage {s_idx} ({st.get('name', '')}): [{st.get('status', '').upper()}] - {dur_s} | {st.get('details', '')}")

                if info.get("error"):
                    err = info["error"]
                    print("  " + "-" * 71)
                    print(f"  🔴 FAILURE IN STAGE {err.get('failed_stage')}: {err.get('stage_name')}")
                    print(f"  Error: {err.get('error_message')}")
                print("=" * 75 + "\n")
            else:
                # If no run-id given, print PROGRESS.md if it exists, else list runs
                if PROGRESS_FILE.exists():
                    print(PROGRESS_FILE.read_text(encoding="utf-8"))
                else:
                    runs = ProgressTracker.list_all_runs()
                    if runs:
                        latest = runs[-1]["run_id"]
                        info = ProgressTracker.get_run_status(latest)
                        print(f"\nActive/Latest Run: {latest} ({info.get('overall_status')})")
                        print(f"Run 'uv run python -m docstudio status --run-id {latest}' for complete details.\n")
                    else:
                        print("No active runs or PROGRESS.md found. Run 'uv run python -m docstudio run --topic \"...\"' to begin.")

if __name__ == "__main__":
    main()
