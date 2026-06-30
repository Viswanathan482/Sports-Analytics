"""Shared CSS and theme constants for all SoccerLens pages."""

GREEN  = "#00C97B"
GOLD   = "#FFD700"
RED    = "#EF4444"
BLUE   = "#3B82F6"
AMBER  = "#F59E0B"
PURPLE = "#8B5CF6"
DARK   = "#0A0E1A"
CARD   = "#111827"
BORDER = "#1f2d45"

PLOT_THEME = dict(
    paper_bgcolor=CARD, plot_bgcolor=CARD,
    font=dict(color="#9CA3AF", size=11),
    margin=dict(l=10, r=10, t=35, b=10)
)

MAIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}

/* ── App background — layered stadium-night theme ──────────────
   Applied once here so every page (Home + all pages/*.py, since
   they all import MAIN_CSS) shares the same backdrop instead of a
   flat solid color. Built from three layers:
   1. A deep navy→near-black diagonal gradient as the base tone
   2. Two soft, very low-opacity radial glows (green + blue) positioned
      off-center so the page doesn't look perfectly symmetrical/flat
   3. A faint repeating diagonal hairline texture for subtle depth,
      kept under 3% opacity so it never competes with content/charts */
.stApp{
  background:
    radial-gradient(ellipse 900px 600px at 12% -10%, rgba(0,201,123,0.10), transparent 55%),
    radial-gradient(ellipse 800px 700px at 105% 15%, rgba(59,130,246,0.08), transparent 55%),
    radial-gradient(ellipse 1000px 800px at 50% 115%, rgba(0,201,123,0.05), transparent 60%),
    repeating-linear-gradient(135deg, rgba(255,255,255,0.012) 0px, rgba(255,255,255,0.012) 1px,
                              transparent 1px, transparent 38px),
    linear-gradient(165deg, #0a0e1a 0%, #0b1018 35%, #090d16 70%, #07090f 100%);
  background-attachment:fixed;
}
.main{background:transparent;}
.main .block-container{background:transparent;}
header[data-testid="stHeader"]{background:transparent !important;box-shadow:none !important;}
[data-testid="stToolbar"]{visibility:hidden !important;}
[data-testid="stDecoration"]{display:none !important;}
[data-testid="stSidebarCollapsedControl"]{display:none !important;}
[data-testid="stSidebarCollapseButton"]{display:none !important;}
[data-testid="collapsedControl"]{display:none !important;}
[data-testid="baseButton-headerNoPadding"]{display:none !important;}
[data-testid="stSidebarHeader"] button{display:none !important;}
[data-testid="stSidebarUserContent"] + div button{display:none !important;}
button[kind="header"]{display:none !important;}
button[kind="headerNoPadding"]{display:none !important;}
button[title*="sidebar" i]{display:none !important;}
button[aria-label*="sidebar" i]{display:none !important;}
header[data-testid="stHeader"] button{display:none !important;}
section[data-testid="stSidebar"] > div:first-child button{display:none !important;}
[data-testid="stSidebar"]{min-width:21rem !important;max-width:21rem !important;
                          transform:none !important;visibility:visible !important;}
[data-testid="stSidebar"][aria-expanded="false"]{margin-left:0 !important;}
.block-container{padding:1rem 1.5rem 2rem !important;}

/* ── Sidebar theme — layered, matches main background mood ───── */
[data-testid="stSidebar"]{
  background:
    radial-gradient(ellipse 500px 400px at 50% 0%, rgba(0,201,123,0.09), transparent 60%),
    radial-gradient(ellipse 400px 500px at 100% 100%, rgba(59,130,246,0.05), transparent 55%),
    linear-gradient(180deg,#0d1320 0%,#0a0e1a 55%,#080b14 100%);
  border-right:1px solid #1f2d45;
  box-shadow:inset -1px 0 0 rgba(0,201,123,0.04);
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"]{padding-top:.5rem;}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] ul li{margin-bottom:2px;}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a{
  font-family:'Outfit',sans-serif;font-weight:600;font-size:.92rem;
  color:#9CA3AF !important;border-radius:8px;padding:.55rem .9rem !important;
  transition:all .15s ease;border-left:2px solid transparent;
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover{
  background:rgba(0,201,123,0.08) !important;color:#e8eaf0 !important;
  border-left:2px solid #00C97B55;
}
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"]{
  background:linear-gradient(90deg,rgba(0,201,123,0.16),rgba(0,201,123,0.02)) !important;
  color:#00C97B !important;border-left:2px solid #00C97B;font-weight:700;
}
[data-testid="stSidebarNavSeparator"]{background:#1f2d45 !important;}

.hero{font-family:'Outfit',sans-serif;font-weight:800;font-size:2.6rem;letter-spacing:1px;color:#00C97B;line-height:1;
      text-shadow:0 0 24px rgba(0,201,123,0.25);}
.hero-sub{font-size:.82rem;color:#6B7280;letter-spacing:2px;text-transform:uppercase;}
.hero-tagline{font-size:1rem;color:#9CA3AF;letter-spacing:1px;font-style:italic;margin-top:.2rem;}
.kicker{font-size:.68rem;color:#6B7280;letter-spacing:3px;text-transform:uppercase;margin:.6rem 0 .3rem;}

.kpi-card{background:linear-gradient(135deg,#111827,#1a2235);border:1px solid #1f2d45;
          border-radius:12px;padding:1.1rem .8rem;text-align:center;overflow:hidden;
          box-shadow:0 4px 16px rgba(0,0,0,0.35),inset 0 1px 0 rgba(255,255,255,0.03);
          transition:transform .15s ease,box-shadow .15s ease;}
.kpi-card:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,0.45),0 0 0 1px rgba(0,201,123,0.15);}
.kpi-val {font-family:'Outfit',sans-serif;font-weight:700;font-size:clamp(1.3rem,2.4vw,2.2rem);
          color:#00C97B;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.kpi-lbl {font-size:.7rem;color:#6B7280;letter-spacing:2px;text-transform:uppercase;margin-top:.3rem;}

.sec-hdr{font-family:'Outfit',sans-serif;font-size:1.15rem;color:#e8eaf0;
         letter-spacing:3px;border-left:3px solid #00C97B;padding-left:10px;margin:1rem 0 .6rem;}

.player-card{background:linear-gradient(160deg,#111827,#1a2235);
             border:1px solid #1f2d45;border-radius:16px;padding:1.4rem;text-align:center;}
.player-name{font-family:'Outfit',sans-serif;font-size:1.8rem;color:#fff;
             letter-spacing:2px;margin:.5rem 0 .2rem;line-height:1.1;}
.player-pos {font-size:.75rem;color:#00C97B;font-weight:600;letter-spacing:2px;text-transform:uppercase;}
.bio-row{display:flex;justify-content:space-between;align-items:center;
         padding:.4rem .4rem;border-bottom:1px solid rgba(31,45,69,0.2);font-size:.82rem;}
.bio-label{color:#6B7280;} .bio-val{color:#e8eaf0;font-weight:500;}
.loan-badge{background:#2d1a0a;border:1px solid #f59e0b;border-radius:6px;
            padding:3px 10px;font-size:.72rem;color:#fcd34d;font-weight:600;
            display:inline-block;margin-top:.5rem;}

.stTabs [data-baseweb="tab-list"]{background:#111827;border-radius:8px;padding:3px;gap:3px;}
.stTabs [data-baseweb="tab"]{color:#6B7280;border-radius:6px;padding:7px 18px;
                              font-size:.78rem;letter-spacing:1.5px;text-transform:uppercase;}
.stTabs [aria-selected="true"]{background:#00C97B!important;color:#0A0E1A!important;font-weight:700;}

[data-testid="stSidebar"] [data-testid="stSidebarNav"]::before{
  content:"";display:block;height:3px;margin:0 .9rem 1rem;border-radius:3px;
  background:linear-gradient(90deg,#00C97B,#0a8f57,transparent);
}
[data-testid="stSidebarUserContent"]{padding-top:.5rem;}
[data-testid="stSidebar"] ::-webkit-scrollbar{width:6px;}
[data-testid="stSidebar"] ::-webkit-scrollbar-thumb{background:#1f2d45;border-radius:4px;}
[data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover{background:#00C97B55;}

hr{border-color:#1f2d45;}
</style>
"""

def kpi(val, label, color=GREEN):
    return (f'<div class="kpi-card" style="border-color:{color}22;">'
            f'<div class="kpi-val" style="color:{color};">{val}</div>'
            f'<div class="kpi-lbl">{label}</div></div>')

def sec_hdr(text):
    return f'<div class="sec-hdr">{text}</div>'

# ── Safe multi-line HTML helper ──────────────────────────────────
# When an f-string HTML block is built inside an indented Python
# block (e.g. inside `with col:` or a loop), the literal leading
# whitespace from the source code gets baked into the string.
# Markdown treats any line indented 4+ spaces as a CODE BLOCK,
# so the HTML renders as literal text instead of being parsed.
# Wrap any multi-line st.markdown(...) HTML/CSS call in this
# helper to strip that leading whitespace before rendering.
import re as _re_dedent
def dedent_html(html: str) -> str:
    """Strip leading whitespace from every line of an HTML/CSS string
    so it never accidentally triggers Markdown's code-block rule."""
    return _re_dedent.sub(r'(?m)^[ \t]+', '', html)

# ── Shared branded sidebar header ────────────────────────────────
SIDEBAR_BRAND = """
<div style="padding:.4rem 1rem 1rem;text-align:center;">
  <div style="font-family:'Outfit',sans-serif;font-weight:800;font-size:1.5rem;
              color:#00C97B;letter-spacing:1px;line-height:1;">⚽ SCOUT IQ</div>
  <div style="font-size:.6rem;color:#6B7280;letter-spacing:2px;text-transform:uppercase;
              margin-top:.3rem;">Discover · Analyze · Decide</div>
</div>
<div style="height:1px;background:linear-gradient(90deg,transparent,#1f2d45 20%,#1f2d45 80%,transparent);
            margin:0 1rem .8rem;"></div>
"""
