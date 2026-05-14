#!/usr/bin/env python3
"""Build ignored Mesen runner assets for first-pass C2 battle trace oracles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HANDOFF = ROOT / "manifests" / "c2-battle-trace-oracle-emulator-handoff.json"
DEFAULT_OUTPUT_ROOT = ROOT / "build" / "c2" / "battle-trace-oracles" / "mesen-runner-assets"
INDEX_NAME = "index.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ignored C2 oracle Mesen runner assets.")
    parser.add_argument("--handoff", default=str(DEFAULT_HANDOFF), help="C2 battle trace-oracle emulator handoff JSON.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Ignored runner asset output root.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def repo_path(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def cpu_address_value(address: str) -> int | None:
    if ":" not in address:
        return None
    bank_text, offset_text = address.split(":", 1)
    try:
        return (int(bank_text, 16) << 16) | int(offset_text, 16)
    except ValueError:
        return None


def wram_address_value(address_or_symbol: str) -> int | None:
    text = address_or_symbol.strip()
    if not text.startswith("$"):
        return None
    hex_text = ""
    for char in text[1:]:
        if char in "0123456789abcdefABCDEF":
            hex_text += char
        else:
            break
    if not hex_text:
        return None
    value = int(hex_text, 16)
    return value if 0 <= value <= 0x1FFFF else None


def lua_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def runner_command(job: dict[str, Any], lua_path: Path, *, output_root: Path) -> str:
    paths = job["output_paths"]
    trace_path = repo_path(paths["raw_trace_path"])
    result_path = repo_path(paths["result_path"])
    job_path = repo_path(paths["job_path"])
    lua_text = repo_relative(lua_path).replace("/", "\\")
    trace_text = repo_relative(trace_path).replace("/", "\\")
    result_text = repo_relative(result_path).replace("/", "\\")
    job_text = repo_relative(job_path).replace("/", "\\")
    return (
        '$env:C2_ORACLE_TRACE_OUT = "{trace}"; '
        '$env:C2_ORACLE_RESULT_OUT = "{result}"; '
        '$env:C2_ORACLE_JOB_PATH = "{job}"; '
        '$env:C2_ORACLE_STATE_PATH = "<local-only save state>"; '
        '$env:C2_ORACLE_FRAME_LIMIT = "3600"; '
        '& "<path-to-Mesen.exe>" --testRunner --enableStdout --doNotSaveSettings '
        '--debug.scriptWindow.allowIoOsAccess=true "{lua}" "<path-to-earthbound-us.sfc>"'
    ).format(trace=trace_text, result=result_text, job=job_text, lua=lua_text)


def external_batch_command(job: dict[str, Any]) -> str:
    return (
        "python tools\\run_c2_battle_trace_oracle_batch.py "
        f"--job-id {job['job_id']} --mode external --force "
        "--external <external-c2-oracle-harness> --job {job} --result {result} --raw-trace {raw_trace}"
    )


def result_assembler_command(job: dict[str, Any]) -> str:
    return (
        "python tools\\build_c2_battle_trace_oracle_result_from_evidence.py "
        f"--job-id {job['job_id']} "
        "--status unresolved --classification unresolved "
        "--classification-rationale \"review pending\""
    )


def result_template(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "earthbound-decomp.c2-battle-trace-oracle-result.v1",
        "job_id": job["job_id"],
        "oracle_id": job["oracle_id"],
        "status": "unresolved",
        "contract_classification": "unresolved",
        "observed_addresses": [],
        "captured_fields": {},
        "promotion_allowed_by_result": False,
        "behavior_change_allowed": False,
        "evidence": {
            "trace_path": job["output_paths"]["raw_trace_path"],
            "classification_rationale": "Runner asset template only; replace after reviewed emulator trace evidence exists.",
            "harness_name": "manual_or_external_c2_battle_trace_oracle_harness",
            "harness_version": "pending",
            "job_path": job["output_paths"]["job_path"],
        },
    }


def route_group_probe_breakpoints(job: dict[str, Any]) -> list[dict[str, Any]]:
    base_addresses = {str(record.get("address")) for record in job.get("breakpoints", [])}
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group_id, group in job.get("route_groups", {}).items():
        for address in group.get("probe_breakpoint_hints", []):
            address_text = str(address)
            if address_text in base_addresses or address_text in seen:
                continue
            seen.add(address_text)
            records.append(
                {
                    "address": address_text,
                    "address_space": "snes_cpu_bus",
                    "hit_policy": "capture_registers_dp_wram_then_continue",
                    "required_for_minimum_capture": False,
                    "probe_source": "route_group_hint",
                    "route_group": str(group_id),
                    "route_group_status": str(group.get("status", "")),
                }
            )
    return records


def runner_job(job: dict[str, Any], lua_path: Path, checklist_path: Path, template_path: Path) -> dict[str, Any]:
    paths = job["output_paths"]
    route_gap_breakpoints = route_group_probe_breakpoints(job)
    return {
        "schema": "earthbound-decomp.c2-battle-trace-oracle-runner-job.v1",
        "status": "runner_asset_generated_no_execution",
        "job_id": job["job_id"],
        "oracle_id": job["oracle_id"],
        "scenario": job["scenario"],
        "minimum_hits": job["minimum_hits"],
        "route_groups": job.get("route_groups", {}),
        "breakpoints": job["breakpoints"],
        "route_gap_probe_breakpoints": route_gap_breakpoints,
        "watch_ranges": job["watch_ranges"],
        "extra_trace_fields": job["extra_trace_fields"],
        "capture_fields": job["capture_fields"],
        "acceptance_criteria": job["acceptance_criteria"],
        "output_paths": paths,
        "assets": {
            "mesen_lua_skeleton": repo_relative(lua_path),
            "operator_checklist": repo_relative(checklist_path),
            "result_template": repo_relative(template_path),
        },
        "commands": {
            "mesen_test_runner_template": runner_command(job, lua_path, output_root=DEFAULT_OUTPUT_ROOT),
            "mesen_wrapper_dry_run": (
                "python tools\\run_c2_battle_trace_oracle_mesen.py "
                f"--job-id {job['job_id']} --dry-run"
            ),
            "mesen_wrapper_trace_run": (
                "python tools\\run_c2_battle_trace_oracle_mesen.py "
                f"--job-id {job['job_id']} --state \"<local-only save state>\" --frame-limit 3600"
            ),
            "external_batch_template": external_batch_command(job),
            "reviewed_result_template": result_assembler_command(job),
            "validate_result": job["result_validator"],
            "collect_results": job["result_collector"],
        },
        "proof_gate": job["proof_gate"],
    }


def render_lua(job: dict[str, Any]) -> str:
    breakpoints = []
    for record in [*job["breakpoints"], *route_group_probe_breakpoints(job)]:
        value = cpu_address_value(str(record["address"]))
        if value is None:
            continue
        breakpoints.append(
            {
                "label": record["address"],
                "address": value,
                "required": bool(record["required_for_minimum_capture"]),
                "probe_source": record.get("probe_source", "oracle_breakpoint"),
                "route_group": record.get("route_group", ""),
            }
        )
    watch_ranges = []
    for record in job["watch_ranges"]:
        value = wram_address_value(str(record["address_or_symbol"]))
        if value is None:
            continue
        watch_ranges.append(
            {
                "id": record["id"],
                "address": value,
                "bytes": int(record["bytes"]),
                "purpose": record["purpose"],
            }
        )

    breakpoint_lines = [
        (
            f'  {{ label = {lua_string(item["label"])}, address = 0x{item["address"]:06X}, '
            f'required = {str(item["required"]).lower()}, probeSource = {lua_string(item["probe_source"])}, '
            f'routeGroup = {lua_string(item["route_group"])} }},'
        )
        for item in breakpoints
    ]
    watch_lines = [
        f'  {{ id = {lua_string(item["id"])}, address = 0x{item["address"]:04X}, bytes = {item["bytes"]}, purpose = {lua_string(item["purpose"])} }},'
        for item in watch_ranges
    ]
    return "\n".join(
        [
            "-- Generated by tools/build_c2_battle_trace_oracle_runner_assets.py",
            "-- Thin Mesen testRunner skeleton for a C2 battle trace-oracle job.",
            "-- It writes raw JSONL trace events only. Reviewed result JSON must be",
            "-- emitted separately and validated before any source-facing promotion.",
            "",
            f"local oracleId = {lua_string(job['oracle_id'])}",
            f"local jobId = {lua_string(job['job_id'])}",
            f"local scenarioName = {lua_string(job['scenario']['scenario_name'])}",
            f"local jobPath = os.getenv(\"C2_ORACLE_JOB_PATH\") or {lua_string(job['output_paths']['job_path'])}",
            f"local outPath = os.getenv(\"C2_ORACLE_TRACE_OUT\") or {lua_string(job['output_paths']['raw_trace_path'])}",
            "local statePath = os.getenv(\"C2_ORACLE_STATE_PATH\")",
            "local frameLimit = tonumber(os.getenv(\"C2_ORACLE_FRAME_LIMIT\") or \"3600\")",
            "local inputPatternSpec = os.getenv(\"C2_ORACLE_INPUT_PATTERN\") or \"neutral:3600\"",
            "local bootstrapInputPatternSpec = os.getenv(\"C2_ORACLE_BOOTSTRAP_INPUT_PATTERN\") or \"\"",
            "local bootstrapFrameCount = tonumber(os.getenv(\"C2_ORACLE_BOOTSTRAP_FRAME_COUNT\") or \"0\") or 0",
            "local wramPatchSpec = os.getenv(\"C2_ORACLE_WRAM_PATCHES\") or \"\"",
            "local wramPatchOnHitSpec = os.getenv(\"C2_ORACLE_WRAM_PATCHES_ON_HIT\") or \"\"",
            "local wramPatchTiming = os.getenv(\"C2_ORACLE_WRAM_PATCH_TIMING\") or \"initial\"",
            "local runnerVersion = os.getenv(\"C2_ORACLE_RUNNER_VERSION\") or \"mesen-runner-assets-v1\"",
            "local out = assert(io.open(outPath, \"w\"))",
            "local wram = emu.memType.snesWorkRam",
            "local snesMemory = emu.memType.snesMemory",
            "local snesCpu = emu.cpuType.snes",
            "",
            "local breakpoints = {",
            *breakpoint_lines,
            "}",
            "",
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
            "local function readFile(path)",
            "  local f = assert(io.open(path, \"rb\")); local d = f:read(\"*a\"); f:close(); return d",
            "end",
            "local function rb(addr) return emu.read(addr, wram, false) end",
            "local function rw(addr) return rb(addr) + (rb(addr + 1) * 0x100) end",
            "local function lowBank(hi) return hi % 0x100 end",
            "local function farPtr(lo, hi) return string.format(\"%02X:%04X\", lowBank(hi), lo) end",
            "local function readBytes(addr, count)",
            "  local parts = {}",
            "  for i = 0, count - 1 do parts[#parts + 1] = string.format(\"%02X\", rb((addr + i) % 0x10000)) end",
            "  return table.concat(parts, \" \")",
            "end",
            "local function wb(addr, value)",
            "  local ok = pcall(function() emu.write(addr, value, wram, false) end)",
            "  if not ok then emu.write(addr, value, wram) end",
            "end",
            "local function wrap16(n) return n % 0x10000 end",
            "local function dpWord(cpu, offset) return rw((cpu.dp + offset) % 0x10000) end",
            "local function dpByte(cpu, offset) return rb((cpu.dp + offset) % 0x10000) end",
            "local function stackByte(cpu, offset) return rb(wrap16(cpu.sp + offset)) end",
            "local function stackWord(cpu, offset) return stackByte(cpu, offset) + (stackByte(cpu, offset + 1) * 0x100) end",
            "local function stackBytes(cpu, offset, count)",
            "  local parts = {}",
            "  for i = 0, count - 1 do parts[#parts + 1] = string.format(\"%02X\", stackByte(cpu, offset + i)) end",
            "  return table.concat(parts, \" \")",
            "end",
            "local function targetDomain(addr)",
            "  if addr >= 0x9FFA and addr < 0xA048 then return \"battle_selection_snapshot\" end",
            "  if addr >= 0xA21C and addr < 0xA2DC then return \"enemy_target_rows\" end",
            "  if addr >= 0x9FAC and addr < 0xA21C then return \"battler_rows\" end",
            "  if addr >= 0x99CE and addr < 0xA588 then return \"live_battler_slot_rows\" end",
            "  return \"unknown\"",
            "end",
            "local function battleSourceSlotBase(slotId)",
            "  if slotId < 1 or slotId > 32 then return nil end",
            "  return 0x99CE + ((slotId - 1) * 0x5F)",
            "end",
            "local function sourceSlotHex(slotId)",
            "  local base = battleSourceSlotBase(slotId)",
            "  if base == nil then return nil, nil end",
            "  return base, readBytes(base, 0x5F)",
            "end",
            "local function textDpFields(cpu)",
            "  local primaryLo = dpWord(cpu, 0x0E)",
            "  local primaryHi = dpWord(cpu, 0x10)",
            "  local payloadLo = dpWord(cpu, 0x12)",
            "  local payloadHi = dpWord(cpu, 0x14)",
            "  return primaryLo, primaryHi, payloadLo, payloadHi",
            "end",
            "local function stateValue(state, key, fallback)",
            "  local value = state[key]",
            "  if value == nil then return fallback end",
            "  return value",
            "end",
            "local function cpuSnapshot()",
            "  local ok, state = pcall(function() return emu.getState() end)",
            "  if not ok or type(state) ~= \"table\" then",
            "    return { a = -1, x = -1, y = -1, db = -1, dp = 0, ps = -1, sp = -1, pc = -1, k = -1, cycle = -1 }",
            "  end",
            "  return {",
            "    a = stateValue(state, \"cpu.a\", -1),",
            "    x = stateValue(state, \"cpu.x\", -1),",
            "    y = stateValue(state, \"cpu.y\", -1),",
            "    db = stateValue(state, \"cpu.dbr\", -1),",
            "    dp = stateValue(state, \"cpu.d\", 0),",
            "    ps = stateValue(state, \"cpu.ps\", -1),",
            "    sp = stateValue(state, \"cpu.sp\", -1),",
            "    pc = stateValue(state, \"cpu.pc\", -1),",
            "    k = stateValue(state, \"cpu.k\", -1),",
            "    cycle = stateValue(state, \"cpu.cycleCount\", -1)",
            "  }",
            "end",
            "local function trim(s) return (s:gsub(\"^%s+\", \"\"):gsub(\"%s+$\", \"\")) end",
            "local function parseNumber(text)",
            "  text = trim(text or \"\")",
            "  if text:match(\"^0[xX]\") then return tonumber(text) end",
            "  if text:match(\"^%$\") then return tonumber(text:sub(2), 16) end",
            "  return tonumber(text, 16) or tonumber(text)",
            "end",
            "local function dynamicBase(name)",
            "  if name == \"selectedTarget\" then return rw(0xA972) end",
            "  if name == \"activeAttacker\" then return rw(0xA970) end",
            "  return nil",
            "end",
            "local function resolvePatchAddress(patch)",
            "  if patch.address ~= nil then return patch.address end",
            "  local text = trim(patch.addressText or \"\")",
            "  local name, offsetText = text:match(\"^([%a_][%w_]*)%s*%+%s*(.+)$\")",
            "  if name ~= nil then",
            "    local base = dynamicBase(name)",
            "    local offset = parseNumber(offsetText)",
            "    if base ~= nil and offset ~= nil then return wrap16(base + offset) end",
            "  end",
            "  local base = dynamicBase(text)",
            "  if base ~= nil then return base end",
            "  return nil",
            "end",
            "local function parseWramPatchSpec(spec)",
            "  local patches = {}",
            "  if spec == nil or trim(spec) == \"\" then return patches end",
            "  for segment in string.gmatch(spec, \"([^;]+)\") do",
            "    local addrText, bytesText = segment:match(\"^%s*([^:=]+)%s*[:=]%s*(.-)%s*$\")",
            "    local addr = parseNumber(addrText)",
            "    local bytes = {}",
            "    if bytesText ~= nil then",
            "      for token in string.gmatch(bytesText, \"[%x][%x]\") do bytes[#bytes + 1] = tonumber(token, 16) end",
            "    end",
            "    if (addr ~= nil or trim(addrText or \"\") ~= \"\") and #bytes > 0 then patches[#patches + 1] = { address = addr, addressText = trim(addrText or \"\"), bytes = bytes, source = trim(segment) }",
            "    else writeJson({ type = \"runner_error\", oracleId = oracleId, jobId = jobId, name = \"parseWramPatchSpec\", message = \"invalid WRAM patch\", segment = tostring(segment) }) end",
            "  end",
            "  return patches",
            "end",
            "local wramPatches = parseWramPatchSpec(wramPatchSpec)",
            "local function parseWramPatchOnHitSpec(spec)",
            "  local patches = {}",
            "  if spec == nil or trim(spec) == \"\" then return patches end",
            "  for segment in string.gmatch(spec, \"([^;]+)\") do",
            "    local label, patchSpec = segment:match(\"^%s*([^=]+)%s*=%s*(.-)%s*$\")",
            "    local parsed = parseWramPatchSpec(patchSpec)",
            "    if label ~= nil and #parsed > 0 then",
            "      for _, patch in ipairs(parsed) do",
            "        patch.label = trim(label)",
            "        patch.source = trim(segment)",
            "        patches[#patches + 1] = patch",
            "      end",
            "    else writeJson({ type = \"runner_error\", oracleId = oracleId, jobId = jobId, name = \"parseWramPatchOnHitSpec\", message = \"invalid on-hit WRAM patch\", segment = tostring(segment) }) end",
            "  end",
            "  return patches",
            "end",
            "local wramPatchesOnHit = parseWramPatchOnHitSpec(wramPatchOnHitSpec)",
            "local wramPatchesApplied = false",
            "local wramPatchesOnHitApplied = {}",
            "local function applyWramPatches(reason)",
            "  if wramPatchesApplied then return end",
            "  wramPatchesApplied = true",
            "  for index, patch in ipairs(wramPatches) do",
            "    local address = resolvePatchAddress(patch)",
            "    if address == nil then writeJson({ type = \"runner_error\", oracleId = oracleId, jobId = jobId, name = \"applyWramPatches\", message = \"unresolved WRAM patch address\", source = patch.source }) else",
            "    local before = readBytes(address, #patch.bytes)",
            "    for i, value in ipairs(patch.bytes) do wb((address + i - 1) % 0x10000, value) end",
            "    writeJson({ type = \"wram_patch\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName, index = index, reason = reason, address = hex(address), addressSource = patch.addressText, bytes = #patch.bytes, beforeHex = before, afterHex = readBytes(address, #patch.bytes), source = patch.source })",
            "    end",
            "  end",
            "end",
            "local function applyDeferredWramPatches(reason)",
            "  if wramPatchTiming == \"first_breakpoint\" then applyWramPatches(reason) end",
            "end",
            "local function applyWramPatchesOnHit(label)",
            "  for index, patch in ipairs(wramPatchesOnHit) do",
            "    if patch.label == label and not wramPatchesOnHitApplied[index] then",
            "      wramPatchesOnHitApplied[index] = true",
            "      local address = resolvePatchAddress(patch)",
            "      if address == nil then writeJson({ type = \"runner_error\", oracleId = oracleId, jobId = jobId, name = \"applyWramPatchesOnHit\", message = \"unresolved WRAM patch address\", source = patch.source }) else",
            "      local before = readBytes(address, #patch.bytes)",
            "      for i, value in ipairs(patch.bytes) do wb((address + i - 1) % 0x10000, value) end",
            "      writeJson({ type = \"wram_patch\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName, index = index, reason = \"on_hit:\" .. label, address = hex(address), addressSource = patch.addressText, bytes = #patch.bytes, beforeHex = before, afterHex = readBytes(address, #patch.bytes), source = patch.source })",
            "      end",
            "    end",
            "  end",
            "end",
            "local function inputForAtom(atom)",
            "  atom = trim(atom or \"\")",
            "  if atom == \"neutral\" or atom == \"none\" or atom == \"\" then return {}",
            "  elseif atom == \"right\" then return { right = true }",
            "  elseif atom == \"left\" then return { left = true }",
            "  elseif atom == \"up\" then return { up = true }",
            "  elseif atom == \"down\" then return { down = true }",
            "  elseif atom == \"down_right\" or atom == \"diag_down_right\" then return { down = true, right = true }",
            "  elseif atom == \"up_right\" or atom == \"diag_up_right\" then return { up = true, right = true }",
            "  elseif atom == \"up_left\" or atom == \"diag_up_left\" then return { up = true, left = true }",
            "  elseif atom == \"down_left\" or atom == \"diag_down_left\" then return { down = true, left = true }",
            "  elseif atom == \"a\" or atom == \"press_a\" then return { a = true }",
            "  elseif atom == \"start\" or atom == \"press_start\" then return { start = true }",
            "  elseif atom == \"a_start\" then return { a = true, start = true }",
            "  end",
            "  writeJson({ type = \"runner_error\", oracleId = oracleId, jobId = jobId, name = \"inputForAtom\", message = \"unsupported input atom\", atom = atom })",
            "  out:close()",
            "  emu.stop(2)",
            "  return {}",
            "end",
            "local function parsePattern(pattern)",
            "  local parsed = {}",
            "  local total = 0",
            "  if pattern == nil or trim(pattern) == \"\" then pattern = \"neutral:\" .. tostring(frameLimit) end",
            "  for segment in string.gmatch(pattern, \"([^,]+)\") do",
            "    local atom, frames = segment:match(\"^%s*([%w_]+)%s*:%s*(%d+)%s*$\")",
            "    if atom == nil then",
            "      writeJson({ type = \"runner_error\", oracleId = oracleId, jobId = jobId, name = \"parsePattern\", message = \"invalid input segment\", segment = tostring(segment) })",
            "      out:close()",
            "      emu.stop(2)",
            "      return {}, 0",
            "    end",
            "    frames = tonumber(frames)",
            "    if frames == nil or frames <= 0 then",
            "      writeJson({ type = \"runner_error\", oracleId = oracleId, jobId = jobId, name = \"parsePattern\", message = \"invalid frame count\", segment = tostring(segment) })",
            "      out:close()",
            "      emu.stop(2)",
            "      return {}, 0",
            "    end",
            "    inputForAtom(atom)",
            "    table.insert(parsed, { atom = trim(atom), frames = frames })",
            "    total = total + frames",
            "  end",
            "  return parsed, total",
            "end",
            "local inputPattern, inputPatternFrames = parsePattern(inputPatternSpec)",
            "local bootstrapInputPattern, bootstrapInputPatternFrames = parsePattern(bootstrapInputPatternSpec ~= \"\" and bootstrapInputPatternSpec or \"neutral:1\")",
            "local function inputForParsedPattern(pattern, patternFrames, frameNumber)",
            "  if #pattern == 0 or patternFrames <= 0 then return {} end",
            "  local cursor = frameNumber % patternFrames",
            "  local total = 0",
            "  for _, segment in ipairs(pattern) do",
            "    total = total + segment.frames",
            "    if cursor < total then return inputForAtom(segment.atom) end",
            "  end",
            "  return {}",
            "end",
            "local function inputForFrame(frameNumber)",
            "  return inputForParsedPattern(inputPattern, inputPatternFrames, frameNumber)",
            "end",
            "local function bootstrapInputForFrame(frameNumber)",
            "  return inputForParsedPattern(bootstrapInputPattern, bootstrapInputPatternFrames, frameNumber)",
            "end",
            "local function emitWatches(eventType, frame, pcLabel)",
            "  for _, watch in ipairs(watchRanges) do",
            "    local readAddress = watch.address",
            "    local pointerAddress = nil",
            "    if watch.id == \"selected_target_row\" then",
            "      pointerAddress = watch.address",
            "      readAddress = rw(watch.address)",
            "    end",
            "    writeJson({",
            "      type = eventType, oracleId = oracleId, jobId = jobId, scenarioName = scenarioName,",
            "      frame = frame, pc = pcLabel, watchId = watch.id, address = hex(readAddress),",
            "      pointerAddress = pointerAddress and hex(pointerAddress) or nil,",
            "      bytes = watch.bytes, purpose = watch.purpose, valueHex = readBytes(readAddress, watch.bytes)",
            "    })",
            "  end",
            "end",
            "local function emitStateSnapshot(reason)",
            "  local activePtr = rw(0xA970)",
            "  local targetPtr = rw(0xA972)",
            "  writeJson({",
            "    type = \"scenario_state_snapshot\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName,",
            "    frame = frame, reason = reason,",
            "    partyPointerTableHex = readBytes(0x4DC8, 12),",
            "    partyCountWord = hex(rw(0x4DBC)),",
            "    battleEntryStateHex = readBytes(0x986F, 48),",
            "    battleWindowStateHex = readBytes(0x88E0, 128),",
            "    activeAttackerPointer = hex(activePtr), activeAttackerDomain = targetDomain(activePtr), activeAttackerRowHex = readBytes(activePtr, 0x4E),",
            "    selectedTargetPointer = hex(targetPtr), selectedTargetDomain = targetDomain(targetPtr), selectedTargetRowHex = readBytes(targetPtr, 0x4E),",
            "    currentTargetMaskHex = readBytes(0xA96C, 4),",
            "    textPayloadSlotsHex = readBytes(0x9D10, 8),",
            "    rollingHpStateHex = readBytes(0x9D11, 16)",
            "  })",
            "end",
            "",
            "local loadedState = statePath == nil or statePath == \"\" or statePath == \"<local-only save state>\"",
            "local frame = 0",
            "local totalHits = 0",
            "local requiredHitCount = 0",
            "local requiredHitLabels = \"\"",
            "local stateLoadCallbackRef = nil",
            "",
            "for _, bp in ipairs(breakpoints) do if bp.required then requiredHitCount = requiredHitCount + 1 end end",
            "writeJson({ type = \"runner_start\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName, jobPath = jobPath, runnerVersion = runnerVersion, requiredHitCount = requiredHitCount, inputPattern = inputPatternSpec, inputPatternFrames = inputPatternFrames, bootstrapInputPattern = bootstrapInputPatternSpec, bootstrapFrameCount = bootstrapFrameCount, wramPatchTiming = wramPatchTiming })",
            "if bootstrapFrameCount > 0 then",
            "  writeJson({ type = \"bootstrap_start\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName, frame = frame, inputPattern = bootstrapInputPatternSpec, frameCount = bootstrapFrameCount })",
            "end",
            "",
            "local function loadInitialStateFromExec()",
            "  if loadedState then return end",
            "  local state = readFile(statePath)",
            "  writeJson({ type = \"before_state_load\", oracleId = oracleId, jobId = jobId, statePath = statePath, bytes = #state })",
            "  local ok = emu.loadSavestate(state)",
            "  loadedState = true",
            "  if stateLoadCallbackRef ~= nil then",
            "    emu.removeMemoryCallback(stateLoadCallbackRef, emu.callbackType.exec, 0x008000, 0xFFFFFF, snesCpu, snesMemory)",
            "  end",
            "  writeJson({ type = \"state_load\", oracleId = oracleId, jobId = jobId, ok = ok })",
            "  if wramPatchTiming == \"initial\" then applyWramPatches(\"after_state_load\") end",
            "  emitStateSnapshot(\"after_state_load\")",
            "end",
            "",
            "if loadedState and wramPatchTiming == \"initial\" then applyWramPatches(\"initial_loaded_state\") end",
            "if loadedState then emitStateSnapshot(\"initial_loaded_state\") end",
            "",
            "if not loadedState then",
            "  stateLoadCallbackRef = emu.addMemoryCallback(loadInitialStateFromExec, emu.callbackType.exec, 0x008000, 0xFFFFFF, snesCpu, snesMemory)",
            "end",
            "",
            "local function makeBreakpoint(bp)",
            "  return function()",
            "    totalHits = totalHits + 1",
            "    if bp.required then requiredHitLabels = requiredHitLabels .. bp.label .. \";\" end",
            "    applyDeferredWramPatches(\"first_breakpoint:\" .. bp.label)",
            "    applyWramPatchesOnHit(bp.label)",
            "    local cpu = cpuSnapshot()",
            "    local targetPtr = rw(0xA972)",
            "    local textPrimaryLo, textPrimaryHi, textPayloadLo, textPayloadHi = textDpFields(cpu)",
            "    local dispatchDpCell = wrap16(cpu.dp + 0xBC)",
            "    local dispatchLo = rw(dispatchDpCell)",
            "    local dispatchHi = rw(wrap16(dispatchDpCell + 2))",
            "    local absoluteDispatchLo = rw(0x00BC)",
            "    local absoluteDispatchHi = rw(0x00BE)",
            "    local activeAttackerPtr = rw(0xA970)",
            "    local stackReturnWord = stackWord(cpu, 1)",
            "    local stackReturnBank = stackByte(cpu, 3)",
            "    local dp06 = dpWord(cpu, 0x06)",
            "    local dp08 = dpWord(cpu, 0x08)",
            "    local dp02 = dpWord(cpu, 0x02)",
            "    local dp0e = dpWord(cpu, 0x0E)",
            "    local dp00 = dpByte(cpu, 0x00)",
            "    local dp01 = dpByte(cpu, 0x01)",
            "    local dp14 = dpWord(cpu, 0x14)",
            "    local dp16 = dpWord(cpu, 0x16)",
            "    local dp18 = dpWord(cpu, 0x18)",
            "    local dp1a = dpWord(cpu, 0x1A)",
            "    local dp1e = dpWord(cpu, 0x1E)",
            "    local dp20 = dpWord(cpu, 0x20)",
            "    local dp22 = dpWord(cpu, 0x22)",
            "    local dp26 = dpWord(cpu, 0x26)",
            "    local dp28 = dpWord(cpu, 0x28)",
            "    local dp2a = dpWord(cpu, 0x2A)",
            "    local dp2c = dpWord(cpu, 0x2C)",
            "    local sourceBase, sourceHex = sourceSlotHex(cpu.a)",
            "    local xDest = wrap16(cpu.x)",
            "    local yDest = wrap16(cpu.y)",
            "    writeJson({",
            "      type = \"breakpoint_hit\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName,",
            "      frame = frame, pc = bp.label, address = hex(bp.address), required = bp.required,",
            "      probeSource = bp.probeSource, routeGroup = bp.routeGroup,",
            "      cpuA = hex(cpu.a), cpuX = hex(cpu.x), cpuY = hex(cpu.y), cpuDB = hex(cpu.db), cpuDP = hex(cpu.dp),",
            "      cpuP = hex(cpu.ps), cpuSP = hex(cpu.sp), cpuPC = hex(cpu.pc), cpuK = hex(cpu.k), cpuCycleCount = cpu.cycle,",
            "      directPageHex = readBytes(cpu.dp, 64), selectedTargetPointer = hex(targetPtr),",
            "      selectedTargetDomain = targetDomain(targetPtr),",
            "      selectedTargetRowHex = readBytes(targetPtr, 96),",
            "      activeAttackerPointer = hex(activeAttackerPtr),",
            "      activeAttackerDomain = targetDomain(activeAttackerPtr),",
            "      activeAttackerRowHex = readBytes(activeAttackerPtr, 0x4E),",
            "      stackWindowHex = stackBytes(cpu, 1, 12),",
            "      stackReturnRaw = farPtr(stackReturnWord, stackReturnBank),",
            "      stackReturnRtlAdjusted = farPtr(wrap16(stackReturnWord + 1), stackReturnBank),",
            "      dp0002Word = hex(dp02), dp0006Word = hex(dp06), dp0008Word = hex(dp08), dp000eWord = hex(dp0e),",
            "      dp0006Pointer = farPtr(dp06, dp08),",
            "      c1Dp0000SelectedTargetByte = string.format(\"0x%02X\", dp00),",
            "      c1Dp0001TextSubstitutionByte = string.format(\"0x%02X\", dp01),",
            "      c1Dp0014Word = hex(dp14), c1Dp0016Word = hex(dp16), c1Dp0014Pointer = farPtr(dp14, dp16),",
            "      c1Dp0018Word = hex(dp18), c1Dp001aWord = hex(dp1a), c1Dp0018Pointer = farPtr(dp18, dp1a),",
            "      c1Dp001eWord = hex(dp1e), c1Dp0020Word = hex(dp20), c1Dp001ePointer = farPtr(dp1e, dp20),",
            "      c1Dp0022Word = hex(dp22), c1Dp0026Word = hex(dp26), c1Dp0028Word = hex(dp28),",
            "      c1Dp002aActingSlotWord = hex(dp2a), c1Dp002cItemSlotWord = hex(dp2c),",
            "      b930SourceSlotBase = sourceBase and hex(sourceBase) or nil,",
            "      b930SourceSlotHex = sourceHex,",
            "      xDestinationBase = hex(xDest), xDestinationDomain = targetDomain(xDest), xDestinationHex = readBytes(xDest, 0x4E),",
            "      yDestinationBase = hex(yDest), yDestinationDomain = targetDomain(yDest), yDestinationHex = readBytes(yDest, 0x4E),",
            "      currentTargetMaskLo = hex(rw(0xA96C)), currentTargetMaskHi = hex(rw(0xA96E)),",
            "      currentTargetMaskHex = readBytes(0xA96C, 4),",
            "      battleBusyFlag1b9e = string.format(\"0x%02X\", rb(0x1B9E)),",
            "      effectCountdownAec2 = string.format(\"0x%02X\", rb(0xAEC2)),",
            "      effectPointerAeccAece = farPtr(rw(0xAECC), rw(0xAECE)),",
            "      effectStepStateHex = readBytes(0xAEC2, 0x24),",
            "      battlerNormalizationStateAa12 = hex(rw(0xAA12)),",
            "      delayedActionSlotsHex = readBytes(0x9E3C, 96),",
            "      dp00bcPointerCell = hex(dispatchDpCell),",
            "      dp00bcPointerHex = readBytes(dispatchDpCell, 4),",
            "      dp00bcPointer = farPtr(dispatchLo, dispatchHi),",
            "      dp00bcLo = hex(dispatchLo), dp00bcHi = hex(dispatchHi),",
            "      dispatchTargetPointerCell = hex(0x00BC),",
            "      dispatchTargetPointerHex = readBytes(0x00BC, 4),",
            "      dispatchTargetPointer = farPtr(absoluteDispatchLo, absoluteDispatchHi),",
            "      dispatchTargetLo = hex(absoluteDispatchLo), dispatchTargetHi = hex(absoluteDispatchHi),",
            "      absolute00bcPointerHex = readBytes(0x00BC, 4),",
            "      absolute00bcPointer = farPtr(absoluteDispatchLo, absoluteDispatchHi),",
            "      absolute00bcLo = hex(absoluteDispatchLo), absolute00bcHi = hex(absoluteDispatchHi),",
            "      callerDpPrimaryTextPointer = farPtr(textPrimaryLo, textPrimaryHi),",
            "      callerDpPrimaryTextLo = hex(textPrimaryLo), callerDpPrimaryTextHi = hex(textPrimaryHi),",
            "      callerDpPayloadPointer = farPtr(textPayloadLo, textPayloadHi),",
            "      callerDpPayloadLo = hex(textPayloadLo), callerDpPayloadHi = hex(textPayloadHi),",
            "      wram9d11 = hex(rb(0x9D11)), wram9d12 = hex(rw(0x9D12)), wram9d14 = hex(rw(0x9D14)),",
            "      textPayloadSlotsHex = readBytes(0x9D10, 8)",
            "    })",
            "    emitWatches(\"watch_snapshot\", frame, bp.label)",
            "    if bp.routeGroup == \"snapshot_export\" and bp.label ~= \"C2:B930\" then",
            "      local returnAddress = bp.address + 4",
            "      local preA = cpu.a",
            "      local preX = xDest",
            "      local preY = yDest",
            "      local preSourceBase = sourceBase",
            "      local preSourceHex = sourceHex",
            "      local postRef = nil",
            "      postRef = emu.addMemoryCallback(function()",
            "        local postCpu = cpuSnapshot()",
            "        writeJson({",
            "          type = \"post_call_snapshot\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName,",
            "          frame = frame, pc = \"return_from:\" .. bp.label, callPc = bp.label, resolvedTarget = \"C2:B930\",",
            "          returnAddress = farPtr(returnAddress % 0x10000, math.floor(returnAddress / 0x10000)),",
            "          preCpuA = hex(preA), preCpuX = hex(preX), preCpuY = hex(preY),",
            "          postCpuA = hex(postCpu.a), postCpuX = hex(postCpu.x), postCpuY = hex(postCpu.y),",
            "          sourceSlotBase = preSourceBase and hex(preSourceBase) or nil,",
            "          sourceSlotHex = preSourceHex,",
            "          xDestinationBase = hex(preX), xDestinationDomain = targetDomain(preX), xDestinationAfterHex = readBytes(preX, 0x4E),",
            "          yDestinationBase = hex(preY), yDestinationDomain = targetDomain(preY), yDestinationAfterHex = readBytes(preY, 0x4E),",
            "          directPageHexAfter = readBytes(postCpu.dp, 64),",
            "          activeAttackerPointer = hex(rw(0xA970)), activeAttackerRowHex = readBytes(rw(0xA970), 0x4E),",
            "          selectedTargetPointer = hex(rw(0xA972)), selectedTargetRowHex = readBytes(rw(0xA972), 0x4E)",
            "        })",
            "        emitWatches(\"post_call_watch_snapshot\", frame, \"return_from:\" .. bp.label)",
            "        if postRef ~= nil then",
            "          emu.removeMemoryCallback(postRef, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "        end",
            "      end, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "    end",
            "    if bp.label == \"C2:B930\" then",
            "      local returnAddress = (stackReturnBank * 0x10000) + wrap16(stackReturnWord + 1)",
            "      local preA = cpu.a",
            "      local preX = xDest",
            "      local preY = yDest",
            "      local preSourceBase = sourceBase",
            "      local postRef = nil",
            "      postRef = emu.addMemoryCallback(function()",
            "        local postCpu = cpuSnapshot()",
            "        writeJson({",
            "          type = \"post_call_snapshot\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName,",
            "          frame = frame, pc = \"return_from:C2:B930\", callPc = bp.label, returnAddress = farPtr(wrap16(stackReturnWord + 1), stackReturnBank),",
            "          preCpuA = hex(preA), preCpuX = hex(preX), preCpuY = hex(preY),",
            "          postCpuA = hex(postCpu.a), postCpuX = hex(postCpu.x), postCpuY = hex(postCpu.y),",
            "          sourceSlotBase = preSourceBase and hex(preSourceBase) or nil,",
            "          sourceSlotHex = preSourceBase and readBytes(preSourceBase, 0x5F) or nil,",
            "          xDestinationBase = hex(preX), xDestinationDomain = targetDomain(preX), xDestinationAfterHex = readBytes(preX, 0x4E),",
            "          yDestinationBase = hex(preY), yDestinationDomain = targetDomain(preY), yDestinationAfterHex = readBytes(preY, 0x4E)",
            "        })",
            "        emitWatches(\"post_call_watch_snapshot\", frame, \"return_from:C2:B930\")",
            "        if postRef ~= nil then",
            "          emu.removeMemoryCallback(postRef, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "        end",
            "      end, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "    end",
            "    if bp.label == \"C2:40A4\" then",
            "      local returnAddress = (stackReturnBank * 0x10000) + wrap16(stackReturnWord + 1)",
            "      local preA = cpu.a",
            "      local preX = xDest",
            "      local preY = yDest",
            "      local prePayloadLo = dp1e",
            "      local prePayloadHi = dp20",
            "      local preMaskLo = rw(0xA96C)",
            "      local preMaskHi = rw(0xA96E)",
            "      local postRef = nil",
            "      postRef = emu.addMemoryCallback(function()",
            "        local postCpu = cpuSnapshot()",
            "        local postTargetPtr = rw(0xA972)",
            "        local postAttackerPtr = rw(0xA970)",
            "        writeJson({",
            "          type = \"post_call_snapshot\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName,",
            "          frame = frame, pc = \"return_from:C2:40A4\", callPc = bp.label, returnAddress = farPtr(wrap16(stackReturnWord + 1), stackReturnBank),",
            "          preCpuA = hex(preA), preCpuX = hex(preX), preCpuY = hex(preY),",
            "          postCpuA = hex(postCpu.a), postCpuX = hex(postCpu.x), postCpuY = hex(postCpu.y),",
            "          callerFrameSecondPayloadPointer = farPtr(prePayloadLo, prePayloadHi),",
            "          currentActionPayloadPointer = farPtr(rw(0x00BC), rw(0x00BE)),",
            "          targetMaskBeforeLo = hex(preMaskLo), targetMaskBeforeHi = hex(preMaskHi),",
            "          targetMaskAfterLo = hex(rw(0xA96C)), targetMaskAfterHi = hex(rw(0xA96E)),",
            "          activeAttackerPointer = hex(postAttackerPtr), activeAttackerRowHex = readBytes(postAttackerPtr, 0x4E),",
            "          activeTargetPointer = hex(postTargetPtr), activeTargetRowHex = readBytes(postTargetPtr, 0x4E),",
            "          battleBusyFlag1b9e = string.format(\"0x%02X\", rb(0x1B9E)),",
            "          effectCountdownAec2 = string.format(\"0x%02X\", rb(0xAEC2)),",
            "          effectPointerAeccAece = farPtr(rw(0xAECC), rw(0xAECE)),",
            "          effectStepStateHex = readBytes(0xAEC2, 0x24)",
            "        })",
            "        emitWatches(\"post_call_watch_snapshot\", frame, \"return_from:C2:40A4\")",
            "        if postRef ~= nil then",
            "          emu.removeMemoryCallback(postRef, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "        end",
            "      end, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "    end",
            "    if bp.label == \"C2:724A\" then",
            "      local returnBank = lowBank(cpu.k)",
            "      local returnAddress = (returnBank * 0x10000) + wrap16(stackReturnWord + 1)",
            "      local preA = wrap16(cpu.a)",
            "      local preX = wrap16(cpu.x)",
            "      local preY = wrap16(cpu.y)",
            "      local preTargetPtr = rw(0xA972)",
            "      local preSlotAddress = wrap16(preA + preX + 0x1D)",
            "      local preSlotValue = rb(preSlotAddress)",
            "      local preRowHex = readBytes(preA, 0x4E)",
            "      local postRef = nil",
            "      postRef = emu.addMemoryCallback(function()",
            "        local postCpu = cpuSnapshot()",
            "        writeJson({",
            "          type = \"post_call_snapshot\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName,",
            "          frame = frame, pc = \"return_from:C2:724A\", callPc = bp.label, returnAddress = farPtr(wrap16(stackReturnWord + 1), returnBank),",
            "          preCpuA = hex(preA), preCpuX = hex(preX), preCpuY = hex(preY),",
            "          postCpuA = hex(postCpu.a), postCpuX = hex(postCpu.x), postCpuY = hex(postCpu.y),",
            "          statusWriterRowPointer = hex(preA), statusWriterRowBeforeHex = preRowHex, statusWriterRowAfterHex = readBytes(preA, 0x4E),",
            "          statusWriterSlotOffset = hex(wrap16(0x1D + preX)), statusWriterSlotAddress = hex(preSlotAddress),",
            "          statusWriterSlotBefore = string.format(\"0x%02X\", preSlotValue), statusWriterSlotAfter = string.format(\"0x%02X\", rb(preSlotAddress)),",
            "          statusWriterValueY = hex(preY), selectedTargetPointer = hex(preTargetPtr), selectedTargetRowHex = readBytes(preTargetPtr, 0x4E),",
            "          callerDpPrimaryTextPointer = farPtr(rw(wrap16(postCpu.dp + 0x0E)), rw(wrap16(postCpu.dp + 0x10))),",
            "          callerDpPayloadPointer = farPtr(rw(wrap16(postCpu.dp + 0x12)), rw(wrap16(postCpu.dp + 0x14))),",
            "          directPageHexAfter = readBytes(postCpu.dp, 64)",
            "        })",
            "        emitWatches(\"post_call_watch_snapshot\", frame, \"return_from:C2:724A\")",
            "        if postRef ~= nil then",
            "          emu.removeMemoryCallback(postRef, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "        end",
            "      end, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "    end",
            "    if bp.label == \"C2:721D\" then",
            "      local returnBank = lowBank(cpu.k)",
            "      local returnAddress = (returnBank * 0x10000) + wrap16(stackReturnWord + 1)",
            "      local preA = wrap16(cpu.a)",
            "      local preX = wrap16(cpu.x)",
            "      local preTargetPtr = rw(0xA972)",
            "      local preAttackerPtr = rw(0xA970)",
            "      local preReducerRowHex = readBytes(preA, 0x4E)",
            "      local postRef = nil",
            "      postRef = emu.addMemoryCallback(function()",
            "        local postCpu = cpuSnapshot()",
            "        writeJson({",
            "          type = \"post_call_snapshot\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName,",
            "          frame = frame, pc = \"return_from:C2:721D\", callPc = bp.label, returnAddress = farPtr(wrap16(stackReturnWord + 1), returnBank),",
            "          preCpuA = hex(preA), preCpuX = hex(preX), postCpuA = hex(postCpu.a), postCpuX = hex(postCpu.x), postCpuY = hex(postCpu.y),",
            "          reducerRowPointer = hex(preA), reducerAmount = hex(preX), reducerRowBeforeHex = preReducerRowHex, reducerRowAfterHex = readBytes(preA, 0x4E),",
            "          selectedTargetPointer = hex(preTargetPtr), selectedTargetRowHex = readBytes(preTargetPtr, 0x4E),",
            "          activeAttackerPointer = hex(preAttackerPtr), activeAttackerRowHex = readBytes(preAttackerPtr, 0x4E),",
            "          callerDpPrimaryTextPointer = farPtr(rw(wrap16(postCpu.dp + 0x0E)), rw(wrap16(postCpu.dp + 0x10))),",
            "          callerDpPayloadPointer = farPtr(rw(wrap16(postCpu.dp + 0x12)), rw(wrap16(postCpu.dp + 0x14))),",
            "          textPayloadSlotsHex = readBytes(0x9D10, 8)",
            "        })",
            "        emitWatches(\"post_call_watch_snapshot\", frame, \"return_from:C2:721D\")",
            "        if postRef ~= nil then",
            "          emu.removeMemoryCallback(postRef, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "        end",
            "      end, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "    end",
            "    if bp.label == \"C2:7191\" then",
            "      local returnBank = lowBank(cpu.k)",
            "      local returnAddress = (returnBank * 0x10000) + wrap16(stackReturnWord + 1)",
            "      local preA = wrap16(cpu.a)",
            "      local preX = wrap16(cpu.x)",
            "      local preRowHex = readBytes(preA, 0x4E)",
            "      local postRef = nil",
            "      postRef = emu.addMemoryCallback(function()",
            "        local postCpu = cpuSnapshot()",
            "        writeJson({",
            "          type = \"post_call_snapshot\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName,",
            "          frame = frame, pc = \"return_from:C2:7191\", callPc = bp.label, returnAddress = farPtr(wrap16(stackReturnWord + 1), returnBank),",
            "          preCpuA = hex(preA), preCpuX = hex(preX), postCpuA = hex(postCpu.a), postCpuX = hex(postCpu.x), postCpuY = hex(postCpu.y),",
            "          ppSetterRowPointer = hex(preA), ppSetterTargetValue = hex(preX), ppSetterRowBeforeHex = preRowHex, ppSetterRowAfterHex = readBytes(preA, 0x4E),",
            "          selectedTargetPointer = hex(rw(0xA972)), activeAttackerPointer = hex(rw(0xA970)),",
            "          selectedTargetRowHex = readBytes(rw(0xA972), 0x4E), activeAttackerRowHex = readBytes(rw(0xA970), 0x4E),",
            "          textPayloadSlotsHex = readBytes(0x9D10, 8)",
            "        })",
            "        emitWatches(\"post_call_watch_snapshot\", frame, \"return_from:C2:7191\")",
            "        if postRef ~= nil then",
            "          emu.removeMemoryCallback(postRef, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "        end",
            "      end, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "    end",
            "    if bp.label == \"C2:BC5C\" then",
            "      local returnBank = stackReturnBank",
            "      local returnAddress = (returnBank * 0x10000) + wrap16(stackReturnWord + 1)",
            "      local sourceRowsBeforeHex = readBytes(0x9FAC, 0x4E * 6)",
            "      local linkedLiveRowBeforeHex = readBytes(0x99CE, 0x5F)",
            "      local liveTransientBeforeHex = readBytes(0x99DE, 5)",
            "      local postRef = nil",
            "      postRef = emu.addMemoryCallback(function()",
            "        local postCpu = cpuSnapshot()",
            "        writeJson({",
            "          type = \"post_call_snapshot\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName,",
            "          frame = frame, pc = \"return_from:C2:BC5C\", callPc = bp.label, returnAddress = farPtr(wrap16(stackReturnWord + 1), returnBank),",
            "          postCpuA = hex(postCpu.a), postCpuX = hex(postCpu.x), postCpuY = hex(postCpu.y),",
            "          sourceRowsBeforeHex = sourceRowsBeforeHex, sourceRowsAfterHex = readBytes(0x9FAC, 0x4E * 6),",
            "          linkedLiveRowBeforeHex = linkedLiveRowBeforeHex, linkedLiveRowAfterHex = readBytes(0x99CE, 0x5F),",
            "          liveTransientBeforeHex = liveTransientBeforeHex, liveTransientAfterHex = readBytes(0x99DE, 5)",
            "        })",
            "        emitWatches(\"post_call_watch_snapshot\", frame, \"return_from:C2:BC5C\")",
            "        if postRef ~= nil then",
            "          emu.removeMemoryCallback(postRef, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "        end",
            "      end, emu.callbackType.exec, returnAddress, returnAddress, snesCpu, snesMemory)",
            "    end",
            "  end",
            "end",
            "",
            "for _, bp in ipairs(breakpoints) do",
            "  emu.addMemoryCallback(makeBreakpoint(bp), emu.callbackType.exec, bp.address, bp.address, snesCpu, snesMemory)",
            "end",
            "",
            "emu.addEventCallback(function()",
            "  if not loadedState then emu.setInput({}, 0); return end",
            "  if bootstrapFrameCount > 0 and frame < bootstrapFrameCount then",
            "    emu.setInput(bootstrapInputForFrame(frame), 0)",
            "  else",
            "    emu.setInput(inputForFrame(frame - bootstrapFrameCount), 0)",
            "  end",
            "end, emu.eventType.inputPolled)",
            "",
            "emu.addEventCallback(function()",
            "  frame = frame + 1",
            "  if bootstrapFrameCount > 0 and frame == bootstrapFrameCount then",
            "    writeJson({ type = \"bootstrap_complete\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName, frame = frame, inputPattern = bootstrapInputPatternSpec, frameCount = bootstrapFrameCount })",
            "    writeJson({ type = \"input_handoff\", oracleId = oracleId, jobId = jobId, scenarioName = scenarioName, frame = frame, fromPhase = \"bootstrap\", toPhase = \"scenario\" })",
            "    emitStateSnapshot(\"post_srm_resume_bootstrap\")",
            "  end",
            "  if frame >= frameLimit then",
            "    writeJson({ type = \"summary\", oracleId = oracleId, jobId = jobId, frames = frame, totalHits = totalHits, requiredHitLabels = requiredHitLabels })",
            "    out:close()",
            "    emu.stop(0)",
            "  end",
            "end, emu.eventType.endFrame)",
            "",
        ]
    )


def render_checklist(job_asset: dict[str, Any]) -> str:
    job = job_asset
    route_gap_lines = [
        "- `{address}` ({group})".format(address=record["address"], group=record["route_group"])
        for record in job.get("route_gap_probe_breakpoints", [])
    ] or ["- None"]
    route_group_lines = []
    if job.get("route_groups"):
        route_group_lines = [
            "## Route Groups",
            "",
            *[
                "- `{group_id}` ({status}): {addresses}{next_probe}".format(
                    group_id=group_id,
                    status=group.get("status", ""),
                    addresses=", ".join(f"`{address}`" for address in group.get("addresses", [])) or "-",
                    next_probe=f"; next probe: {group.get('next_probe_goal')}" if group.get("next_probe_goal") else "",
                )
                for group_id, group in job.get("route_groups", {}).items()
            ],
            *[
                "- `{group_id}` probe hints: breakpoints {breakpoints}; watches {watches}".format(
                    group_id=group_id,
                    breakpoints=", ".join(f"`{address}`" for address in group.get("probe_breakpoint_hints", [])) or "-",
                    watches=", ".join(f"`{watch}`" for watch in group.get("watch_hints", [])) or "-",
                )
                for group_id, group in job.get("route_groups", {}).items()
                if group.get("probe_breakpoint_hints") or group.get("watch_hints")
            ],
            "",
        ]
    return "\n".join(
        [
            f"# C2 Oracle Runner Checklist: `{job['oracle_id']}`",
            "",
            "Generated by `tools/build_c2_battle_trace_oracle_runner_assets.py`.",
            "",
            "This ignored asset is runner plumbing only. It can produce a raw JSONL",
            "trace, but it is not proof until a reviewed non-stub result JSON passes",
            "`tools/validate_c2_battle_trace_oracle_result.py` and the collector.",
            "",
            "## Scenario",
            "",
            f"- name: `{job['scenario']['scenario_name']}`",
            f"- save state: `{job['scenario']['save_state_path_local_only']}`",
            f"- stop condition: {job['scenario']['stop_condition']}",
            "",
            "## Minimum Hits",
            "",
            *[f"- `{address}`" for address in job["minimum_hits"]],
            "",
            "## Route-Gap Probe Breakpoints",
            "",
            *route_gap_lines,
            "",
            *route_group_lines,
            "## Mesen Test Runner Template",
            "",
            "```powershell",
            job["commands"]["mesen_test_runner_template"],
            "```",
            "",
            "## Mesen Wrapper Templates",
            "",
            "```powershell",
            job["commands"]["mesen_wrapper_dry_run"],
            job["commands"]["mesen_wrapper_trace_run"],
            "```",
            "",
            "## External Batch Template",
            "",
            "```powershell",
            job["commands"]["external_batch_template"],
            "```",
            "",
            "## Reviewed Result Template",
            "",
            "```powershell",
            job["commands"]["reviewed_result_template"],
            "```",
            "",
            "## Output Paths",
            "",
            f"- raw trace: `{job['output_paths']['raw_trace_path']}`",
            f"- result: `{job['output_paths']['result_path']}`",
            f"- result template: `{job['assets']['result_template']}`",
            f"- validator: `{job['commands']['validate_result']}`",
            "",
            "## Capture Fields",
            "",
            *[f"- `{field}`" for field in job["capture_fields"]],
            "",
        ]
    )


def build_assets(handoff: dict[str, Any], output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    jobs: list[dict[str, Any]] = []
    commands: list[str] = []
    for job in handoff.get("jobs", []):
        job_dir = output_root / str(job["oracle_id"])
        lua_path = job_dir / "mesen-runner-skeleton.lua"
        checklist_path = job_dir / "operator-checklist.md"
        template_path = job_dir / "result-template.json"
        runner_path = job_dir / "runner-job.json"
        job_asset = runner_job(job, lua_path, checklist_path, template_path)
        job_dir.mkdir(parents=True, exist_ok=True)
        lua_path.write_text(render_lua(job), encoding="utf-8")
        write_json(template_path, result_template(job))
        write_json(runner_path, job_asset)
        checklist_path.write_text(render_checklist(job_asset), encoding="utf-8")
        jobs.append(
            {
                "job_id": job["job_id"],
                "oracle_id": job["oracle_id"],
                "runner_job": repo_relative(runner_path),
                "mesen_lua_skeleton": repo_relative(lua_path),
                "operator_checklist": repo_relative(checklist_path),
                "result_template": repo_relative(template_path),
                "target_raw_trace_path": job["output_paths"]["raw_trace_path"],
                "target_result_path": job["output_paths"]["result_path"],
                "minimum_hits": job["minimum_hits"],
                "route_groups": job.get("route_groups", {}),
                "route_gap_probe_breakpoints": job_asset["route_gap_probe_breakpoints"],
                "capture_field_count": len(job["capture_fields"]),
            }
        )
        commands.append(job_asset["commands"]["mesen_test_runner_template"])
    commands_path = output_root / "commands.md"
    commands_path.write_text(
        "\n".join(
            [
                "# C2 Battle Trace Oracle Runner Commands",
                "",
                "Generated ignored command snippets. Replace local placeholders before running.",
                "",
                *sum((["```powershell", command, "```", ""] for command in commands), []),
            ]
        ),
        encoding="utf-8",
    )
    readme_path = output_root / "README.md"
    readme_path.write_text(render_readme(handoff, output_root, jobs), encoding="utf-8")
    index = {
        "schema": "earthbound-decomp.c2-battle-trace-oracle-runner-assets.v1",
        "status": "runner_assets_generated_no_execution",
        "handoff": "manifests/c2-battle-trace-oracle-emulator-handoff.json",
        "output_root": repo_relative(output_root),
        "source_policy": {
            "generated_assets_are_ignored": True,
            "requires_user_supplied_rom": True,
            "requires_local_save_states": True,
            "source_promotion_allowed": False,
            "behavior_change_allowed": False,
            "lua_skeletons_are_proof": False,
        },
        "summary": {
            "job_count": len(jobs),
            "proof_grade_result_count": 0,
            "source_promotion_allowed": False,
            "behavior_change_allowed": False,
        },
        "assets": {
            "readme": repo_relative(readme_path),
            "commands": repo_relative(commands_path),
        },
        "jobs": jobs,
        "validation_commands": [
            "python tools/validate_c2_battle_trace_oracle_runner_assets.py",
            "python tools/run_c2_battle_trace_oracle_batch.py --mode dry-run-stub --force",
            "python tools/collect_c2_battle_trace_oracle_results.py",
            "python tools/validate_c2_battle_trace_oracle_results_summary.py",
        ],
    }
    write_json(output_root / INDEX_NAME, index)
    return index


def render_readme(handoff: dict[str, Any], output_root: Path, jobs: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# C2 Battle Trace Oracle Runner Assets",
            "",
            "Generated by `tools/build_c2_battle_trace_oracle_runner_assets.py` under ignored `build/` output.",
            "",
            "These files package the first-pass emulator handoff into Mesen testRunner",
            "skeletons and operator checklists. They do not execute automatically, do",
            "not include a ROM or save state, and do not prove any C2 runtime behavior",
            "until a reviewed non-stub result passes validation.",
            "",
            "## Policy",
            "",
            f"- source promotion allowed: `{handoff['summary']['source_promotion_allowed']}`",
            f"- behavior change allowed: `{handoff['summary']['behavior_change_allowed']}`",
            "- ROM and save-state fixtures stay local and uncommitted.",
            "- Breakpoints use SNES CPU bus addresses; ROM patches must use Mesen address conversion.",
            "",
            "## Jobs",
            "",
            "| Oracle | Lua skeleton | Checklist | Target result |",
            "| --- | --- | --- | --- |",
            *[
                f"| `{job['oracle_id']}` | `{job['mesen_lua_skeleton']}` | `{job['operator_checklist']}` | `{job['target_result_path']}` |"
                for job in jobs
            ],
            "",
            "## Validation",
            "",
            "```powershell",
            "python tools\\validate_c2_battle_trace_oracle_runner_assets.py",
            "python tools\\run_c2_battle_trace_oracle_mesen.py --job-id <job-id> --dry-run",
            "python tools\\build_c2_battle_trace_oracle_result_from_evidence.py --job-id <job-id> --status unresolved --classification unresolved --classification-rationale \"review pending\"",
            "```",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    output_root = Path(args.output_root)
    index = build_assets(load_json(Path(args.handoff)), output_root)
    print(f"Wrote {output_root / INDEX_NAME}")
    print(f"Generated {index['summary']['job_count']} C2 runner asset jobs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
