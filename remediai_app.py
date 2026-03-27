import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# --- 1. SETUP ---
st.set_page_config(page_title="RemediAI Ultra", layout="wide")

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("🔑 OpenAI API Key missing!")
    st.stop()

# Persistent Storage
if 'vault' not in st.session_state: st.session_state['vault'] = {}

# --- 2. MULTICOLORED PDF ENGINE ---
def create_premium_pdf(metadata, info, school_name):
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

    y = h - 140
    for idx, q in enumerate(metadata.get('questions', [])):
        if y < 150: p.showPage(); y = h - 50
        p.setFont("Helvetica-Bold", 11)
        p.setFillColor(colors.HexColor("#1e3a8a"))
        p.drawString(50, y, f"{idx+1}.")
        p.setFillColor(colors.black)
        
        q_text = q.get('question') or q.get('q') or ""
        p.drawString(70, y, q_text[:85]) # Basic line wrap
        if len(q_text) > 85:
            y -= 15
            p.drawString(70, y, q_text[85:])
            
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

# --- 3. APP WORKFLOW ---
st.title("🎯 RemediAI Ultra: The EI-Killer")

tab1, tab2, tab3 = st.tabs(["🏗️ 1. Create Assessment", "📤 2. Upload Responses", "📊 3. View Diagnosis"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        u_school = st.text_input("School Name", "Global International School")
        u_topic = st.text_input("Topic", "Animal Adaptation")
        u_grade = st.selectbox("Grade", ["3", "4", "5", "10"])
    with c2:
        u_num = st.number_input("Questions", 1, 15, 5)
        u_diff = st.slider("Diagnostic Depth", 1, 12, 10)
        u_aid = st.text_input("Assessment ID", value="DIAG-01")

    if st.button("🚀 GENERATE DIAGNOSTIC SYSTEM"):
        with st.spinner("Engineering high-fidelity questions..."):
            prompt = f"""
            Act as a Psychometrician for EI ASSET. 
            Create {u_num} 'Deep Diagnostic' MCQs for Grade {u_grade} on '{u_topic}'.
            Difficulty: {u_diff}/12.
            
            RULES:
            1. Every wrong option MUST be a 'Smart Mistake' (Misconception).
            2. NO literal or easy questions.
            3. For every wrong option, explain the 'Logic Gap'.
            
            Return JSON:
            {{ "questions": [ {{ "id": 1, "question": "...", "options": {{"A":"","B":"","C":"","D":""}}, "correct": "A", "mappings": {{"B":"Misconception Description", "C":"Misconception Description", "D":"Logic Error Description"}}, "remedy": "Pedagogical advice." }} ] }}
            """
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            meta = json.loads(response.choices[0].message.content)
            
            # Save mapping to Vault
            st.session_state['vault'][u_aid] = {"meta": meta, "topic": u_topic, "subject": "General"}
            
            # Downloads
            pdf = create_premium_pdf(meta, {"subject": "Diagnostic", "topic": u_topic, "aid": u_aid, "grade": u_grade}, u_school)
            st.download_button("📥 Download Branded Paper (PDF)", pdf, f"{u_aid}.pdf")
            
            xl_df = pd.DataFrame(columns=["Student Name"] + [f"Q{i+1}" for i in range(u_num)])
            out = BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                xl_df.to_excel(writer, index=False)
            st.download_button("📥 Download Excel Template", out.getvalue(), f"Template_{u_aid}.xlsx")

with tab2:
    target_aid = st.text_input("Enter Assessment ID")
    xl_file = st.file_uploader("Upload Student Excel", type=["xlsx"])
    if xl_file and target_aid:
        if target_aid in st.session_state['vault']:
            st.session_state[f"data_{target_aid}"] = pd.read_excel(xl_file)
            st.success("Responses uploaded successfully.")
        else:
            st.error("ID not found. Generate the assessment first.")

with tab3:
    active_id = st.selectbox("Select ID", list(st.session_state['vault'].keys()))
    if active_id and f"data_{active_id}" in st.session_state:
        vault = st.session_state['vault'][active_id]
        results = st.session_state[f"data_{active_id}"]
        
        student = st.selectbox("Select Student", results['Student Name'].unique())
        s_row = results[results['Student Name'] == student].iloc[0]
        
        for q in vault['meta']['questions']:
            q_id = q.get('id')
            s_ans = str(s_row[f"Q{q_id}"]).strip().upper()
            if s_ans != q['correct']:
                st.error(f"**Question {q_id} - Incorrect**")
                st.write(f"Student reveal: **{q['mappings'].get(s_ans, 'Conceptual Error')}**")
                st.info(f"💡 **Remedy:** {q['remedy']}")
            else:
                st.success(f"**Question {q_id} - Mastered**")
