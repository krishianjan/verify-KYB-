import streamlit as st

import api
import components

st.header("Onboard a business")
st.caption("Submit a business for identity verification and risk scoring.")

try:
    _provider = api.health().get("registry_provider", "us_sos")
except api.ApiError as exc:
    st.error(str(exc))
    st.stop()

if _provider == "us_sos":
    st.info(
        "Live US Secretary-of-State lookup (Apify). **Pick a state** — a "
        "nationwide search hits all 51 registries and will time out. "
        "Switch `REGISTRY_PROVIDER=mock` in the backend `.env` for instant testing.",
        icon=":material/bolt:",
    )

_US_STATES = ["", "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA",
              "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI",
              "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND",
              "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA",
              "WA", "WV", "WI", "WY"]

with st.form("onboard"):
    legal_name = st.text_input("Legal name", placeholder="e.g. 38 TESLA, LLC")
    c1, c2 = st.columns(2)
    state = c1.selectbox("State", _US_STATES, help="Narrows the registry search (fast + precise).")
    company_number = c2.text_input("Company / entity number", placeholder="optional")
    website = st.text_input("Website", placeholder="https://example.com")
    registered_address = st.text_area("Registered address", placeholder="optional")
    submitted = st.form_submit_button("Verify business", type="primary", width="stretch")

if submitted:
    if not legal_name.strip():
        st.warning("Legal name is required.")
        st.stop()
    if _provider == "us_sos" and not state and not company_number.strip():
        st.info(
            "No state given — skipping the registry and building a web-presence "
            "profile for review. Add a state for a precise registry match."
        )

    payload = {"legal_name": legal_name.strip()}
    if state:
        payload["state"] = state
    if company_number.strip():
        payload["company_number"] = company_number.strip()
    if website.strip():
        payload["website"] = website.strip()
    if registered_address.strip():
        payload["registered_address"] = registered_address.strip()

    try:
        with st.spinner("Verifying against the registry (live lookups can take ~30–60s)…"):
            resp = api.create_case(payload)
    except api.ApiError as exc:
        st.error(str(exc))
        st.stop()

    if resp.status_code != 201:
        st.error(f"Error {resp.status_code}: {resp.text[:300]}")
        st.stop()

    case = resp.json()
    cid = case["business"]["id"]
    st.session_state["case_id"] = cid
    st.success(f"Case created: {cid}")
    try:
        rep = api.get_report(cid)
        if rep.status_code == 200:
            components.render_report(rep.json())
    except api.ApiError as exc:
        st.error(str(exc))
    st.info("Open **Case detail** to run the digital-footprint analysis and take action.")
