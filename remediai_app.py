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
    
    # Header: Branding (Deep Blue)
    p.setFillColor(colors.HexColor("#1e3a8a"))
    p.rect(0, h - 90, w, 90, fill=1, stroke=0)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(w/2, h - 40, school_name.upper())
    p.setFont("Helvetica", 10)
    p.drawCentredString(w/2, h - 60, f"DIAGNOSTIC ASSESSMENT | {info['subject'].upper()}")
    p.drawCentredString(w/2, h - 75, f"ID: {info['aid']} | Topic: {info['topic']}")

    # Content
    y = h - 140
    for idx, q in enumerate(metadata.get('questions', [])):
        if y < 120: p.showPage(); y = h - 50
        p.setFont("Helvetica-Bold", 11)
        p.setFillColor(colors.HexColor("#1e3a8a"))
        p.drawString(50, y, f"{idx+1}.")
        p.setFillColor(colors.black)
        p.drawString(70, y, q.get('question', ''))
        y -= 25
        p.setFont("Helvetica", 10)
        for label in ["A", "B", "C", "D"]:
            p.drawString(85, y, f"{label}) {q['options'].get(label, '')}")
            y -= 18
        y -= 15
    p.save()
    buffer.seek(0)
    return buffer

# --- 3. APP WORKFLOW ---
st.title("🚀 RemediAI Ultra: The EI-Killer")

# Sidebar Setup
with st.sidebar:
    st.header("⚙️ Configuration")
    u_school = st.text_input("School Name", "Global International Academy")
    u_topic = st.text_input("Topic", "A Letter to God")
    u_grade = st.selectbox("Grade", ["9", "10", "11", "12"])
    u_num = st.number_input("Questions", 1, 15, 5)
    u_diff = st.slider("Complexity", 1, 12, 8)
    u_aid = st.text_input("Assessment ID", value="RAI-EN-10")

if st.button("GENERATE PSYCHOMETRIC ASSESSMENT"):
    with st.spinner("Engineering high-fidelity misconceptions..."):
        # CRITICAL: This prompt is what creates the quality
        prompt = f"""
        You are a Psychometrician for EI ASSET. 
        Create {u_num} 'Deep Diagnostic' MCQs for Grade {u_grade} English on '{u_topic}'.
        Difficulty: {u_diff}/12.
        
        RULES:
        1. Target 'Cognitive Gaps' (e.g., misinterpreting irony, tone, or character motivation).
        2. Distractors must be 'Plausible Errors'—choices that seem correct to a student with a specific thinking flaw.
        3. NO literal 'what happened' questions. Focus on 'Why' and 'How'.
        
        Return JSON:
        {{
          "questions": [
            {{
              "id": 1,
              "question": "...",
              "options": {{"A":"","B":"","C":"","D":""}},
              "correct": "A",
              "mappings": {{"B":"Misconception X", "C":"Misconception Y", "D":"Logic Gap Z"}},
              "remedy": "Specific pedagogical fix."
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
        
        # Display & Download
        st.success("High-Fidelity Assessment Generated!")
        pdf = create_premium_pdf(meta, {"subject": "English", "topic": u_topic, "aid": u_aid, "grade": u_grade}, u_school)
        st.download_button("📥 Download Branded Paper", pdf, f"{u_aid}.pdf")
        
        for q in meta['questions']:
            with st.expander(f"Question {q['id']} - Diagnostic Logic"):
                st.write(f"**Q:** {q['question']}")
                st.write(f"**Correct:** {q['correct']}")
                st.write("**Engine Map:**", q['mappings'])
