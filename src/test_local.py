# test_local.py
import json
import sys
from pathlib import Path

# Ensure Python can import from src/
ROOT = Path(__file__).parent
sys.path.append(str(ROOT / "src"))

from handler import handler  # import your dRPC handler


def main():
    print("=====================================")
    print("      AAVE HF Snapshot — Test Local   ")
    print("=====================================\n")

    # Choose test address
    address = input("Enter wallet address (or press Enter for placeholder): ").strip()
    if not address:
        address = "0x1111111111111111111111111111111111111111"

    # Choose RPC URL
    rpc_url = input("Enter RPC URL (or press Enter for https://base.drpc.org): ").strip()
    if not rpc_url:
        rpc_url = "https://base.drpc.org"

    print("\n=== Calling handler(event) ===")
    event = {
        "address": address,
        "rpc_url": rpc_url
    }

    # Execute the handler directly
    snapshot = handler(event)

    print("\n--- Snapshot Output ---")
    print(json.dumps(snapshot, indent=2, ensure_ascii=False))

    # Save to examples/sample-response.json for schema validation
    examples_dir = ROOT / "examples"
    examples_dir.mkdir(exist_ok=True)

    output_path = examples_dir / "sample-response.json"
    output_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n✅ Snapshot saved to: {output_path}")


if __name__ == "__main__":
    main()
