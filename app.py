import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
import os
from dotenv import load_dotenv

# --- Phase 1: Setup & Data ---
st.set_page_config(page_title="Dallas 311 Insight", layout="wide")
load_dotenv()

# API Setup
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.error("Missing OPENAI_API_KEY in .env file.")
    st.stop()

# Clean up API key (remove quotes or whitespace if present)
api_key = api_key.strip().strip('"').strip("'")

client = OpenAI(api_key=api_key)

# Helper to load data
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("311_Lite.csv")
        df['Created Date'] = pd.to_datetime(df['Created Date'])
        return df
    except FileNotFoundError:
        st.error("311_Lite.csv not found. Please run prepare_data.py first.")
        return pd.DataFrame()

if 'df' not in st.session_state:
    st.session_state['df'] = load_data()

df = st.session_state['df']

# --- Phase 2: State Management ---
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

if 'agent_state' not in st.session_state:
    st.session_state['agent_state'] = "INTERVIEW"

if 'user_intent' not in st.session_state:
    st.session_state['user_intent'] = ""

if 'analysis_history' not in st.session_state:
    st.session_state['analysis_history'] = []

# --- Phase 3: Agent A (The Interviewer) ---
def run_interviewer_agent(user_input):
    # Add user message to history
    st.session_state['chat_history'].append({"role": "user", "content": user_input})
    
    # Construct prompt
    system_prompt = f"""You are a requirements analyst for Dallas 311 data.
You have access to these columns: {list(df.columns)}.
Your goal is to clarify the user's request. Ask specific questions about time ranges, specific request types, or visualization preferences.
If the request is vague (e.g., 'show me bad data'), ask for a definition.
Termination Condition: When you have all necessary details, output a SINGLE line starting with '###READY###' followed by a detailed summary of the request.
"""
    
    messages = [{"role": "system", "content": system_prompt}] + st.session_state['chat_history']
    
    try:
        with st.spinner("Agent A is thinking..."):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7 # A bit of creativity for conversation
            )
        reply = response.choices[0].message.content
        
        if "###READY###" in reply:
            # Extract summary
            parts = reply.split("###READY###")
            # Usually the summary is the part after the marker.
            # Sometimes the model might output text before the marker too, but we care about the summary.
            summary = parts[1].strip()
            
            st.session_state['user_intent'] = summary
            st.session_state['agent_state'] = "EXECUTING"
            st.rerun()
        else:
            st.session_state['chat_history'].append({"role": "assistant", "content": reply})
            # Force a rerun to update the chat display if we aren't using st.chat_message locally
            # But better: return the reply and handle display in the loop
            return reply
            
    except Exception as e:
        st.error(f"Error communicating with Agent A: {e}")
        return None

# --- Phase 4: Agent B (The Executor) ---
def run_coder_agent(user_intent):
    system_prompt = f"""You are a Python Data Scientist. You have a pandas dataframe `df` loaded.
User Intent: {user_intent}
Write a Python script to analyze `df` and visualize the results.
Return ONLY valid Python code wrapped in ```python blocks.
Assign the final figure (if any) to variable `fig` and data tables to `result_df`.

AVAILABLE LIBRARIES:
You may ONLY use the following libraries:
- pandas (aliased as pd)
- plotly.express (aliased as px)
- plotly.graph_objects (aliased as go)
- streamlit (aliased as st) - though usually not needed for logic, only display.
Do NOT import or use any other libraries (like matplotlib, seaborn, folium, etc) as they are not installed.

Ensure columns used exist in the dataframe.
Columns available: {list(df.columns)}

IMPORTANT: If the user asks for a map and you only have 'Lat_Long Location', you MUST split this column into 'Latitude' and 'Longitude' numeric columns before plotting. 
Use this pattern:
# Split by comma, handling potential spaces
lat_long = df['Lat_Long Location'].astype(str).str.strip('()').str.split(',', expand=True)
if len(lat_long.columns) == 2:
    df['Latitude'] = lat_long[0].astype(float)
    df['Longitude'] = lat_long[1].astype(float)
"""
    
    # We can pass column info again to be safe
    # system_prompt += f"Columns: {list(df.columns)}"

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt}
            ],
            temperature=0
        )
        code_response = response.choices[0].message.content
        
        # Extract code block
        if "```python" in code_response:
            code = code_response.split("```python")[1].split("```")[0].strip()
        elif "```" in code_response: # Fallback
            code = code_response.split("```")[1].strip()
        else:
            code = code_response # Assume full text is code if no blocks (risky but possible)
            
        return code
    except Exception as e:
        st.error(f"Error communicating with Agent B: {e}")
        return None

# --- Phase 5: UI Layout ---

# --- Phase 5: UI Layout ---

# --- Phase 5: UI Layout ---

# SIDEBAR: Context & History Log
with st.sidebar:
    st.title("Dallas 311 Insight")
    if not df.empty:
        min_date = df['Created Date'].min().date()
        max_date = df['Created Date'].max().date()
        st.info(f"Data Range: {min_date} to {max_date}")

    st.markdown("---")
    st.subheader("History Log")
    
    # Read-only history view
    history_container = st.container(height=400)
    with history_container:
        for msg in st.session_state['chat_history']:
            # Simplified view for history
            st.caption(f"**{msg['role'].title()}:** {msg['content'][:100]}..." if len(msg['content']) > 100 else f"**{msg['role'].title()}:** {msg['content']}")

    st.markdown("---")
    if st.button("Reset Conversation"):
        st.session_state['chat_history'] = []
        st.session_state['agent_state'] = "INTERVIEW"
        st.session_state['user_intent'] = ""
        st.session_state['analysis_history'] = []
        st.rerun()

# MAIN AREA: Two Columns [Left: Live Chat, Right: Results Feed]
col_left, col_results = st.columns([0.6, 0.4])

with col_left:
    st.subheader("Analyst Chat")
    
    # Live Chat Interface
    # We display the full chat history here as the "Live" conversation
    chat_container = st.container(height=600)
    with chat_container:
        for msg in st.session_state['chat_history']:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        # Show status inside the chat flow if executing
        if st.session_state['agent_state'] == "EXECUTING":
            with st.status("Agent B is analyzing...", expanded=True) as status:
                st.write(f"**Intent:** {st.session_state['user_intent']}")
                st.write("Generating code...")
                
                code = run_coder_agent(st.session_state['user_intent'])
                
                if code:
                    st.write("Executing analysis...")
                    local_scope = {"df": df, "pd": pd, "px": px, "go": go}
                    
                    try:
                        exec(code, {}, local_scope)
                        status.update(label="Analysis Complete!", state="complete", expanded=False)
                        
                        # Capture Results
                        new_result = {
                            "intent": st.session_state['user_intent'],
                            "code": code,
                            "fig": local_scope.get('fig'),
                            "result_df": local_scope.get('result_df'),
                            "timestamp": pd.Timestamp.now()
                        }
                        
                        st.session_state['analysis_history'].append(new_result)
                        
                        # Reset state
                        st.session_state['agent_state'] = "INTERVIEW"
                        st.session_state['user_intent'] = ""
                        st.rerun()
                        
                    except Exception as e:
                        status.update(label="Execution Failed", state="error")
                        st.error(f"Error: {e}")
                        st.code(code, language='python')
                else:
                    status.update(label="Code Generation Failed", state="error")

    # Chat Input associated with the left column
    if prompt := st.chat_input("Ask about 311 data..."):
        reply = run_interviewer_agent(prompt)
        if reply:
             st.rerun()

# RIGHT COLUMN: Results Feed
with col_results:
    st.subheader("Analysis Feed")
    
    if not st.session_state['analysis_history']:
        st.info("No analysis generated yet.")
    
    # Display in reverse order (newest top) or append (oldest top)?
    # User said: "Append new outputs... scroll and see all". 
    # Usually lists append downward. So we iterate normally.
    
    for i, result in enumerate(st.session_state['analysis_history']):
        with st.expander(f"#{i+1}: {result['intent'][:50]}...", expanded=(i == len(st.session_state['analysis_history']) - 1)):
            st.write(f"**Query:** {result['intent']}")
            
            fig = result.get('fig')
            # Check if fig is a valid plotly object or dict-like (not None) before plotting
            if fig is not None:
                try:
                    # Handle multiple figures returned as list/tuple
                    if isinstance(fig, (list, tuple)):
                        for f in fig:
                             st.plotly_chart(f, use_container_width=True)
                    else:
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error displaying chart: {e}")
            
            result_df = result.get('result_df')
            if result_df is not None:
                if isinstance(result_df, pd.DataFrame):
                    if not result_df.empty:
                        st.dataframe(result_df)
                elif isinstance(result_df, (list, tuple)):
                    for item in result_df:
                        if isinstance(item, pd.DataFrame) and not item.empty:
                             st.dataframe(item)
                        else:
                            st.write(item)
                else:
                    st.write(result_df)
            
            with st.popover("Show Code"):
                st.code(result['code'], language="python")
