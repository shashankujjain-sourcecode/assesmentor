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

# Accessing the Gemini API Key from Streamlit Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("❌ API Key Missing! Please go to Streamlit Cloud > Settings > Secrets and add: GEMINI_API_KEY = 'your_key'")
    st.stop()

model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. CORE LOGIC FUNCTIONS ---
def generate_asset_questions(grade, subject, topic, outcomes):
    """Uses Gemini to create 5 conceptual questions with misconception mapping."""
    prompt = f"""
    You are an expert Indian curriculum designer and assessment creator at Ei ASSET level.
    Create exactly 5 high-quality, conceptual questions for:
    - Grade: {grade} | Subject: {subject} | Topic: {topic}
    - Learning Outcomes: {outcomes}

    STRICT RULES:
    1. Questions must test deep conceptual understanding, NOT rote memorization.
    2. Each WRONG option (distractor) must represent a specific common student misconception.
    3. Return ONLY a valid JSON object:
    {{
      "questions": [
        {{
          "qno": 1,
          "question": "Full question text...",
          "type": "MCQ",
          "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
          "correct": "A",
          "mappings": {{"B": "Misconception Name", "C": "Misconception Name", "D": "Logic Error"}}
        }}
      ]
    }}
    """
    response = model.generate_content(prompt)
    # Cleaning the response to ensure valid JSON
    json_text = response.text.strip().replace('```json', '').replace('```', '')
    return json.loads(json_text)

# --- 3. STREAMLIT UI ---
st.title("🎯 RemediAI: The Independent Engine")
st.caption("No Master Database required. Enter details manually for instant assessment design.")
st.markdown("---")

tab1, tab2 = st.tabs(["🏗️ Create Assessment", "📊 Generate Diagnostic Report"])

with tab1:
    st.header("1. Design Your Assessment")
    col1, col2 = st.columns(2)
    
    with col1:
        u_grade = st.selectbox("Grade", [f"Class {i}" for i in range(1, 13)] + ["Nursery", "LKG", "UKG"])
        u_subject = st.text_input("Subject", placeholder="e.g. Science, Mathematics")
        u_topic = st.text_input("Chapter/Topic Name", placeholder="e.g. Respiration in Plants")
        
    with col2:
        u_outcomes = st.text_area("Learning Outcomes (Paste from NCERT/Syllabus)", 
                                  placeholder="e.g. Understands the difference between aerobic and anaerobic respiration...")
        u_aid = st.text_input("Unique Assessment ID", value="TEST-101")

    if st.button("Generate Conceptual Questions"):
        if not u_subject or not u_topic or not u_outcomes:
            st.warning("Please fill in all fields to generate a high-quality test.")
        else:
            with st.spinner("AI is crafting conceptual questions and mapping misconceptions..."):
                try:
                    metadata = generate_asset_questions(u_grade, u_subject, u_topic, u_outcomes)
                    st.session_state[f"meta_{u_aid}"] = metadata
                    st.success(f"Assessment {u_aid} ready!")
                    st.json(metadata)
                except Exception as e:
                    st.error(f"Generation failed: {e}")

with tab2:
    st.header("2. Upload & Analyze Responses")
    st.info("Ensure your Excel file has the Assessment ID in Cell B1 and data starting from Row 4.")
    
    uploaded_file = st.file_uploader("Upload Student Responses (.xlsx)", type=["xlsx"])
    
    if uploaded_file:
        # Read the ID from B1 to match the metadata
        id_df = pd.read_excel(uploaded_file, header=None, nrows=1)
        excel_aid = str(id_df.iloc[0, 1]).strip()
        
        if f"meta_{excel_aid}" not in st.session_state:
            st.error(f"Metadata for ID '{excel_aid}' not found. Please create it in Tab 1 first.")
        else:
            st.success(f"Linked to Assessment: {excel_aid}")
            data_df = pd.read_excel(uploaded_file, skiprows=2) # Assumes headers on row 3
            
            if st.button("Generate Diagnostic PDF"):
                # Processing logic
                meta = st.session_state[f"meta_{excel_aid}"]
                # [Diagnostic Analysis Logic Here]
                st.balloons()
                st.write("Generating deep remedial plan...")
                # (You can add the PDF generation code here)
