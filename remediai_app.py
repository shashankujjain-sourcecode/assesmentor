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

# Custom CSS for a professional look
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_stdio=True)

# OpenAI API Setup
if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing! Please add 'OPENAI_API_KEY' to Streamlit Secrets.")
    st.stop()

# --- 2. DATA LOADING ---
@st.cache_data
def load_db():
    # Loading your master database [cite: 1, 2, 3]
    file_name = "Teachshank_Master_Database_FINAL (1).tsv"
    if os.path.exists(file_name):
        return pd.read_csv(file_name, sep='\t')
    else:
        st.error(f"❌ '{file_name}' not found in repository.")
        return pd.DataFrame()

db = load_db()

# --- 3. PDF GENERATOR FUNCTION ---
def generate_teacher_pdf(metadata, test_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # --- PAGE 1: STUDENT QUESTION PAPER ---
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"Assessment: {test_info['topic']}")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 70, f"ID: {test_info['aid']} | Time: {test_info['time']} mins | Difficulty: {test_info['difficulty']}/12")
    p.line(50, height - 75, 550, height - 75)
    
    y = height - 100
    for q in metadata['questions']:
        # Question Text
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"Q{q['qno']}. {q['question']}")
        y -= 20
        
        # Options
        p.setFont("Helvetica", 10)
        for label, text in q['options'].items():
            p.drawString(70, y, f"{label}. {text}")
            y -= 15
        y -= 20
        
        if y < 100:
            p.showPage()
            y = height - 50

    # --- PAGE 2: TEACHER'S LOGIC & ANSWER KEY ---
    p.showPage()
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "CONFIDENTIAL: Teacher's Answer Key & Guide")
    p.line(50, height - 55, 550, height - 55)
    
    y = height - 80
    for q in metadata['questions']:
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"Q{q['qno']} Correct Answer: {q['correct']}")
        y -= 15
        p.setFont("Helvetica-Oblique", 10)
        p.drawString(50, y, "Misconception Mapping (Diagnostic Logic):")
        y -= 15
        
        for option, error in q['mappings'].items():
            p.setFont("Helvetica", 9)
            p.drawString(70, y, f"Option {option}: {error}")
            y -= 12
        y -= 20
        
    p.save()
    buffer.seek(0)
    return buffer

# --- 4. STREAMLIT UI ---
st.title("🎯 RemediAI: Autopilot Assessment Creator")
st.write("Generate Ei ASSET-level conceptual tests using your NCERT Master Database.")

if not db.empty:
    with st.container():
        st.subheader("🏗️ Step 1: Design the Assessment")
        with st.form("creator_form"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                u_grade = st.selectbox("1. Select Grade", sorted(db['Grade'].unique()))
                sub_list = sorted(db[db['Grade'] == u_grade]['Subject'].unique())
                u_subject = st.selectbox("2. Select Subject", sub_list)

            with col2:
                topic_list = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]['Chapter Name'].unique()
                u_topic = st.selectbox("3. Select Topic", topic_list)
                u_diff = st.slider("4. Difficulty (1-12)", 1, 12, 6)

            with col3:
                u_num_q = st.number_input("5. Questions", 1, 15, 5)
                u_time = st.number_input("6. Time (Mins)", 10, 180, 30)
                u_aid = st.text_input("7. Assessment ID", value=f"{u_subject[:3].upper()}-{u_grade[-1] if u_grade[-1].isdigit() else 'X'}-101")

            # Fetch outcomes silently from DB [cite: 1, 27, 46]
            u_outcomes = db[(db['Grade'] == u_grade) & (db['Chapter Name'] == u_topic)]['Learning Outcomes'].values[0]
            st.info(f"**Target Outcomes:** {u_outcomes}")
            
            submit = st.form_submit_button("Generate AI Assessment")

    if submit:
        with st.spinner("AI is analyzing learning outcomes and mapping misconceptions..."):
            try:
                # OpenAI Request
                prompt = f"""
                You are an expert Indian assessment designer (Ei ASSET).
                Create {u_num_q} conceptual MCQ questions for {u_grade} {u_subject} on topic '{u_topic}'.
                NCERT Outcomes: {u_outcomes}
                Difficulty: {u_diff}/12.
                
                STRICT: Return ONLY valid JSON. Every wrong option MUST map to a specific student misconception.
                Structure: {{"questions": [{{"qno":1, "question":"", "options":{{"A":"","B":"","C":"","D":""}}, "correct":"A", "mappings":{{"B":"Error1", "C":"Error2", "D":"Error3"}}}}]}}
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "You output valid JSON for educational diagnostics."},
                              {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                metadata = json.loads(response.choices[0].message.content)
                test_info = {"topic": u_topic, "aid": u_aid, "time": u_time, "difficulty": u_diff}
                
                # Success & Preview
                st.success(f"Assessment {u_aid} Generated!")
                
                # PDF Download
                pdf_data = generate_teacher_pdf(metadata, test_info)
                st.download_button(
                    label="📥 Download Teacher's Printout (PDF)",
                    data=pdf_data,
                    file_name=f"Teacher_Printout_{u_aid}.pdf",
                    mime="application/pdf"
                )
                
                # Session Storage for Diagnostic Tab
                st.session_state[f"meta_{u_aid}"] = metadata
                st.json(metadata)
                
            except Exception as e:
                st.error(f"Error during generation: {e}")

else:
    st.error("Database initialization failed. Check your TSV file.")

st.markdown("---")
st.subheader("📊 Step 2: Diagnostic Reporting")
st.write("Once the test is done, upload your response Excel here.")
# (Response processing logic as built in previous steps goes here)
