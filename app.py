import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import re

# Seite konfigurieren
st.set_page_config(page_title="Bot 1.0", page_icon="🤖", layout="wide")

# --- DESIGN & FARBEN ---
st.markdown("""
    <style>
    div.stMarkdown b { color: #1E90FF; font-weight: bold; }
    .stChatMessage { border-radius: 10px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- KI SETUP ---
@st.cache_resource
def setup_ki():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        return True
    except:
        return False

KI_BEREIT = setup_ki()

# --- SPEICHER (CHAT & TEXT) ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pdf_cache" not in st.session_state:
    st.session_state.pdf_cache = {}

# --- UI ---
st.title("🤖 Bot 1.0")

with st.sidebar:
    st.header("⚙️ Verwaltung")
    uploaded_files = st.file_uploader("PDFs hochladen", type="pdf", accept_multiple_files=True)
    if st.button("Gesamten Chat löschen"):
        st.session_state.messages = []
        st.rerun()

# Eingabefeld (Hier startet alles)
user_input = st.text_input("Deine Frage oder dein Suchbegriff:", "")

if uploaded_files and user_input:
    all_results = []
    full_context_for_ki = ""
    
    with st.status("Dokumente werden durchsucht...", expanded=False) as status:
        for up_file in uploaded_files:
            # Schnelles Einlesen (Cache)
            if up_file.name not in st.session_state.pdf_cache:
                doc = fitz.open(stream=up_file.read(), filetype="pdf")
                st.session_state.pdf_cache[up_file.name] = [p.get_text() for p in doc]
            
            pages = st.session_state.pdf_cache[up_file.name]
            for i, page_text in enumerate(pages):
                if user_input.lower() in page_text.lower():
                    # Fundstelle für die linke Spalte aufbereiten
                    start_pos = page_text.lower().find(user_input.lower())
                    snippet = page_text[max(0, start_pos-250):min(len(page_text), start_pos+250)].replace("\n", " ")
                    
                    # Suchwort fett machen (CSS macht es blau)
                    pattern = re.compile(re.escape(user_input), re.IGNORECASE)
                    highlighted = pattern.sub(f"**{user_input}**", snippet)
                    
                    all_results.append({"file": up_file.name, "page": i+1, "text": highlighted})
                    # Den ganzen Text für die KI-Zusammenfassung sammeln
                    full_context_for_ki += f"\n--- Datei: {up_file.name}, Seite: {i+1} ---\n{page_text}"
        
        status.update(label="Suche abgeschlossen!", state="complete")

    # LAYOUT: Links Fundstellen, Rechts Chat
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.subheader("📄 Einzelne Fundstellen")
        if all_results:
            for res in all_results[:8]: # Top 8 Treffer
                with st.expander(f"Seite {res['page']} - {res['file']}"):
                    st.markdown(res['text'])
        else:
            st.info("Keine direkten Text-Treffer gefunden.")

    with col2:
        st.subheader("💬 KI-Chat & Zusammenfassung")
        
        # Den bisherigen Chatverlauf anzeigen
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        # Wenn eine neue Anfrage kommt, KI aktivieren
        if KI_BEREIT:
            # Wir prüfen, ob die letzte Nachricht schon die aktuelle Frage war, um Dopplungen zu vermeiden
            if not st.session_state.messages or st.session_state.messages[-1]["content"] != user_input:
                
                with st.chat_message("user"):
                    st.markdown(user_input)
                st.session_state.messages.append({"role": "user", "content": user_input})

                try:
                    # Wir nehmen 1.5 Flash für Geschwindigkeit und Stabilität
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    
                    with st.spinner("Bot 1.0 erstellt Zusammenfassung..."):
                        prompt = (
                            f"Du bist Bot 1.0. Hier ist der Text aus den PDFs:\n{full_context_for_ki[:15000]}\n\n"
                            f"Aufgabe: Beantworte die Frage '{user_input}' basierend auf dem Text. "
                            f"Fasse die Informationen intelligent zusammen, nenne Fakten und Details. "
                            f"Wenn im Text nichts dazu steht, sag es höflich. "
                            f"Füge am Ende '🌐 Recherche-Empfehlung' hinzu."
                        )
                        
                        response = model.generate_content(prompt)
                        
                        with st.chat_message("assistant"):
                            st.markdown(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                
                except Exception as e:
                    if "429" in str(e):
                        st.error("⏳ Limit erreicht. Bitte 30 Sek. warten.")
                    else:
                        st.error(f"Fehler: {e}")
