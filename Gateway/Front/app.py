import streamlit as st

st.set_page_config(page_title="Peel Potato Chat", layout="centered")

st.title("Peel Potato")
st.caption("AI-native assistant for data analysis workflows")

st.markdown(
    """
    <style>
      .stApp {
        background: linear-gradient(180deg, #f7f3e9 0%, #f0ede3 100%);
      }
      .block-container {
        max-width: 820px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Model status")
    st.info("Offline mode: mocked response")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I am Peel Potato. Ask me about your data tasks.",
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_prompt = st.chat_input("Type your message and press Enter")

if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("user"):
        st.markdown(user_prompt)

    mock_reply = "I'm still learning..."
    st.session_state.messages.append({"role": "assistant", "content": mock_reply})

    with st.chat_message("assistant"):
        st.markdown(mock_reply)
