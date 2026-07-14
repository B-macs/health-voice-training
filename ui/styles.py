"""Oura-style dark theme CSS, injected once via st.markdown(unsafe_allow_html=True).

Color palette (kept in one place so components.py / app.py stay consistent):
  background      #0B0F14   near-black
  card            #161B22   layered charcoal
  card border     rgba(255,255,255,.08)  hairline
  text primary    #E6EDF3
  text muted      #8B98A5
  accent optimal  #5EEAD4   crystal/teal cyan
  accent warning  #F5B461   warm amber/gold
  accent bad      #F2726B   soft coral
  accent gold     #C9A94A   AVQI badge
  accent blue     #6FA8DC   ABI badge
  streak amber    #F5B301   Training tab: active streak/XP/"Next" state
  streak green    #22C55E   Training tab: completed state
"""

COLORS = {
    "bg": "#0B0F14",
    "card": "#161B22",
    "card_border": "rgba(255,255,255,0.08)",
    "text": "#E6EDF3",
    "muted": "#8B98A5",
    "optimal": "#5EEAD4",
    "warning": "#F5B461",
    "bad": "#F2726B",
    "gold": "#C9A94A",
    "blue": "#6FA8DC",
    "streak_amber": "#F5B301",
    "streak_green": "#22C55E",
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}}

.stApp {{
    background: {COLORS['bg']};
    color: {COLORS['text']};
}}

/* narrow, centered, phone-like column */
.main .block-container {{
    max-width: 600px;
    padding-top: 1.25rem;
    padding-bottom: 3rem;
}}

#MainMenu, footer, header {{ visibility: hidden; }}

/* ---------- hero ring fill animation (global -- see ui/svg_components.py::hero_ring) ---------- */
@keyframes vxRingFill {{
    to {{ stroke-dashoffset: var(--vx-ring-target); }}
}}
.vx-ring-fill {{
    animation: vxRingFill 1.1s cubic-bezier(.22,.8,.35,1) forwards;
}}

/* ---------- header ---------- */
.vx-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.1rem;
}}
.vx-header-left {{ display: flex; align-items: baseline; gap: 0.5rem; }}
.vx-app-name {{ font-size: 1.05rem; font-weight: 700; letter-spacing: 0.02em; color: {COLORS['text']}; }}
.vx-app-version {{ font-size: 0.75rem; color: {COLORS['muted']}; }}
.vx-header-right {{ display: flex; align-items: center; gap: 0.5rem; color: {COLORS['muted']}; font-size: 0.85rem; }}
.vx-avatar {{
    width: 26px; height: 26px; border-radius: 50%;
    background: {COLORS['card']}; border: 1px solid {COLORS['card_border']};
    display: flex; align-items: center; justify-content: center; font-size: 0.75rem;
}}

/* ---------- tab bar ---------- */
.vx-tabbar {{
    display: flex;
    gap: 1.6rem;
    border-bottom: 1px solid {COLORS['card_border']};
    margin-bottom: 1.25rem;
}}
.vx-tab {{
    padding-bottom: 0.6rem;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    color: {COLORS['muted']};
    font-weight: 600;
    cursor: default;
}}
.vx-tab.active {{
    color: {COLORS['text']};
    border-bottom: 2px solid {COLORS['optimal']};
}}

/* Force Streamlit's column layout to stay side-by-side even at
   mobile-narrow widths -- this is a mobile-first phone-style UI by
   design, and Streamlit's own responsive breakpoint would otherwise
   stack every st.columns() row (tab bar, hero, capture buttons, ...)
   vertically below ~640px, which is exactly our target width.
   Deliberately does NOT touch each column's own width/flex (that used
   to be forced to "flex: 1 1 0" here, which silently overrode Streamlit's
   own inline ratio styling and made every st.columns([1, 7])-style
   unequal split render as equal-width instead -- e.g. the capture flow's
   close-button/progress-bar row. Only min-width needs a nudge, to stop a
   narrow column from refusing to shrink below its content's natural size. */
div[data-testid="stHorizontalBlock"] {{
    flex-wrap: nowrap !important;
    gap: 0.5rem;
}}
div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
    min-width: 0 !important;
}}

/* Tab-bar buttons only (scoped to the st.container(key="tabbar") wrapper):
   an active tab is rendered with type="primary" (kind="primary"),
   inactive with the default "secondary" -- restyle both to look like
   flat, underlined tab labels rather than boxed buttons. Other buttons
   in the app (Neue Aufnahme, capture flow, trend-granularity toggle)
   keep the normal boxed button style. */
.st-key-tabbar div[data-testid="stButton"] button {{
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
    color: {COLORS['muted']} !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase;
    padding: 0 0 0.6rem 0 !important;
    box-shadow: none !important;
}}
.st-key-tabbar div[data-testid="stButton"] button[kind="primary"] {{
    color: {COLORS['text']} !important;
    border-bottom: 2px solid {COLORS['optimal']} !important;
}}
.st-key-tabbar div[data-testid="stButton"] button:hover {{
    color: {COLORS['text']} !important;
}}

/* ---------- generic card ----------
   Cards are real st.container(key="card_...") blocks (see app.py), styled
   via this attribute-contains selector -- NOT a raw "open div in one
   st.markdown call, close it in a later call" hack. Verified that hack is
   broken: each st.markdown() call is an independent DOM fragment in
   Streamlit, so an unclosed <div> self-closes immediately and everything
   "inside" it actually renders as an empty-looking sibling instead. */
div[class*="st-key-card_"] {{
    background: {COLORS['card']};
    border: 1px solid {COLORS['card_border']};
    border-radius: 20px;
    padding: 1.25rem 1.3rem;
    margin-bottom: 1rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    animation: vxFadeIn 0.5s ease-out;
}}

/* The embedded Health view has a much wider content area than Voxplot's
   standalone phone-style layout. Keep the detailed chart at a readable
   desktop width; the SVG itself scales its height from its viewBox, so its
   lines and labels retain their intended proportions. */
div[class*="st-key-card_trends"] {{
    max-width: 920px;
    margin-left: auto;
    margin-right: auto;
}}

@keyframes vxFadeIn {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

.vx-section-label {{
    font-size: 0.68rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: {COLORS['muted']};
    font-weight: 600;
    margin-bottom: 0.6rem;
}}

/* Details tab's General/Breathiness/Hoarseness group headers -- deliberately
   NOT .vx-section-label: that class (0.68rem, muted) reads smaller and the
   same color as the row sub-captions below it (.vx-insight-sub, 0.72rem,
   also muted), so it didn't read as a header at all. This is bigger, bold,
   and full-brightness text so each group clearly separates from its rows. */
.vx-group-title {{
    font-size: 1.05rem;
    font-weight: 700;
    color: {COLORS['text']};
    margin: 1.3rem 0 0.7rem 0;
}}

/* ---------- hero ---------- */
.vx-hero-row {{ display: flex; gap: 1.4rem; align-items: center; }}
.vx-hero-ring-wrap {{ position: relative; flex-shrink: 0; }}
.vx-hero-caption {{ font-size: 0.78rem; color: {COLORS['muted']}; margin-top: 0.15rem; }}
.vx-hero-side {{ flex: 1; display: flex; flex-direction: column; gap: 0.65rem; }}
.vx-hero-compare {{
    font-size: 0.75rem; color: {COLORS['muted']};
    margin-top: 0.5rem; display: flex; gap: 1rem;
}}
.vx-hero-compare b {{ color: {COLORS['text']}; font-weight: 600; }}

/* ---------- gradient headline bars (AVQI/ABI) ---------- */
.vx-gbar-label-row {{ display: flex; justify-content: space-between; font-size: 0.78rem; margin-bottom: 0.3rem; }}
.vx-gbar-name {{ color: {COLORS['muted']}; font-weight: 600; letter-spacing: 0.03em; }}
.vx-gbar-value {{ color: {COLORS['text']}; font-weight: 600; }}

/* ---------- pills ---------- */
.vx-pill {{
    display: inline-flex; align-items: center; gap: 0.3rem;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
}}
.vx-pill-optimal {{ background: rgba(94,234,212,0.14); color: {COLORS['optimal']}; }}
.vx-pill-attention {{ background: rgba(245,180,97,0.14); color: {COLORS['warning']}; }}
.vx-pill-concerning {{ background: rgba(242,114,107,0.14); color: {COLORS['bad']}; }}

/* ---------- insight / contributor rows ---------- */
.vx-insight-row {{ padding: 0.75rem 0; border-bottom: 1px solid {COLORS['card_border']}; }}
.vx-insight-row:last-child {{ border-bottom: none; padding-bottom: 0; }}
.vx-insight-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem; }}
.vx-insight-name {{ font-size: 0.92rem; font-weight: 500; color: {COLORS['text']}; }}
.vx-insight-value-row {{ display: flex; align-items: center; gap: 0.5rem; }}
.vx-insight-value {{ font-size: 0.92rem; font-weight: 600; color: {COLORS['text']}; }}
.vx-insight-sub {{ font-size: 0.72rem; color: {COLORS['muted']}; margin-top: 0.3rem; }}

/* ---------- numerals ---------- */
.vx-big-number {{ font-size: 2.6rem; font-weight: 300; line-height: 1; color: {COLORS['text']}; }}
.vx-status-word {{ font-size: 0.95rem; font-weight: 600; margin-top: 0.15rem; }}

/* ---------- verdict line ---------- */
.vx-verdict {{ font-size: 0.9rem; color: {COLORS['text']}; margin-top: 0.9rem; line-height: 1.5; }}

/* ---------- legend ---------- */
.vx-legend {{ display: flex; gap: 1rem; font-size: 0.72rem; color: {COLORS['muted']}; margin-top: 0.4rem; }}
.vx-legend-item {{ display: flex; align-items: center; gap: 0.35rem; }}
.vx-legend-swatch {{ width: 10px; height: 10px; border-radius: 2px; display: inline-block; }}

/* ---------- capture flow ---------- */
.vx-reading-passage {{
    background: rgba(255,255,255,0.03);
    border: 1px solid {COLORS['card_border']};
    border-radius: 14px;
    padding: 1rem 1.1rem;
    font-size: 0.95rem;
    line-height: 1.6;
    color: {COLORS['text']};
    margin: 0.75rem 0;
}}

/* recording screen shell (progress bar + title + illustration + text card) */
.rec-progress-track {{
    flex: 1;
    height: 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    overflow: hidden;
}}
.rec-progress-fill {{
    height: 100%;
    border-radius: 999px;
    background: {COLORS['streak_amber']};
    transition: width 0.3s ease;
}}
div[class*="st-key-rec_close_btn"] button {{
    border-radius: 50% !important;
    width: 38px; height: 38px;
    padding: 0 !important;
    font-weight: 700;
}}
.rec-title {{ font-size: 1.35rem; font-weight: 800; color: {COLORS['text']}; text-align: center; margin: 1rem 0 1.1rem 0; }}
div[class*="st-key-rec_illustration_"] img {{ border-radius: 16px; width: 100%; }}
.rec-text-card-label {{ font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; color: {COLORS['muted']}; font-weight: 600; margin-top: 1rem; text-align: center; }}
.rec-congrats-title {{ font-size: 1.6rem; font-weight: 800; color: {COLORS['text']}; text-align: center; margin: 1.2rem 0 0.5rem 0; }}
.rec-congrats-subtitle {{ font-size: 0.95rem; color: {COLORS['muted']}; text-align: center; margin-bottom: 1.5rem; }}
/* Center every text element on the capture screens (title/label/passage
   already have their own text-align above; this covers the passage-card
   body plus the record/upload widgets' own native labels and captions,
   which don't have a class of ours to target directly). Doesn't disturb
   the widgets' own internal layout (waveform bars, sliders, buttons all
   use their own flex/grid, which text-align doesn't override). */
div[class*="st-key-card_capture"] {{ text-align: center; }}
div[class*="st-key-card_capture"] .vx-reading-passage {{ text-align: center; }}
/* stWidgetLabel and the file-uploader instructions are flex containers, so
   text-align alone doesn't move them -- they need justify-content too. */
div[class*="st-key-card_capture"] label[data-testid="stWidgetLabel"] {{ justify-content: center; width: 100%; }}
div[class*="st-key-card_capture"] div[data-testid="stFileUploaderDropzoneInstructions"] {{ text-align: center; width: 100%; }}
div[class*="st-key-card_capture"] div[data-testid="stFileUploaderDropzoneInstructions"] > div {{ justify-content: center; width: 100%; }}

/* streamlit widget tweaks to fit the dark card language */
div[data-testid="stButton"] > button {{
    border-radius: 12px;
    border: 1px solid {COLORS['card_border']};
    font-weight: 600;
}}
div[data-testid="stButton"] > button[kind="primary"] {{
    background: {COLORS['optimal']};
    color: #06201C;
    border: none;
}}
div[data-testid="stButton"] > button:disabled,
div[data-testid="stButton"] > button:disabled[kind="primary"] {{
    background: rgba(255,255,255,0.05);
    color: {COLORS['muted']};
    opacity: 0.6;
}}

/* ---------- Training tab ---------- */
.tr-status-bar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.1rem; }}
.tr-streak-group {{ display: flex; gap: 0.5rem; }}
.tr-pill {{
    display: inline-flex; align-items: center; gap: 0.35rem;
    background: {COLORS['card']};
    border: 1px solid {COLORS['card_border']};
    border-radius: 999px;
    padding: 0.35rem 0.75rem;
    font-size: 0.88rem;
    font-weight: 700;
    color: {COLORS['text']};
}}
.tr-xp-pill {{ position: relative; }}
.tr-xp-dot {{
    position: absolute; top: -2px; right: -2px;
    width: 8px; height: 8px; border-radius: 50%;
    background: {COLORS['bad']};
    border: 1.5px solid {COLORS['bg']};
}}

.tr-week-row {{ display: flex; justify-content: space-between; margin: 0.9rem 0 1.15rem 0; }}
.tr-day-col {{ display: flex; flex-direction: column; align-items: center; gap: 0.35rem; flex: 1; }}
.tr-day-circle {{
    width: 34px; height: 34px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.95rem; box-sizing: border-box;
}}
.tr-day-complete {{ background: {COLORS['streak_green']}; border: 1.5px solid {COLORS['streak_green']}; color: #06210F; }}
.tr-day-missed {{ background: rgba(255,255,255,0.04); border: 1.5px solid {COLORS['card_border']}; color: {COLORS['muted']}; }}
.tr-day-future {{ background: transparent; border: 1.5px solid {COLORS['card_border']}; }}
.tr-day-active-unlit {{ background: rgba(245,179,1,0.10); border: 1.5px solid {COLORS['streak_amber']}; opacity: 0.55; }}
.tr-day-active-lit {{ background: {COLORS['streak_amber']}; border: 1.5px solid {COLORS['streak_amber']}; box-shadow: 0 0 0 3px rgba(245,179,1,0.18); }}
.tr-day-label {{ font-size: 0.72rem; color: {COLORS['muted']}; font-weight: 600; }}

.tr-divider {{ border: none; border-top: 1px solid {COLORS['card_border']}; margin: 0.3rem 0 1.2rem 0; }}

.tr-plan-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }}
.tr-plan-title {{ font-size: 1.3rem; font-weight: 800; color: {COLORS['text']}; }}
.tr-help-btn {{
    width: 28px; height: 28px; border-radius: 50%;
    background: {COLORS['card']}; border: 1px solid {COLORS['card_border']};
    display: flex; align-items: center; justify-content: center;
    color: {COLORS['muted']}; font-weight: 700; font-size: 0.85rem;
    flex-shrink: 0;
}}

.tr-card-top {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.3rem; }}
.tr-card-node {{
    width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: 700;
}}
.tr-card-node-next {{ border: 2px solid {COLORS['streak_amber']}; color: {COLORS['streak_amber']}; }}
.tr-card-node-complete {{ background: {COLORS['streak_green']}; color: #06210F; }}
.tr-card-node-upcoming {{ border: 2px solid {COLORS['card_border']}; }}
.tr-card-status {{ font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }}
.tr-card-status-next {{ color: {COLORS['streak_amber']}; }}
.tr-card-status-complete {{ color: {COLORS['streak_green']}; }}
.tr-card-title {{ font-size: 1.15rem; font-weight: 800; color: {COLORS['text']}; margin: 0.1rem 0 0.5rem 0; }}
.tr-card-body {{ display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; }}
.tr-card-meta {{ display: flex; gap: 0.9rem; font-size: 0.8rem; color: {COLORS['muted']}; font-weight: 500; }}
.tr-card-illustration {{
    flex-shrink: 0; width: 56px; height: 56px; border-radius: 16px;
    display: flex; align-items: center; justify-content: center; font-size: 1.6rem;
}}

div[class*="st-key-card_training_act_next_"],
div[class*="st-key-card_training_rec_next"] {{
    border-left: 4px solid {COLORS['streak_amber']} !important;
    box-shadow: 0 4px 18px rgba(245,179,1,0.10), inset 0 1px 0 rgba(255,255,255,0.04) !important;
}}
div[class*="st-key-card_training_act_complete_"],
div[class*="st-key-card_training_rec_complete"] {{ opacity: 0.72; }}
div[class*="st-key-card_training_act_upcoming_"],
div[class*="st-key-card_training_rec_upcoming"] {{ opacity: 0.6; }}

div[class*="st-key-card_training_plan_complete"] {{ text-align: center; }}
.tr-plan-complete-title {{ font-size: 1.3rem; font-weight: 800; color: {COLORS['streak_amber']}; margin-bottom: 0.6rem; }}
.tr-plan-complete-body {{ font-size: 0.92rem; color: {COLORS['muted']}; line-height: 1.6; }}

/* ---------- Activity explanation (Screen A) & results (Screen C) ---------- */
.act-progress-track {{
    flex: 1;
    height: 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    overflow: hidden;
}}
.act-progress-fill {{
    height: 100%;
    border-radius: 999px;
    background: {COLORS['streak_amber']};
    transition: width 0.3s ease;
}}
div[class*="st-key-act_close_btn"] button,
div[class*="st-key-act_timer_close_btn"] button {{
    border-radius: 50% !important;
    width: 38px; height: 38px;
    padding: 0 !important;
    font-weight: 700;
}}
div[class*="st-key-act_skip_btn"] button {{
    border-radius: 50% !important;
    width: 38px; height: 38px;
    padding: 0 !important;
    font-weight: 700;
    background: transparent !important;
    border: none !important;
    color: {COLORS['muted']} !important;
    font-size: 1.2rem;
}}
.act-title {{ font-size: 1.35rem; font-weight: 800; color: {COLORS['text']}; text-align: center; margin: 1rem 0 1.1rem 0; }}
div[class*="st-key-act_illustration_"] img {{ border-radius: 16px; width: 100%; }}
.act-step-dots {{ display: flex; justify-content: center; gap: 0.4rem; margin: 0.9rem 0 1.3rem 0; }}
.act-dot {{ width: 7px; height: 7px; border-radius: 999px; background: rgba(255,255,255,0.18); transition: all 0.2s ease; }}
.act-dot-active {{ background: {COLORS['streak_amber']}; width: 18px; }}
.act-instruction {{ font-size: 1.1rem; font-weight: 700; color: {COLORS['text']}; text-align: center; line-height: 1.55; margin: 0 0.5rem; }}
.act-practice-paragraph {{ background: {COLORS['card']}; border: 1px solid {COLORS['card_border']}; border-left: 3px solid {COLORS['streak_amber']}; border-radius: 14px; padding: 0.9rem 1rem; margin: 1rem 0 0.4rem; }}
.act-practice-paragraph-title {{ color: {COLORS['streak_amber']}; font-size: 0.75rem; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; margin-bottom: 0.45rem; }}
.act-practice-paragraph-copy {{ color: {COLORS['text']}; font-size: 0.98rem; line-height: 1.6; }}
.act-practice-paragraph-hint {{ color: {COLORS['muted']}; font-size: 0.78rem; line-height: 1.45; margin-top: 0.65rem; }}
div[class*="st-key-act_continue_btn"] button[kind="primary"],
div[class*="st-key-act_done_btn"] button[kind="primary"] {{
    background: {COLORS['streak_amber']} !important;
    color: #241a00 !important;
    border: none !important;
    box-shadow: 0 4px 14px rgba(245,179,1,0.28);
}}

/* Results screen (C) */
.act-tabs {{ display: flex; gap: 1.6rem; border-bottom: 1px solid {COLORS['card_border']}; margin-bottom: 1.3rem; }}
.act-tab {{ font-size: 0.8rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; color: {COLORS['muted']}; padding-bottom: 0.65rem; }}
.act-tab-active {{ color: {COLORS['text']}; border-bottom: 2px solid {COLORS['streak_amber']}; }}
div[class*="st-key-act_results_illustration"] img {{ width: 62%; margin: 0 auto; display: block; }}
.act-results-heading {{ font-size: 1.5rem; font-weight: 800; color: {COLORS['streak_amber']}; text-align: center; margin: 0.9rem 0 0.5rem 0; }}
.act-results-subtext {{ font-size: 0.92rem; color: {COLORS['muted']}; text-align: center; line-height: 1.55; margin-bottom: 1.5rem; }}
.act-metric-row {{ margin-bottom: 1.15rem; }}
.act-metric-top {{ display: flex; justify-content: space-between; align-items: baseline; }}
.act-metric-label {{ font-weight: 700; color: {COLORS['text']}; font-size: 0.95rem; }}
.act-metric-value {{ font-weight: 800; color: {COLORS['text']}; font-size: 1.05rem; }}

/* Timed practice (Screen B) */
.act-timer-reminder-heading {{ font-size: 0.78rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; color: {COLORS['muted']}; margin: 0.4rem 0 0.6rem 0; }}
.act-timer-instructions {{ margin-bottom: 1.4rem; }}
.act-timer-instruction {{ font-size: 0.92rem; color: {COLORS['text']}; line-height: 1.5; margin-bottom: 0.5rem; }}
.act-timer-label {{ font-size: 0.85rem; color: {COLORS['muted']}; text-align: center; margin-top: 1.6rem; }}
.act-timer-clock {{ font-size: 3.2rem; font-weight: 800; color: {COLORS['streak_amber']}; text-align: center; letter-spacing: 0.02em; font-variant-numeric: tabular-nums; margin-bottom: 1rem; }}
</style>
"""


def inject(st) -> None:
    st.markdown(CSS, unsafe_allow_html=True)
