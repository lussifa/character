import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEED = ROOT / "examples" / "worldx_seed.json"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def main():
    seed_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SEED
    base_url = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_BASE_URL

    if not seed_path.exists():
        raise SystemExit(f"seed file not found: {seed_path}")

    seed = json.loads(seed_path.read_text(encoding="utf-8"))
    payload = {
        "seed": seed,
        "reset_graph": False,
    }

    response = httpx.post(f"{base_url}/world/load-seed", json=payload, timeout=30.0)
    response.raise_for_status()
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
