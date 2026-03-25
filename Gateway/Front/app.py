from pathlib import Path
import base64

import streamlit as st
import streamlit.components.v1 as components

from controller import ensure_stream_server_running

BASE_DIR = Path(__file__).parent
UI_DIR = BASE_DIR / "ui"
avatar_path = BASE_DIR / "xiexin-avatar.png"
COMPONENT_HEIGHT = 980

st.set_page_config(
    page_title="xiexin-da-agent",
    page_icon=str(avatar_path),
    layout="wide",
)

hide_decoration_bar_style = """
<style>
  html,
  body,
  .stApp,
  [data-testid="stAppViewContainer"],
  [data-testid="stMain"],
  .main {
    height: 100vh !important;
    overflow: hidden !important;
  }

  .block-container {
    max-width: 100% !important;
    height: 100vh !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
  }

  header,
  [data-testid="stHeader"],
  [data-testid="stToolbar"],
  [data-testid="stStatusWidget"],
  [data-testid="stHeaderActionElements"],
  [data-testid="stAppHeader"],
  .stAppDeployButton,
  #MainMenu,
  footer {
    display: none !important;
  }

  [data-testid="stDecoration"] {
    display: none !important;
  }

  [data-testid="stAppViewContainer"],
  [data-testid="stMain"],
  .main {
    border: 0 !important;
    box-shadow: none !important;
  }
</style>
"""
st.markdown(hide_decoration_bar_style, unsafe_allow_html=True)


def _read_text_file(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")

with open(avatar_path, "rb") as img_file:
    avatar_b64 = base64.b64encode(img_file.read()).decode("utf-8")

stream_host, stream_port = ensure_stream_server_running()
stream_api_url = f"http://{stream_host}:{stream_port}/api/chat/stream"

template_html = _read_text_file(UI_DIR / "index.html")
styles_css = _read_text_file(UI_DIR / "styles.css")
script_js = _read_text_file(UI_DIR / "app.js")

html = (
    template_html
    .replace("{{ styles }}", styles_css)
    .replace("{{ script }}", script_js)
    .replace("{{ avatar_b64 }}", avatar_b64)
  .replace("{{ stream_api_url }}", stream_api_url)
)

components.html(html, height=COMPONENT_HEIGHT, scrolling=False)
