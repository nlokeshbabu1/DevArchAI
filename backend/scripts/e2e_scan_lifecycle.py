#!/usr/bin/env python3
"""Live E2E verification for backend-driven scan lifecycle."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from typing import Any

import httpx
import websockets

API = "http://localhost:8000/api/v1"
REPO = "https://github.com/fluxcd/flux2-kustomize-helm-example"
SCAN_TIMEOUT_S = 300


async def main() -> int:
    events: list[dict[str, Any]] = []
    stages_seen: set[str] = set()
    tech_seen: set[str] = set()
    findings_total = 0
    scan_completed = False
    scan_state_received = False
    ai_started = False

    async with httpx.AsyncClient(timeout=60.0) as client:
        stages_resp = await client.get(f"{API}/scan/stages")
        stages_resp.raise_for_status()
        stage_ids = [s["id"] for s in stages_resp.json().get("stages", [])]
        print(f"[stages] {stage_ids}")
        if "connecting_repository" not in stage_ids:
            print("FAIL: lifecycle stages endpoint not updated")
            return 1

        start_resp = await client.post(
            f"{API}/scan/start",
            json={
                "repository_url": REPO,
                "branch": "main",
                "include_ai_explanations": True,
            },
        )
        start_resp.raise_for_status()
        start = start_resp.json()
        scan_id = start["scan_id"]
        session_token = start.get("session_token")
        print(f"[start] scan_id={scan_id} status={start.get('status')}")

        state_resp = await client.get(f"{API}/scan/state/{scan_id}")
        if state_resp.status_code == 200:
            state = state_resp.json()
            print(f"[state] stage={state.get('stage')} status={state.get('status')} progress={state.get('progress')}")
            scan_state_received = True

    ws_url = f"ws://localhost:8000/ws/scan/{scan_id}"
    if session_token:
        ws_url += f"?session_token={session_token}"

    deadline = time.time() + SCAN_TIMEOUT_S
    async with websockets.connect(ws_url, ping_interval=None) as ws:
        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
            except TimeoutError:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    state_resp = await client.get(f"{API}/scan/state/{scan_id}")
                    if state_resp.status_code == 200:
                        state = state_resp.json()
                        print(f"[poll] stage={state.get('stage')} status={state.get('status')} terminal={state.get('is_terminal')}")
                        if state.get("is_terminal"):
                            scan_completed = state.get("status") == "completed"
                            break
                continue

            msg = json.loads(raw)
            event_type = msg.get("type")
            data = msg.get("data", {})
            events.append({"type": event_type, "data": data})

            if event_type == "scan_state":
                scan_state_received = True
                print(f"[ws scan_state] stage={data.get('stage')} status={data.get('status')}")

            if event_type in ("scan_progress", "scan_started", "scan_stage", "stage_transition"):
                stage = data.get("stage") or data.get("current_step")
                if stage:
                    stages_seen.add(str(stage))
                print(f"[ws {event_type}] stage={stage} msg={data.get('message', '')[:80]}")

            if event_type == "technology_detected":
                tech = data.get("technology")
                name = tech.get("name") if isinstance(tech, dict) else tech
                if name:
                    tech_seen.add(str(name))
                print(f"[ws technology_detected] {name}")

            if event_type in ("finding_added", "finding_detected"):
                findings_total = data.get("total_findings", findings_total + 1)
                print(f"[ws finding] total={findings_total}")

            if event_type in ("scan_complete", "scan_completed"):
                scan_completed = True
                print(f"[ws scan_completed] findings={data.get('findings_count')} techs={data.get('technologies_count')}")
                break

            if event_type in ("ai_started", "ai.analysis.started"):
                ai_started = True
                print(f"[ws ai_started] {data.get('message', '')}")

            if event_type == "scan_failed":
                print(f"FAIL: scan_failed {data.get('error')}")
                return 1

    async with httpx.AsyncClient(timeout=30.0) as client:
        final_state = (await client.get(f"{API}/scan/state/{scan_id}")).json()
        print(f"[final] status={final_state.get('status')} stage={final_state.get('stage')} terminal={final_state.get('is_terminal')}")

    print("\n=== Summary ===")
    print(f"events: {len(events)}")
    print(f"stages_seen: {sorted(stages_seen)}")
    print(f"technologies: {sorted(tech_seen)}")
    print(f"findings_total: {findings_total}")
    print(f"scan_state_received: {scan_state_received}")
    print(f"scan_completed: {scan_completed}")
    print(f"ai_started: {ai_started}")

    checks = [
        ("lifecycle stages API", "connecting_repository" in stage_ids),
        ("state recovery", scan_state_received),
        ("lifecycle events", len(stages_seen) >= 2),
        ("scan completed", scan_completed or final_state.get("status") == "completed"),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        print(f"FAIL checks: {failed}")
        return 1

    print("PASS: E2E scan lifecycle verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
