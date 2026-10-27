import streamlit as st

import api

st.header("Review queue")
st.caption("Cases awaiting analyst review, newest first.")

c1, c2, c3 = st.columns(3)
status = c1.selectbox("Status", ["", "manual_review", "auto_approved", "rejected",
                                 "approved", "received", "verifying"])
rating = c2.selectbox("Risk rating", ["", "low", "medium", "high"])
decision = c3.selectbox("Risk recommendation", ["", "approve", "review", "reject"])

try:
    data = api.list_cases(status=status or None, rating=rating or None,
                          decision=decision or None, limit=100)
except api.ApiError as exc:
    st.error(str(exc))
    st.stop()
items = data.get("items", [])
st.markdown(f"**{data.get('total', 0)}** case(s)")

if not items:
    st.info("No cases match the filter.")
else:
    st.dataframe(
        items, width="stretch",
        column_order=["legal_name", "jurisdiction", "status", "risk_rating",
                      "overall_risk", "identity_decision", "identity_confidence",
                      "created_at", "id"],
    )
    ids = [it["id"] for it in items]
    chosen = st.selectbox("Open a case", ids,
                          format_func=lambda i: next(
                              (f"{it['legal_name']} ({it['risk_rating'] or '—'})"
                               for it in items if it["id"] == i), i))
    if st.button("Open in case detail", type="primary", icon=":material/open_in_new:"):
        st.session_state["case_id"] = chosen
        st.switch_page("app_pages/case.py")
