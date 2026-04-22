import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import re

# Seite konfigurieren
st.set_page_config(page_title="Bot 1.0", page_icon="🤖", layout="wide")

# --- DESIGN ---
st.markdown("""
    <style>
    div.stMarkdown b { color: #1E90FF; font-weight: bold; }
    .stChatMessage { border-radius: 10px; }
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

# --- SPEICHER (HISTORY & CHAT) ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []
if "pdf_cache" not in st.session_state:
    st.session_state.pdf_cache = {}

def add_to_history(query):
    if query and query not in st.session_state.history:
        st.session_state.history.insert(0, query)
        st.session_state.history = st.session_state.history[:5]

# --- UI SEITENLEISTE ---
with st.sidebar:
    st.title("🤖 Bot 1.0")
    st.header("⚙️ Verwaltung")
    uploaded_files = st.file_uploader("PDFs hochladen", type="pdf", accept_multiple_files=True)
    
    if st.button("Gesamten Verlauf löschen"):
        st.session_state.messages = []
        st.session_state.history = []
        st.rerun()
    
    if st.session_state.history:
        st.subheader("🕒 Letzte Suchen")
        for item in st.session_state.history:
            if st.sidebar.button(f"🔍 {item}", key=f"hist_{item}"):
                # Ermöglicht schnelles Wiederholen einer Suche
                pass

# --- HAUPTBEREICH ---
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
                    
                    pattern = re.compile(re.escape(user_input), re.IGNORECASE)
                    highlighted = pattern.sub(f"**{user_input}**", snippet)
                    
                    all_results.append({"file": up_file.name, "page": i+1, "text": highlighted})
                    full_context_for_ki += f"\n[Quelle: {up_file.name}, Seite: {i+1}]\n{page_text}"
        
        status.update(label="Suche abgeschlossen!", state="complete")

    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.subheader("📄 Einzelne Fundstellen")
        if all_results:
            for res in all_results[:10]:
                with st.expander(f"Seite {res['page']} - {res['file']}"):
                    st.markdown(res['text'])
        else:
            st.warning("Keine direkten Treffer.")

    with col2:
        st.subheader("💬 KI-Chat & Zusammenfassung")
        
        for m in st.session_state.messages:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        if KI_BEREIT and (not st.session_state.messages or st.session_state.messages[-1]["content"] != user_input):
            with st.chat_message("user"):
                st.markdown(user_input)
            st.session_state.messages.append({"role": "user", "content": user_input})

            try:
                # --- EXPLIZITE GEMINI 3.0 FLASH WAHL ---
                # Wir suchen nach dem exakten Namen in der API-Liste
                models = [m.name for m in genai.list_models()]
                g3_models = [m for m in models if "gemini-3.0-flash" in m]
                
                # Falls 3.0 Flash gefunden wird, nimm ihn, sonst 1.5 als Backup
                target_model = g3_models[0] if g3_models else "models/gemini-1.5-flash"
                
                model = genai.GenerativeModel(target_model)
                
                with st.spinner(f"Bot 1.0 nutzt {target_model}..."):
                    prompt = (
                        f"SYSTEM: Du bist Bot 1.0. Nutze NUR den PDF-Inhalt unten.\n"
                        f"KONTEXT AUS PDFs:\n{full_context_for_ki[:15000]}\n\n"
                        f"AUFGABE: Beantworte die Frage '{user_input}' ausführlich und als Zusammenfassung. "
                        f"Nutze Fakten aus dem Kontext. Antworte auf DEUTSCH.\n"
                        f"AM ENDE: Füge '🌐 Recherche-Empfehlung' mit Suchbegriffen hinzu."
                    )
                    
                    response = model.generate_content(prompt)
                    
                    with st.chat_message("assistant"):
                        st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
            
            except Exception as e:
                st.error(f"KI-Fehler: {e}")
