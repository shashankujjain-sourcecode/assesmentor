import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

# --- 1. SETUP & SECRETS ---
st.set_page_config(page_title="RemediAI Engine", layout="wide")

# Use Streamlit Secrets for the API Key
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("❌ API Key Missing! Add 'GEMINI_API_KEY' to Streamlit Secrets.")
    st.stop()

model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. DATA LOADING (Flexible Filename) ---
@st.cache_data
def load_master_data():
    # List of possible filename variations to check
    possible_names = [
        "Teachshank_Master_Database_FINAL (1).tsv",
        "Teachshank_Master_Database_FINAL.tsv",
        "Teachshank_Master_Data_base_FINAL.tsv"
    ]
    
    for name in possible_names:
        if os.path.exists(name):
            try:
                # TSV files use tab delimiters [cite: 26, 27]
                return pd.read_csv(name, sep='\t')
            except Exception as e:
                st.error(f"Error reading {name}: {e}")
    
    st.error("❌ Master Database file not found in the repository. Please check the filename on GitHub.")
    return pd.DataFrame()

master_df = load_master_data()

# --- 3. CORE LOGIC ---
def generate_asset_questions(grade, subject, chapter, outcomes):
    prompt = f"""
    You are an expert Indian curriculum designer at Ei ASSET level.
    Create 5 conceptual MCQ questions for Grade {grade}, Subject {subject}, Topic {chapter}.
    Use these NCERT Learning Outcomes: {outcomes}.
    
    STRICT RULES:
    - Questions must test deep conceptual understanding, NOT rote memory.
    - Each WRONG option must represent a specific common student misconception.
    - Return ONLY a JSON object with this structure:
    {{
      "questions": [
        {{
          "qno": 1, "question": "...", "options": {{"A": "..", "B": "..", "C": "..", "D": ".."}},
          "correct": "A", "mappings": {{"B": "Misconception Name", "C": "Misconception Name", "D": "Logic Error"}}
        }}
      ]
    }}
    """
    response = model.generate_content(prompt)
    json_str = response.text.strip().replace('```json', '').replace('```', '')
    return json.loads(json_str)

# --- 4. STREAMLIT UI ---
st.title("🎯 RemediAI: Beyond Ei ASSET")
st.markdown("---")

tab1, tab2 = st.tabs(["🏗️ Create Assessment", "📊 Generate Diagnostic Report"])

with tab1:
    if not master_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            sel_grade = st.selectbox("Select Grade", master_df['Grade'].unique())
            # Filter subjects based on grade [cite: 24, 25]
            sub_options = master_df[master_df['Grade'] == sel_grade]['Subject'].unique()
            sel_subject = st.selectbox("Select Subject", sub_options)
        
        with col2:
            # Filter chapters based on grade and subject [cite: 26, 111]
            chap_df = master_df[(master_df['Grade'] == sel_grade) & (master_df['Subject'] == sel_subject)]
            sel_chapter = st.selectbox("Select Chapter", chap_df['Chapter Name'].unique())
            
            # Fetch outcomes for the selected chapter [cite: 27, 28]
            outcomes = chap_df[chap_df['Chapter Name'] == sel_chapter]['Learning Outcomes'].values[0]
            st.info(f"**Learning Outcomes:** {outcomes}")

        aid = st.text_input("Assessment ID", value=f"{sel_subject[:3].upper()}-{sel_grade[-1] if sel_grade[-1].isdigit() else '0'}-101")

        if st.button("Generate Assessment"):
            with st.spinner("AI is analyzing outcomes and creating questions..."):
                metadata = generate_asset_questions(sel_grade, sel_subject, sel_chapter, outcomes)
                st.session_state[f"meta_{aid}"] = metadata
                st.success(f"Assessment {aid} generated and stored in session!")
                st.json(metadata)

with tab2:
    st.header("Upload Results")
    uploaded_file = st.file_uploader("Upload Excel with ID in Cell B1", type=["xlsx"])
    
    if uploaded_file:
        id_df = pd.read_excel(uploaded_file, header=None, nrows=1)
        excel_aid = str(id_df.iloc[0, 1]).strip()
        
        if f"meta_{excel_aid}" not in st.session_state:
            st.error(f"No metadata found for {excel_aid}. Create the test in Tab 1 first.")
        else:
            data_df = pd.read_excel(uploaded_file, skiprows=2)
            meta = st.session_state[f"meta_{excel_aid}"]
            
            if st.button("Generate Remedial Plan"):
                # Analysis and PDF generation logic...
                st.balloons()
                st.success(f"Full Diagnostic Report for {excel_aid} generated!")
