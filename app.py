import html as html_lib
import streamlit as st

from parser import extract_text_from_pdf, split_into_clauses, extract_clause_title
from analyzer import analyze_clause, get_document_summary, build_llm
from models import AnalyzedClause
from exporter import build_pdf_report

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Viveka",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
#MainMenu, footer { visibility: hidden; }

.plain-title {
    font-size: 2rem; font-weight: 800;
    letter-spacing: -0.03em; color: #0f0e0c; margin-bottom: 2px;
}
.plain-sub { font-size: 0.9rem; color: #7a7670; margin-bottom: 0; }

/* Clause detail cards */
.cl-card {
    border-radius: 0 10px 10px 0;
    background: white;
    border-top: 1px solid #e3dfd6;
    border-right: 1px solid #e3dfd6;
    border-bottom: 1px solid #e3dfd6;
    margin-bottom: 8px;
    overflow: hidden;
    transition: box-shadow .15s;
}
.cl-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,.07); }
.cl-card summary {
    padding: 13px 18px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    list-style: none;
    user-select: none;
    gap: 12px;
}
.cl-card summary::-webkit-details-marker { display: none; }
.cl-card summary::marker { display: none; }
.cl-title { font-size: 13px; font-weight: 600; color: #0f0e0c; flex: 1; }
.cl-right  { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.cl-badge  {
    font-size: 10px; font-weight: 700; letter-spacing: .07em;
    text-transform: uppercase; padding: 3px 11px; border-radius: 10px;
    white-space: nowrap;
}
.cl-chevron { font-size: 13px; color: #aaa; transition: transform .2s; }
.cl-card[open] .cl-chevron { transform: rotate(180deg); }
.cl-body { padding: 0 18px 16px; border-top: 1px solid #f0ede8; }
.cl-text {
    border-radius: 8px; padding: 12px 14px;
    font-size: 13px; line-height: 1.7; color: #3a3831;
    margin-top: 12px; font-style: italic;
}
.cl-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 14px; }
@media (max-width: 640px) { .cl-grid { grid-template-columns: 1fr; } }
.cl-label {
    font-size: 10px; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: #9a9690; margin: 12px 0 5px;
}
.cl-label:first-child { margin-top: 0; }
.cl-p { font-size: 13px; color: #3a3831; line-height: 1.6; margin: 0; }
.tag-chip {
    display: inline-block; background: #eeebe4;
    border: 1px solid #e3dfd6; color: #3a3831;
    padding: 2px 9px; border-radius: 6px;
    font-size: 11px; margin: 2px 2px 2px 0;
}

/* Summary tab */
.clause-card {
    border-radius: 10px; padding: 12px 16px;
    margin-bottom: 8px; border: 1px solid; font-size: 14px; line-height: 1.7;
}
.clause-card-high   { background:#fbeaea; border-color:#f0c0c0; color:#5a1010; }
.clause-card-medium { background:#fdf3e3; border-color:#f0d9a8; color:#5a3800; }
.clause-card-low    { background:#e6f4f0; border-color:#a8d9ce; color:#0f3d30; }
.section-hdr {
    font-size: 11px; font-weight: 700; letter-spacing: .12em;
    text-transform: uppercase; color: #7a7670;
    margin-bottom: 12px; border-bottom: 1px solid #e3dfd6; padding-bottom: 6px;
}
.q-item {
    background: white; border: 1px solid #e3dfd6; border-radius: 8px;
    padding: 10px 14px; margin-bottom: 8px; font-size: 14px; color: #3a3831;
}
.disclaimer {
    background: #fdf3e3; border: 1px solid #f0d9a8; border-radius: 8px;
    padding: 10px 14px; font-size: 12px; color: #7a4f00; margin-top: 24px;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────


CARD_COLORS = {
    "high":   {"border": "#e24b4a", "bg": "#fbeaea", "text": "#8b1a1a", "label": "High Risk"},
    "medium": {"border": "#e8a020", "bg": "#fdf3e3", "text": "#7a4f00", "label": "Review Carefully"},
    "low":    {"border": "#1d9e75", "bg": "#e6f4f0", "text": "#1a5c4a", "label": "Standard"},
    "none":   {"border": "#c0bbb5", "bg": "#f7f4ef", "text": "#7a7670", "label": "Unanalyzed"},
}


def render_clause(ac: AnalyzedClause) -> None:
    level = ac.analysis.risk_level if ac.analysis else "none"
    title = extract_clause_title(ac.text) or f"Clause {ac.index + 1}"
    c = CARD_COLORS[level]

    # Build analysis section
    analysis_html = ""
    if ac.analysis:
        tags = "".join(
            f'<span class="tag-chip">{html_lib.escape(t)}</span>'
            for t in ac.analysis.tags
        )
        questions = "".join(
            f'<li style="margin-bottom:5px">{html_lib.escape(q)}</li>'
            for q in ac.analysis.questions
        )
        analysis_html = f"""
        <div class="cl-grid">
          <div>
            <div class="cl-label">Plain English</div>
            <p class="cl-p">{html_lib.escape(ac.analysis.plain_english)}</p>
            <div class="cl-label">Why it matters</div>
            <p class="cl-p">{html_lib.escape(ac.analysis.risk_reason)}</p>
          </div>
          <div>
            <div class="cl-label">Tags</div>
            <div style="margin-bottom:10px">{tags}</div>
            <div class="cl-label">Questions to ask</div>
            <ul style="margin:0;padding-left:16px;font-size:13px;color:#3a3831;line-height:1.7">
              {questions}
            </ul>
          </div>
        </div>"""
    elif ac.error:
        analysis_html = f'<p style="color:#e24b4a;font-size:12px;margin-top:8px">⚠ {html_lib.escape(ac.error[:300])}</p>'

    card = f"""
    <details class="cl-card" style="border-left: 4px solid {c['border']}">
      <summary>
        <span class="cl-title">{html_lib.escape(title)}</span>
        <div class="cl-right">
          <span class="cl-badge" style="background:{c['bg']};color:{c['text']};border:1px solid {c['border']}">{c['label']}</span>
          <span class="cl-chevron">▾</span>
        </div>
      </summary>
      <div class="cl-body">
        <div class="cl-text" style="background:{c['bg']};color:{c['text']}">{html_lib.escape(ac.text)}</div>
        {analysis_html}
      </div>
    </details>"""
    st.markdown(card, unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚖️ Viveka")
    st.markdown("Decipher your legal documents.")
    st.divider()

    lmstudio_url = st.text_input(
        "LM Studio URL",
        value="http://localhost:1234/v1",
        help="The local server URL from LM Studio → Local Server tab",
    )

    uploaded = st.file_uploader("Upload contract (PDF or TXT)", type=["pdf", "txt"])

    max_clauses = st.slider("Max clauses to analyze", min_value=5, max_value=50, value=30)

    analyze_btn = st.button("Analyze Contract", type="primary", use_container_width=True)

    st.markdown("""
<div class="disclaimer">
⚠️ <strong>Not legal advice.</strong> Viveka helps you understand contracts but does not replace a qualified lawyer.
</div>
""", unsafe_allow_html=True)


# ── Main ───────────────────────────────────────────────────────────────────────

st.markdown('<p class="plain-title">Viveka</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="plain-sub">Upload any contract — decipher every clause instantly.</p>',
    unsafe_allow_html=True,
)

if not uploaded:
    st.info("Upload a PDF or text contract in the sidebar to get started.")
    st.stop()

# ── Process ────────────────────────────────────────────────────────────────────

if analyze_btn:
    with st.spinner("Reading document…"):
        if uploaded.type == "application/pdf":
            raw_text = extract_text_from_pdf(uploaded.read())
        else:
            raw_text = uploaded.read().decode("utf-8", errors="replace")

    clauses = split_into_clauses(raw_text, max_clauses=max_clauses)

    if not clauses:
        st.error("Could not extract any clauses from this document. Try a different file.")
        st.stop()

    st.info(f"Found **{len(clauses)} clauses**. Analyzing with local LLM…")

    llm = build_llm(base_url=lmstudio_url)
    analyzed: list[AnalyzedClause] = []

    progress = st.progress(0, text="Analyzing clauses…")
    for i, clause in enumerate(clauses):
        result = analyze_clause(llm, clause, i)
        analyzed.append(result)
        progress.progress((i + 1) / len(clauses), text=f"Clause {i + 1} / {len(clauses)}")

    progress.empty()

    with st.spinner("Generating document summary…"):
        summary = get_document_summary(llm, analyzed)

    st.session_state["analyzed"] = analyzed
    st.session_state["summary"] = summary
    st.session_state["filename"] = uploaded.name
    st.rerun()


# ── Results ────────────────────────────────────────────────────────────────────

if "analyzed" not in st.session_state:
    st.stop()

analyzed: list[AnalyzedClause] = st.session_state["analyzed"]
summary = st.session_state["summary"]

# Risk counts
counts = {"high": 0, "medium": 0, "low": 0, "none": 0}
for a in analyzed:
    level = a.analysis.risk_level if a.analysis else "none"
    counts[level] += 1

# Stats row
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Clauses", len(analyzed))
c2.metric("🔴 High Risk", counts["high"])
c3.metric("🟡 Review", counts["medium"])
c4.metric("🟢 Standard", counts["low"])

st.divider()

tab_contract, tab_summary = st.tabs(["📄 Contract", "📋 Summary"])

# ── Contract tab ──────────────────────────────────────────────────────────────
with tab_contract:
    # Filter controls
    col_filter, col_sort = st.columns([3, 1])
    with col_filter:
        filter_level = st.multiselect(
            "Show risk levels",
            options=["high", "medium", "low"],
            default=["high", "medium", "low"],
        )

    # Always show failed clauses so errors are visible; filter only applies to successfully analyzed ones
    filtered = [
        a for a in analyzed
        if not a.analysis or a.analysis.risk_level in filter_level
    ]

    if not filtered:
        st.caption("No clauses match the current filter.")
    else:
        # Sort high-risk to top
        ordered = sorted(
            filtered,
            key=lambda a: {"high": 0, "medium": 1, "low": 2}.get(
                a.analysis.risk_level if a.analysis else "low", 3
            ),
        )
        for ac in ordered:
            render_clause(ac)

# ── Summary tab ───────────────────────────────────────────────────────────────
with tab_summary:
    if not summary:
        st.warning("Summary generation failed. Check that LM Studio is running.")
    else:
        col_info, col_export = st.columns([3, 1])
        with col_info:
            st.markdown(f"### {summary.contract_type}")
            st.markdown(summary.one_liner)
        with col_export:
            filename = st.session_state.get("filename", "contract")
            try:
                pdf_bytes = build_pdf_report(analyzed, summary, filename)
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"viveka_{filename.rsplit('.', 1)[0]}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.caption(f"PDF export unavailable: {e}")

        st.divider()

        st.markdown('<div class="section-hdr">Top Risks</div>', unsafe_allow_html=True)
        for risk in summary.top_risks:
            st.markdown(
                f'<div class="clause-card clause-card-high">⚠ {risk}</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="section-hdr" style="margin-top:20px">Questions to Ask Before Signing</div>', unsafe_allow_html=True)
        for q in summary.lawyer_questions:
            st.markdown(f'<div class="q-item">💬 {q}</div>', unsafe_allow_html=True)
