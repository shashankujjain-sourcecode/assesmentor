import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from io import BytesIO

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="RemediAI: Autopilot Engine", layout="wide")

# FIX: Changed unsafe_allow_stdio to unsafe_allow_html to fix the TypeError
st.markdown(
    """
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { 
        width: 100%; 
        border-radius: 5px; 
        height: 3em; 
        background-color: #007bff; 
        color: white; 
        font-weight: bold;
    }
    .stSelectbox label { font-weight: bold; color: #1f2937; }
    </style>
    """, 
    unsafe_allow_html=True 
)

# OpenAI API Setup
if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing! Please add 'OPENAI_API_KEY' to Streamlit Secrets.")
    st.stop()

# --- 2. DATA LOADING (Robust Version) ---
@st.cache_data
def load_db():
    # Primary filename check
    file_name = "Teachshank_Master_Database_FINAL (1).tsv"
    
    if os.path.exists(file_name):
        return pd.read_csv(file_name, sep='\t')
    else:
        # Fallback: Search the directory for any .tsv file with 'Master' in the name
        for f in os.listdir("."):
            if f.endswith(".tsv") and "Master" in f:
                return pd.read_csv(f, sep='\t')
        return pd.DataFrame()

db = load_db()

# --- 3. PDF GENERATOR FUNCTION ---
def generate_teacher_pdf(metadata, test_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # PAGE 1: STUDENT QUESTION PAPER
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"Assessment: {test_info['topic']}")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 70, f"ID: {test_info['aid']} | Time: {test_info['time']} mins | Difficulty: {test_info['difficulty']}/12")
    p.line(50, height - 75, 550, height - 75)
    
    y = height - 100
    for q in metadata['questions']:
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"Q{q['qno']}. {q['question']}")
        y -= 20
        p.setFont("Helvetica", 10)
        for label, text in q['options'].items():
            p.drawString(70, y, f"{label}. {text}")
            y -= 15
        y -= 20
        if y < 100:
            p.showPage()
            y = height - 50

    # PAGE 2: TEACHER'S DIAGNOSTIC KEY
    p.showPage()
    p.setFont("Helvetica-Bold", 16)
    p.setStrokeColor(colors.red)
    p.drawString(50, height - 50, "CONFIDENTIAL: Teacher's Answer Key & Logic")
    p.line(50, height - 55, 550, height - 55)
    
    y = height - 80
    for q in metadata['questions']:
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"Q{q['qno']} Correct Answer: {q['correct']}")
        y -= 15
        p.setFont("Helvetica-Oblique", 9)
        p.drawString(50, y, "Misconception Mapping:")
        y -= 12
        for opt, err in q['mappings'].items():
            p.drawString(70, y, f"Option {opt}: {err}")
            y -= 11
        y -= 15
    p.save()
    buffer.seek(0)
    return buffer

# --- 4. STREAMLIT UI ---
st.title("🎯 RemediAI: Autopilot Assessment Creator")

if not db.empty:
    with st.form("creator_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 1. GRADE Selection
            u_grade = st.selectbox("1. Select Class", sorted(db['Grade'].unique()))
            # 2. SUBJECT Selection (Filtered by Grade)
            sub_list = sorted(db[db['Grade'] == u_grade]['Subject'].unique())
            u_subject = st.selectbox("2. Select Subject", sub_list)

        with col2:
            # 3. TOPIC Selection (Filtered by Grade and Subject)
            topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
            u_topic = st.selectbox("3. Select Topic", topic_df['Chapter Name'].unique())
            # 4. DIFFICULTY
            u_diff = st.slider("4. Difficulty (1-12)", 1, 12, 6)

        with col3:
            u_num_q = st.number_input("5. No. of Questions", 1, 15, 5)
            u_time = st.number_input("6. Time (Mins)", 10, 180, 30)
            u_aid = st.text_input("7. Assessment ID", value=f"{u_subject[:3].upper()}-101")

        # Automatically find Learning Outcomes from the DB for the prompt
        u_outcomes = db[(db['Grade'] == u_grade) & (db['Chapter Name'] == u_topic)]['Learning Outcomes'].values[0]
        st.info(f"**Outcome Found:** {u_outcomes}")
        
        submit = st.form_submit_button("Generate AI Assessment")

    if submit:
        with st.spinner("OpenAI is analyzing outcomes and mapping misconceptions..."):
            try:
                prompt = f"""
                You are an expert Indian assessment designer (Ei ASSET).
                Create {u_num_q} conceptual MCQ questions for {u_grade} {u_subject} on {u_topic}. 
                Outcomes: {u_outcomes}. Difficulty: {u_diff}/12.
                Return ONLY a JSON object. Each wrong option MUST map to a specific logic error.
                Structure: {{"questions": [{{"qno":1, "question":"", "options":{{"A":"","B":"","C":"","D":""}}, "correct":"A", "mappings":{{"B":"Error1", "C":"Error2", "D":"Error3"}}}}]}}
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "You are a specialized diagnostic assessment JSON generator."},
                              {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                metadata = json.loads(response.choices[0].message.content)
                test_info = {"topic": u_topic, "aid": u_aid, "time": u_time, "difficulty": u_diff}
                
                st.success(f"Assessment {u_aid} Generated!")
                
                # Download PDF Button
                pdf_data = generate_teacher_pdf(metadata, test_info)
                st.download_button(
                    label="📥 Download Teacher's Printout (PDF)",
                    data=pdf_data,
                    file_name=f"Teacher_Key_{u_aid}.pdf",
                    mime="application/pdf"
                )
                st.json(metadata)
                
            except Exception as e:
                st.error(f"Error during generation: {e}")
else:
    st.error("❌ Database file not found. Ensure 'Teachshank_Master_Database_FINAL (1).tsv' is in your GitHub repository.")
