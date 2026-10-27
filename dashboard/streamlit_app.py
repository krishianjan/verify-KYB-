import importlib

import streamlit as st

import api
import components

# Streamlit re-runs page scripts on save but does NOT re-import helper modules,
# so edits to api.py/components.py would otherwise serve stale code. Reload them
# every run during development to avoid "module has no attribute X" errors.
importlib.reload(api)
importlib.reload(components)

st.set_page_config(page_title="verifyKYB", page_icon=":material/verified_user:",
                   layout="wide")

with st.sidebar:
    st.title(":material/verified_user: verifyKYB")
    st.caption("KYB analyst console")
    try:
        h = api.health()
        st.success(f"API online · registry `{h.get('registry_provider')}`")
    except Exception:
        st.error(f"API unreachable at {api.BASE_URL}. Start the FastAPI backend.")

pages = [
    st.Page("app_pages/onboard.py", title="Onboard", icon=":material/add_business:"),
    st.Page("app_pages/queue.py", title="Review queue", icon=":material/inbox:"),
    st.Page("app_pages/case.py", title="Case detail", icon=":material/business_center:"),
]
st.navigation(pages).run()
