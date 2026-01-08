
import streamlit as st
import json
import os
import subprocess
from datetime import datetime

# ==== UI HEADER ====
st.set_page_config(page_title="WebScanPro UI", layout="wide")
st.title("🛡️ WebScanPro - Vulnerability Scanner Dashboard")

# ==== Input Section ====
st.subheader("🔗 Target Configuration")
target_urls = st.text_area(
    "Enter target URLs (one per line):",
    "http://localhost:3000\nhttp://localhost:8080\nhttps://localhost:3443"
)

scan_type = st.selectbox(
    "Select scanning mode:",
    ["Passive Scan", "Active Scan", "Both"]
)

output_folder = "ui_outputs"
os.makedirs(output_folder, exist_ok=True)

# ==== Button ====
if st.button("Start Scan"):
    st.info("Running scan... Please wait ⏳")

    urls = [u.strip() for u in target_urls.split("\n") if u.strip()]

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_output = os.path.join(output_folder, f"results-{timestamp}.json")
    html_output = os.path.join(output_folder, f"report-{timestamp}.html")

    # === Prepare command ===
    cmd = [
        "python", "report_runner.py",
        "--targets", *urls,
        "--out-json", json_output,
        "--out-html", html_output
    ]

    if scan_type == "Passive Scan":
        cmd += ["--mode", "passive"]

    elif scan_type == "Active Scan":
        cmd += ["--mode", "active"]

    else:
        cmd += ["--mode", "both"]

    # === Run the backend ===
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True
        )

        if result.returncode != 0:
            st.error("Error occurred during scanning! ❌")
            st.code(result.stderr)
        else:
            st.success("Scan completed successfully! 🎉")

            # Load JSON results
            try:
                with open(json_output, "r") as f:
                    data = json.load(f)

                st.subheader("📄 Scan Results (JSON)")
                st.json(data)

                st.subheader("📑 Download Outputs")
                st.download_button(
                    "Download JSON Result",
                    data=json.dumps(data, indent=2),
                    file_name=f"results-{timestamp}.json",
                    mime="application/json"
                )

                with open(html_output, "r") as f:
                    html_report = f.read()

                st.download_button(
                    "Download HTML Report",
                    data=html_report,
                    file_name=f"report-{timestamp}.html",
                    mime="text/html"
                )

            except Exception as e:
                st.error("Could not load scan results ❗")
                st.code(str(e))

    except Exception as e:
        st.error("Something went wrong running the scanner ❌")
        st.code(str(e))
