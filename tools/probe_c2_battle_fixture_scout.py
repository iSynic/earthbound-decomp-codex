#!/usr/bin/env python3
"""Scout local Mesen save states for C2 battle-entry fixture potential."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import rom_tools


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = ROOT / "build" / "c2" / "battle-trace-oracles" / "fixture-scout"
DEFAULT_STATE_DIR = Path(r"F:\Mesen\SaveStates")
COMMON_MESEN_PATHS = [
    Path(os.environ.get("MESEN_EXE", "")) if os.environ.get("MESEN_EXE") else None,
    Path(os.environ.get("MESEN_PATH", "")) if os.environ.get("MESEN_PATH") else None,
    Path(r"F:\Mesen\Mesen.exe"),
    Path(r"C:\Mesen\Mesen.exe"),
]
DEFAULT_PATTERNS = [
    ("neutral_short", "neutral:600"),
    ("confirm_probe", "neutral:30,a:4,neutral:20,a:4,neutral:540"),
    ("walk_box", "right:90,down:90,left:90,up:90"),
]
SCOUT_ADDRESSES = [
    ("C0:D19B", 0xC0D19B, "ordinary_encounter_prep"),
    ("C0:D323", 0xC0D323, "ordinary_enemy_list_build"),
    ("C0:44DA", 0xC044DA, "ordinary_encounter_sets_battle_flag"),
    ("C0:B731", 0xC0B731, "overworld_battle_entry"),
    ("C2:E8E0", 0xC2E8E0, "encounter_prep_c2_bridge"),
    ("C2:2F38", 0xC22F38, "scripted_battle_entry"),
    ("C2:4821", 0xC24821, "battle_runtime_entry"),
    ("C2:4830", 0xC24830, "battle_runtime_debug_seed_path"),
    ("C2:311B", 0xC2311B, "battle_start_menu_controller"),
    ("C1:ADB4", 0xC1ADB4, "target_prompt_resolver"),
    ("C1:CE85", 0xC1CE85, "item_action_selection"),
    ("C1:CFC6", 0xC1CFC6, "psi_action_selection"),
    ("C2:B930", 0xC2B930, "c2_target_action_candidate_export"),
    ("C2:BAC5", 0xC2BAC5, "c2_target_action_candidate_followup"),
]
WATCH_RANGES = [
    ("debug_gate_436c", 0x436C, 2),
    ("debug_control_suppress_flag_4dc2", 0x4DC2, 2),
    ("encounter_slot_4db6", 0x4DB6, 2),
    ("battle_id_4a8c", 0x4A8C, 2),
    ("encounter_countdown_5d60", 0x5D60, 2),
    ("battle_entry_pointer_9f8a", 0x9F8A, 2),
    ("battle_entry_pointer_9f8c", 0x9F8C, 2),
    ("target_snapshot_header_9ffa", 0x9FFA, 4),
    ("candidate_row_pointer_9fac", 0x9FAC, 2),
    ("current_action_payload_a96c", 0xA96C, 2),
    ("current_action_payload_a96e", 0xA96E, 2),
]
BATTLE_ENTRY_LABELS = {"C0:D19B", "C0:D323", "C0:44DA", "C0:B731", "C2:E8E0", "C2:2F38", "C2:4821", "C2:311B"}
COMMAND_LABELS = {"C1:ADB4", "C1:CE85", "C1:CFC6", "C2:B930"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scout local Mesen save states for C2 battle fixture potential.")
    parser.add_argument("--state", action="append", help="Specific .mss save state. May repeat.")
    parser.add_argument("--state-dir", default=str(DEFAULT_STATE_DIR), help="Directory to scan for .mss save states.")
    parser.add_argument("--pattern", action="append", help="Pattern as id=atom:frames,... or just atom:frames,...")
    parser.add_argument("--frame-limit", type=int, default=900)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--limit", type=int, help="Maximum number of candidate save states to scout.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--mesen", help="Path to Mesen.exe.")
    parser.add_argument("--rom", help="Path to EarthBound (USA).sfc.")
    return parser.parse_args()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value or "item"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def candidate_states(args: argparse.Namespace) -> list[Path]:
    if args.state:
        states = [Path(item) for item in args.state]
    else:
        state_dir = Path(args.state_dir)
        states = sorted(state_dir.glob("*.mss")) if state_dir.exists() else []
    if args.limit is not None:
        states = states[: args.limit]
    return states


def parse_patterns(args: argparse.Namespace) -> list[tuple[str, str]]:
    if not args.pattern:
        return DEFAULT_PATTERNS
    patterns: list[tuple[str, str]] = []
    for index, item in enumerate(args.pattern, start=1):
        if "=" in item:
            pattern_id, spec = item.split("=", 1)
        else:
            pattern_id, spec = f"pattern_{index:02d}", item
        patterns.append((slug(pattern_id), spec.strip()))
    return patterns


def resolve_mesen(explicit_path: str | None) -> Path:
    if explicit_path:
        path = Path(explicit_path)
        if not path.is_file():
            raise FileNotFoundError(f"Mesen executable not found: {path}")
        return path
    for candidate in COMMON_MESEN_PATHS:
        if candidate and candidate.is_file():
            return candidate
    found = shutil.which("Mesen.exe") or shutil.which("Mesen")
    if found:
        return Path(found)
    searched = "\n".join(f"- {path}" for path in COMMON_MESEN_PATHS if path)
    raise FileNotFoundError(f"Unable to find Mesen.exe. Searched:\n{searched}\nPass --mesen.")


def lua_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_lua(path: Path) -> None:
    address_lines = [
        f'  {{ label = {lua_string(label)}, address = 0x{address:06X}, role = {lua_string(role)} }},'
        for label, address, role in SCOUT_ADDRESSES
    ]
    watch_lines = [
        f'  {{ id = {lua_string(watch_id)}, address = 0x{address:04X}, bytes = {byte_count} }},'
        for watch_id, address, byte_count in WATCH_RANGES
    ]
    write_text(
        path,
        "\n".join(
            [
                "-- Generated by tools/probe_c2_battle_fixture_scout.py",
                "-- Local-only C2 battle fixture scout. It emits raw trace events only.",
                "",
                "local outPath = os.getenv(\"C2_FIXTURE_SCOUT_TRACE_OUT\")",
                "local statePath = os.getenv(\"C2_FIXTURE_SCOUT_STATE_PATH\")",
                "local frameLimit = tonumber(os.getenv(\"C2_FIXTURE_SCOUT_FRAME_LIMIT\") or \"900\")",
                "local inputPatternSpec = os.getenv(\"C2_FIXTURE_SCOUT_INPUT_PATTERN\") or \"neutral:900\"",
                "local out = assert(io.open(outPath, \"w\"))",
                "local wram = emu.memType.snesWorkRam",
                "local snesMemory = emu.memType.snesMemory",
                "local snesCpu = emu.cpuType.snes",
                "local frame = 0",
                "local totalHits = 0",
                "local hitLabels = \"\"",
                "local loadedState = statePath == nil or statePath == \"\"",
                "local stateLoadCallbackRef = nil",
                "",
                "local breakpoints = {",
                *address_lines,
                "}",
                "local watchRanges = {",
                *watch_lines,
                "}",
                "",
                "local function q(s) return '\"' .. tostring(s):gsub('\\\\', '\\\\\\\\'):gsub('\"', '\\\\\"') .. '\"' end",
                "local function hex(n) return string.format(\"0x%06X\", n) end",
                "local function writeJson(obj)",
                "  local first = true",
                "  out:write(\"{\")",
                "  for k, v in pairs(obj) do",
                "    if not first then out:write(\",\") end",
                "    first = false",
                "    out:write(q(k), \":\")",
                "    if v == nil then out:write(\"null\")",
                "    elseif type(v) == \"string\" then out:write(q(v))",
                "    elseif type(v) == \"boolean\" then out:write(v and \"true\" or \"false\")",
                "    else out:write(tostring(v)) end",
                "  end",
                "  out:write(\"}\\n\")",
                "  out:flush()",
                "end",
                "local function readFile(filePath)",
                "  local f = assert(io.open(filePath, \"rb\")); local d = f:read(\"*a\"); f:close(); return d",
                "end",
                "local function rb(addr) return emu.read(addr, wram, false) end",
                "local function readBytes(addr, count)",
                "  local parts = {}",
                "  for i = 0, count - 1 do parts[#parts + 1] = string.format(\"%02X\", rb(addr + i)) end",
                "  return table.concat(parts, \" \")",
                "end",
                "local function trim(s) return (s:gsub(\"^%s+\", \"\"):gsub(\"%s+$\", \"\")) end",
                "local function inputForAtom(atom)",
                "  atom = trim(atom or \"\")",
                "  if atom == \"neutral\" or atom == \"none\" or atom == \"\" then return {}",
                "  elseif atom == \"right\" then return { right = true }",
                "  elseif atom == \"left\" then return { left = true }",
                "  elseif atom == \"up\" then return { up = true }",
                "  elseif atom == \"down\" then return { down = true }",
                "  elseif atom == \"down_right\" then return { down = true, right = true }",
                "  elseif atom == \"up_right\" then return { up = true, right = true }",
                "  elseif atom == \"up_left\" then return { up = true, left = true }",
                "  elseif atom == \"down_left\" then return { down = true, left = true }",
                "  elseif atom == \"a\" then return { a = true }",
                "  elseif atom == \"start\" then return { start = true }",
                "  elseif atom == \"a_start\" then return { a = true, start = true }",
                "  end",
                "  writeJson({ type = \"runner_error\", message = \"unsupported input atom\", atom = atom })",
                "  out:close()",
                "  emu.stop(2)",
                "  return {}",
                "end",
                "local function parsePattern(pattern)",
                "  local parsed = {}",
                "  local total = 0",
                "  for segment in string.gmatch(pattern, \"([^,]+)\") do",
                "    local atom, frames = segment:match(\"^%s*([%w_]+)%s*:%s*(%d+)%s*$\")",
                "    if atom == nil then",
                "      writeJson({ type = \"runner_error\", message = \"invalid input segment\", segment = tostring(segment) })",
                "      out:close()",
                "      emu.stop(2)",
                "      return {}, 0",
                "    end",
                "    frames = tonumber(frames)",
                "    inputForAtom(atom)",
                "    table.insert(parsed, { atom = trim(atom), frames = frames })",
                "    total = total + frames",
                "  end",
                "  return parsed, total",
                "end",
                "local inputPattern, inputPatternFrames = parsePattern(inputPatternSpec)",
                "local function inputForFrame(frameNumber)",
                "  if #inputPattern == 0 then return {} end",
                "  local cursor = frameNumber % inputPatternFrames",
                "  local total = 0",
                "  for _, segment in ipairs(inputPattern) do",
                "    total = total + segment.frames",
                "    if cursor < total then return inputForAtom(segment.atom) end",
                "  end",
                "  return {}",
                "end",
                "local function emitWatches(eventType, pcLabel)",
                "  for _, watch in ipairs(watchRanges) do",
                "    writeJson({ type = eventType, frame = frame, pc = pcLabel, watchId = watch.id, address = hex(watch.address), bytes = watch.bytes, valueHex = readBytes(watch.address, watch.bytes) })",
                "  end",
                "end",
                "writeJson({ type = \"runner_start\", inputPattern = inputPatternSpec, inputPatternFrames = inputPatternFrames, frameLimit = frameLimit })",
                "local function loadInitialStateFromExec()",
                "  if loadedState then return end",
                "  local state = readFile(statePath)",
                "  writeJson({ type = \"before_state_load\", statePath = statePath, bytes = #state })",
                "  local ok = emu.loadSavestate(state)",
                "  loadedState = true",
                "  if stateLoadCallbackRef ~= nil then emu.removeMemoryCallback(stateLoadCallbackRef, emu.callbackType.exec, 0x008000, 0xFFFFFF, snesCpu, snesMemory) end",
                "  writeJson({ type = \"state_load\", ok = ok })",
                "end",
                "if not loadedState then stateLoadCallbackRef = emu.addMemoryCallback(loadInitialStateFromExec, emu.callbackType.exec, 0x008000, 0xFFFFFF, snesCpu, snesMemory) end",
                "local function makeBreakpoint(bp)",
                "  return function()",
                "    totalHits = totalHits + 1",
                "    hitLabels = hitLabels .. bp.label .. \";\"",
                "    writeJson({ type = \"breakpoint_hit\", frame = frame, pc = bp.label, address = hex(bp.address), role = bp.role })",
                "    emitWatches(\"watch_snapshot\", bp.label)",
                "  end",
                "end",
                "for _, bp in ipairs(breakpoints) do emu.addMemoryCallback(makeBreakpoint(bp), emu.callbackType.exec, bp.address, bp.address, snesCpu, snesMemory) end",
                "emu.addEventCallback(function() if not loadedState then emu.setInput({}, 0); return end; emu.setInput(inputForFrame(frame), 0) end, emu.eventType.inputPolled)",
                "emu.addEventCallback(function()",
                "  frame = frame + 1",
                "  if frame == 1 then emitWatches(\"initial_watch\", \"start\") end",
                "  if frame >= frameLimit then",
                "    emitWatches(\"final_watch\", \"summary\")",
                "    writeJson({ type = \"summary\", frames = frame, totalHits = totalHits, hitLabels = hitLabels })",
                "    out:close()",
                "    emu.stop(0)",
                "  end",
                "end, emu.eventType.endFrame)",
                "",
            ]
        ),
    )


def read_trace(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    invalid = 0
    if not path.exists():
        return rows, invalid
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            invalid += 1
            continue
        if isinstance(row, dict):
            rows.append(row)
        else:
            invalid += 1
    return rows, invalid


def summarize_trace(path: Path) -> dict[str, Any]:
    rows, invalid = read_trace(path)
    hit_counts: dict[str, int] = {}
    event_counts: dict[str, int] = {}
    first_hit_frame: int | None = None
    last_frame: int | None = None
    for row in rows:
        event_type = str(row.get("type", "unknown"))
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
        frame = row.get("frame")
        if isinstance(frame, int):
            last_frame = frame if last_frame is None else max(last_frame, frame)
        if event_type == "breakpoint_hit":
            pc = str(row.get("pc", ""))
            if pc:
                hit_counts[pc] = hit_counts.get(pc, 0) + 1
                if isinstance(frame, int):
                    first_hit_frame = frame if first_hit_frame is None else min(first_hit_frame, frame)
    observed = sorted(hit_counts)
    return {
        "trace_path": manifest_path(path),
        "trace_exists": path.exists(),
        "trace_nonempty": path.exists() and path.stat().st_size > 0,
        "line_count": len(rows),
        "invalid_line_count": invalid,
        "event_counts": dict(sorted(event_counts.items())),
        "breakpoint_hit_counts": dict(sorted(hit_counts.items())),
        "observed_addresses": observed,
        "battle_entry_candidate": bool(BATTLE_ENTRY_LABELS.intersection(observed)),
        "command_fixture_candidate": COMMAND_LABELS.issubset(observed),
        "first_hit_frame": first_hit_frame,
        "last_frame": last_frame,
    }


def run_scout(
    *,
    state: Path,
    pattern_id: str,
    pattern: str,
    output_dir: Path,
    lua_path: Path,
    mesen: Path,
    rom: Path,
    frame_limit: int,
    timeout: int,
) -> dict[str, Any]:
    trace_path = output_dir / "raw-trace.jsonl"
    env = os.environ.copy()
    env["C2_FIXTURE_SCOUT_TRACE_OUT"] = str(trace_path)
    env["C2_FIXTURE_SCOUT_STATE_PATH"] = str(state)
    env["C2_FIXTURE_SCOUT_FRAME_LIMIT"] = str(frame_limit)
    env["C2_FIXTURE_SCOUT_INPUT_PATTERN"] = pattern
    command = [
        str(mesen),
        "--testRunner",
        "--enableStdout",
        "--doNotSaveSettings",
        "--debug.scriptWindow.allowIoOsAccess=true",
        str(lua_path),
        str(rom),
    ]
    record: dict[str, Any] = {
        "state_path_local_only": str(state),
        "pattern_id": pattern_id,
        "input_pattern": pattern,
        "output_dir": manifest_path(output_dir),
        "raw_trace_path": manifest_path(trace_path),
        "command": command,
        "status": "pending",
        "source_promotion_allowed": False,
        "behavior_change_allowed": False,
    }
    if not state.is_file():
        record["status"] = "missing_state"
        record["error"] = f"save state not found: {state}"
        return record
    record["state_size"] = state.stat().st_size
    record["state_sha256"] = sha256(state)
    output_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=timeout, check=False)
    record["returncode"] = result.returncode
    record["status"] = "completed" if result.returncode == 0 else "failed"
    record["stdout_tail"] = result.stdout[-2000:]
    record["stderr_tail"] = result.stderr[-2000:]
    record.update(summarize_trace(trace_path))
    return record


def build_summary(args: argparse.Namespace, records: list[dict[str, Any]], output_root: Path, patterns: list[tuple[str, str]]) -> dict[str, Any]:
    battle_candidates = [
        f"{record['state_id']}:{record['pattern_id']}"
        for record in records
        if record.get("battle_entry_candidate")
    ]
    command_candidates = [
        f"{record['state_id']}:{record['pattern_id']}"
        for record in records
        if record.get("command_fixture_candidate")
    ]
    return {
        "schema": "earthbound-decomp.c2-battle-fixture-scout.v1",
        "status": "fixture_scout_completed",
        "output_root": manifest_path(output_root),
        "frame_limit": args.frame_limit,
        "timeout": args.timeout,
        "scout_addresses": [{"label": label, "role": role} for label, _, role in SCOUT_ADDRESSES],
        "watch_ranges": [{"id": watch_id, "address": f"${address:04X}", "bytes": byte_count} for watch_id, address, byte_count in WATCH_RANGES],
        "patterns": [{"id": pattern_id, "input_pattern": pattern} for pattern_id, pattern in patterns],
        "summary": {
            "run_count": len(records),
            "completed_count": sum(1 for record in records if record.get("status") == "completed"),
            "failed_count": sum(1 for record in records if record.get("status") == "failed"),
            "missing_state_count": sum(1 for record in records if record.get("status") == "missing_state"),
            "battle_entry_candidate_count": len(battle_candidates),
            "command_fixture_candidate_count": len(command_candidates),
            "battle_entry_candidates": battle_candidates,
            "command_fixture_candidates": command_candidates,
            "source_promotion_allowed": False,
            "behavior_change_allowed": False,
        },
        "records": records,
    }


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    lua_path = output_root / "fixture-scout.lua"
    render_lua(lua_path)
    mesen = resolve_mesen(args.mesen)
    rom = rom_tools.find_rom(args.rom)
    states = candidate_states(args)
    patterns = parse_patterns(args)
    records: list[dict[str, Any]] = []
    for state_index, state in enumerate(states, start=1):
        state_id = f"{state_index:02d}-{slug(state.stem)}"
        for pattern_id, pattern in patterns:
            output_dir = output_root / state_id / pattern_id
            record = run_scout(
                state=state,
                pattern_id=pattern_id,
                pattern=pattern,
                output_dir=output_dir,
                lua_path=lua_path,
                mesen=mesen,
                rom=rom,
                frame_limit=args.frame_limit,
                timeout=args.timeout,
            )
            record["state_id"] = state_id
            records.append(record)
    summary = build_summary(args, records, output_root, patterns)
    summary_path = output_root / "fixture-scout-summary.json"
    write_json(summary_path, summary)
    print(
        "C2 battle fixture scout: "
        f"{summary['summary']['run_count']} runs, "
        f"{summary['summary']['battle_entry_candidate_count']} battle-entry candidates, "
        f"{summary['summary']['command_fixture_candidate_count']} command candidates"
    )
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
