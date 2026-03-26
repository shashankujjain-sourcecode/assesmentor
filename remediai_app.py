import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
import re

# --- 1. SETTINGS & STYLING ---
st.set_page_config(page_title="RemediAI: Diagnostic Suite", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { border-radius: 8px; background-color: #2563eb; color: white; font-weight: bold; width: 100%; height: 3em; }
    .question-box { background-color: #ffffff; padding: 25px; border-radius: 15px; border: 1px solid #e2e8f0; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .misconception-alert { background-color: #fff7ed; border-left: 6px solid #f97316; padding: 15px; border-radius: 0 10px 10px 0; margin-top: 15px; font-weight: 500; }
    .success-badge { color: #059669; font-weight: bold; background-color: #ecfdf5; padding: 5px 10px; border-radius: 20px; }
    </style>
    """, unsafe_allow_html=True)

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing! Please add it to Streamlit Secrets.")
    st.stop()

# --- 2. DATABASE LOADING & CLEANING ---
@st.cache_data
def load_and_clean_db():
    # Looks for any file with 'Master' in it to avoid naming errors
    db_file = next((f for f in os.listdir(".") if "Master" in f and (f.endswith(".tsv") or f.endswith(".csv"))), None)
    if db_file:
        sep = ',' if db_file.endswith(".csv") else '\t'
        df = pd.read_csv(db_file, sep=sep)
        # Remove <br> tags from the data
        df['Learning Outcomes'] = df['Learning Outcomes'].str.replace(r'<[^>]*>', ' ', regex=True)
        return df
    return pd.DataFrame()

db = load_and_clean_db()

# --- 3. THE PRODUCT WORKFLOW ---
st.title("🎯 RemediAI: Full Assessment & Diagnostic Suite")

if not db.empty:
    # --- STAGE 1: THE CREATOR PANEL ---
    with st.expander("🏗️ STAGE 1: Assessment Generator (Setup)", expanded=True):
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            u_grade = st.selectbox("Select Grade", sorted(db['Grade'].unique()))
        with col_b:
            sub_list = sorted(db[db['Grade'] == u_grade]['Subject'].unique())
            u_subject = st.selectbox("Select Subject", sub_list)
        with col_c:
            topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
            u_topic = st.selectbox("Select Topic/Chapter", topic_df['Chapter Name'].unique())
        
        u_outcomes = topic_df[topic_df['Chapter Name'] == u_topic]['Learning Outcomes'].values[0]
        st.info(f"**Targeting NCERT Outcomes:** {u_outcomes}")
        
        if st.button("✨ Generate Live Assessment"):
            with st.spinner("AI is reverse-engineering misconceptions..."):
                prompt = f"Create 3 conceptual MCQs for {u_grade} {u_subject} on {u_topic}. Outcomes: {u_outcomes}. Return JSON only."
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "Output JSON: {'questions': [{'id':1, 'q':'', 'options':{'A':'','B':'','C':'','D':''}, 'correct':'A', 'mappings':{'B':'Err','C':'Err','D':'Err'}}] }"},
                              {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                st.session_state['active_test'] = json.loads(response.choices[0].message.content)
                st.session_state['current_topic'] = u_topic

    # --- STAGE 2: THE STUDENT INTERFACE ---
    if 'active_test' in st.session_state:
        st.markdown("---")
        st.header(f"📝 Live Test: {st.session_state['current_topic']}")
        
        with st.form("assessment_form"):
            student_choices = {}
            for q in st.session_state['active_test']['questions']:
                st.markdown(f"#### Q{q['id']}. {q['q']}")
                student_choices[q['id']] = st.radio(
                    f"Select Option for Q{q['id']}:",
                    options=["A", "B", "C", "D"],
                    format_func=lambda x: f"{x}: {q['options'][x]}",
                    key=f"q_{q['id']}"
                )
                st.markdown("<br>", unsafe_allow_html=True)
            
            run_engine = st.form_submit_button("Submit & Run Misconception Engine")

        # --- STAGE 3: THE MISCONCEPTION ENGINE ---
        if run_engine:
            st.markdown("---")
            st.header("🧠 Diagnostic Engine Results")
            
            total_correct = 0
            for q in st.session_state['active_test']['questions']:
                user_ans = student_choices[q['id']]
                correct_ans = q['correct']
                
                with st.container():
                    st.write(f"**Question {q['id']} Diagnostic:**")
                    if user_ans == correct_ans:
                        st.markdown(f"<span class='success-badge'>✅ Correct</span> — Student selected {user_ans}. Perfect conceptual alignment.", unsafe_allow_html=True)
                        total_correct += 1
                    else:
                        error_detail = q['mappings'].get(user_ans, "Conceptual Gap Identified")
                        st.markdown(f"❌ **Incorrect (Selected {user_ans})**")
                        st.markdown(f"<div class='misconception-alert'><b>Engine Detection:</b> {error_detail}</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
            
            st.metric("Total Score", f"{total_correct} / {len(st.session_state['active_test']['questions'])}")

else:
    st.error("❌ Database Not Found. Ensure the TSV file is in your GitHub folder.")
