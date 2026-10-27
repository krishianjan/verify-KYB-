"""Shared render helpers for the verify KYB dashboard."""
from __future__ import annotations

import streamlit as st

_RATING_COLOR = {"low": "green", "medium": "orange", "high": "red"}
_SEV_COLOR = {"info": "gray", "low": "blue", "medium": "orange", "high": "red"}
_VERDICT_COLOR = {"real": "green", "thin": "orange", "inconsistent": "orange",
                  "ghost": "red", "unknown": "gray"}


def rating_badge(rating: str | None) -> str:
    if not rating:
        return ":gray-badge[no rating]"
    return f":{_RATING_COLOR.get(rating, 'gray')}-badge[{rating.upper()} risk]"


def decision_badge(decision: str | None) -> str:
    colors = {"approve": "green", "auto_approve": "green", "review": "orange",
              "manual_review": "orange", "provisional_review": "orange",
              "reject": "red"}
    if not decision:
        return ":gray-badge[—]"
    return f":{colors.get(decision, 'gray')}-badge[{decision}]"


def render_signals(signals: list[dict]) -> None:
    if not signals:
        st.caption("No risk signals.")
        return
    for s in sorted(signals, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x["severity"], 3)):
        color = _SEV_COLOR.get(s["severity"], "gray")
        st.markdown(f":{color}-badge[{s['severity']}] **{s['code']}** — {s.get('detail') or ''}")


_REASON_LABELS = {
    "REGISTRY_NOT_FOUND": "No matching company found in the official registry",
    "COMPANY_INACTIVE": "Company is dissolved or inactive on the registry",
    "NUMBER_MISMATCH": "Submitted company number doesn't match the registry",
    "LOW_IDENTITY_CONFIDENCE": "Submitted details only weakly match the registry",
    "WEAK_WEB_FOOTPRINT": "Weak or suspicious online presence",
    "WEAK_OWNERSHIP_DATA": "Limited director/owner information available",
    "CLONED_SITE_MATCH": "Website closely matches another business (possible shell)",
    "SITE_UNREACHABLE": "Business website could not be reached",
    "PARKED_OR_PLACEHOLDER": "Website is a parked/placeholder page",
    "ML_ANOMALY": "Profile is unusual compared with other businesses",
}
_CATEGORY_LABELS = {"identity": "Identity & registry", "footprint": "Digital footprint",
                    "ownership": "Ownership & structure"}


def render_risk(risk: dict | None) -> None:
    if not risk:
        st.info("No risk score yet.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Overall risk", f"{risk['overall_risk']}/100")
    c2.markdown("Rating\n\n" + rating_badge(risk["rating"]))
    c3.markdown("Recommendation\n\n" + decision_badge(risk["decision"]))

    # Plain-English summary first — the thing a non-technical reader reads.
    if risk.get("explanation"):
        st.markdown(f"**In plain terms:** {risk['explanation']}")

    with st.expander("Technical details"):
        reasons = risk.get("reason_codes") or []
        if reasons:
            st.markdown("**Factors**")
            for code in reasons:
                st.markdown(f"- {_REASON_LABELS.get(code, code)}  \n  `{code}`")
        cats = risk.get("category_scores") or {}
        if cats:
            st.markdown("**Category risk (0–100, higher = riskier)**")
            for k, v in cats.items():
                st.markdown(f"- {_CATEGORY_LABELS.get(k, k)}: **{v}**")


def render_case(case: dict) -> None:
    b = case["business"]
    st.subheader(b["legal_name"])
    st.markdown(
        f"Case `{b['id']}`  ·  {b['jurisdiction']}  ·  status **{b['status']}**"
    )

    with st.container(border=True):
        st.markdown("##### Combined risk")
        render_risk(case.get("risk"))

    a = case.get("assessment")
    if a:
        with st.container(border=True):
            st.markdown("##### Identity verification")
            conf = a.get("confidence")
            conf_txt = f"**{conf:.2f}**" if conf is not None else "**pending** (registry not checked)"
            st.markdown(
                f"Confidence {conf_txt}  ·  "
                f"decision {decision_badge(a['decision'])}  ·  "
                f"matched `{a.get('matched_company_number')}`"
            )
            if a.get("summary"):
                st.caption(a["summary"])
            if a.get("mismatches"):
                st.dataframe(a["mismatches"], width="stretch")

    with st.container(border=True):
        st.markdown("##### Risk signals")
        render_signals(case.get("risk_signals", []))

    col_a, col_b = st.columns(2)
    with col_a.container(border=True):
        st.markdown("##### Directors / officers")
        directors = case.get("directors", [])
        st.dataframe(directors, width="stretch") if directors else st.caption("None on record.")
    with col_b.container(border=True):
        st.markdown("##### Beneficial owners")
        ubos = case.get("beneficial_owners", [])
        st.dataframe(ubos, width="stretch") if ubos else st.caption("None on record.")


_GRADE_COLOR = {"A": "green", "B": "green", "C": "orange", "D": "orange", "F": "red"}
_MATCH_COLOR = {"EXACT": "green", "SIMILAR": "green", "PARTIAL": "orange", "NONE": "red"}


def _grade_badge(score: dict) -> str:
    rating = score.get("rating", "?")
    c = _GRADE_COLOR.get(rating, "gray")
    val = score.get("score")
    return f":{c}-badge[{rating}]" + (f"  {val}" if val is not None else "")


def _render_enrichment(enr: dict) -> None:
    """Web-intelligence block (Feature 4): what the open web says."""
    with st.expander("Web intelligence", expanded=True):
        if enr.get("narrative"):
            st.markdown(enr["narrative"])
        bits = []
        if enr.get("industry"):
            bits.append(f"**Industry:** {enr['industry']}")
        if enr.get("hq"):
            bits.append(f"**HQ:** {enr['hq']}")
        if enr.get("employee_range"):
            bits.append(f"**Team:** {enr['employee_range']}")
        if enr.get("founded_year"):
            bits.append(f"**Founded:** {enr['founded_year']}")
        if bits:
            st.markdown("  ·  ".join(bits))
        if enr.get("locations"):
            st.markdown("**Locations:** " + ", ".join(enr["locations"]))
        people = (enr.get("founders") or []) + (enr.get("executives") or [])
        if people:
            st.markdown("**People:** " + ", ".join(people))
        if enr.get("funding"):
            st.markdown("**Funding**")
            for f in enr["funding"]:
                line = " · ".join(str(x) for x in
                                  (f.get("round"), f.get("amount"), f.get("date")) if x)
                src = f" ([source]({f['source']}))" if f.get("source") else ""
                st.markdown(f"- {line or 'reported'}{src}")
        if enr.get("recent_news"):
            st.markdown("**Recent news**")
            for n in enr["recent_news"]:
                title = n.get("title") or n.get("url") or "article"
                st.markdown(f"- [{title}]({n.get('url')})"
                            + (f" — {n['date']}" if n.get("date") else ""))
        presence = enr.get("presence_score")
        if presence is not None:
            conf = enr.get("judge_confidence") or "?"
            st.caption(f"LLM web-presence judgment: {presence}/100 "
                       f"(confidence: {conf}) — complementary signal, not the decision.")
        if enr.get("sources"):
            with st.expander("Sources"):
                for s in enr["sources"]:
                    st.markdown(f"- {s}")


def render_report(report: dict) -> None:
    """Customer-facing card + expandable full report."""
    scores = {s["type"]: s for s in report.get("scores", [])}
    kyb = scores.get("kyb", {"rating": "?", "score": 0})
    risk = scores.get("risk", {"rating": "?", "score": 0})
    biz = report.get("business", {})
    reg = (biz.get("registrations") or [{}])[0]
    decision = report.get("decision", {})
    fp = report.get("digital_footprint")
    enr = report.get("enrichment")

    with st.container(border=True):
        top = st.columns([3, 1])
        top[0].subheader(biz.get("name") or "—")
        verified = report.get("verified")
        if verified == "pending" or verified is None and kyb.get("rating") == "PENDING":
            top[1].markdown(":orange-badge[PENDING]")
        elif verified:
            top[1].markdown(":green-badge[✓ VERIFIED]")
        else:
            top[1].markdown(":red-badge[NOT VERIFIED]")
        g1, g2 = st.columns(2)
        g1.markdown("**KYB rating**  \n" + _grade_badge(kyb))
        g2.markdown("**Risk rating**  \n" + _grade_badge(risk))

        nm = report.get("business_name_match")
        am = report.get("business_address_match")
        st.markdown(
            f"Name match :{_MATCH_COLOR.get(nm,'gray')}-badge[{nm}]"
            + (f" ({report.get('name_match_score')})" if report.get("name_match_score") else "")
            + (f"  ·  Address :{_MATCH_COLOR.get(am,'gray')}-badge[{am}]" if am else "")
        )
        st.markdown(
            f"Registration **{reg.get('status') or '—'}**"
            f"{' · ' + reg.get('state') if reg.get('state') else ''}"
            f"{' · filed ' + reg.get('filing_date') if reg.get('filing_date') else ''}"
            f"{' · ' + str(biz.get('months_in_business')) + ' mo' if biz.get('months_in_business') else ''}"
        )
        hits = report.get("watchlist_hits") or []
        st.markdown("Watchlist " + (":green-badge[Clear]" if not hits else f":red-badge[{len(hits)} hit(s)]"))
        if fp:
            wp = fp.get("web_presence_score")
            wp_txt = f" · web presence {wp}/100" if wp is not None else ""
            st.markdown(
                f"Web presence :blue-badge[{fp['verdict']}] "
                f"{fp['legitimacy_score']}/100{wp_txt}"
            )
        st.markdown("**Decision:** " + decision_badge(decision.get("action")))
        if decision.get("reasoning"):
            st.markdown(f"_{decision['reasoning']}_")
        for w in report.get("warnings") or []:
            st.warning(w)

        if enr:
            _render_enrichment(enr)

        with st.expander("View full report"):
            st.markdown("**Match (entity resolution)**")
            st.markdown(f"- Name: `{nm}`" + (f" (fuzzy {report.get('name_match_score')})" if report.get("name_match_score") else ""))
            st.markdown(f"- Address: `{am or 'n/a'}`")
            st.markdown(f"- TIN matched: `{report.get('tin_matched')}` _(planned)_")
            st.markdown("**Registration**")
            st.json(biz.get("registrations") or [])
            if biz.get("officers"):
                st.markdown("**Officers**")
                st.dataframe(biz["officers"], width="stretch")
            if fp:
                st.markdown("**Digital footprint**")
                st.markdown(
                    f"- domain `{fp.get('domain')}` · age {fp.get('domain_age_days')}d · "
                    f"TLS {fp.get('has_tls')}"
                )
                links = fp.get("social_links") or {}
                if links:
                    st.markdown("- social: " + "  ·  ".join(
                        f"[{k}]({v})" for k, v in links.items()))
                elif fp.get("social_profiles"):
                    st.markdown("- social: " + ", ".join(fp["social_profiles"]))
                if fp.get("profile_summary"):
                    st.markdown("**Company profile (AI)**")
                    st.markdown(fp["profile_summary"])
                if fp.get("screenshot_url"):
                    st.image(fp["screenshot_url"], width="stretch", caption="urlscan.io")
            st.markdown("**Source of truth**")
            st.json(report.get("sources") or {})


def render_footprint(fp: dict) -> None:
    v = fp.get("verdict", "unknown")
    c1, c2 = st.columns([1, 2])
    wp = fp.get("web_presence_score")
    c1.metric("Web legitimacy", f"{fp['legitimacy_score']}/100",
              delta=(f"{wp} presence" if wp is not None else None), delta_color="off")
    c2.markdown(
        f"Verdict  :{_VERDICT_COLOR.get(v, 'gray')}-badge[{v}]  ·  "
        f"crawler `{fp.get('crawler_source')}`  ·  domain `{fp.get('domain')}`"
    )
    if fp.get("judge_rationale"):
        st.caption("Web-presence judge: " + fp["judge_rationale"])
    meta = (f"age {fp.get('domain_age_days')}d · MX {fp.get('has_mx')} · "
            f"TLS {fp.get('has_tls')} · HTTP {fp.get('http_status')}")
    st.caption(meta)
    links = fp.get("social_links") or {}
    if links:
        st.markdown("Social: " + "  ·  ".join(f"[{k}]({v})" for k, v in links.items()))
    if fp.get("profile_summary"):
        st.markdown("**Company profile (AI)**")
        st.markdown(fp["profile_summary"])
    if fp.get("summary"):
        st.caption(fp["summary"])
    if fp.get("screenshot_url"):
        st.image(fp["screenshot_url"], width="stretch",
                 caption="Website screenshot (urlscan.io)")
    if fp.get("enrichment"):
        _render_enrichment(fp["enrichment"])
    st.markdown("**Footprint signals**")
    render_signals(fp.get("signals", []))
