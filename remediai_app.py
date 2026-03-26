import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
import re
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# --- 1. THEME & SETUP ---
st.set_page_config(page_title="RemediAI: Master Suite", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { border-radius: 8px; background-color: #1e40af; color: white; font-weight: bold; width: 100%; height: 3.5em; }
    .report-card { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .remedial-box { background-color: #fff7ed; border-left: 5px solid #f97316; padding: 15px; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing in Secrets!")
    st.stop()

# --- 2. DATABASE & SESSION STATE ---
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

if 'meta_store' not in st.session_state: st.session_state['meta_store'] = {}
if 'history' not in st.session_state: st.session_state['history'] = []

# --- 3. MULTICOLORED PDF ENGINE (FIXED) ---
def generate_branded_pdf(metadata, info, school_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # Header Banner (Deep Blue)
    p.setFillColor(colors.HexColor("#1e40af"))
    p.rect(0, h - 80, w, 80, fill=1, stroke=0)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(w/2, h - 40, school_name.upper())
    p.setFont("Helvetica", 10)
    p.drawCentredString(w/2, h - 65, f"Assessment Topic: {info['topic']}")

    # Info Bar (Light Grey) - FIXED KeyError by using stroke=1
    p.setLineWidth(0.5)
    p.setStrokeColor(colors.lightgrey)
    p.setFillColor(colors.HexColor("#f1f5f9"))
    p.rect(40, h - 115, w - 80, 25, fill=1, stroke=1)
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, h - 108, f"ID: {info['aid']} | Grade: {info['grade']} | Sub: {info['subject']} | Time: {info['time']} Mins")
    
    # Questions
    y = h - 150
    for q in metadata.get('questions', []):
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"Q{q['id']}. {q['q']}")
        y -= 20
        p.setFont("Helvetica", 10)
        for lbl, txt in q.get('options', {}).items():
            p.drawString(70, y, f"{lbl}. {txt}")
            y -= 15
        y -= 25
        if y < 100: p.showPage(); y = h - 50

    p.save()
    buffer.seek(0)
    return buffer

# --- 4. THE WORKFLOW ---
st.title("🎯 RemediAI: Next-Gen Diagnostic Suite")
tab1, tab2 = st.tabs(["🏗️ Phase 1: Assessment Creator", "📊 Phase 2: Diagnostic Reporting"])

with tab1:
    if not db.empty:
        with st.sidebar:
            st.header("🏫 Branding & Configuration")
            u_school = st.text_input("School Name", "Vikas International School")
            u_grade = st.selectbox("Grade", sorted(db['Grade'].unique()))
            u_subject = st.selectbox("Subject", sorted(db[db['Grade'] == u_grade]['Subject'].unique()))
            topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
            u_topic = st.selectbox("Topic", topic_df['Chapter Name'].unique())
            
            u_num = st.number_input("No. of Questions", 1, 15, 5)
            u_time = st.number_input("Time (Mins)", 5, 180, 30)
            u_diff = st.select_slider("Difficulty Level", options=list(range(1, 13)), value=6)
            u_aid = st.text_input("Assessment ID", value=f"DIAG-{u_subject[:3].upper()}-01")
            
            u_outcomes = topic_df[topic_df['Chapter Name'] == u_topic]['Learning Outcomes'].values[0]

        if st.button("🚀 Generate Branded Paper & Template"):
            avoid = ", ".join(st.session_state['history'][-5:])
            with st.spinner("Engineering high-fidelity misconceptions..."):
                prompt = f"""
                Create {u_num} conceptual MCQs for {u_grade} {u_subject} on '{u_topic}'.
                Difficulty: {u_diff}/12. Outcomes: {u_outcomes}. NO diagrams. 
                NO repetition of: {avoid}. Text only.
                Each wrong option must map to a specific conceptual misconception.
                Return JSON only.
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                metadata = json.loads(response.choices[0].message.content)
                info = {"topic": u_topic, "grade": u_grade, "subject": u_subject, "aid": u_aid, "time": u_time, "diff": u_diff}
                
                st.session_state['meta_store'][u_aid] = {"metadata": metadata, "info": info}
                st.session_state['history'].append(u_topic)
                st.success(f"Assessment {u_aid} Ready!")

                # 1. Download Multicolored PDF
                pdf = generate_branded_pdf(metadata, info, u_school)
                st.download_button("📥 Download Branded Paper (PDF)", pdf, f"{u_aid}_Paper.pdf", "application/pdf")
                
                # 2. Download Excel Template
                tpl_df = pd.DataFrame(columns=["Student Name"] + [f"Q{i+1}" for i in range(u_num)])
                out = BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    tpl_df.to_excel(writer, index=False)
                st.download_button("📥 Download Excel Template", out.getvalue(), f"Template_{u_aid}.xlsx")

with tab2:
    st.header("Upload Results & Get Detailed Reports")
    input_aid = st.text_input("Enter Assessment ID (e.g. DIAG-MAT-01)")
    uploaded_file = st.file_uploader("Upload Student Excel", type=["xlsx"])

    if uploaded_file and input_aid:
        if input_aid not in st.session_state['meta_store']:
            st.error("ID not found in current session.")
        else:
            df_res = pd.read_excel(uploaded_file)
            store = st.session_state['meta_store'][input_aid]
            meta = store['metadata']
            
            st.subheader("📊 Class-Wise Summary")
            all_errs = []
            for _, row in df_res.iterrows():
                for q in meta['questions']:
                    ans = str(row[f"Q{q['id']}"]).strip().upper()
                    if ans != q['correct']:
                        all_errs.append(q['mappings'].get(ans, "Logic Gap"))
            
            if all_errs:
                st.bar_chart(pd.Series(all_errs).value_counts())
            
            st.divider()
            
            st.subheader("👤 Individual Report & Remedial Plan")
            student = st.selectbox("Select Student", df_res['Student Name'].unique())
            s_data = df_res[df_res['Student Name'] == student].iloc[0]
            
            for q in meta['questions']:
                s_ans = str(s_data[f"Q{q['id']}"]).strip().upper()
                with st.container():
                    if s_ans == q['correct']:
                        st.markdown(f"**Q{q['id']}:** ✅ Correct")
                    else:
                        err = q['mappings'].get(s_ans, 'Conceptual Error')
                        st.markdown(f"**Q{q['id']}:** ❌ Incorrect (Selected {s_ans})")
                        st.markdown(f"""<div class="remedial-box">
                            <b>Misconception:</b> {err}<br>
                            <b>🛠️ Remedial Action:</b> Focus on foundational logic of {u_topic}.
                        </div>""", unsafe_allow_html=True)
                st.write("")
