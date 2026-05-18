import streamlit as st
from groq import Groq
import time

st.set_page_config(page_title="Jonathan's Groq Monitor", page_icon="📈")
st.title("⚡ Groq Chat + Live Monitor")

# SECURE: Pulls key from deployment environment settings instead of hardcoding
API_KEY = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=API_KEY)

MAX_HISTORY = 10
MAX_OUTPUT_TOKENS = 800

with st.sidebar:
    st.header("📊 Live Traffic Monitor")
    tps_metric = st.empty()
    in_out_metric = st.empty()
    latency_metric = st.empty()
    st.divider()
    st.caption("Model: llama-3.3-70b-versatile")
    
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask something..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    if len(st.session_state.messages) > MAX_HISTORY:
        st.session_state.messages = st.session_state.messages[-MAX_HISTORY:]

    try:
        start_time = time.time()
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=st.session_state.messages,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
        
        end_time = time.time()

        # FIXED LINE
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

        st.session_state.messages.append(
            {"role": "assistant", "content": response}
        )

    except Exception as e:
        st.error(f"Error: {e}")
