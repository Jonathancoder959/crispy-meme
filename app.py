import streamlit as st
from groq import Groq
import time

st.set_page_config(page_title="Jonathan's Groq Monitor", page_icon="📈", layout="wide")
st.title("⚡ Groq Chat + Live Monitor")

# SECURE: Pulls key from deployment environment settings instead of hardcoding
API_KEY = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=API_KEY)

MAX_HISTORY = 10
MAX_OUTPUT_TOKENS = 800
TARGET_MODEL = "openai/gpt-oss-120b"

# Aggressive CSS layout reset to kill standard headers and footers
st.markdown("""
    <style>
    footer {display: none !important;}
    header {display: none !important;}
    .stAppDeployButton {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# STATE MANAGEMENT: Initialize Multiple Chat History
# ----------------------------------------------------
if "chats" not in st.session_state:
    # Key: chat identifier (string), Value: list of message objects
    st.session_state.chats = {
        "Chat 1": []
    }

if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"

# ----------------------------------------------------
# SIDEBAR: Manage Multiple Conversations & Traffic
# ----------------------------------------------------
with st.sidebar:
    st.header("💬 Conversations")
    
    # Action Button: Create a New Chat Thread
    if st.button("➕ New Chat", use_container_width=True):
        new_chat_index = len(st.session_state.chats) + 1
        new_chat_name = f"Chat {new_chat_index}"
        
        # Ensure name uniqueness
        while new_chat_name in st.session_state.chats:
            new_chat_index += 1
            new_chat_name = f"Chat {new_chat_index}"
            
        st.session_state.chats[new_chat_name] = []
        st.session_state.current_chat = new_chat_name
        st.rerun()
        
    st.write("---")
    
    # Render clickable buttons for each active chat thread
    for chat_name in list(st.session_state.chats.keys()):
        # Highlight the currently active chat visually using a label prefix
        is_active = (chat_name == st.session_state.current_chat)
        button_label = f"➡️ {chat_name}" if is_active else f"📄 {chat_name}"
        
        if st.button(button_label, key=f"nav_{chat_name}", use_container_width=True):
            st.session_state.current_chat = chat_name
            st.rerun()

    st.write("---")
    st.header("📊 Live Traffic Monitor")
    tps_metric = st.empty()
    in_out_metric = st.empty()
    latency_metric = st.empty()
    
    st.divider()
    st.caption(f"Model: {TARGET_MODEL}")
    
    # Delete the currently selected conversation channel
    if st.button("🗑️ Delete Current Chat", use_container_width=True):
        active_chat = st.session_state.current_chat
        
        # Remove the target key from history tracking dictionary
        del st.session_state.chats[active_chat]
        
        # If no threads left, provision a fresh one
        if not st.session_state.chats:
            st.session_state.chats["Chat 1"] = []
            st.session_state.current_chat = "Chat 1"
        else:
            # Shift focus onto whatever remaining key is available first
            st.session_state.current_chat = list(st.session_state.chats.keys())[0]
            
        st.rerun()
    
    st.divider()
    st.caption("Created by **Jonathancoder959** 🤖")

# ----------------------------------------------------
# MAIN UI: Render Selected Active Thread History
# ----------------------------------------------------
active_messages = st.session_state.chats[st.session_state.current_chat]

# Paint the existing messages for the open tab onto screen layout container
for message in active_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle incoming runtime chat payloads
if prompt := st.chat_input("Ask something..."):
    st.chat_message("user").markdown(prompt)
    active_messages.append({"role": "user", "content": prompt})
    
    # Prune historical buffer depth boundaries
    if len(active_messages) > MAX_HISTORY:
        active_messages = active_messages[-MAX_HISTORY:]
        st.session_state.chats[st.session_state.current_chat] = active_messages
        
    try:
        start_time = time.time()
        completion = client.chat.completions.create(
            model=TARGET_MODEL,
            messages=active_messages,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        end_time = time.time()
        
        response = completion.choices[0].message.content
        usage = completion.usage
        prompt_tokens = usage.prompt_tokens if usage else 0
        comp_tokens = usage.completion_tokens if usage else 0
        
        groq_time = 0
        if hasattr(completion, 'x_groq') and completion.x_groq:
            groq_time = getattr(completion.x_groq.usage, 'total_time', 0)
            
        final_time = groq_time if groq_time > 0 else (end_time - start_time)
        tps = comp_tokens / final_time if final_time > 0 else 0
        
        tps_metric.metric("Tokens/Sec (TPS)", f"{tps:.2f}")
        in_out_metric.metric("Traffic (In / Out)", f"{prompt_tokens} / {comp_tokens}")
        latency_metric.metric("Latency", f"{final_time:.3f}s")
        
        with st.chat_message("assistant"):
            st.markdown(response)
            
        active_messages.append({"role": "assistant", "content": response})
        st.session_state.chats[st.session_state.current_chat] = active_messages
        
    except Exception as e:
        st.error(f"Error executing token stream generation: {e}")
