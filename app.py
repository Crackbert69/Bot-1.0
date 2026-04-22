import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import re

# Seite konfigurieren
st.set_page_config(page_title="Bot 1.0", page_icon="🤖", layout="wide")

# --- BLAUE MARKIERUNG CSS ---
st.markdown("""
    <style>
    .highlight {
        color: #1E90FF;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_status=True)

# --- KI SETUP ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    KI_BEREIT = True
except Exception:
    KI_BEREIT = False

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []

def add_to_history(query):
    if query and query not in st.session_state.history:
        st.session_state.history.insert(0, query)
        st.session_state.history = st.session_state.history[:5]

# --- UI DESIGN ---
st.title("🤖 Bot 1.0")

with st.sidebar:
    st.header("⚙️ Verwaltung")
    uploaded_files = st.file_uploader("PDFs hochladen", type="pdf", accept_multiple_files=True)
    
    if st.button("Chat löschen"):
        st.session_state.messages = []
        st.rerun()

    if st.session_state.history:
        st.subheader("🕒 Letzte Suchen")
        for h in st.session_state.history:
            st.info(h)

suchbegriff = st.text_input("Frag den Bot etwas zu deinen PDFs:", "")

if uploaded_files and suchbegriff:
    add_to_history(suchbegriff)
    all_results = []
    full_text_context = ""
    
    # --- LADEBALKEN AKTIVIEREN ---
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Durchsuche {uploaded_file.name}...")
        file_bytes = uploaded_file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if suchbegriff.lower() in text.lower():
                start_pos = text.lower().find(suchbegriff.lower())
                start_idx = max(0, start_pos - 250)
                end_idx = min(len(text), start_pos + 250)
                snippet = text[start_idx:end_idx].replace("\n", " ").strip()
                
                # Blaues Highlighting vorbereiten (Case-Insensitive)
                pattern = re.compile(re.escape(suchbegriff), re.IGNORECASE)
                highlighted_snippet = pattern.sub(f'<span class="highlight">{suchbegriff}</span>', snippet)
                
                all_results.append({
                    "Datei": uploaded_file.name,
                    "Seite": page_num + 1,
                    "Vorschau": highlighted_snippet
                })
                full_text_context += f"\n--- Seite {page_num+1} ({uploaded_file.name}) ---\n{text}"
        
        # Ladebalken aktualisieren
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    status_text.text("Suche abgeschlossen!")
    progress_bar.empty() # Balken nach Erfolg entfernen

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 Fundstellen")
        if all_results:
            for res in all_results[:10]:
                with st.expander(f"Seite {res['Seite']} - {res['Datei']}"):
                    # HTML erlauben für das blaue Wort
                    st.markdown(res['Vorschau'], unsafe_allow_html=True)
        else:
            st.warning("Keine Treffer gefunden.")

    with col2:
        st.subheader("💬 Chat-Analyse")
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if KI_BEREIT and st.button("Analyse starten / Rückfrage"):
            with st.chat_message("user"):
                st.markdown(suchbegriff)
            st.session_state.messages.append({"role": "user", "content": suchbegriff})

            try:
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                target_model = "models/gemini-3-flash-preview" if any("gemini-3" in m for m in models) else "gemini-1.5-flash"
                m = genai.GenerativeModel(target_model)
                
                system_instruction = (
                    "Du bist Bot 1.0. Antworte NUR basierend auf dem PDF-Kontext. "
                    "Nenne am Ende eine Sektion '🌐 Recherche-Empfehlung' mit Internet-Suchbegriffen."
                )
                
                with st.spinner("KI denkt nach..."):
                    response = m.generate_content(f"{system_instruction}\n\nKontext:\n{full_text_context[:12000]}\n\nFrage: {suchbegriff}")
                    with st.chat_message("assistant"):
                        st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"KI-Fehler: {e}")
