import argparse
import json
from scanners.active import run_active_scan
from utils.logger import get_logger

logger = get_logger("active-runner")

def main():
    parser = argparse.ArgumentParser(description="Run active scan")
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--out", default="outputs/active_output.json")
    args = parser.parse_args()

    logger.info(f"Starting active scan on {args.url}")
    results = run_active_scan(args.url)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Active scan completed. Output saved to {args.out}")

if __name__ == "__main__":
    main()
