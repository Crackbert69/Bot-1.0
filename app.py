import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import re

# Seite konfigurieren
st.set_page_config(page_title="Bot 1.0", page_icon="🤖", layout="wide")

# --- BLAUE MARKIERUNG CSS (FIXED) ---
st.markdown("""
    <style>
    .highlight { color: #1E90FF; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- KI SETUP ---
@st.cache_resource
def setup_ki():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return True
    except:
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

suchbegriff = st.text_input("Frag den Bot etwas zu deinen PDFs:", "")

if uploaded_files and suchbegriff:
    all_results = []
    full_text_context = ""
    
    with st.status("Suche in Dokumenten...", expanded=False) as status:
        for up_file in uploaded_files:
            # Schneller Cache-Check
            if up_file.name not in st.session_state.pdf_cache:
                doc = fitz.open(stream=up_file.read(), filetype="pdf")
                st.session_state.pdf_cache[up_file.name] = [p.get_text() for p in doc]
            
            pages = st.session_state.pdf_cache[up_file.name]
            for i, page_text in enumerate(pages):
                if suchbegriff.lower() in page_text.lower():
                    start_pos = page_text.lower().find(suchbegriff.lower())
                    snippet = page_text[max(0, start_pos-250):min(len(page_text), start_pos+250)].replace("\n", " ")
                    
                    # Blaues Highlighting
                    pattern = re.compile(re.escape(suchbegriff), re.IGNORECASE)
                    highlighted = pattern.sub(f'<span class="highlight">{suchbegriff}</span>', snippet)
                    
                    all_results.append({"file": up_file.name, "page": i+1, "text": highlighted})
                    full_text_context += f"\n{page_text}"
        status.update(label="Suche fertig!", state="complete")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📄 Fundstellen")
        for res in all_results[:10]:
            with st.expander(f"Seite {res['page']} - {res['file']}"):
                st.markdown(res['text'], unsafe_allow_html=True)

    with col2:
        st.subheader("💬 Chat")
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])

        if KI_BEREIT and st.button("KI Analyse"):
            st.session_state.messages.append({"role": "user", "content": suchbegriff})
            with st.chat_message("user"): st.markdown(suchbegriff)
            
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"Antworte NUR mit PDF-Infos: {full_text_context[:10000]}\nFrage: {suchbegriff}\nAm Ende: 🌐 Recherche-Empfehlung."
            
            response = model.generate_content(prompt)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            with st.chat_message("assistant"): st.markdown(response.text)
