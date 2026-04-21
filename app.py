import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import google.generativeai as genai

st.set_page_config(page_title="Bot 1.0 Ultra", page_icon="🚀", layout="wide")

# --- 1. KEY VERSTECKEN ---
# Streamlit sucht diesen Key automatisch in deinen "Secrets"
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    KI_BEREIT = True
except:
    KI_BEREIT = False

# --- 2. INDIVIDUELLER SPEICHER (Letzte 5 Anfragen) ---
if "history" not in st.session_state:
    st.session_state.history = []

def add_to_history(query):
    if query not in st.session_state.history:
        st.session_state.history.insert(0, query)
        st.session_state.history = st.session_state.history[:5] # Nur die letzten 5

st.title("🚀 Bot 1.0 Ultra - Mit KI & Verlauf")

with st.sidebar:
    st.header("Dateien & Verlauf")
    uploaded_files = st.file_uploader("PDFs hochladen", type="pdf", accept_multiple_files=True)
    
    if st.session_state.history:
        st.subheader("Deine letzten Suchen:")
        for h in st.session_state.history:
            if st.button(f"🔍 {h}", key=h):
                # Hier könnte man die Suche erneut triggern
                pass

suchbegriff = st.text_input("Suche nach Inhalten oder frage die KI:", "")

if uploaded_files and suchbegriff:
    add_to_history(suchbegriff)
    all_results = []
    full_text_context = "" # Für die KI
    
    for uploaded_file in uploaded_files:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            if suchbegriff.lower() in text.lower():
                all_results.append({
                    "Datei": uploaded_file.name,
                    "Seite": page_num + 1,
                    "Vorschau": text[:150].replace("\n", " ") + "..."
                })
                full_text_context += f"\nQuelle {uploaded_file.name}, Seite {page_num+1}: {text}"

    # Ergebnisse anzeigen
    if all_results:
        st.success(f"{len(all_results)} Treffer gefunden!")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Fundstellen")
            for res in all_results[:10]: # Zeige max 10 zur Übersicht
                with st.expander(f"Seite {res['Seite']} - {res['Datei']}"):
                    st.write(res['Vorschau'])
        
        with col2:
            if KI_BEREIT:
                st.subheader("🧠 KI-Experten-Check")
                if st.button("Diese Fundstellen analysieren"):
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    prompt = f"Basierend auf diesen Textstellen: {full_text_context[:5000]} \n\n Beantworte/Analysiere: {suchbegriff}"
                    response = model.generate_content(prompt)
                    st.info(response.text)
            else:
                st.warning("KI-Key fehlt in den Streamlit-Secrets!")
