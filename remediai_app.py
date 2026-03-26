import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
import re

# --- 1. PAGE CONFIG & THEME ---
st.set_page_config(page_title="RemediAI: Misconception Engine", layout="wide")

st.markdown(
    """
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { border-radius: 8px; background-color: #2563eb; color: white; font-weight: 600; height: 3em; }
    .engine-container { 
        background-color: #ffffff; padding: 30px; border-radius: 15px; 
        border: 1px solid #e2e8f0; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); 
    }
    .misconception-card {
        background-color: #fff7ed; border-left: 5px solid #f97316;
        padding: 15px; margin-top: 10px; border-radius: 0 8px 8px 0;
    }
    .question-text { font-size: 1.2rem; font-weight: 700; color: #1e293b; }
    </style>
    """, 
    unsafe_allow_html=True 
)

# --- 2. API & DATA INITIALIZATION ---
if "OPENAI_API_KEY" in st.secrets:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
else:
    st.error("❌ OpenAI API Key Missing! Add 'OPENAI_API_KEY' to Streamlit Secrets.")
    st.stop()

@st.cache_data
def load_vetted_database():
    """Scans for the Master Database and cleans HTML noise."""
    db_file = next((f for f in os.listdir(".") if "Master" in f and (f.endswith(".tsv") or f.endswith(".csv"))), None)
    
    if db_file:
        sep = ',' if db_file.endswith(".csv") else '\t'
        df = pd.read_csv(db_file, sep=sep)
        # Regex to strip <br> and other HTML tags [cite: 27, 55, 111]
        df['Learning Outcomes'] = df['Learning Outcomes'].str.replace(r'<[^>]*>', ' ', regex=True)
        return df
    return pd.DataFrame()

db = load_vetted_database()

# --- 3. THE INTERFACE ---
st.title("🎯 RemediAI: The Misconception Engine")

if not db.empty:
    # SIDEBAR: SETUP & FILTERS
    with st.sidebar:
        st.header("🛠️ Engine Controls")
        
        # Cascading Selection based on your Master Data 
        u_grade = st.selectbox("1. Grade", sorted(db['Grade'].unique()))
        sub_list = sorted(db[db['Grade'] == u_grade]['Subject'].unique())
        u_subject = st.selectbox("2. Subject", sub_list)
        
        topic_df = db[(db['Grade'] == u_grade) & (db['Subject'] == u_subject)]
        u_topic = st.selectbox("3. Topic/Chapter", topic_df['Chapter Name'].unique())
        
        u_num_q = st.slider("4. Number of Diagnostic Questions", 1, 10, 5)
        
        # Fetch the clean outcome
        u_outcomes = topic_df[topic_df['Chapter Name'] == u_topic]['Learning Outcomes'].values[0]
        
        generate_btn = st.button("🚀 Run Misconception Engine")

    # MAIN AREA: ENGINE OUTPUT
    if generate_btn:
        with st.spinner("AI is reverse-engineering student logic..."):
            try:
                prompt = f"""
                You are a senior pedagogical expert at Ei ASSET. 
                Generate {u_num_q} conceptual MCQs for {u_grade} {u_subject} on {u_topic}.
                Learning Outcomes: {u_outcomes}.

                DIAGNOSTIC REQUIREMENT:
                For every question, map each incorrect option to a specific student misconception 
                prevalent in the Indian education context.

                RETURN JSON ONLY:
                {{
                  "engine_output": [
                    {{
                      "q_id": 1,
                      "question": "...",
                      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
                      "correct_option": "A",
                      "misconception_map": {{
                        "B": "Specific Misconception Name",
                        "C": "Specific Misconception Name",
                        "D": "Specific Misconception Name"
                      }}
                    }}
                  ]
                }}
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "You are a diagnostic assessment engine. Output valid JSON."},
                              {"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                st.session_state['engine_results'] = json.loads(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Engine Error: {e}")

    # DISPLAY THE RESULTS IN A DEDICATED SPACE
    if 'engine_results' in st.session_state:
        st.subheader(f"Diagnostic Map: {u_topic}")
        st.info(f"**Target Outcomes:** {u_outcomes}") [cite: 27, 113, 138]

        for q in st.session_state['engine_results'].get('engine_output', []):
            with st.container():
                st.markdown(f"""
                <div class="engine-container">
                    <div class="question-text">Q{q['q_id']}. {q['question']}</div>
                    <hr>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                        <div style="padding: 10px; border: 1px solid #e2e8f0;">A: {q['options']['A']}</div>
                        <div style="padding: 10px; border: 1px solid #e2e8f0;">B: {q['options']['B']}</div>
                        <div style="padding: 10px; border: 1px solid #e2e8f0;">C: {q['options']['C']}</div>
                        <div style="padding: 10px; border: 1px solid #e2e8f0;">D: {q['options']['D']}</div>
                    </div>
                    <p style="margin-top:15px; color: #059669; font-weight: bold;">✔ Correct Answer: {q['correct_option']}</p>
                    
                    <div class="misconception-card">
                        <strong>🧠 Misconception Mapping (The Engine):</strong><br>
                        • Option {list(q['misconception_map'].keys())[0]}: {list(q['misconception_map'].values())[0]}<br>
                        • Option {list(q['misconception_map'].keys())[1]}: {list(q['misconception_map'].values())[1]}<br>
                        • Option {list(q['misconception_map'].keys())[2]}: {list(q['misconception_map'].values())[2]}
                    </div>
                </div>
                <br>
                """, unsafe_allow_html=True)
else:
    st.error("❌ Database Not Found.")
    st.write("Ensure your .tsv file is in your GitHub root folder.")
