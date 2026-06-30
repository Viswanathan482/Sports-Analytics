"""Player image fetching with Transfermarkt CDN + avatar fallback."""
import requests, base64
import streamlit as st
import pandas as pd

@st.cache_data(ttl=3600, show_spinner=False)
def get_player_image_html(image_url: str, name: str, size: int = 130) -> str:
    """Returns HTML <img> or styled avatar div for a player."""
    if image_url and pd.notna(image_url) and 'default' not in str(image_url):
        try:
            r = requests.get(image_url, timeout=5, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; SoccerLens/2.0)'
            })
            if r.status_code == 200 and len(r.content) > 2000:
                ext  = 'png' if str(image_url).endswith('.png') else 'jpeg'
                b64  = base64.b64encode(r.content).decode()
                return (f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
                        f'border:3px solid #00C97B;overflow:hidden;margin:0 auto;">'
                        f'<img src="data:image/{ext};base64,{b64}" '
                        f'style="width:100%;height:100%;object-fit:cover;"/></div>')
        except Exception:
            pass
    # Styled avatar fallback
    initials = ''.join(p[0].upper() for p in str(name).split()[:2] if p)[:2] or '?'
    colors   = ['#1f4d3a','#0a2040','#2d1a3a','#1a2d0a','#2d1500']
    bg       = colors[hash(name) % len(colors)]
    return (f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
            f'border:3px solid #00C97B;background:linear-gradient(135deg,{bg},#0a0e1a);'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:{size//3}px;font-weight:700;color:#00C97B;margin:0 auto;">'
            f'{initials}</div>')
