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
st.set_page_config(page_title="RemediAI: Professional Edition", layout="wide")

# Enhanced CSS for Visual Appeal
st.markdown(
    """
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { border-radius: 8px; height: 3em; background-color: #2563eb; color: white; font-weight: 600; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #1d4ed8; border: none; }
    .question-card { background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
    .outcome-box { background-color: #eff6ff; padding: 15px; border-left: 5px solid #3b82f6; border-radius: 4px; margin-bottom: 20px; }
    .option-tag { color: #64748b; font-weight: bold; margin-right: 10px; }
    </style>
    """, 
    unsafe_allow_html=True 
)

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing! Add it to Streamlit Secrets.")
    st.stop()

# --- 2. DATA LOADING & CLEANING ---
@st.cache_data
def load_db():
    file_name = "Teachshank_Master_Database_FINAL (1).tsv"
    if os.path.exists(file_name):
        df = pd.read_csv(file_name, sep='\t')
        # FIX: Clean HTML tags like <br> from the database outcomes
        df['Learning Outcomes'] = df['Learning Outcomes'].str.replace(r'<[^>]*>', ' ', regex=True)
        return df
    return pd.DataFrame()

db = load_db()

# --- 3. PDF GENERATOR ---
def generate_teacher_pdf(metadata, test_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # STUDENT VIEW
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, h - 50, f"Assessment: {test_info['topic']}")
    p.setFont("Helvetica", 10)
    p.setFillColor(colors.grey)
    p.drawString(50, h - 70, f"ID: {test_info['aid']}  |  Grade: {test_info['grade']}  |  Time: {test_info['time']} mins")
    p.setStrokeColor(colors.lightgrey)
    p.line(50, h - 80, 545, h - 80)
    
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

    # TEACHER KEY VIEW
    p.showPage()
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, h - 50, "Teacher's Answer Key & Diagnostic Guide")
    y = h - 80
    for q in metadata.get('questions', []):
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"Q{q.get('qno', '?')} Correct: {q.get('correct', '')}")
        y -= 15
        p.setFont("Helvetica-Oblique", 9)
        p.setFillColor(colors.red)
        for opt, err in q.get('mappings', {}).items():
            p.drawString(70, y, f"Choice {opt} indicates: {err}")
            y -= 12
        p.setFillColor(colors.black)
        y -= 15
    p.save()
    buffer.seek(0)
    return buffer

# --- 4. UI ---
st.title("🎯 RemediAI Professional")
st.write("Generate and visualize high-fidelity conceptual assessments.")

if not db.empty:
    with st.sidebar:
        st.header("⚙️ Settings")
        u_grade = st.selectbox("Grade", sorted(db['Grade'].unique()))
        sub_list = sorted(db[db['Grade'] == u_grade]['Subject'].unique())
        u_subject = st.selectbox("Subject", sub_list)
        topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
        u_topic = st.selectbox("Topic", topic_df['Chapter Name'].unique())
        u_num_q = st.slider("Questions", 1, 10, 5)
        u_time = st.number_input("Time (Mins)", 10, 180, 30)
        u_aid = st.text_input("Assessment ID", value=f"{u_subject[:3].upper()}-101")
        
        # Get outcome
        u_outcomes = db[(db['Grade'] == u_grade) & (db['Chapter Name'] == u_topic)]['Learning Outcomes'].values[0]
        
    # Main Dashboard
    st.markdown(f"<div class='outcome-box'><b>Target Learning Outcomes:</b><br>{u_outcomes}</div>", unsafe_allow_html=True)
    
    if st.button("✨ Generate Assessment"):
        with st.spinner("AI is crafting conceptual questions..."):
            try:
                prompt = f"Create {u_num_q} conceptual questions for {u_grade} {u_subject} on {u_topic}. Outcomes: {u_outcomes}. JSON format: {{'questions': [{{'qno':1, 'question':'', 'options':{{'A':'','B':'','C':'','D':''}}, 'correct':'A', 'mappings':{{'B':'Err','C':'Err','D':'Err'}}}} ]}}"
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "You are a diagnostic assessment generator. Output ONLY JSON."},
                              {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                metadata = json.loads(response.choices[0].message.content)
                test_info = {"topic": u_topic, "aid": u_aid, "time": u_time, "grade": u_grade}
                
                st.session_state['current_test'] = metadata
                st.session_state['test_info'] = test_info
                st.success("Test Generated Successfully!")

            except Exception as e:
                st.error(f"Generation Error: {e}")

    # Visualizing the Test
    if 'current_test' in st.session_state:
        meta = st.session_state['current_test']
        info = st.session_state['test_info']
        
        col_dl, col_blank = st.columns([1, 2])
        pdf_data = generate_teacher_pdf(meta, info)
        col_dl.download_button("📥 Download PDF Report", pdf_data, f"{info['aid']}_RemediAI.pdf", "application/pdf")
        
        st.subheader("Preview Assessment")
        for q in meta.get('questions', []):
            with st.container():
                st.markdown(f"""
                <div class="question-card">
                    <b>Q{q.get('qno', '?')}:</b> {q.get('question', '')}<br><br>
                    <span class="option-tag">A.</span> {q.get('options', {}).get('A')}<br>
                    <span class="option-tag">B.</span> {q.get('options', {}).get('B')}<br>
                    <span class="option-tag">C.</span> {q.get('options', {}).get('C')}<br>
                    <span class="option-tag">D.</span> {q.get('options', {}).get('D')}<br><br>
                    <span style='color:green; font-size:0.8em;'>✔ Correct: {q.get('correct')}</span>
                </div>
                """, unsafe_allow_html=True)

else:
    st.error("Master Database file missing.")
