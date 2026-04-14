#!/usr/bin/env python3
"""
autorun.py — Install runtime dependencies and save credentials on first activation.
Runs automatically when the agent is installed or reactivated.
"""

import json
import os
import sys
import shutil
import subprocess
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.resolve()
SECRETS_DIR = WORKSPACE_ROOT / ".secrets"
ENV_PATH = SECRETS_DIR / "env.json"


def install_agentcard():
    if shutil.which("agentcard"):
        print(f"[ok] agentcard already installed ({shutil.which('agentcard')})")
        return
    print("[...] Installing agentcard CLI...")
    result = subprocess.run(
        ["npm", "install", "-g", "agentcard"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[ok] agentcard installed.")
    else:
        print(f"[error] agentcard install failed:\n{result.stderr}")
        sys.exit(1)


def install_browser_use_sdk():
    try:
        import browser_use_sdk  # noqa: F401
        print("[ok] browser-use-sdk already installed.")
        return
    except ImportError:
        pass
    print("[...] Installing browser-use-sdk...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "browser-use-sdk"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("[ok] browser-use-sdk installed.")
    else:
        print(f"[error] browser-use-sdk install failed:\n{result.stderr}")
        sys.exit(1)


def save_credentials(data: dict):
    api_key = data.get("browser_use_api_key", "").strip()
    if not api_key:
        return

    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    env = {}
    if ENV_PATH.exists():
        try:
            env = json.loads(ENV_PATH.read_text())
        except Exception:
            pass

    env["BROWSER_USE_API_KEY"] = api_key

    tmp = ENV_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(env, ensure_ascii=False, indent=2))
    tmp.replace(ENV_PATH)
    print("[ok] BROWSER_USE_API_KEY saved to .secrets/env.json")


def main():
    print("=== Payment Assistant — Setup ===")

    # 1. Install dependencies
    install_agentcard()
    install_browser_use_sdk()

    # 2. Save credentials from formData (if provided at install time)
    raw = os.environ.get("OPENCLAW_FORM_DATA", "").strip()
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read().strip()

    if raw:
        try:
            data = json.loads(raw)
            save_credentials(data)
        except json.JSONDecodeError:
            pass

    print("=== Setup complete ===")


if __name__ == "__main__":
    main()
