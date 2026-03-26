import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
import re

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="RemediAI: Misconception Engine", layout="wide")

st.markdown(
    """
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { border-radius: 8px; background-color: #2563eb; color: white; font-weight: 600; }
    .question-card { 
        background-color: white; padding: 24px; border-radius: 12px; 
        border: 1px solid #e2e8f0; margin-bottom: 20px; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); 
    }
    .outcome-box { 
        background-color: #eff6ff; padding: 15px; border-left: 5px solid #3b82f6; 
        border-radius: 4px; margin-bottom: 25px; font-size: 0.95rem;
    }
    .correct-ans { color: #059669; font-weight: bold; margin-top: 10px; display: block; }
    </style>
    """, 
    unsafe_allow_html=True 
)

if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing in Streamlit Secrets.")
    st.stop()

# --- 2. DATA LOADING (ROBUST SEARCH) ---
@st.cache_data
def load_db():
    # List all files to help user debug if missing
    all_files = os.listdir(".")
    
    # Try finding any .tsv or .csv file with 'Master' in the name
    db_file = None
    for f in all_files:
        if "Master" in f and (f.endswith(".tsv") or f.endswith(".csv")):
            db_file = f
            break
            
    if db_file:
        ext = ',' if db_file.endswith(".csv") else '\t'
        df = pd.read_csv(db_file, sep=ext)
        # CLEAN HTML: Remove <br> and other tags from outcomes [cite: 27, 52]
        df['Learning Outcomes'] = df['Learning Outcomes'].str.replace(r'<[^>]*>', ' ', regex=True)
        return df, all_files
    return pd.DataFrame(), all_files

db, files_found = load_db()

# --- 3. UI LAYOUT ---
st.title("🎯 RemediAI: Misconception Engine")

if not db.empty:
    with st.sidebar:
        st.header("📋 Assessment Setup")
        # Grade, Subject, Topic cascaded selection [cite: 1, 9, 35, 111]
        u_grade = st.selectbox("Select Grade", sorted(db['Grade'].unique()))
        sub_list = sorted(db[db['Grade'] == u_grade]['Subject'].unique())
        u_subject = st.selectbox("Select Subject", sub_list)
        
        topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
        u_topic = st.selectbox("Select Topic", topic_df['Chapter Name'].unique())
        
        u_num_q = st.slider("Number of Questions", 1, 10, 5)
        
        # Get outcomes based on selection [cite: 125, 127, 133]
        u_outcomes = topic_df[topic_df['Chapter Name'] == u_topic]['Learning Outcomes'].values[0]

    # Display Outcomes Cleanly [cite: 158, 201]
    st.markdown(f"<div class='outcome-box'><b>NCERT Learning Outcomes:</b><br>{u_outcomes}</div>", unsafe_allow_html=True)
    
    if st.button("✨ Generate Misconception-Mapped Assessment"):
        with st.spinner("AI is analyzing outcomes and distractors..."):
            try:
                # Prompt OpenAI for deep diagnostic assessment [cite: 148, 216]
                prompt = f"""
                Create {u_num_q} high-fidelity conceptual MCQ questions for {u_grade} {u_subject} on {u_topic}. 
                Outcomes: {u_outcomes}.
                
                For every question, ensure:
                - The correct answer is conceptually solid.
                - Distractors (wrong options) represent specific common student misconceptions.
                
                Return JSON only:
                {{
                  "questions": [
                    {{
                      "qno": 1,
                      "question": "...",
                      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
                      "correct": "A",
                      "mappings": {{"B": "Misconception Name", "C": "Misconception Name", "D": "Logic Error"}}
                    }}
                  ]
                }}
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "You are a pedagogy expert. Output ONLY JSON."},
                              {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                st.session_state['test'] = json.loads(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Error: {e}")

    # Visualization of the Engine Output
    if 'test' in st.session_state:
        st.subheader("Assessment Preview")
        for q in st.session_state['test'].get('questions', []):
            with st.container():
                st.markdown(f"""
                <div class="question-card">
                    <b>Question {q.get('qno')}:</b> {q.get('question')}<br><br>
                    <div><b>A.</b> {q.get('options', {}).get('A')}</div>
                    <div><b>B.</b> {q.get('options', {}).get('B')}</div>
                    <div><b>C.</b> {q.get('options', {}).get('C')}</div>
                    <div><b>D.</b> {q.get('options', {}).get('D')}</div>
                    <span class="correct-ans">✔ Correct Answer: {q.get('correct')}</span>
                    <hr>
                    <small><b>Misconception Mapping:</b><br>
                    {", ".join([f"Option {k}: {v}" for k,v in q.get('mappings', {}).items()])}</small>
                </div>
                """, unsafe_allow_html=True)
else:
    # Diagnostic Screen 
    st.error("❌ Master Database file missing.")
    st.write("Files found in your GitHub repo:")
    st.code(files_found)
    st.info("Ensure you have a .tsv or .csv file with 'Master' in the filename.")
