import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import re
import subprocess
import sys
import os
from google.generativeai.types import Tool
from google.generativeai import protos
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
if "web_messages" not in st.session_state:
    st.session_state.web_messages = []
if "web_expanded" not in st.session_state:
    st.session_state.web_expanded = {}

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
    <h1>🤖 Bot 1.0 - Exportierte Antworten</h1>
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

    if st.button("Gesamten Verlauf loeschen"):
        st.session_state.messages = []
        st.session_state.history = []
        st.session_state.ki_expanded = {}
        st.session_state.web_messages = []
        st.session_state.web_expanded = {}
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
    st.markdown(
        "**1. Terminal:**\n\n"
        "`pip install streamlit pymupdf google-generativeai`\n\n"
        "**2. App starten:**\n\n"
        "`streamlit run app.py`\n\n"
        "**3. API Key** in `.streamlit/secrets.toml`:\n\n"
        "`GEMINI_API_KEY = 'dein-key'`\n\n"
        "Dann oeffnet sich: `http://localhost:8501`"
    )

user_input = st.text_input("Deine Frage oder dein Suchbegriff:", "")

if uploaded_files and user_input:
    add_to_history(user_input)
    all_results = []
    full_context_for_ki = ""

    with st.status("Analysiere Dokumente mit Bot 1.0...", expanded=False) as status:
        for up_file in uploaded_files:
            if up_file.name not in st.session_state.pdf_cache:
                doc = fitz.open(stream=up_file.read(), filetype="pdf")
                st.session_state.pdf_cache[up_file.name] = [p.get_text() for p in doc]

            pages = st.session_state.pdf_cache[up_file.name]
            for i, page_text in enumerate(pages):
                if user_input.lower() in page_text.lower():
                    start_pos = page_text.lower().find(user_input.lower())
                    snippet = page_text[max(0, start_pos-250):min(len(page_text), start_pos+250)].replace("\n", " ")
                    highlighted = highlight_text(snippet, user_input)
                    all_results.append({"file": up_file.name, "page": i+1, "text": highlighted})
                    full_context_for_ki += f"\n[Quelle: {up_file.name}, Seite: {i+1}]\n{page_text}"

        status.update(label="Suche abgeschlossen!", state="complete")

    if len(st.session_state.messages) > 10:
        st.session_state.messages = st.session_state.messages[-10:]

    total = len(all_results)
    col1, col2 = st.columns([1, 1.2])

    with col1:
        st.subheader(f"📄 Einzelne Fundstellen ({total} gesamt, zeige max. {max_treffer})")
        if all_results:
            for res in all_results[:max_treffer]:
                with st.expander(f"Seite {res['page']} - {res['file']}"):
                    st.markdown(res['text'], unsafe_allow_html=True)
        else:
            st.warning("Keine direkten Treffer.")

    with col2:
        st.subheader("💬 KI-Chat & Zusammenfassung")

        if KI_BEREIT and (not st.session_state.messages or st.session_state.messages[-1]["content"] != user_input):
            st.session_state.messages.append({"role": "user", "content": user_input})

            try:
                available_models = [m.name for m in genai.list_models()]

                preferred = [
                    "models/gemini-3.1-flash-lite-preview",
                    "models/gemini-3-flash-preview",
                    "models/gemini-2.5-flash-lite",
                    "models/gemini-2.5-flash",
                    "models/gemini-2.0-flash-lite",
                    "models/gemini-2.0-flash",
                ]

                target_model = None
                for candidate in preferred:
                    if candidate in available_models:
                        target_model = candidate
                        break

                if target_model is None:
                    target_model = available_models[0]

                model = genai.GenerativeModel(target_model)

                with st.spinner(f"Bot 1.0 nutzt {target_model}..."):
                    prompt = (
                        f"SYSTEM: Du bist Bot 1.0. Nutze NUR den PDF-Inhalt unten.\n"
                        f"KONTEXT AUS PDFs:\n{full_context_for_ki[:15000]}\n\n"
                        f"AUFGABE: Beantworte die Frage '{user_input}' ausfuehrlich und als Zusammenfassung. "
                        f"Nutze Fakten aus dem Kontext. Antworte auf DEUTSCH.\n"
                        f"AM ENDE: Fuege 'Recherche-Empfehlung' mit Suchbegriffen hinzu."
                    )

                    response = model.generate_content(prompt)
                    ki_antwort = response.text
                    st.session_state.messages.append({"role": "assistant", "content": ki_antwort})

            except Exception as e:
                st.error(f"KI-Fehler: {e}")
                st.info(f"Verfuegbare Modelle: {[m.name for m in genai.list_models()]}")

        for idx, m in enumerate(st.session_state.messages):
            if m["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(m["content"])
            else:
                msg_key = f"ki_msg_{idx}"
                if msg_key not in st.session_state.ki_expanded:
                    st.session_state.ki_expanded[msg_key] = True
                with st.expander("🤖 KI-Antwort anzeigen / einklappen", expanded=st.session_state.ki_expanded[msg_key]):
                    st.markdown(m["content"])

# --- WEB SUCHE - unterhalb beider Spalten ---
st.divider()
st.subheader("🌐 KI Web-Suche")
st.caption("Sucht im Internet – unabhaengig vom PDF. Nutzt Gemini 2.0 Flash.")

web_col1, web_col2 = st.columns([4, 1])

with web_col1:
    web_input = st.text_input("Suchbegriff fuer Web-Suche:", "", key="web_input")

with web_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    web_suchen = st.button("🔍 Suchen", use_container_width=True)

if web_suchen:
    if web_input and KI_BEREIT:
        st.session_state.web_messages.append({"role": "user", "content": web_input})

        try:
            web_model = genai.GenerativeModel("models/gemini-2.0-flash")

            with st.spinner("Suche im Internet..."):
                web_prompt = (
                    f"Suche im Internet nach aktuellen Informationen zu: '{web_input}'\n"
                    f"Fasse die Ergebnisse ausfuehrlich auf DEUTSCH zusammen.\n"
                    f"Gib am Ende die wichtigsten Quellen an."
                )

                    from google.generativeai import protos
                    
                    search_tool = protos.Tool(
                       google_search=protos.GoogleSearch()
                    )

                    web_response = web_model.generate_content(
                       web_prompt,
                       tools=[search_tool]
                    )
    
                    web_antwort = web_response.text

                st.session_state.web_messages.append({"role": "assistant", "content": web_antwort})

        except Exception as e:
            st.error(f"Web-Suche Fehler: {e}")
    elif not web_input:
        st.warning("Bitte einen Suchbegriff eingeben.")

if len(st.session_state.web_messages) > 10:
    st.session_state.web_messages = st.session_state.web_messages[-10:]

for idx, m in enumerate(st.session_state.web_messages):
    if m["role"] == "user":
        with st.chat_message("user"):
            st.markdown(m["content"])
    else:
        msg_key = f"web_msg_{idx}"
        if msg_key not in st.session_state.web_expanded:
            st.session_state.web_expanded[msg_key] = True
        with st.expander("🌐 Web-Antwort anzeigen / einklappen", expanded=st.session_state.web_expanded[msg_key]):
            st.markdown(m["content"])
