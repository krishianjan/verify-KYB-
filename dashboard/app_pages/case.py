import streamlit as st

import api
import components

st.header("Case detail")

case_id = st.text_input("Case id", value=st.session_state.get("case_id", ""))
if not case_id:
    st.info("Enter a case id, or open one from the review queue.")
    st.stop()
st.session_state["case_id"] = case_id

try:
    resp = api.get_case(case_id)
except api.ApiError as exc:
    st.error(str(exc))
    st.stop()
if resp.status_code == 404:
    st.error("Case not found.")
    st.stop()
if resp.status_code != 200:
    st.error(f"Error {resp.status_code}: {resp.text[:300]}")
    st.stop()

case = resp.json()

# Customer-facing verification report (card + expandable full report).
try:
    rep = api.get_report(case_id)
    if rep.status_code == 200:
        components.render_report(rep.json())
except api.ApiError as exc:
    st.error(str(exc))

with st.expander("Analyst detail (raw signals & scores)"):
    components.render_case(case)

if case.get("risk") and st.button("Explain with AI", icon=":material/auto_awesome:"):
    with st.status("Reading the report…", expanded=True) as status:
        try:
            status.update(label="Analyzing signals and evidence…")
            r = api.explain_case(case_id)
            status.update(label="Writing the summary…")
        except api.ApiError as exc:
            status.update(label="Failed", state="error")
            st.error(str(exc))
            st.stop()
        status.update(label="Done", state="complete")
    if r.status_code == 200:
        st.markdown(r.json()["explanation"])
    else:
        st.error(f"Error {r.status_code}: {r.text[:200]}")

# --- Digital footprint ----------------------------------------------------
st.divider()
st.markdown("### Digital footprint")
try:
    fp_resp = api.get_footprint(case_id)
    if fp_resp.status_code == 200:
        components.render_footprint(fp_resp.json())
    else:
        st.caption("No footprint analysis yet.")
except api.ApiError as exc:
    st.error(str(exc))
if st.button("Run footprint analysis", icon=":material/travel_explore:"):
    try:
        with st.spinner("Crawling site, domain intel, reputation, AI summary…"):
            r = api.run_footprint(case_id)
    except api.ApiError as exc:
        st.error(str(exc))
        st.stop()
    if r.status_code == 200:
        st.success("Footprint analysis complete.")
        st.rerun()
    else:
        st.error(f"Error {r.status_code}: {r.text[:300]}")

# --- Analyst actions ------------------------------------------------------
st.divider()
st.markdown("### Analyst decision")
notes = st.text_area("Notes", placeholder="Rationale for the decision…")
actor = st.text_input("Analyst", value="analyst")
a1, a2, a3, a4 = st.columns(4)
actions = [
    (a1, "approve", "Approve", ":material/check_circle:", "primary"),
    (a2, "reject", "Reject", ":material/cancel:", "secondary"),
    (a3, "request_docs", "Request docs", ":material/description:", "secondary"),
    (a4, "escalate", "Escalate", ":material/priority_high:", "secondary"),
]
for col, action, label, icon, kind in actions:
    if col.button(label, icon=icon, type=kind, width="stretch", key=f"act_{action}"):
        try:
            r = api.post_action(case_id, action, notes, actor or "analyst")
        except api.ApiError as exc:
            st.error(str(exc))
            st.stop()
        if r.status_code == 200:
            st.success(f"Recorded '{action}'. Status → {r.json()['status']}")
            st.rerun()
        else:
            st.error(f"Error {r.status_code}: {r.text[:300]}")

# --- Case memory ----------------------------------------------------------
with st.expander("Case memory (prior findings)", icon=":material/history:"):
    try:
        mem = api.get_memory(case_id)
        notes_list = mem.get("notes", [])
        if notes_list:
            for n in notes_list:
                st.markdown(f"- {n}")
        else:
            st.caption("No memory notes recorded.")
    except Exception as exc:  # noqa: BLE001
        st.caption(f"Memory unavailable: {exc}")
