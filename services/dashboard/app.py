import os
from datetime import datetime

import httpx
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://api:8000")
DASHBOARD_API_KEY = os.getenv("DASHBOARD_API_KEY", "local-dashboard-key-change-me-123456789")
HEADERS = {"X-Dashboard-API-Key": DASHBOARD_API_KEY, "X-Actor-Id": "portfolio-reviewer"}

st.set_page_config(page_title="FinCore Lead Operations", page_icon="📊", layout="wide")


@st.cache_data(ttl=10)
def load_kpis() -> dict:
    with httpx.Client(timeout=10) as client:
        response = client.get(f"{API_BASE_URL}/api/v1/dashboard/kpis", headers=HEADERS)
        response.raise_for_status()
        return response.json()


@st.cache_data(ttl=10)
def load_leads() -> list[dict]:
    with httpx.Client(timeout=10) as client:
        response = client.get(f"{API_BASE_URL}/api/v1/dashboard/leads?limit=500", headers=HEADERS)
        response.raise_for_status()
        return response.json()


def update_status(lead_id: str, new_status: str, reason: str, assigned_to: str | None) -> None:
    with httpx.Client(timeout=10) as client:
        response = client.post(
            f"{API_BASE_URL}/api/v1/dashboard/leads/{lead_id}/status",
            headers=HEADERS,
            json={"status": new_status, "reason": reason, "assigned_to": assigned_to or None},
        )
        response.raise_for_status()
    load_kpis.clear()
    load_leads.clear()


st.title("FinCore Accounting — Lead Operations")
st.caption(
    "Portfolio demo: AI-assisted triage with deterministic scoring, "
    "human review, audit logging and synthetic data only."
)

try:
    kpis = load_kpis()
    leads = load_leads()
except Exception as exc:
    st.error(f"Dashboard API is unavailable: {exc}")
    st.stop()

metric_columns = st.columns(6)
metric_columns[0].metric("Total leads", kpis.get("total_leads", 0))
metric_columns[1].metric("Last 7 days", kpis.get("leads_last_7_days", 0))
metric_columns[2].metric("Qualified", kpis.get("qualified_leads", 0))
metric_columns[3].metric("Needs review", kpis.get("review_required", 0))
metric_columns[4].metric("Awaiting info", kpis.get("awaiting_information", 0))
metric_columns[5].metric("High priority", kpis.get("high_priority", 0))

if not leads:
    st.info("No leads are available yet. Submit one through the intake form.")
    st.stop()

df = pd.DataFrame(leads)
df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
df["score"] = pd.to_numeric(df.get("score"), errors="coerce")

with st.sidebar:
    st.header("Filters")
    status_options = sorted(df["status"].dropna().unique().tolist())
    selected_statuses = st.multiselect("Status", status_options, default=status_options)
    priority_options = sorted(df["priority"].dropna().unique().tolist())
    selected_priorities = st.multiselect("Priority", priority_options, default=priority_options)
    min_score = st.slider("Minimum score", 0, 100, 0)
    search = st.text_input("Company or contact")
    if st.button("Refresh data"):
        load_kpis.clear()
        load_leads.clear()
        st.rerun()

filtered = df[
    df["status"].isin(selected_statuses)
    & df["priority"].isin(selected_priorities)
    & (df["score"].fillna(0) >= min_score)
].copy()
if search:
    mask = filtered["company_name"].str.contains(search, case=False, na=False) | filtered["contact_name"].str.contains(
        search, case=False, na=False
    )
    filtered = filtered[mask]

st.subheader("Pipeline")
status_counts = filtered.groupby("status", dropna=False).size().rename("leads")
st.bar_chart(status_counts)

visible_columns = [
    "id",
    "created_at",
    "company_name",
    "contact_name",
    "status",
    "priority",
    "score",
    "industry",
    "urgency",
    "requested_services",
    "document_count",
    "next_action",
]
st.dataframe(
    filtered[[column for column in visible_columns if column in filtered.columns]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "id": st.column_config.TextColumn("Lead ID", width="medium"),
        "created_at": st.column_config.DatetimeColumn("Created", format="YYYY-MM-DD HH:mm"),
        "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
        "requested_services": st.column_config.ListColumn("Services"),
    },
)

st.subheader("Human review")
lead_options = {
    f"{row['company_name']} — {row['status']} — score {row.get('score')}": row
    for row in filtered.to_dict(orient="records")
}
if not lead_options:
    st.info("No lead matches the selected filters.")
    st.stop()

selected_label = st.selectbox("Select a lead", list(lead_options.keys()))
selected = lead_options[selected_label]
left, right = st.columns([2, 1])
with left:
    st.markdown(f"### {selected['company_name']}")
    st.write(selected.get("ai_summary") or "No AI summary yet.")
    st.write("**Requested services:**", ", ".join(selected.get("requested_services") or []))
    st.write("**Missing information:**", ", ".join(selected.get("missing_information") or []) or "None")
    st.write("**Risk flags:**", ", ".join(selected.get("risk_flags") or []) or "None")
    if selected.get("breakdown"):
        breakdown = pd.DataFrame([{"criterion": key, "points": value} for key, value in selected["breakdown"].items()])
        st.dataframe(breakdown, hide_index=True, use_container_width=True)
with right:
    st.write("**Current status:**", selected["status"])
    st.write("**Priority:**", selected["priority"])
    st.write("**Documents:**", selected.get("document_count", 0))
    st.write("**Created:**", selected.get("created_at"))

with st.form("review_form"):
    new_status = st.selectbox(
        "Decision",
        [
            "review_required",
            "awaiting_information",
            "qualified",
            "onboarding",
            "active",
            "archived",
            "rejected",
        ],
        index=0,
    )
    assigned_to = st.text_input("Assigned reviewer", value="demo-reviewer@fincore.demo")
    reason = st.text_area(
        "Reason (recorded in the audit trail)",
        placeholder="Example: Required documents received and scope confirmed during discovery call.",
    )
    submitted = st.form_submit_button("Record human decision")
    if submitted:
        if len(reason.strip()) < 3:
            st.warning("Provide a meaningful reason for the audit trail.")
        else:
            try:
                update_status(str(selected["id"]), new_status, reason.strip(), assigned_to.strip())
                st.success(f"Status updated at {datetime.now().isoformat(timespec='seconds')}.")
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to update lead: {exc}")

st.divider()
st.caption("FinCore Accounting is fictional. Do not upload real personal, payroll, tax or financial records.")
