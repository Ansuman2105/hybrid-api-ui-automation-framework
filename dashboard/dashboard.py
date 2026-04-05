# dashboard_pro.py

import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

RESULTS_FILE = Path("reports/results.json")

st.set_page_config(
    page_title="STB Dashboard",
    layout="wide",
    page_icon="📺"
)

# =========================
# 🔥 MODERN UI STYLE
# =========================
st.markdown("""
<style>
body {background-color: #0f172a;}
.metric-card {
    background: linear-gradient(145deg, #1e293b, #0f172a);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}
.status-pass {color:#22c55e;}
.status-fail {color:#ef4444;}
.status-error {color:#f59e0b;}
</style>
""", unsafe_allow_html=True)

# =========================
# LOAD DATA
# =========================
def load():
    if not RESULTS_FILE.exists():
        return []
    try:
        return json.load(open(RESULTS_FILE))
    except:
        return []

data = load()

df = pd.DataFrame(data)

if not df.empty:
    df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce")

# =========================
# HEADER
# =========================
st.title("📺 STB Automation Dashboard")
st.caption("Live Monitoring + Debug Console")

# =========================
# SUMMARY
# =========================
if df.empty:
    st.warning("No test results yet")
    st.stop()

total = len(df)
passed = len(df[df.status == "PASS"])
failed = len(df[df.status == "FAIL"])
errors = len(df[df.status == "ERROR"])
pass_rate = round(passed / total * 100, 1)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total", total)
c2.metric("Passed", passed)
c3.metric("Failed", failed)
c4.metric("Pass %", f"{pass_rate}%")

# =========================
# 🔥 TREND CHART
# =========================
st.subheader("📈 Pass Trend")

df["run"] = df["timestamp"].dt.strftime("%H:%M")

trend = df.groupby("run")["status"].apply(lambda x: (x == "PASS").mean()*100).reset_index()

fig = px.line(trend, x="run", y="status", title="Pass % Over Time")
st.plotly_chart(fig, use_container_width=True)

# =========================
# MODULE CHART
# =========================
st.subheader("📊 Module Results")

df["module"] = df["test_name"].apply(lambda x: x.split("::")[0])

mod = df.groupby(["module", "status"]).size().reset_index(name="count")

fig2 = px.bar(mod, x="module", y="count", color="status")
st.plotly_chart(fig2, use_container_width=True)

# =========================
# RESULTS TABLE
# =========================
st.subheader("📋 Test Results")

st.dataframe(df, use_container_width=True)

# =========================
# FAILURES
# =========================
st.subheader("🔍 Failures")

fails = df[df.status.isin(["FAIL", "ERROR"])]

for _, row in fails.iterrows():
    with st.expander(row["test_name"]):
        st.write("Status:", row["status"])
        st.write("Device:", row.get("device"))
        st.write("Error:", row.get("error_msg"))

# =========================
# ACTIONS
# =========================
if st.button("🗑 Clear Results"):
    json.dump([], open(RESULTS_FILE, "w"))
    st.success("Cleared")
    st.rerun()