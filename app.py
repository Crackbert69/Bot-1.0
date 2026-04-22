import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import re

# Seite konfigurieren
st.set_page_config(page_title="Bot 1.0", page_icon="🤖", layout="wide")

# --- BLAUE MARKIERUNG CSS ---
# Wir nutzen eine sichere Methode für das Design
st.markdown("""
    <style>
    div.stMarkdown b { color: #1E90FF; font-weight: bold; }
    .stStatus { color: #1E90FF; }
    </style>
""", unsafe_allow_html=True)

# --- KI SETUP ---
@st.cache_resource
def setup_ki():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except Exception:
        return False

KI_BEREIT = setup_ki()

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_cache" not in st.session_state:
    st.session_state.pdf_cache = {}

# --- UI ---
st.title("🤖 Bot 1.0")

with st.sidebar:
    st.header("⚙️ Verwaltung")
    uploaded_files = st.file_uploader("PDFs hochladen", type="pdf", accept_multiple_files=True)
    if st.button("Chat löschen"):
        st.session_state.messages = []
        st.rerun()

# Such-Eingabe
suchbegriff = st.text_input("Frag den Bot etwas zu deinen PDFs:", "")

if uploaded_files and suchbegriff:
    all_results = []
    full_text_context = ""
    
    with st.status("Dokumente werden analysiert...", expanded=False) as status:
        for up_file in uploaded_files:
            # PDFs im Cache speichern für Speed
            if up_file.name not in st.session_state.pdf_cache:
                doc = fitz.open(stream=up_file.read(), filetype="pdf")
                st.session_state.pdf_cache[up_file.name] = [p.get_text() for p in doc]
            
            pages = st.session_state.pdf_cache[up_file.name]
            for i, page_text in enumerate(pages):
                if suchbegriff.lower() in page_text.lower():
                    # Fundstelle ausschneiden (Zentriert)
                    start_pos = page_text.lower().find(suchbegriff.lower())
                    start_idx = max(0, start_pos - 250)
                    end_idx = min(len(page_text), start_pos + 250)
                    snippet = page_text[start_idx:end_idx].replace("\n", " ").strip()
                    
                    # Suchwort markieren (wird durch CSS oben blau)
                    pattern = re.compile(re.escape(suchbegriff), re.IGNORECASE)
                    highlighted = pattern.sub(f"**{suchbegriff}**", snippet)
                    
                    all_results.append({"file": up_file.name, "page": i+1, "text": highlighted})
                    full_text_context += f"\n--- Seite {i+1} ---\n{page_text}"
        
        status.update(label="Suche abgeschlossen!", state="complete")

    # Zweispaltiges Layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Fundstellen")
        if all_results:
            for res in all_results[:10]:
                with st.expander(f"Seite {res['page']} - {res['file']}"):
                    st.markdown(res['text'])
        else:
            st.warning("Keine Treffer im Text gefunden.")

    with col2:
        st.subheader("💬 Chat")
        # Verlauf anzeigen
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        if KI_BEREIT and st.button("KI Analyse starten"):
            # User Nachricht hinzufügen
            st.session_state.messages.append({"role": "user", "content": suchbegriff})
            with st.chat_message("user"):
                st.markdown(suchbegriff)
            
            try:
                # Automatisches Finden des richtigen Modells (Gemini 3 oder 1.5)
                available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                target = "models/gemini-1.5-flash" # Standard
                if any("gemini-3" in m for m in available):
                    target = [m for m in available if "gemini-3" in m][0]
                elif any("gemini-1.5-flash" in m for m in available):
                    target = [m for m in available if "gemini-1.5-flash" in m][0]

                model = genai.GenerativeModel(target)
                
                with st.spinner(f"Bot 1.0 analysiert mit {target}..."):
                    prompt = (
                        f"SYSTEM: Antworte NUR basierend auf dem PDF-Text. Erfinde nichts dazu.\n"
                        f"KONTEXT:\n{full_text_context[:12000]}\n\n"
                        f"FRAGE: {suchbegriff}\n\n"
                        f"HINWEIS: Füge am Ende eine Sektion '🌐 Recherche-Empfehlung' an."
                    )
                    
                    response = model.generate_content(prompt)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    with st.chat_message("assistant"):
                        st.markdown(response.text)
            
            except Exception as e:
                st.error(f"KI-Fehler: {e}")
