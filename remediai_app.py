import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# --- 1. CORE CONFIGURATION ---
st.set_page_config(page_title="RemediAI Ultra | Professional Diagnostic Suite", layout="wide")

# Custom CSS for a "Premium Product" feel
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .stButton>button { 
        border-radius: 8px; background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); 
        color: white; font-weight: bold; height: 3.5em; width: 100%; border: none;
    }
    .diagnostic-card { 
        background-color: white; padding: 24px; border-radius: 12px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-left: 6px solid #1e3a8a; margin-bottom: 20px;
    }
    .outcome-banner {
        background-color: #eff6ff; padding: 15px; border-radius: 8px; border: 1px solid #bfdbfe; color: #1e40af; font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("🔑 OpenAI API Key missing in Streamlit Secrets.")
    st.stop()

# --- 2. DATABASE ENGINE ---
@st.cache_data
def load_master_db():
    # Scans for the Master Data file
    db_file = next((f for f in os.listdir(".") if "Master" in f and (f.endswith(".tsv") or f.endswith(".csv"))), None)
    if db_file:
        sep = ',' if db_file.endswith(".csv") else '\t'
        df = pd.read_csv(db_file, sep=sep)
        # Clean HTML noise
        df['Learning Outcomes'] = df['Learning Outcomes'].str.replace(r'<[^>]*>', ' ', regex=True)
        return df
    return pd.DataFrame()

db = load_master_db()

# Session persistence for Assessment IDs and Metadata
if 'vault' not in st.session_state: st.session_state['vault'] = {}

# --- 3. MULTICOLORED PDF GENERATOR ---
def create_premium_pdf(metadata, info, school_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # Header: Branding (Deep Blue Theme)
    p.setFillColor(colors.HexColor("#1e3a8a"))
    p.rect(0, h - 90, w, 90, fill=1, stroke=0)
    
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(w/2, h - 40, school_name.upper())
    p.setFont("Helvetica", 10)
    p.drawCentredString(w/2, h - 60, f"DIAGNOSTIC ASSESSMENT | {info['subject'].upper()}")
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(w/2, h - 80, f"ID: {info['aid']}")

    # Metadata Bar (Light Grey)
    p.setLineWidth(1)
    p.setStrokeColor(colors.lightgrey)
    p.setFillColor(colors.HexColor("#f8fafc"))
    p.rect(40, h - 125, w - 80, 25, fill=1, stroke=1)
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(55, h - 118, f"CLASS: {info['grade']}  |  TOPIC: {info['topic'][:40]}...")
    p.drawRightString(w - 55, h - 118, f"TIME: {info['time']} MINS")

    # Question Body
    y = h - 160
    for idx, q in enumerate(metadata.get('questions', [])):
        if y < 120:
            p.showPage()
            y = h - 50
            
        p.setFont("Helvetica-Bold", 11)
        p.setFillColor(colors.HexColor("#1e3a8a"))
        p.drawString(50, y, f"{idx+1}.")
        
        p.setFillColor(colors.black)
        # Safe get to avoid KeyErrors
        q_txt = q.get('question') or q.get('q') or "Missing Text"
        p.drawString(70, y, q_txt)
        y -= 25
        
        p.setFont("Helvetica", 10)
        opts = q.get('options', {})
        for label in ["A", "B", "C", "D"]:
            p.drawString(85, y, f"{label}) {opts.get(label, '')}")
            y -= 18
        y -= 15

    p.save()
    buffer.seek(0)
    return buffer

# --- 4. APP WORKFLOW ---
st.title("🚀 RemediAI Ultra: The EI-Killer")

tab1, tab2, tab3 = st.tabs(["🏗️ 1. GENERATE ASSESSMENT", "📤 2. UPLOAD RESPONSES", "📊 3. DIAGNOSTIC HUB"])

with tab1:
    if not db.empty:
        c1, c2, c3 = st.columns(3)
        with c1:
            u_school = st.text_input("School Name", "Global International Academy")
            u_grade = st.selectbox("Grade", sorted(db['Grade'].unique()))
            u_subject = st.selectbox("Subject", sorted(db[db['Grade'] == u_grade]['Subject'].unique()))
        with c2:
            topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
            u_topic = st.selectbox("Topic", topic_df['Chapter Name'].unique())
            u_diff = st.select_slider("Difficulty (1-12)", options=list(range(1, 13)), value=7)
        with c3:
            u_num = st.number_input("Questions", 1, 15, 5)
            u_time = st.number_input("Time (Mins)", 10, 180, 40)
            u_aid = st.text_input("Assessment ID", value=f"RAI-{u_subject[:2].upper()}-{u_grade[-1] if u_grade[-1].isdigit() else 'X'}")

        u_outcomes = topic_df[topic_df['Chapter Name'] == u_topic]['Learning Outcomes'].values[0]
        st.markdown(f"<div class='outcome-banner'><b>Target Outcomes:</b> {u_outcomes}</div>", unsafe_allow_html=True)

        if st.button("GENERATE PREMIUM DIAGNOSTIC"):
            with st.spinner("Psychometric AI is engineering misconceptions..."):
                # PSYCHOMETRIC PROMPT
                prompt = f"""
                You are a Lead Assessment Scientist at Educational Initiatives (EI). 
                Create {u_num} 'Deep Diagnostic' MCQs for {u_grade} {u_subject} on '{u_topic}'.
                Difficulty: {u_diff}/12. Outcomes: {u_outcomes}.

                STRICT QUALITY RULES:
                1. NO diagrams. Text only.
                2. Every wrong option MUST be a 'Smart Distractor' representing a specific logical thinking error.
                3. Do NOT repeat previous concepts.
                
                Return JSON structure:
                {{
                  "questions": [
                    {{
                      "id": 1, 
                      "question": "...", 
                      "options": {{"A":"","B":"","C":"","D":""}}, 
                      "correct": "A", 
                      "mappings": {{"B":"Misconception Name", "C":"Misconception Name", "D":"Logic Error"}},
                      "remedy": "Specific 1-sentence pedagogical intervention."
                    }}
                  ]
                }}
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                meta = json.loads(response.choices[0].message.content)
                info = {"grade": u_grade, "subject": u_subject, "topic": u_topic, "aid": u_aid, "time": u_time, "outcome": u_outcomes}
                
                st.session_state['vault'][u_aid] = {"meta": meta, "info": info}
                
                # 📥 PDF Download
                pdf = create_premium_pdf(meta, info, u_school)
                st.download_button("📥 Download Branded Question Paper", pdf, f"{u_aid}_Paper.pdf")
                
                # 📥 Excel Template
                xl_df = pd.DataFrame(columns=["Student Name"] + [f"Q{i+1}" for i in range(u_num)])
                out = BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    xl_df.to_excel(writer, index=False)
                st.download_button("📥 Download Response Template", out.getvalue(), f"Template_{u_aid}.xlsx")

with tab2:
    target_id = st.text_input("Enter Assessment ID (to link logic)")
    uploaded_file = st.file_uploader("Upload Completed Student Responses (Excel)", type=["xlsx"])
    if uploaded_file and target_id:
        if target_id in st.session_state['vault']:
            st.session_state[f"res_{target_id}"] = pd.read_excel(uploaded_file)
            st.success("Data ingested for diagnosis.")
        else:
            st.error("ID not found. Did you generate the test in this session?")

with tab3:
    active_id = st.selectbox("Select ID for Analysis", list(st.session_state['vault'].keys()))
    if active_id and f"res_{active_id}" in st.session_state:
        vault = st.session_state['vault'][active_id]
        results = st.session_state[f"res_{active_id}"]
        
        # --- CLASS SUMMARY ---
        st.subheader("📊 Classwide Misconception Ranking")
        all_errs = []
        for _, row in results.iterrows():
            for q in vault['meta']['questions']:
                ans = str(row[f"Q{q['id']}"]).strip().upper()
                if ans != q['correct']:
                    all_errs.append(q['mappings'].get(ans, "Conceptual Gap"))
        
        if all_errs:
            st.bar_chart(pd.Series(all_errs).value_counts())
        
        st.divider()
        
        # --- INDIVIDUAL REMEDIAL PLAN ---
        st.subheader("👤 Individual Learning Diagnosis")
        student = st.selectbox("Select Student", results['Student Name'].unique())
        s_row = results[results['Student Name'] == student].iloc[0]
        
        for q in vault['meta']['questions']:
            s_ans = str(s_row[f"Q{q['id']}"]).strip().upper()
            with st.container():
                if s_ans == q['correct']:
                    st.write(f"**Q{q['id']}:** ✅ Correct (Mastered)")
                else:
                    err_desc = q['mappings'].get(s_ans, 'Logic Error')
                    st.markdown(f"""
                    <div class="diagnostic-card">
                        <b>Question {q['id']} - At Risk (Selected {s_ans})</b><br>
                        <i>Detected Misconception:</i> {err_desc}<br>
                        <b>📍 Remediation:</b> {q.get('remedy', 'Review core logic.')}
                    </div>
                    """, unsafe_allow_html=True)
