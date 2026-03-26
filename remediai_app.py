import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from io import BytesIO

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="RemediAI: Autopilot Engine", layout="wide")

st.markdown(
    """
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; font-weight: bold; }
    </style>
    """, 
    unsafe_allow_html=True 
)

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing! Add it to Streamlit Secrets.")
    st.stop()

# --- 2. DATABASE LOADING ---
@st.cache_data
def load_db():
    file_name = "Teachshank_Master_Database_FINAL (1).tsv"
    if os.path.exists(file_name):
        return pd.read_csv(file_name, sep='\t')
    else:
        for f in os.listdir("."):
            if f.endswith(".tsv") and "Master" in f:
                return pd.read_csv(f, sep='\t')
        return pd.DataFrame()

db = load_db()

# --- 3. PDF GENERATION (With Error Handling) ---
def generate_teacher_pdf(metadata, test_info):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # STUDENT PAGE
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, f"Assessment: {test_info['topic']}")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 70, f"ID: {test_info['aid']} | Class: {test_info['grade']}")
    p.line(50, height - 75, 550, height - 75)
    
    y = height - 100
    # Use .get() to prevent 'qno' or other key errors
    for q in metadata.get('questions', []):
        q_num = q.get('qno', '??')
        q_text = q.get('question', 'Question text missing')
        
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"Q{q_num}. {q_text}")
        y -= 20
        
        p.setFont("Helvetica", 10)
        options = q.get('options', {})
        for label, text in options.items():
            p.drawString(70, y, f"{label}. {text}")
            y -= 15
        y -= 20
        if y < 100: p.showPage(); y = height - 50

    # TEACHER KEY PAGE
    p.showPage()
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "Teacher's Diagnostic Key")
    y = height - 80
    for q in metadata.get('questions', []):
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"Q{q.get('qno', '??')} Answer: {q.get('correct', 'N/A')}")
        y -= 15
        p.setFont("Helvetica-Oblique", 9)
        mappings = q.get('mappings', {})
        for opt, err in mappings.items():
            p.drawString(70, y, f"Option {opt}: {err}")
            y -= 12
        y -= 15
    p.save()
    buffer.seek(0)
    return buffer

# --- 4. APP UI ---
st.title("🎯 RemediAI Assessment Creator")

if not db.empty:
    with st.form("creator_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            u_grade = st.selectbox("1. Select Class", sorted(db['Grade'].unique()))
            sub_list = sorted(db[db['Grade'] == u_grade]['Subject'].unique())
            u_subject = st.selectbox("2. Select Subject", sub_list)
        with col2:
            topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
            u_topic = st.selectbox("3. Select Topic", topic_df['Chapter Name'].unique())
            u_diff = st.slider("4. Difficulty (1-12)", 1, 12, 6)
        with col3:
            u_num_q = st.number_input("5. Questions", 1, 15, 5)
            u_time = st.number_input("6. Time (Mins)", 10, 180, 30)
            u_aid = st.text_input("7. Assessment ID", value=f"{u_subject[:3].upper()}-101")

        u_outcomes = db[(db['Grade'] == u_grade) & (db['Chapter Name'] == u_topic)]['Learning Outcomes'].values[0]
        st.info(f"**Target Learning Outcomes:** {u_outcomes}")
        submit = st.form_submit_button("Generate Assessment")

    if submit:
        with st.spinner("AI is crafting conceptual questions..."):
            try:
                # ENFORCED SCHEMA PROMPT
                prompt = f"""
                Create {u_num_q} conceptual questions for {u_grade} {u_subject} on {u_topic}. 
                Outcomes: {u_outcomes}. 
                
                You MUST return a JSON object with exactly this structure:
                {{
                  "questions": [
                    {{
                      "qno": 1,
                      "question": "...",
                      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
                      "correct": "A",
                      "mappings": {{"B": "Misconception Name", "C": "Misconception Name", "D": "Logic Error"}}
                    }}
                  ]
                }}
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "You are a diagnostic assessment generator. Output ONLY the specified JSON format."},
                              {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                metadata = json.loads(response.choices[0].message.content)
                test_info = {"topic": u_topic, "aid": u_aid, "time": u_time, "difficulty": u_diff, "grade": u_grade}
                
                st.success("Test Generated!")
                pdf_data = generate_teacher_pdf(metadata, test_info)
                st.download_button("📥 Download Teacher PDF", pdf_data, f"{u_aid}_Key.pdf", "application/pdf")
                st.json(metadata)
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.error("❌ Database file not found. Ensure your .tsv file is in the GitHub repository.")
