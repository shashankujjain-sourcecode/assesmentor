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

# Premium UI Styling
st.markdown("""
    <style>
    .main { background-color: #f4f7f9; }
    .stButton>button { 
        border-radius: 8px; background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%); 
        color: white; font-weight: bold; border: none; height: 3.5em; width: 100%;
    }
    .diagnostic-card { 
        background-color: white; padding: 20px; border-radius: 12px; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); border-left: 6px solid #1e3a8a; margin-bottom: 15px;
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
    # Looks for any file with 'Master' in it
    db_file = next((f for f in os.listdir(".") if "Master" in f and (f.endswith(".tsv") or f.endswith(".csv"))), None)
    if db_file:
        sep = ',' if db_file.endswith(".csv") else '\t'
        df = pd.read_csv(db_file, sep=sep)
        df['Learning Outcomes'] = df['Learning Outcomes'].str.replace(r'<[^>]*>', ' ', regex=True)
        return df
    return pd.DataFrame()

db = load_master_db()

# Session persistence
if 'vault' not in st.session_state: st.session_state['vault'] = {}
if 'history' not in st.session_state: st.session_state['history'] = []

# --- 3. PREMIUM PDF GENERATOR (PRINT-READY) ---
def create_premium_pdf(metadata, info, school_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # Header: Branding (Deep Blue Theme)
    p.setFillColor(colors.HexColor("#1e3a8a"))
    p.rect(0, h - 100, w, 100, fill=1, stroke=0)
    
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(w/2, h - 45, school_name.upper())
    p.setFont("Helvetica", 10)
    p.drawCentredString(w/2, h - 65, f"DIAGNOSTIC ASSESSMENT | {info['subject'].upper()}")
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(w/2, h - 85, f"TOPIC: {info['topic']}")

    # Sub-Header: Metadata Bar (Fixed Stroke Error)
    p.setLineWidth(1)
    p.setStrokeColor(colors.lightgrey)
    p.setFillColor(colors.HexColor("#f8fafc"))
    p.rect(40, h - 140, w - 80, 30, fill=1, stroke=1)
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(55, h - 128, f"CLASS: {info['grade']}")
    p.drawCentredString(w/2, h - 128, f"ID: {info['aid']}")
    p.drawRightString(w - 55, h - 128, f"TIME: {info['time']} MINS")

    # Question Body
    y = h - 180
    for idx, q in enumerate(metadata.get('questions', [])):
        if y < 120:
            p.showPage()
            y = h - 50
            
        p.setFont("Helvetica-Bold", 11)
        p.setFillColor(colors.HexColor("#1e3a8a"))
        p.drawString(50, y, f"{idx+1}.")
        
        p.setFillColor(colors.black)
        q_txt = q.get('question') or q.get('q') or "N/A"
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

tab1, tab2, tab3 = st.tabs(["🏗️ 1. CREATE", "📤 2. UPLOAD", "📊 3. DIAGNOSTICS"])

with tab1:
    if not db.empty:
        c1, c2, c3 = st.columns(3)
        with c1:
            u_school = st.text_input("School Name", "Global Academy")
            u_grade = st.selectbox("Grade", sorted(db['Grade'].unique()))
            u_subject = st.selectbox("Subject", sorted(db[db['Grade'] == u_grade]['Subject'].unique()))
        with c2:
            topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
            u_topic = st.selectbox("Topic", topic_df['Chapter Name'].unique())
            u_diff = st.select_slider("Difficulty", options=list(range(1, 13)), value=6)
        with c3:
            u_num = st.number_input("Questions", 1, 15, 5)
            u_time = st.number_input("Time (Mins)", 10, 180, 40)
            u_aid = st.text_input("Assessment ID", value=f"RAI-{u_subject[:2].upper()}-101")

        if st.button("GENERATE PREMIUM ASSESSMENT"):
            outcome = topic_df[topic_df['Chapter Name'] == u_topic]['Learning Outcomes'].values[0]
            with st.spinner("Engineering diagnostic logic..."):
                prompt = f"Create {u_num} conceptual MCQs for {u_grade} {u_subject} on {u_topic}. Outcomes: {outcome}. Return JSON: {{'questions': [{{'id':1, 'q':'', 'options':{{'A':'','B':'','C':'','D':''}}, 'correct':'A', 'misconceptions':{{'B':'Err1','C':'Err2','D':'Err3'}}, 'remedy':''}}]}}"
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                meta = json.loads(response.choices[0].message.content)
                info = {"grade": u_grade, "subject": u_subject, "topic": u_topic, "aid": u_aid, "time": u_time}
                
                st.session_state['vault'][u_aid] = {"meta": meta, "info": info}
                
                # PDF & Excel Generation
                pdf = create_premium_pdf(meta, info, u_school)
                st.download_button("📥 Download Branded PDF", pdf, f"{u_aid}.pdf")
                
                xl_df = pd.DataFrame(columns=["Student Name"] + [f"Q{i+1}" for i in range(u_num)])
                out = BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    xl_df.to_excel(writer, index=False)
                st.download_button("📥 Download Excel Template", out.getvalue(), f"Template_{u_aid}.xlsx")

with tab2:
    target_aid = st.text_input("Enter Assessment ID")
    uploaded_file = st.file_uploader("Upload Student Responses (Excel)", type=["xlsx"])
    if uploaded_file and target_aid:
        if target_aid in st.session_state['vault']:
            st.session_state[f"results_{target_aid}"] = pd.read_excel(uploaded_file)
            st.success("Responses Ingested.")
        else:
            st.error("ID not found in session.")

with tab3:
    active_id = st.selectbox("Select Active Assessment", list(st.session_state['vault'].keys()))
    if active_id and f"results_{active_id}" in st.session_state:
        vault = st.session_state['vault'][active_id]
        results = st.session_state[f"results_{active_id}"]
        
        # Individual Remediation Plan
        student = st.selectbox("Select Student", results['Student Name'].unique())
        s_row = results[results['Student Name'] == student].iloc[0]
        
        for q in vault['meta']['questions']:
            ans = str(s_row[f"Q{q['id']}"]).strip().upper()
            with st.container():
                if ans == q['correct']:
                    st.write(f"**Q{q['id']}:** ✅ Mastered")
                else:
                    err = q['misconceptions'].get(ans, "Logic Gap")
                    st.markdown(f"""
                    <div class="diagnostic-card">
                        <b>Q{q['id']} - At Risk</b><br>
                        <i>Misconception:</i> {err}<br>
                        <b>Remedy:</b> {q.get('remedy', 'Review core logic.')}
                    </div>
                    """, unsafe_allow_html=True)
