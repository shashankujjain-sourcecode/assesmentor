import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from io import BytesIO

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="RemediAI Professional", layout="wide")

# CSS for high-fidelity "ASSET-style" visualization
st.markdown(
    """
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { border-radius: 8px; background-color: #2563eb; color: white; font-weight: 600; border: none; }
    .question-card { 
        background-color: white; padding: 24px; border-radius: 12px; 
        border: 1px solid #e2e8f0; margin-bottom: 20px; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); 
    }
    .outcome-box { 
        background-color: #eff6ff; padding: 15px; border-left: 5px solid #3b82f6; 
        border-radius: 4px; margin-bottom: 25px; font-size: 0.95rem;
    }
    .option-row { margin: 8px 0; padding: 8px; border-radius: 6px; background-color: #f1f5f9; }
    .correct-ans { color: #059669; font-weight: bold; margin-top: 10px; display: block; }
    </style>
    """, 
    unsafe_allow_html=True 
)

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing in Streamlit Secrets.")
    st.stop()

# --- 2. DATA LOADING & HTML CLEANING ---
@st.cache_data
def load_db():
    # Searching for your specific filename
    file_name = "Teachshank_Master_Database_FINAL (1).tsv"
    if os.path.exists(file_name):
        df = pd.read_csv(file_name, sep='\t')
        # Remove <br> tags from the NCERT Learning Outcomes [cite: 27, 35, 126]
        df['Learning Outcomes'] = df['Learning Outcomes'].str.replace(r'<[^>]*>', ' ', regex=True)
        return df
    return pd.DataFrame()

db = load_db()

# --- 3. PDF GENERATOR ---
def generate_pdf(metadata, test_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # Student Header
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, h - 50, f"Assessment: {test_info['topic']}")
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.grey)
    p.drawString(50, h - 70, f"ID: {test_info['aid']}  |  Grade: {test_info['grade']}")
    p.line(50, h - 75, 545, h - 75)
    
    # Questions
    y = h - 110
    p.setFillColor(colors.black)
    for q in metadata.get('questions', []):
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"Q{q.get('qno', '?')}. {q.get('question', '')}")
        y -= 20
        p.setFont("Helvetica", 10)
        for label, text in q.get('options', {}).items():
            p.drawString(70, y, f"{label}. {text}")
            y -= 15
        y -= 25
        if y < 100: p.showPage(); y = h - 50
    
    p.save()
    buffer.seek(0)
    return buffer

# --- 4. APP INTERFACE ---
st.title("🎯 RemediAI: Conceptual Assessment Engine")

if not db.empty:
    with st.sidebar:
        st.header("📋 Setup")
        u_grade = st.selectbox("Grade", sorted(db['Grade'].unique())) [cite: 26, 54]
        sub_list = sorted(db[db['Grade'] == u_grade]['Subject'].unique()) [cite: 27, 44]
        u_subject = st.selectbox("Subject", sub_list)
        
        topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
        u_topic = st.selectbox("Topic", topic_df['Chapter Name'].unique()) [cite: 115, 142]
        
        u_num_q = st.slider("Number of Questions", 1, 10, 5)
        u_aid = st.text_input("Assessment ID", value=f"{u_subject[:3].upper()}-101")
        
        # Outcome retrieval [cite: 27, 47, 123]
        u_outcomes = db[(db['Grade'] == u_grade) & (db['Chapter Name'] == u_topic)]['Learning Outcomes'].values[0]

    # Main Area
    st.markdown(f"<div class='outcome-box'><b>NCERT Learning Outcomes:</b><br>{u_outcomes}</div>", unsafe_allow_html=True)
    
    if st.button("✨ Generate Conceptual Assessment"):
        with st.spinner("AI is analyzing outcomes for deep misconceptions..."):
            try:
                # Prompting OpenAI for strict diagnostic JSON
                prompt = f"Create {u_num_q} high-fidelity conceptual questions for {u_grade} {u_subject} on {u_topic}. Focus on these outcomes: {u_outcomes}. Return JSON only."
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "You are a diagnostic assessment expert. Output ONLY JSON."},
                              {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                st.session_state['assessment'] = json.loads(response.choices[0].message.content)
                st.session_state['info'] = {"topic": u_topic, "aid": u_aid, "grade": u_grade}
            except Exception as e:
                st.error(f"Error: {e}")

    # Visualization
    if 'assessment' in st.session_state:
        res = st.session_state['assessment']
        info = st.session_state['info']
        
        pdf_file = generate_pdf(res, info)
        st.download_button("📥 Download PDF Paper", pdf_file, f"{info['aid']}.pdf", "application/pdf")
        
        for q in res.get('questions', []):
            st.markdown(f"""
            <div class="question-card">
                <b>Question {q.get('qno')}:</b> {q.get('question')}<br><br>
                <div class="option-row"><b>A.</b> {q.get('options', {}).get('A')}</div>
                <div class="option-row"><b>B.</b> {q.get('options', {}).get('B')}</div>
                <div class="option-row"><b>C.</b> {q.get('options', {}).get('C')}</div>
                <div class="option-row"><b>D.</b> {q.get('options', {}).get('D')}</div>
                <span class="correct-ans">✔ Correct Answer: {q.get('correct')}</span>
            </div>
            """, unsafe_allow_html=True)
else:
    st.error("❌ Master Database file missing. Please ensure 'Teachshank_Master_Database_FINAL (1).tsv' is in your GitHub folder.")
