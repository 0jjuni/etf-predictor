"""Create the HuggingFace Space, push the repo, and set Space secrets.

Run via: uv run python scripts/setup_hf_space.py

Required env vars:
  HF_TOKEN              write-scoped token
  HF_USERNAME           HF account that will own the Space
  SUPABASE_URL          for Space env
  SUPABASE_ANON_KEY     for Space env
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from huggingface_hub import HfApi
from huggingface_hub.errors import HfHubHTTPError

load_dotenv()

TOKEN = os.environ["HF_TOKEN"]
USERNAME = os.environ["HF_USERNAME"]
SPACE_NAME = os.environ.get("HF_SPACE_NAME", "etf-predictor")
REPO_ID = f"{USERNAME}/{SPACE_NAME}"

IGNORE = [
    ".git/**",
    ".venv/**",
    "venv/**",
    "__pycache__/**",
    "**/__pycache__/**",
    "*.pyc",
    "artifacts/**",
    ".env",
    ".env.local",
    "tests/**",
    ".github/**",
    "scripts/**",
    "db/**",
    ".gitignore",
    "uv.lock",
    ".python-version",
]


def main() -> int:
    api = HfApi(token=TOKEN)

    try:
        info = api.repo_info(repo_id=REPO_ID, repo_type="space")
        print(f"[exists] {info.id}")
    except HfHubHTTPError:
        print(f"[create] {REPO_ID} (sdk=streamlit)")
        api.create_repo(
            repo_id=REPO_ID,
            repo_type="space",
            space_sdk="docker",
            private=False,
            exist_ok=True,
        )

    print("[upload] pushing repo files...")
    api.upload_folder(
        repo_id=REPO_ID,
        repo_type="space",
        folder_path=".",
        ignore_patterns=IGNORE,
        commit_message="Initial deploy from GitHub",
    )

    print("[secrets] setting Space env vars")
    for key in ("SUPABASE_URL", "SUPABASE_ANON_KEY"):
        val = os.environ.get(key)
        if not val:
            print(f"  ! skip {key} (not set in env)")
            continue
        api.add_space_secret(repo_id=REPO_ID, key=key, value=val)
        print(f"  + {key}")

    print(f"\nDone. Space URL: https://huggingface.co/spaces/{REPO_ID}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
