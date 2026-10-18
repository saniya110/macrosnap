import streamlit as st
from google import genai
from google.genai import types
from prompts import SUMMARY_REQUEST_PROMPT, SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE

MODEL_NAME = "gemini-3.5-flash" 
st.set_page_config(page_title="MacroSnap", page_icon="🥗")

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)

gemini_client = get_gemini_client()


def render_message(message):
    with st.chat_message(message["role"]):
        if message["kind"] == "text":
            st.write(message["content"])
        elif message["kind"] == "image":
            st.image(message["content"])

def add_message(role, kind, content):
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})
    render_message(st.session_state.messages[-1])

def ask_gemini(parts):
    try:
        return st.session_state.chat.send_message(parts).text
    except Exception as error:
        return f"Sorry, something went wrong: {error}"


if "onboarded" not in st.session_state:
    st.title("🥗 MacroSnap")
    st.caption("Snap it. Track it. View your summary instantly.")
    with st.form("onboarding_form"):
        name = st.text_input("Your name")
        submitted = st.form_submit_button("Let's go 🚀")

        if submitted:
            if not name.strip():
                st.warning("Please fill in your name.")
            else:
                st.session_state.name = name.strip()
                st.session_state.chat = gemini_client.chats.create(
                    model=MODEL_NAME,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                )
                st.session_state.messages = []
                st.session_state.onboarded = True
                st.rerun()
    st.stop()


header_col, button_col = st.columns([5, 2], vertical_alignment="center")
with header_col:
    st.title("🥗 MacroSnap")
with button_col:
    send_disabled = len(st.session_state.messages) <= 2
    # Switched logic away from mailing servers to a safe local state viewer anchor variable
    if st.button("📋 Generate Summary", disabled=send_disabled, use_container_width=True):
        st.session_state.show_summary = True

st.caption(f"Logged in as {st.session_state.name}")

if "show_summary" in st.session_state and st.session_state.show_summary:
    with st.spinner("Compiling your daily summary..."):
        daily_summary = ask_gemini([SUMMARY_REQUEST_PROMPT])
    
    st.success("Daily digest sheet generated successfully! Copy text details below:")
    st.text_area("Your MacroSnap Summary Output", value=daily_summary, height=250)
    if st.button("Close Summary Panel"):
        st.session_state.show_summary = False
        st.rerun()

if not st.session_state.messages:
    add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_message(message)


user_input = st.chat_input(
    "Ask a question, or attach a photo of your meal",
    accept_file=True,
    file_type=["jpg", "jpeg", "png"],
)

if user_input:
    photo = user_input.files if user_input.files else None
    text = user_input.text
    parts = []
    
    if photo is not None and len(photo) > 0:
        first_photo = photo[0]
        photo_bytes = first_photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=first_photo.type))
        
    if text:
        add_message("user", "text", text)
        parts.append(text)
    elif photo is not None and len(photo) > 0:
        parts.append("What is this meal? Give me the calories and macros.")
        
    with st.spinner("Crunching the numbers..."):
        answer = ask_gemini(parts)
        add_message("assistant", "text", answer)