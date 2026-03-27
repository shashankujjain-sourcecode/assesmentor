import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# --- 1. CORE SETUP & PREMIUM STYLING ---
st.set_page_config(page_title="RemediAI Ultra | Diagnostic Engine", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { 
        border-radius: 8px; background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); 
        color: white; font-weight: bold; height: 3.5em; width: 100%; border: none;
    }
    .report-card { 
        background-color: white; padding: 24px; border-radius: 12px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-left: 6px solid #1e3a8a; margin-bottom: 20px;
    }
    .outcome-banner {
        background-color: #eff6ff; padding: 15px; border-radius: 8px; border: 1px solid #bfdbfe; color: #1e40af; margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("🔑 OpenAI API Key missing in Secrets!")
    st.stop()

# --- 2. DATABASE LOADING ---
@st.cache_data
def load_vetted_db():
    db_file = next((f for f in os.listdir(".") if "Master" in f and (f.endswith(".tsv") or f.endswith(".csv"))), None)
    if db_file:
        sep = ',' if db_file.endswith(".csv") else '\t'
        df = pd.read_csv(db_file, sep=sep)
        df['Learning Outcomes'] = df['Learning Outcomes'].str.replace(r'<[^>]*>', ' ', regex=True)
        return df
    return pd.DataFrame()

db = load_vetted_db()

# Persistent Storage for Assessment IDs and Logic
if 'vault' not in st.session_state: st.session_state['vault'] = {}

# --- 3. MULTICOLORED PDF ENGINE ---
def create_branded_pdf(metadata, info, school_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # Header: Branding (Deep Blue)
    p.setFillColor(colors.HexColor("#1e3a8a"))
    p.rect(0, h - 90, w, 90, fill=1, stroke=0)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(w/2, h - 40, school_name.upper())
    p.setFont("Helvetica", 10)
    p.drawCentredString(w/2, h - 60, f"DIAGNOSTIC ASSESSMENT | {info['subject'].upper()}")
    p.drawCentredString(w/2, h - 75, f"ID: {info['aid']} | Topic: {info['topic']}")

    # Content Area
    y = h - 130
    for idx, q in enumerate(metadata.get('questions', [])):
        if y < 120: p.showPage(); y = h - 50
        p.setFont("Helvetica-Bold", 11)
        p.setFillColor(colors.HexColor("#1e3a8a"))
        p.drawString(50, y, f"{idx+1}.")
        p.setFillColor(colors.black)
        
        # Safe get for question text
        q_text = q.get('question') or q.get('q') or "Missing Question"
        p.drawString(70, y, q_text)
        y -= 25
        
        p.setFont("Helvetica", 10)
        opts = q.get('options', {})
        for label in ["A", "B", "C", "D"]:
            p.drawString(85, y, f"{label}) {opts.get(label, '---')}")
            y -= 18
        y -= 20

    p.save()
    buffer.seek(0)
    return buffer

# --- 4. THE 3-STEP WORKFLOW ---
st.title("🚀 RemediAI Ultra: The EI-Killer Engine")
t1, t2, t3 = st.tabs(["🏗️ Phase 1: Create", "📤 Phase 2: Upload", "📊 Phase 3: Diagnose"])

with t1:
    if not db.empty:
        c1, c2, c3 = st.columns(3)
        with c1:
            u_school = st.text_input("School Name", "Global International Academy")
            u_grade = st.selectbox("Grade", sorted(db['Grade'].unique()))
            u_subject = st.selectbox("Subject", sorted(db[db['Grade'] == u_grade]['Subject'].unique()))
        with c2:
            topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
            u_topic = st.selectbox("Topic", topic_df['Chapter Name'].unique())
            u_diff = st.select_slider("Difficulty Level", options=list(range(1, 13)), value=7)
        with c3:
            u_num = st.number_input("Questions", 1, 15, 5)
            u_time = st.number_input("Time (Mins)", 10, 180, 40)
            u_aid = st.text_input("Assessment ID", value=f"RAI-{u_subject[:2].upper()}-{u_grade[-1] if u_grade[-1].isdigit() else 'X'}")

        u_outcomes = topic_df[topic_df['Chapter Name'] == u_topic]['Learning Outcomes'].values[0]
        st.markdown(f"<div class='outcome-banner'><b>Target Outcomes:</b> {u_outcomes}</div>", unsafe_allow_html=True)

        if st.button("GENERATE PREMIUM ASSESSMENT"):
            with st.spinner("Engineering high-fidelity psychometric questions..."):
                prompt = f"""
                You are a Lead Psychometrician at EI ASSET.
                Topic: {u_topic} | Grade: {u_grade} | Outcomes: {u_outcomes}.
                Create {u_num} 'Deep Diagnostic' MCQs.
                RULES: 4 options. Every wrong answer MUST be a plausible misconception.
                NO diagrams. Text only. Focus on 'Why' over 'What'.
                Return JSON structure: {{'questions': [{{'id':1, 'q':'', 'options':{{'A':'','B':'','C':'','D':''}}, 'correct':'A', 'mappings':{{'B':'Error X','C':'Error Y','D':'Error Z'}}, 'remedy':''}}]}}
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                metadata = json.loads(response.choices[0].message.content)
                info = {"topic": u_topic, "grade": u_grade, "subject": u_subject, "aid": u_aid, "time": u_time}
                
                # Save to Vault
                st.session_state['vault'][u_aid] = {"meta": metadata, "info": info}
                
                st.success(f"Assessment {u_aid} Generated!")
                
                # 📥 PDF Download
                pdf = create_branded_pdf(metadata, info, u_school)
                st.download_button("📥 Download Branded Question Paper (PDF)", pdf, f"{u_aid}_Paper.pdf")
                
                # 📥 Excel Template
                xl_df = pd.DataFrame(columns=["Student Name"] + [f"Q{i+1}" for i in range(u_num)])
                out = BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    xl_df.to_excel(writer, index=False)
                st.download_button("📥 Download Excel Response Template", out.getvalue(), f"Template_{u_aid}.xlsx")

with t2:
    st.header("Upload Results")
    target_id = st.text_input("Enter Assessment ID (to link mapping)")
    uploaded_file = st.file_uploader("Upload Completed Student Excel", type=["xlsx"])
    if uploaded_file and target_id:
        if target_id in st.session_state['vault']:
            st.session_state[f"res_{target_id}"] = pd.read_excel(uploaded_file)
            st.success(f"Successfully ingested data for {target_id}.")
        else:
            st.error("ID not found in current session.")

with t3:
    st.header("Diagnostic Dashboard")
    active_id = st.selectbox("Select Assessment ID", list(st.session_state['vault'].keys()))
    if active_id and f"res_{active_id}" in st.session_state:
        vault = st.session_state['vault'][active_id]
        results = st.session_state[f"res_{active_id}"]
        
        # Individual Report
        student = st.selectbox("Select Student", results['Student Name'].unique())
        s_row = results[results['Student Name'] == student].iloc[0]
        
        for q in vault['meta']['questions']:
            q_id = q.get('id')
            s_ans = str(s_row[f"Q{q_id}"]).strip().upper()
            
            with st.container():
                if s_ans == q.get('correct'):
                    st.write(f"**Q{q_id}:** ✅ Mastered")
                else:
                    err_map = q.get('mappings') or q.get('engine') or {}
                    err_desc = err_map.get(s_ans, 'Conceptual Error')
                    st.markdown(f"""
                    <div class="report-card">
                        <b>Question {q_id} - At Risk (Selected {s_ans})</b><br>
                        <i>Misconception:</i> {err_desc}<br>
                        <b>📍 Remediation:</b> {q.get('remedy', 'Review foundations.')}
                    </div>
                    """, unsafe_allow_html=True)
