import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
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
    .remedial-box { background-color: #fff7ed; border-left: 5px solid #f97316; padding: 15px; border-radius: 8px; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing! Please add it to Streamlit Secrets.")
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

# Persistent Storage
if 'meta_store' not in st.session_state: st.session_state['meta_store'] = {}
if 'history' not in st.session_state: st.session_state['history'] = []

# --- 3. MULTICOLORED PDF ENGINE (CRASH-PROOF) ---
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

    # Info Bar (Light Grey)
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
        # FIX: Safe-checking multiple keys to avoid KeyError
        q_text = q.get('q') or q.get('question') or "Text Missing"
        q_id = q.get('id') or q.get('qno') or "?"
        
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"Q{q_id}. {q_text}")
        y -= 20
        p.setFont("Helvetica", 10)
        opts = q.get('options', {})
        for lbl in ["A", "B", "C", "D"]:
            p.drawString(70, y, f"{lbl}. {opts.get(lbl, '---')}")
            y -= 15
        y -= 25
        if y < 100: p.showPage(); y = h - 50

    p.save()
    buffer.seek(0)
    return buffer

# --- 4. THE WORKFLOW ---
st.title("🎯 RemediAI: Professional Diagnostic Suite")
tab1, tab2 = st.tabs(["🏗️ Phase 1: Creator", "📊 Phase 2: Diagnostic Reporting"])

with tab1:
    if not db.empty:
        with st.sidebar:
            st.header("🏫 Setup")
            u_school = st.text_input("School Name", "Global International School")
            u_grade = st.selectbox("Grade", sorted(db['Grade'].unique()))
            u_subject = st.selectbox("Subject", sorted(db[db['Grade'] == u_grade]['Subject'].unique()))
            topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
            u_topic = st.selectbox("Topic", topic_df['Chapter Name'].unique())
            u_num = st.number_input("Questions", 1, 15, 5)
            u_time = st.number_input("Time (Mins)", 5, 180, 30)
            u_diff = st.slider("Difficulty", 1, 12, 6)
            u_aid = st.text_input("Assessment ID", value=f"DIAG-{u_subject[:3].upper()}-01")
            u_outcomes = topic_df[topic_df['Chapter Name'] == u_topic]['Learning Outcomes'].values[0]

        if st.button("🚀 Generate Branded Paper & Template"):
            avoid = ", ".join(st.session_state['history'][-5:])
            with st.spinner("Engineering high-fidelity misconceptions..."):
                prompt = f"Create {u_num} conceptual MCQs for {u_grade} {u_subject} on '{u_topic}'. Difficulty: {u_diff}/12. Outcomes: {u_outcomes}. NO diagrams. NO repetition of: {avoid}. Return JSON."
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                metadata = json.loads(response.choices[0].message.content)
                info = {"topic": u_topic, "grade": u_grade, "subject": u_subject, "aid": u_aid, "time": u_time}
                
                st.session_state['meta_store'][u_aid] = {"metadata": metadata, "info": info}
                st.session_state['history'].append(u_topic)
                
                # Downloadable Files
                pdf = generate_branded_pdf(metadata, info, u_school)
                st.download_button("📥 Download Branded Paper (PDF)", pdf, f"{u_aid}_Paper.pdf")
                
                tpl_df = pd.DataFrame(columns=["Student Name"] + [f"Q{i+1}" for i in range(u_num)])
                out = BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                    tpl_df.to_excel(writer, index=False)
                st.download_button("📥 Download Excel Template", out.getvalue(), f"Template_{u_aid}.xlsx")

with tab2:
    st.header("Upload Results & Get Detailed Reports")
    input_aid = st.text_input("Enter Assessment ID (from Phase 1)")
    uploaded_file = st.file_uploader("Upload Student Excel", type=["xlsx"])

    if uploaded_file and input_aid:
        if input_aid not in st.session_state['meta_store']:
            st.error("ID not found. Ensure you created it in Phase 1.")
        else:
            df_res = pd.read_excel(uploaded_file)
            store = st.session_state['meta_store'][input_aid]
            meta = store['metadata']
            
            st.subheader("📊 Class Summary")
            all_errs = []
            for _, row in df_res.iterrows():
                for q in meta.get('questions', []):
                    q_id = q.get('id') or q.get('qno')
                    ans = str(row[f"Q{q_id}"]).strip().upper()
                    if ans != q.get('correct'):
                        maps = q.get('mappings') or q.get('engine') or {}
                        all_errs.append(maps.get(ans, "Logic Gap"))
            
            if all_errs:
                st.bar_chart(pd.Series(all_errs).value_counts())
            
            st.divider()
            
            st.subheader("👤 Individual Diagnostic & Remedial Plan")
            student = st.selectbox("Select Student", df_res['Student Name'].unique())
            s_row = df_res[df_res['Student Name'] == student].iloc[0]
            
            for q in meta.get('questions', []):
                q_id = q.get('id') or q.get('qno')
                s_ans = str(s_row[f"Q{q_id}"]).strip().upper()
                with st.container():
                    if s_ans == q.get('correct'):
                        st.markdown(f"**Q{q_id}:** ✅ Correct")
                    else:
                        maps = q.get('mappings') or q.get('engine') or {}
                        err = maps.get(s_ans, 'Conceptual Error')
                        st.markdown(f"**Q{q_id}:** ❌ Incorrect (Selected {s_ans})")
                        st.markdown(f"""<div class="remedial-box">
                            <b>Detected Misconception:</b> {err}<br>
                            <b>🛠️ Remedial Action:</b> Re-teach the foundational logic of {u_topic}.
                        </div>""", unsafe_allow_html=True)
