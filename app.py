import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai

# Seite konfigurieren
st.set_page_config(page_title="Bot 1.0 Ultra", page_icon="🚀", layout="wide")

# --- KI SETUP ---
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
    
    for uploaded_file in uploaded_files:
        # Datei einlesen
        file_bytes = uploaded_file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            
            if suchbegriff.lower() in text.lower():
                # KONTEXT-LOGIK: Wir suchen die Position des Wortes
                start_pos = text.lower().find(suchbegriff.lower())
                
                # Wir nehmen 250 Zeichen davor und 250 danach für mehr Kontext
                start_idx = max(0, start_pos - 250)
                end_idx = min(len(text), start_pos + 250)
                
                snippet = text[start_idx:end_idx].replace("\n", " ").strip()
                
                all_results.append({
                    "Datei": uploaded_file.name,
                    "Seite": page_num + 1,
                    "Vorschau": f"... {snippet} ..."
                })
                # Wir speichern den ganzen Seitentext für die KI
                full_text_context += f"\n--- Seite {page_num+1} ({uploaded_file.name}) ---\n{text}"

    # Layout für Ergebnisse und KI
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 Fundstellen (Erweiterter Kontext)")
        if all_results:
            st.write(f"Anzahl der Treffer: {len(all_results)}")
            for res in all_results[:15]:
                with st.expander(f"Seite {res['Seite']} - {res['Datei']}"):
                    # Das Suchwort hervorheben (einfache Markdown-Fettung)
                    highlighted = res['Vorschau'].replace(suchbegriff, f"**{suchbegriff}**").replace(suchbegriff.capitalize(), f"**{suchbegriff.capitalize()}**")
                    st.write(highlighted)
        else:
            st.warning("Keine Treffer gefunden.")

    with col2:
        st.subheader("🧠 KI-Analyse")
        if KI_BEREIT:
            if st.button("KI-Experten fragen"):
                with st.spinner("Gemini 3 Flash analysiert den Kontext..."):
                    try:
                        # Modell-Check für 2026
                        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        target_model = "models/gemini-3-flash-preview" if any("gemini-3" in m for m in models) else "gemini-1.5-flash"
                        
                        m = genai.GenerativeModel(target_model)
                        # Wir geben der KI eine klare Rolle
                        prompt = (
                            f"Du bist ein technischer Experte. Hier sind Fundstellen aus einem PDF-Dokument:\n"
                            f"{full_text_context[:10000]}\n\n"
                            f"Frage des Nutzers: {suchbegriff}\n"
                            f"Erkläre basierend auf dem Text präzise, was dazu im Dokument steht."
                        )
                        
                        response = m.generate_content(prompt)
                        st.success("Analyse abgeschlossen:")
                        st.write(response.text)
                    except Exception as e:
                        st.error(f"KI-Fehler: {e}")
        else:
            st.warning("⚠️ Bitte GEMINI_API_KEY in den Secrets hinterlegen.")
