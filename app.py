import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import re

# Seite konfigurieren
st.set_page_config(page_title="Bot 1.0", page_icon="🤖", layout="wide")

# --- BLAUE MARKIERUNG CSS ---
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
            if up_file.name not in st.session_state.pdf_cache:
                doc = fitz.open(stream=up_file.read(), filetype="pdf")
                st.session_state.pdf_cache[up_file.name] = [p.get_text() for p in doc]
            
            pages = st.session_state.pdf_cache[up_file.name]
            for i, page_text in enumerate(pages):
                if suchbegriff.lower() in page_text.lower():
                    start_pos = page_text.lower().find(suchbegriff.lower())
                    snippet = page_text[max(0, start_pos - 250):min(len(page_text), start_pos + 250)].replace("\n", " ").strip()
                    
                    pattern = re.compile(re.escape(suchbegriff), re.IGNORECASE)
                    highlighted = pattern.sub(f"**{suchbegriff}**", snippet)
                    
                    all_results.append({"file": up_file.name, "page": i+1, "text": highlighted})
                    full_text_context += f"\n{page_text}"
        
        status.update(label="Suche abgeschlossen!", state="complete")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Fundstellen")
        if all_results:
            for res in all_results[:10]:
                with st.expander(f"Seite {res['page']} - {res['file']}"):
                    st.markdown(res['text'])
        else:
            st.warning("Keine Treffer gefunden.")

    with col2:
        st.subheader("💬 Chat")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        if KI_BEREIT and st.button("KI Analyse starten"):
            st.session_state.messages.append({"role": "user", "content": suchbegriff})
            with st.chat_message("user"):
                st.markdown(suchbegriff)
            
            try:
                # Modellauswahl: Wir erzwingen Flash für höhere Limits
                available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                # Wir suchen nach der stabilsten Flash-Version
                target = "models/gemini-1.5-flash" 
                if any("gemini-1.5-flash" in m for m in available):
                    target = [m for m in available if "gemini-1.5-flash" in m][0]
                elif any("flash" in m.lower() for m in available):
                    target = [m for m in available if "flash" in m.lower()][0]

                model = genai.GenerativeModel(target)
                
                with st.spinner("Bot 1.0 denkt nach..."):
                    prompt = (
                        f"Du bist Bot 1.0. Antworte NUR basierend auf diesem Text:\n"
                        f"{full_text_context[:10000]}\n\n"
                        f"Frage: {suchbegriff}\n\n"
                        f"WICHTIG: Antworte auf Deutsch. "
                        f"Füge am Ende '🌐 Recherche-Empfehlung' mit Web-Suchbegriffen hinzu."
                    )
                    
                    response = model.generate_content(prompt)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    with st.chat_message("assistant"):
                        st.markdown(response.text)
            
            except Exception as e:
                if "429" in str(e):
                    st.error("⏳ Limit erreicht. Google erlaubt im Gratis-Tarif nur wenige Fragen pro Minute. Bitte warte kurz und klicke dann erneut auf den Button.")
                else:
                    st.error(f"KI-Fehler: {e}")
