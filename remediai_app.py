import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

# --- 1. CORE SETUP ---
st.set_page_config(page_title="RemediAI Ultra", layout="wide")

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("🔑 API Key missing!")
    st.stop()

# --- 2. MULTICOLORED PDF ENGINE ---
def create_premium_pdf(metadata, info, school_name):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    
    # Header: Branding
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
        
        # Safe Wrap for Question Text
        q_text = q.get('question') or q.get('q') or ""
        p.drawString(70, y, q_text[:85])
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

with st.sidebar:
    st.header("⚙️ Settings")
    u_school = st.text_input("School Name", "Global International School")
    u_topic = st.text_input("Topic", "Animal Classification & Adaptations")
    u_grade = st.selectbox("Grade", ["3", "4", "5", "6", "10"])
    u_num = st.number_input("Questions", 1, 15, 5)
    u_diff = st.slider("Diagnostic Depth", 1, 12, 9)
    u_aid = st.text_input("Assessment ID", value="DIAG-SCI-01")

if st.button("🚀 GENERATE PSYCHOMETRIC ASSESSMENT"):
    with st.spinner("Engineering high-fidelity misconceptions..."):
        prompt = f"""
        You are an expert Psychometrician at Educational Initiatives (EI). 
        Create {u_num} 'Deep Diagnostic' MCQs for Grade {u_grade} Science on '{u_topic}'.
        Difficulty: {u_diff}/12.
        
        RULES:
        1. NO literal questions. Use scenarios/hypotheticals.
        2. Distractors must be 'Plausible Concept Gaps' (Smart Mistakes).
        3. NO silly or obviously wrong options.
        4. Focus on 'Why' things happen, not just facts.
        
        Return JSON:
        {{
          "questions": [
            {{
              "id": 1,
              "question": "...",
              "options": {{"A":"","B":"","C":"","D":""}},
              "correct": "A",
              "mappings": {{"B":"Misconception Description", "C":"Misconception Description", "D":"Logic Error Description"}},
              "remedy": "Pedagogical advice for this specific error."
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
        st.session_state['last_meta'] = meta
        
        # Downloads
        st.success("High-Fidelity Assessment Ready!")
        pdf = create_premium_pdf(meta, {"subject": "Science", "topic": u_topic, "aid": u_aid, "grade": u_grade}, u_school)
        st.download_button("📥 Download Branded Paper (PDF)", pdf, f"{u_aid}.pdf")
