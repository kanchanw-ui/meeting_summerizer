import streamlit as st
import google.generativeai as genai
import sqlite3
import json
import os
from dotenv import load_dotenv
import docx
from datetime import datetime
import streamlit.components.v1 as components
import urllib.parse

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

def read_file(uploaded_file):
    if uploaded_file.name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([para.text for para in doc.paragraphs])
    return ""

def format_date(date_str):
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%B %d, %Y at %I:%M %p')
    except:
        return date_str

# --- Database Functions ---
def init_db():
    conn = sqlite3.connect('meetings.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS meetings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT,
                  transcript TEXT,
                  summary TEXT,
                  emails TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_meeting(filename, transcript, summary, emails):
    try:
        conn = sqlite3.connect('meetings.db')
        c = conn.cursor()
        c.execute("INSERT INTO meetings (filename, transcript, summary, emails) VALUES (?, ?, ?, ?)",
                  (filename, transcript, summary, json.dumps(emails)))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Database Error: {e}")

def get_history():
    conn = sqlite3.connect('meetings.db')
    c = conn.cursor()
    c.execute("SELECT id, filename, transcript, summary, emails, timestamp FROM meetings ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        try:
            email_list = json.loads(row[4])
        except:
            email_list = []
        history.append({
            "id": row[0],
            "filename": row[1],
            "transcript": row[2],
            "summary": row[3],
            "emails": email_list,
            "timestamp": row[5]
        })
    return history

# Initialize DB on start
init_db()

# --- AI Generation Function ---
def generate_content(transcript, api_key):
    if not api_key:
        st.error("API Key not found. Please check your .env file.")
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash-latest')
    
    prompt = f"""
    You are an expert meeting assistant. Analyze the following meeting transcript and provide:
    1. A summary of the meeting (100-150 words).
    2. Three distinct follow-up email drafts:
       - Option 1: Formal and detailed.
       - Option 2: Concise and action-oriented.
       - Option 3: Friendly and casual.
    
    Return the output strictly in VALID JSON format with the following structure. Do not include any markdown formatting like ```json ... ```, just the raw JSON string:
    {{
        "summary": "...",
        "emails": ["Email 1 content...", "Email 2 content...", "Email 3 content..."]
    }}
    
    Transcript:
    {transcript[:10000]} 
    """
    
    try:
        response = model.generate_content(prompt)
        content = response.text
        
        # Clean up markdown
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
    except Exception as e:
        st.error(f"Error generating content: {e}")
        return None

# --- Session State Management ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'view' not in st.session_state:
    st.session_state.view = 'home'
if 'step' not in st.session_state:
    st.session_state.step = 'upload'
if 'transcript' not in st.session_state:
    st.session_state.transcript = ""
if 'filename' not in st.session_state:
    st.session_state.filename = ""
if 'generation_result' not in st.session_state:
    st.session_state.generation_result = None

# --- Login Screen ---
if not st.session_state.user:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🎙️ AI Meeting Summarizer")
        st.markdown("### Welcome Back")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if username == "admin" and password:
                    st.session_state.user = username
                    st.rerun()
                else:
                    st.error("Invalid credentials. Username must be 'admin'.")
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.markdown("<h1 style='color:#2563eb; font-size:1.25rem; margin-bottom:2rem;'>Meeting AI</h1>", unsafe_allow_html=True)
    
    if st.button("➕ New Meeting", use_container_width=True):
        st.session_state.view = 'home'
        st.session_state.step = 'upload'
        st.session_state.transcript = ""
        st.session_state.generation_result = None
        st.rerun()
        
    if st.button("📜 History", use_container_width=True):
        st.session_state.view = 'history'
        st.rerun()
    
    st.divider()
    
    col_av, col_user = st.columns([1, 4])
    with col_av:
        st.markdown(f"<div style='background-color:#2563eb;color:white;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;'>{st.session_state.user[0].upper()}</div>", unsafe_allow_html=True)
    with col_user:
        st.write(f"**{st.session_state.user}**")
        
    if st.button("Logout", type="primary", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# --- Main Content ---
if st.session_state.view == 'history':
    st.header("Meeting History")
    history = get_history()
    
    if not history:
        st.info("No meeting history found.")
    
    for item in history:
        with st.expander(f"{item['filename']} - {format_date(item['timestamp'])}"):
            st.markdown("### Summary")
            st.write(item['summary'])
            
            st.markdown("### Emails")
            tabs = st.tabs(["Formal", "Action-Oriented", "Casual"])
            for i, tab in enumerate(tabs):
                if i < len(item['emails']):
                    with tab:
                        st.text_area(f"Email {i+1}", item['emails'][i], height=200, key=f"hist_email_{item['id']}_{i}")

elif st.session_state.view == 'home':
    if st.session_state.step == 'upload':
        st.header("Upload Transcript")
        st.markdown("Supported formats: .txt, .docx")
        
        uploaded_file = st.file_uploader("Choose a file", type=['txt', 'docx'])
        
        if uploaded_file:
            st.session_state.filename = uploaded_file.name
            st.session_state.transcript = read_file(uploaded_file)
            st.session_state.step = 'transcript'
            st.rerun()

    elif st.session_state.step == 'transcript':
        st.header("Review Transcript")
        
        col_back, col_gen = st.columns([1, 5])
        with col_back:
            if st.button("← Back"):
                st.session_state.step = 'upload'
                st.rerun()
        
        # Show file info instead of the big text editor
        st.success(f"✅ Ready to process: **{st.session_state.filename}**")
        
        # Collapsible view of the transcript
        with st.expander("👁️ View Transcript Content"):
            st.markdown(f"""
            <div style='background-color:white; padding:1rem; border-radius:8px; border:1px solid #e5e7eb; max-height:300px; overflow-y:auto; white-space: pre-wrap; font-family: monospace; font-size: 0.9rem; color: #374151;'>
            {st.session_state.transcript}
            </div>
            """, unsafe_allow_html=True)
        
        st.write("") # Spacer
        
        if st.button("Generate Summary & Emails", type="primary"):
            with st.spinner("Generating content with Gemini AI..."):
                api_key = os.getenv("GEMINI_API_KEY")
                result = generate_content(st.session_state.transcript, api_key)
                
                if result:
                    st.session_state.generation_result = result
                    save_meeting(
                        st.session_state.filename,
                        st.session_state.transcript,
                        result['summary'],
                        result['emails']
                    )
                    st.session_state.step = 'result'
                    st.rerun()

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
        
        if st.button("📋 Copy Summary"):
            copy_to_clipboard(result['summary'])
            st.toast("Summary copied!")
        
        st.divider()
        
        # Email Section
        st.subheader("Email Drafts")
        tab1, tab2, tab3 = st.tabs(["Formal", "Action-Oriented", "Casual"])
        
        emails = result['emails']
        
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
                            
                    safe_subject = urllib.parse.quote(subject)
                    safe_body = urllib.parse.quote(body)
                    
                    st.markdown(f"""
                    <div style="display:flex;gap:10px;margin-top:10px;">
                        <a href="https://mail.google.com/mail/?view=cm&fs=1&su={safe_subject}&body={safe_body}" target="_blank" style="text-decoration:none;background-color:#ea4335;color:white;padding:8px 16px;border-radius:5px;font-weight:bold;">Send via Gmail</a>
                        <a href="mailto:?subject={safe_subject}&body={safe_body}" style="text-decoration:none;background-color:#0078d4;color:white;padding:8px 16px;border-radius:5px;font-weight:bold;">Send via Outlook</a>
                    </div>
                    """, unsafe_allow_html=True)
