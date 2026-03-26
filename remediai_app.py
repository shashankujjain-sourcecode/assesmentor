import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import re
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="RemediAI: OpenAI Edition", layout="wide")

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing! Add 'OPENAI_API_KEY' to Streamlit Secrets.")
    st.stop()

# --- 2. GENERATION LOGIC (OPENAI GPT-4o) ---
def generate_questions_openai(grade, subject, outcomes):
    """Generates 5 conceptual questions using OpenAI's JSON mode."""
    prompt = f"""
    You are an expert Indian assessment creator (Ei ASSET level).
    Create exactly 5 high-quality, conceptual MCQ questions for {grade} {subject}.
    Base them strictly on these NCERT Learning Outcomes: {outcomes}

    STRICT RULES:
    1. Test 'Why' and 'How', not rote memory.
    2. Each WRONG option must be a plausible distractor representing a common Indian student misconception.
    3. Return the response as a valid JSON object.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant designed to output JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"} # Forces valid JSON output
    )
    
    return json.loads(response.choices[0].message.content)

# --- 3. INTERFACE ---
st.title("🎯 RemediAI: OpenAI Outcome Engine")
st.caption("Using GPT-4o-mini for precision misconception mapping.")

tab1, tab2 = st.tabs(["🏗️ Create Assessment", "📊 Generate Report"])

with tab1:
    st.header("1. Input NCERT Outcomes")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        u_grade = st.selectbox("Grade", [f"Class {i}" for i in range(1, 13)] + ["Nursery", "LKG", "UKG"])
        u_subject = st.text_input("Subject")
        u_aid = st.text_input("Assessment ID", value="OPEN-OUT-101")
        
    with col2:
        u_outcomes = st.text_area("Paste NCERT Learning Outcomes here", height=200)

    if st.button("Generate Conceptual Test"):
        if u_outcomes and u_subject:
            with st.spinner("OpenAI is analyzing outcomes..."):
                try:
                    metadata = generate_questions_openai(u_grade, u_subject, u_outcomes)
                    st.session_state[f"meta_{u_aid}"] = metadata
                    st.success(f"Assessment {u_aid} successfully created via OpenAI!")
                    st.json(metadata)
                except Exception as e:
                    st.error(f"OpenAI Error: {e}")
        else:
            st.warning("Please provide Subject and Outcomes.")

with tab2:
    st.header("2. Diagnostic Analysis")
    uploaded_file = st.file_uploader("Upload Responses (.xlsx)", type=["xlsx"])
    
    if uploaded_file:
        id_df = pd.read_excel(uploaded_file, header=None, nrows=1)
        excel_aid = str(id_df.iloc[0, 1]).strip()
        
        if f"meta_{excel_aid}" in st.session_state:
            st.success(f"✅ Linked to OpenAI Metadata for {excel_aid}")
            # PDF generation logic would go here
        else:
            st.error(f"❌ ID '{excel_aid}' not found in current session.")
