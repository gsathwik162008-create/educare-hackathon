"""
Smart Campus Analytics - UI Design System & Component Helpers
Injects institutional CSS tokens, renders standard KPI cards, badges, and banners.
"""

from pathlib import Path
import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
CSS_PATH = ASSETS_DIR / "style.css"

def load_css():
    """
    Load and inject the global design system stylesheet assets/style.css into Streamlit.
    Must be called at the top of every page.
    """
    if CSS_PATH.exists():
        with open(CSS_PATH, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>\n{css_content}\n</style>", unsafe_allow_html=True)
    
    # Ensure sidebar entry 'app' displays cleanly as 'Home'
    st.markdown("""
    <script>
    const renameSidebar = () => {
        const links = window.parent.document.querySelectorAll('section[data-testid="stSidebar"] ul li div a span');
        links.forEach(el => {
            if (el.textContent.trim().toLowerCase() === 'app') {
                el.textContent = 'Home';
            }
        });
    };
    renameSidebar();
    setInterval(renameSidebar, 300);
    </script>
    """, unsafe_allow_html=True)

def render_kpi_card(number, label: str):
    """
    Render standard institutional KPI card:
    White background, 1px border #DDE3EC, 4px radius, large KPMG navy number, small grey uppercase label.
    No shadows, no gradients.
    """
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-num">{number}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

def render_insight_header(sentence: str):
    """
    Render standard institutional insight banner / sentence without emojis.
    """
    st.markdown(f"""
    <div class="insight-header">
        {sentence}
    </div>
    """, unsafe_allow_html=True)

def render_demo_badge(text: str = "DEMO DATA — SYNTHETIC BENCHMARK & TRACKING"):
    """
    Render institutional Demo Data badge: amber outline, small caps, subtle background.
    """
    st.markdown(f'<div class="demo-badge">{text}</div>', unsafe_allow_html=True)
