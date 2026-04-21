import streamlit as st
import fitz  # PyMuPDF
import re

# 1. Name der App festlegen
APP_NAME = "Bot 1.0"

st.set_page_config(page_title=APP_NAME, page_icon="🔎", layout="wide")
st.title(f"🔎 {APP_NAME}")
st.markdown("Durchsuche mehrere PDFs gleichzeitig und speichere die Ergebnisse.")

# 2. Multi-Datei Upload in der Sidebar
with st.sidebar:
    st.header("Einstellungen")
    uploaded_files = st.file_uploader("PDF-Dateien wählen", type="pdf", accept_multiple_files=True)

if uploaded_files:
    suchbegriff = st.text_input("Wonach suchst du in allen Dokumenten?")

    if suchbegriff:
        all_results = []
        progress_bar = st.progress(0)
        
        # Durch alle hochgeladenen PDFs loopen
        for f_idx, uploaded_file in enumerate(uploaded_files):
            file_bytes = uploaded_file.read()
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            
            for i, seite in enumerate(doc):
                text = seite.get_text()
                if suchbegriff.lower() in text.lower():
                    zeilen = text.split('\n')
                    for z_idx, zeile in enumerate(zeilen):
                        if suchbegriff.lower() in zeile.lower():
                            start = max(0, z_idx - 1)
                            ende = min(len(zeilen), z_idx + 2)
                            kontext = " ... ".join(zeilen[start:ende])
                            markierter_text = re.sub(f"({re.escape(suchbegriff)})", r"**\1**", kontext, flags=re.IGNORECASE)
                            
                            all_results.append({
                                "datei": uploaded_file.name,
                                "seite": i + 1,
                                "text": markierter_text,
                                "roh_text": kontext # Für den Export ohne Sterne
                            })
            
            progress_bar.progress((f_idx + 1) / len(uploaded_files))

        # 3. Ergebnisse anzeigen
        if all_results:
            st.write(f"### {len(all_results)} Treffer gefunden:")
            
            # Export-Datei vorbereiten
            export_text = f"Suchergebnisse für: {suchbegriff}\n" + "="*30 + "\n\n"
            for res in all_results:
                export_text += f"Datei: {res['datei']} | Seite: {res['seite']}\nText: {res['roh_text']}\n" + "-"*10 + "\n"
                
                with st.expander(f"{res['datei']} - Seite {res['seite']}"):
                    st.markdown(res['text'])

            # 4. DOWNLOAD BUTTON
            st.sidebar.markdown("---")
            st.sidebar.download_button(
                label="📥 Ergebnisse als .txt speichern",
                data=export_text,
                file_name=f"Suchergebnisse_{suchbegriff}.txt",
                mime="text/plain"
            )
        else:
            st.warning("Keine Treffer in den Dateien gefunden.")
else:
    st.info("Bitte lade eine oder mehrere PDF-Dateien hoch.")
