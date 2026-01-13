import streamlit as st
import google.generativeai as genai
import sqlite3
import json
import os
from dotenv import load_dotenv
import docx
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure Page
st.set_page_config(
    page_title="Meeting AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS to mimic React UI ---
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: white;
        border-right: 1px solid #e5e7eb;
    }
    
    /* Sidebar Nav Buttons */
    div[data-testid="stSidebar"] button {
        background-color: transparent;
        color: #6b7280;
        border: none;
        text-align: left;
        font-weight: 500;
        padding: 0.75rem 1rem;
        transition: all 0.2s;
    }
    div[data-testid="stSidebar"] button:hover {
        background-color: #f1f5f9;
        color: #111827;
    }
    
    /* Primary Button (Blue) */
    div.stButton > button[kind="primary"] {
        background-color: #2563eb;
        color: white;
        border-radius: 12px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #1d4ed8;
        border-color: #1d4ed8;
    }
    
    /* Secondary Button (White) */
    div.stButton > button[kind="secondary"] {
        background-color: white;
        color: #111827;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
    }
    
    /* Cards/Containers */
    div[data-testid="stExpander"], div.stTextArea, div.stTextInput {
        background-color: white;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #111827;
        font-weight: 700;
    }
    
    /* Remove standard Streamlit header decoration */
    header {visibility: hidden;}
    
    /* Custom Avatar Circle */
    .avatar-circle {
        width: 32px;
        height: 32px;
        background-color: #2563eb;
        color: white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 14px;
    }
    
    /* Improve File Uploader UI */
    [data-testid="stFileUploader"] {
        border: 2px dashed #cbd5e1;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        background-color: #f8fafc;
        transition: border-color 0.3s;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #2563eb;
        background-color: #f1f5f9;
    }
    section[data-testid="stFileUploader"] > div > div > button {
        background-color: #2563eb;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def clean_text(text):
    """Removes markdown formatting like **bold** for cleaner plain text display."""
    if not text: return ""
    return text.replace("**", "").replace("__", "").replace("`", "")

# ... (Database functions remain same)

# ... (Inside Generate Content - clean the output)
        # Clean up markdown (existing code)
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        data = json.loads(content.strip())
        
        # Clean the text fields
        data['summary'] = clean_text(data['summary'])
        data['emails'] = [clean_text(email) for email in data['emails']]
        
        return data

# ... (Inside Main Content)

    elif st.session_state.step == 'result':
        st.header("Generation Results")
        
        if st.button("← Start Over"):
            st.session_state.step = 'upload'
            st.session_state.transcript = ""
            st.session_state.generation_result = None
            st.rerun()
            
        result = st.session_state.generation_result
        
        # Stacked Layout (No Columns)
        
        # Summary Section
        st.subheader("Meeting Summary")
        # Use markdown with custom styling for black text instead of st.info
        st.markdown(f"<div style='background-color:white; padding:1.5rem; border-radius:12px; border:1px solid #e5e7eb; color:#111827; line-height:1.6;'>{result['summary']}</div>", unsafe_allow_html=True)
        st.button("📋 Copy Summary", on_click=lambda: st.write("Copied! (Simulated)"))
        
        st.divider()
        
        # Email Section
        st.subheader("Email Drafts")
        tab1, tab2, tab3 = st.tabs(["Formal", "Action-Oriented", "Casual"])
        
        emails = result['emails']
        
import streamlit.components.v1 as components

def copy_to_clipboard(text):
    # JavaScript hack to copy text to clipboard
    components.html(
        f"""
        <script>
        navigator.clipboard.writeText(`{text.replace('`', '\`')}`);
        </script>
        """,
        height=0,
    )

# ... (inside the loop)
        for i, tab in enumerate([tab1, tab2, tab3]):
            with tab:
                if i < len(emails):
                    # Copy Button
                    if st.button("📋 Copy Text", key=f"copy_btn_{i}"):
                        copy_to_clipboard(emails[i])
                        st.toast("Copied to clipboard!")

                    # Capture the edited text from the text area (Label hidden)
                    email_content = st.text_area("Email Draft", value=emails[i], height=300, key=f"email_res_{i}", label_visibility="collapsed")
                    
                    # Extract subject for mailto
                    subject = "Meeting Follow-up"
                    body = email_content
                    
                    # Improved Subject Parsing
                    lines = email_content.split('\n')
                    for idx, line in enumerate(lines):
                        if "Subject:" in line:
                            subject = line.replace("Subject:", "").replace("*", "").strip()
                            body = "\n".join(lines[idx+1:]).strip()
                            break
                            
                    import urllib.parse
                    safe_subject = urllib.parse.quote(subject)
                    safe_body = urllib.parse.quote(body)
                    
                    st.markdown(f"""
                    <div style="display:flex;gap:10px;margin-top:10px;">
                        <a href="https://mail.google.com/mail/?view=cm&fs=1&su={safe_subject}&body={safe_body}" target="_blank" style="text-decoration:none;background-color:#ea4335;color:white;padding:8px 16px;border-radius:5px;font-weight:bold;">Send via Gmail</a>
                        <a href="mailto:?subject={safe_subject}&body={safe_body}" style="text-decoration:none;background-color:#0078d4;color:white;padding:8px 16px;border-radius:5px;font-weight:bold;">Send via Outlook</a>
                    </div>
                    """, unsafe_allow_html=True)
