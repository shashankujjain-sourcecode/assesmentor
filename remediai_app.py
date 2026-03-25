import streamlit as st

# Load OpenAI Key securely from secrets
if "openai_key" not in st.session_state:
    try:
        st.session_state.openai_key = st.secrets["openai"]["api_key"]
    except:
        st.session_state.openai_key = ""

# Show in sidebar
openai_key = st.sidebar.text_input(
    "OpenAI API Key", 
    value=st.session_state.openai_key, 
    type="password",
    help="Your key is stored securely in secrets.toml"
)

if openai_key:
    st.session_state.openai_key = openai_key
