import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

# --- 1. SETUP & MODEL VERIFICATION ---
st.set_page_config(page_title="RemediAI: Outcome Engine", layout="wide")

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("❌ API Key Missing! Add 'GEMINI_API_KEY' to Streamlit Secrets.")
    st.stop()

# Helper to ensure the model exists and is reachable
@st.cache_resource
def get_model():
    try:
        # Standard model string for 1.5 Flash
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Model Initialization Error: {e}")
        return None

model = get_model()

# --- 2. GENERATION LOGIC ---
def generate_questions(grade, subject, outcomes):
    prompt = f"""
    Expert Assessment Designer (Ei ASSET style). 
    Grade: {grade} | Subject: {subject}
    NCERT Outcomes: {outcomes}
    
    Task: Create 5 conceptual MCQ questions. 
    Rule: Each wrong option MUST map to a specific Indian student misconception.
    Output: Return ONLY a JSON object. No markdown. No intro.
    {{
      "questions": [
        {{
          "qno": 1, "question": "...", "options": {{"A":"", "B":"", "C":"", "D":""}},
          "correct": "A", "mappings": {{"B":"Misconception", "C":"Misconception", "D":"Logic Error"}}
        }}
      ]
    }}
    """
    response = model.generate_content(prompt)
    # Aggressive cleaning for JSON safety
    raw_text = response.text.strip()
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0]
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0]
    
    return json.loads(raw_text)

# --- 3. THE INTERFACE ---
st.title("🎯 RemediAI: Outcome-First Engine")
st.info("Generating deep-diagnostic assessments based strictly on NCERT Learning Outcomes.")

tab1, tab2 = st.tabs(["🏗️ Create Assessment", "📊 Generate Report"])

with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        u_grade = st.selectbox("Grade", [f"Class {i}" for i in range(1, 13)] + ["Nursery", "LKG", "UKG"])
        u_subject = st.text_input("Subject")
        u_aid = st.text_input("Assessment ID", value="OUTCOME-101")
    with col2:
        # Purely Outcome Based
        u_outcomes = st.text_area("Paste NCERT Learning Outcomes", height=200)

    if st.button("Generate Conceptual Test"):
        if model and u_outcomes and u_subject:
            with st.spinner("Analyzing outcomes..."):
                try:
                    metadata = generate_questions(u_grade, u_subject, u_outcomes)
                    st.session_state[f"meta_{u_aid}"] = metadata
                    st.success(f"Assessment {u_aid} successfully mapped to misconceptions!")
                    st.json(metadata)
                except Exception as e:
                    st.error(f"Parsing Error: {e}. Check if the AI returned valid JSON.")
        else:
            st.warning("Please provide Subject and Outcomes.")

with tab2:
    st.header("Upload Results & Analyze")
    uploaded_file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
    
    if uploaded_file:
        id_df = pd.read_excel(uploaded_file, header=None, nrows=1)
        excel_aid = str(id_df.iloc[0, 1]).strip()
        
        if f"meta_{excel_aid}" in st.session_state:
            st.success(f"Metadata Found for {excel_aid}")
            # PDF Generation logic will go here
        else:
            st.error("ID mismatch or Metadata missing.")
