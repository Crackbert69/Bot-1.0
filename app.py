import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import re
import subprocess
import sys
import os
from io import BytesIO

st.set_page_config(page_title="Bot 1.0", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    .treffer-highlight {
        color: #1E90FF;
        font-weight: bold;
    }
    .stChatMessage { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def setup_ki():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except:
        return False

KI_BEREIT = setup_ki()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []
if "pdf_cache" not in st.session_state:
    st.session_state.pdf_cache = {}
if "ki_expanded" not in st.session_state:
    st.session_state.ki_expanded = {}

def add_to_history(query):
    if query and query not in st.session_state.history:
        st.session_state.history.insert(0, query)
        st.session_state.history = st.session_state.history[:5]

def highlight_text(text, keyword):
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return pattern.sub(
        lambda m: f'<span class="treffer-highlight">{m.group()}</span>',
        text
    )

def export_as_txt():
    lines = []
    lines.append("=== Bot 1.0 - Exportierte KI-Antworten ===\n")
    for m in st.session_state.messages:
        if m["role"] == "user":
            lines.append(f"\n[FRAGE]\n{m['content']}\n")
        else:
            lines.append(f"\n[KI-ANTWORT]\n{m['content']}\n")
            lines.append("-" * 60)
    return "\n".join(lines).encode("utf-8")

def export_as_html():
    html = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Bot 1.0 Export</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #1E90FF; }
        .frage { background: #16213e; border-left: 4px solid #1E90FF; padding: 12px; margin: 20px 0; border-radius: 4px; }
        .antwort { background: #0f3460; padding: 12px; margin: 10px 0; border-radius: 4px; }
        .label { color: #1E90FF; font-weight: bold; font-size: 0.85em; margin-bottom: 6px; }
        hr { border-color: #333; }
    </style>
</head>
<body>
    <h1>🤖 Bot 1.0 – Exportierte Antworten</h1>
"""
    for m in st.session_state.messages:
        if m["role"] == "user":
            html += f'<div class="frage"><div class="label">FRAGE</div>{m["content"]}</div>'
        else:
            content = m["content"].replace("\n", "<br>")
            html += f'<div class="antwort"><div class="label">KI-ANTWORT</div>{content}</div><hr>'
    html += "</body></html>"
    return html.encode("utf-8")

with st.sidebar:
    st.title("🤖 Bot 1.0")
    st.header("⚙️ Verwaltung")
    uploaded_files = st.file_uploader("PDFs hochladen", type="pdf", accept_multiple_files=True)

    current_names = [f.name for f in uploaded_files] if uploaded_files else []
    for cached in list(st.session_state.pdf_cache.keys()):
        if cached not in current_names:
            del st.session_state.pdf_cache[cached]

    st.subheader("🔧 Einstellungen")
    max_treffer = st.slider("Max. angezeigte Treffer", min_value=5, max_value=100, value=25, step=5)

    if st.button("Gesamten Verlauf löschen"):
        st.session_state.messages = []
        st.session_state.history = []
        st.session_state.ki_expanded = {}
        st.rerun()

    if st.session_state.messages:
        st.subheader("💾 Export")
        st.download_button(
            label="📄 Als TXT exportieren",
            data=export_as_txt(),
            file_name="bot1_export.txt",
            mime="text/plain"
        )
        st.download_button(
            label="🌐 Als HTML exportieren",
            data=export_as_html(),
            file_name="bot1_export.html",
            mime="text/html"
        )

    if st.session_state.history:
        st.subheader("🕒 Letzte Suchen")
        for item in st.session_state.history:
            if st.sidebar.button(f"🔍 {item}", key=f"hist_{item}"):
                pass

    st.divider()
    st.subheader("🖥️ Lokal installieren")
    st.markdown("""
Führe diese Befehle im Terminal aus:
