import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import google.generativeai as genai

# Seite konfigurieren
st.set_page_config(page_title="Bot 1.0 Ultra", page_icon="🚀", layout="wide")

# --- KI SETUP ---
# Wir prüfen, ob der Key in den Streamlit Secrets vorhanden ist
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    KI_BEREIT = True
except Exception:
    KI_BEREIT = False

# --- SPEICHER (Letzte 5 Suchen) ---
if "history" not in st.session_state:
    st.session_state.history = []

def add_to_history(query):
    if query and query not in st.session_state.history:
        # Fügt die neue Suche oben ein und behält nur die letzten 5
        st.session_state.history.insert(0, query)
        st.session_state.history = st.session_state.history[:5]

# --- UI DESIGN ---
st.title("🚀 Bot 1.0 Ultra (2026 Edition)")

with st.sidebar:
    st.header("⚙️ Verwaltung")
    uploaded_files = st.file_uploader("PDFs hochladen", type="pdf", accept_multiple_files=True)
    
    if st.session_state.history:
        st.subheader("🕒 Letzte Suchen")
        for h in st.session_state.history:
            st.info(h)

# Haupt-Eingabefeld
suchbegriff = st.text_input("Wonach suchst du im Dokument?", "")

if uploaded_files and suchbegriff:
    add_to_history(suchbegriff)
    all_results = []
    full_text_context = ""
    
    # PDF Verarbeitung
    for uploaded_file in uploaded_files:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if suchbegriff.lower() in text.lower():
                all_results.append({
                    "Datei": uploaded_file.name,
                    "Seite": page_num + 1,
                    "Vorschau": text[:200].replace("\n", " ") + "..."
                })
                full_text_context += f"\n--- Seite {page_num+1} ({uploaded_file.name}) ---\n{text}"

    # Layout für Ergebnisse und KI
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 Fundstellen")
        if all_results:
            for res in all_results[:15]:
                with st.expander(f"Seite {res['Seite']} - {res['Datei']}"):
                    st.write(f"**Vorschau:** {res['Vorschau']}")
        else:
            st.warning("Keine Treffer im Text gefunden.")

    with col2:
        st.subheader("🧠 KI-Analyse")
        if KI_BEREIT:
            if st.button("KI-Experten fragen"):
                with st.spinner("KI denkt nach..."):
                    try:
                        # Automatische Wahl des besten Modells (Gemini 3 oder 1.5)
                        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        target_model = "models/gemini-3-flash-preview" if any("gemini-3" in m for m in models) else "gemini-1.5-flash"
                        
                        m = genai.GenerativeModel(target_model)
                        prompt = f"Du bist ein PDF-Analyst. Basierend auf diesem Text: '{full_text_context[:8000]}' \nBeantworte folgende Frage präzise: {suchbegriff}"
                        
                        response = m.generate_content(prompt)
                        st.success("Analyse abgeschlossen:")
                        st.write(response.text)
                    except Exception as e:
                        st.error(f"KI-Fehler: {e}")
        else:
            st.warning("⚠️ KI-Key nicht gefunden. Bitte in den Streamlit-Secrets hinterlegen.")
