import argparse
import os
from datetime import datetime

from scanners.passive import run_passive_scan
from scanners.active import run_active_scan
from scanners.reporting import (
    aggregate_results,
    save_as_json,
    save_as_csv,
    render_html_report,
    render_text_report
)


# -------------------------------------------------
# SAFE PATH (prevents ui_outputs/ui_outputs duplication)
# -------------------------------------------------
def safe_path(filename):
    if os.path.dirname(filename):  # If user already gave a folder
        return filename
    return os.path.join("ui_outputs", filename)


# -------------------------------------------------
# MAIN RUNNER
# -------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="DV-WebScanPro Report Runner")

    parser.add_argument("--mode", choices=["passive", "active", "both"], default="passive")
    parser.add_argument("--targets", nargs="+", required=True)

    parser.add_argument("--out-json", default="results.json")
    parser.add_argument("--out-csv", default="results.csv")
    parser.add_argument("--out-html", default="report.html")
    parser.add_argument("--out-text", default="report.txt")

    args = parser.parse_args()

    print(f"Running scan mode: {args.mode}")
    print(f"Targets: {args.targets}")

    passive_results = []
    active_results = []

    # -----------------------------
    # RUN PASSIVE SCAN
    # -----------------------------
    if args.mode in ["passive", "both"]:
        print("\nRunning PASSIVE scans...")
        for target in args.targets:
            try:
                passive_results.append(run_passive_scan(target))
            except Exception as e:
                passive_results.append({"url": target, "error": str(e)})

    # -----------------------------
    # RUN ACTIVE SCAN
    # -----------------------------
    if args.mode in ["active", "both"]:
        print("\nRunning ACTIVE scans...")
        for target in args.targets:
            try:
                active_results.append(run_active_scan(target))
            except Exception as e:
                active_results.append({"url": target, "error": str(e)})

    # -----------------------------
    # AGGREGATE RESULTS
    # -----------------------------
    aggregated = aggregate_results(passive_results, active_results)

    meta = {
        "generated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "targets": args.targets,
        "scan_mode": args.mode,
        "total_findings": aggregated["total_findings"]
    }

    print("\nSaving reports...")

    # -----------------------------
    # PREPARE PATHS (using safe_path)
    # -----------------------------
    json_path = safe_path(args.out_json)
    csv_path = safe_path(args.out_csv)
    html_path = safe_path(args.out_html)
    text_path = safe_path(args.out_text)

    # -----------------------------
    # SAVE JSON
    # -----------------------------
    save_as_json(aggregated, json_path)
    print(f"JSON saved: {json_path}")

    # -----------------------------
    # SAVE CSV
    # -----------------------------
    save_as_csv(aggregated, csv_path)
    print(f"CSV saved: {csv_path}")

    # -----------------------------
    # SAVE HTML REPORT  (THE FIXED PART)
    # -----------------------------
    try:
        render_html_report(
            aggregated_results=aggregated,
            template_dir="templates",
            template_file="report.html.j2",
            out_path=html_path,
            meta=meta
        )
        print(f"HTML saved: {html_path}")
    except Exception as e:
        print("HTML generation failed:", e)

    # -----------------------------
    # SAVE TEXT REPORT
    # -----------------------------
    try:
        render_text_report(aggregated, text_path, meta=meta)
        print(f"TEXT report saved: {text_path}")
    except Exception as e:
        print("TEXT report failed:", e)

    print("\nScan Completed Successfully.")


if __name__ == "__main__":
    main()
