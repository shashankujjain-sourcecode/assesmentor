import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
import re

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="RemediAI: Full Suite", layout="wide")

st.markdown(
    """
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { border-radius: 8px; background-color: #2563eb; color: white; font-weight: 600; width: 100%; }
    .card { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .misconception-box { background-color: #fff7ed; border-left: 5px solid #f97316; padding: 10px; margin-top: 10px; border-radius: 4px; }
    </style>
    """, 
    unsafe_allow_html=True 
)

# OpenAI API Setup
if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing!")
    st.stop()

# --- 2. DATA LOADING ---
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

# --- 3. THE APP INTERFACE ---
st.title("🎯 RemediAI: Creator & Diagnostic Engine")

if not db.empty:
    # --- ZONE 1: THE ASSESSMENT GENERATOR (Sidebar) ---
    with st.sidebar:
        st.header("🏗️ Generator Settings")
        u_grade = st.selectbox("Select Grade", sorted(db['Grade'].unique()))
        sub_list = sorted(db[db['Grade'] == u_grade]['Subject'].unique())
        u_subject = st.selectbox("Select Subject", sub_list)
        topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
        u_topic = st.selectbox("Select Topic", topic_df['Chapter Name'].unique())
        u_outcomes = topic_df[topic_df['Chapter Name'] == u_topic]['Learning Outcomes'].values[0]
        
        if st.button("Generate Assessment"):
            with st.spinner("AI is crafting questions..."):
                prompt = f"Create 3 conceptual MCQs for {u_grade} {u_subject} on {u_topic}. Outcomes: {u_outcomes}. Return JSON only."
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "Output JSON: {'questions': [{'id':1, 'q':'', 'options':{'A':'','B':'','C':'','D':''}, 'correct':'A', 'map':{'B':'Err','C':'Err','D':'Err'}}] }"},
                              {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                st.session_state['current_test'] = json.loads(response.choices[0].message.content)
                st.session_state['topic'] = u_topic

    # --- ZONE 2: ASSESSMENT DISPLAY & SUBMISSION ---
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("📝 Assessment Viewer")
        if 'current_test' in st.session_state:
            st.info(f"**Topic:** {st.session_state['topic']}")
            
            # Form to submit student answers
            with st.form("student_submission"):
                user_answers = {}
                for q in st.session_state['current_test']['questions']:
                    st.markdown(f"**Q{q['id']}. {q['q']}**")
                    for lbl, txt in q['options'].items():
                        st.write(f"{lbl}. {txt}")
                    user_answers[q['id']] = st.radio(f"Select Answer for Q{q['id']}", ["A", "B", "C", "D"], key=f"rad_{q['id']}")
                    st.markdown("---")
                
                submit_test = st.form_submit_button("Submit & Run Misconception Engine")

    # --- ZONE 3: THE MISCONCEPTION ENGINE (Analysis) ---
    with col_right:
        st.subheader("🧠 Misconception Engine")
        if 'current_test' in st.session_state and submit_test:
            st.success("Analysis Complete!")
            
            for q in st.session_state['current_test']['questions']:
                student_ans = user_answers[q['id']]
                is_correct = student_ans == q['correct']
                
                with st.container():
                    st.markdown(f"**Question {q['id']} Analysis**")
                    if is_correct:
                        st.markdown("✅ **Correct!** Student understands the concept.")
                    else:
                        error_type = q['map'].get(student_ans, "Unknown Conceptual Gap")
                        st.markdown(f"❌ **Incorrect (Selected {student_ans})**")
                        st.markdown(f"""<div class="misconception-box">
                            <b>Detected Misconception:</b> {error_type}
                        </div>""", unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.write("Submit the assessment to see the diagnostic analysis.")

else:
    st.error("❌ Master Database not found.")
