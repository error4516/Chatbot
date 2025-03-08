import streamlit as st
import requests
import json
import hashlib

# 🔹 Backend URL
backend_url = "http://127.0.0.1:8000"

# 🔐 Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 🔹 Load users from file
def load_users():
    try:
        with open("users.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# 🔹 Save users to file
def save_users(users):
    with open("users.json", "w") as file:
        json.dump(users, file, indent=4)

# ✅ Initialize session state for authentication
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "chat_sessions" not in st.session_state:
    st.session_state["chat_sessions"] = {}
if "user_store" not in st.session_state:
    st.session_state["user_store"] = load_users()  # Load stored users

# ✅ Set up Streamlit Page Config
st.set_page_config(page_title="Chatbot with Document Search", layout="wide")
st.title("📄 AI Chatbot with Document Search")

# ✅ Sidebar: Authentication
st.sidebar.header("🔑 User Authentication")
if not st.session_state["logged_in"]:
    auth_choice = st.sidebar.radio("Login or Sign Up", ["Login", "Sign Up"])
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    hashed_password = hash_password(password)

    if auth_choice == "Sign Up":
        if st.sidebar.button("📝 Sign Up"):
            if username and password:
                if username in st.session_state["user_store"]:
                    st.sidebar.error("⚠️ Username already exists!")
                else:
                    st.session_state["user_store"][username] = hashed_password
                    save_users(st.session_state["user_store"])  # Save to file
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.sidebar.success("🎉 Account created! Logged in.")
            else:
                st.sidebar.error("⚠️ Please enter a username and password.")
    else:  # Login
        if st.sidebar.button("🔓 Login"):
            if username in st.session_state["user_store"] and st.session_state["user_store"][username] == hashed_password:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.sidebar.success("✅ Logged in successfully!")
            else:
                st.sidebar.error("❌ Invalid credentials.")
else:
    st.sidebar.success(f"👋 Welcome, {st.session_state['username']}!")
    if st.sidebar.button("🚪 Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["messages"] = []
        st.sidebar.warning("You have logged out.")
        st.experimental_rerun()

# Restrict access until login
if st.session_state["logged_in"]:
    # ✅ Sidebar: File Upload
    st.sidebar.header("📁 Upload Documents")
    uploaded_file = st.sidebar.file_uploader("Choose a file (.pdf or .txt)", type=["pdf", "txt"])

    if uploaded_file:
        with st.spinner("Uploading and processing file..."):
            files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
            response = requests.post(f"{backend_url}/upload/", files=files)

            if response.status_code == 200:
                st.sidebar.success("✅ File uploaded successfully!")
            else:
                st.sidebar.error("❌ Upload failed!")

    # ✅ Sidebar: Display Uploaded Files
    st.sidebar.header("📄 Uploaded Files")
    file_list_response = requests.get(f"{backend_url}/files/")
    if file_list_response.status_code == 200:
        files = file_list_response.json().get("uploaded_files", [])
        if files:
            st.sidebar.success("📂 Uploaded Files:")
            for file in files:
                st.sidebar.write(f"- `{file}`")
        else:
            st.sidebar.info("No files uploaded yet.")

    # ✅ Chat UI
    st.subheader("💬 Chat with Documents")
    user_input = st.text_input("Ask a question...", key="user_input")

    if st.button("Send"):
        if user_input:
            st.session_state["messages"].append(("🧑 You", user_input))
            response = requests.get(f"{backend_url}/search/", params={"query": user_input})
            answer = response.json().get("answer", "❌ Error fetching response") if response.status_code == 200 else "❌ Error fetching response"
            st.session_state["messages"].append(("🤖 Bot", answer))

    for sender, message in st.session_state["messages"]:
        with st.chat_message("user" if sender == "🧑 You" else "assistant"):
            st.markdown(f"**{sender}**: {message}")

    # ✅ Sidebar: Save & Load Chat Sessions
    st.sidebar.header("💾 Chat Sessions")
    if st.sidebar.button("💾 Save Chat"):
        session_name = f"Session {len(st.session_state['chat_sessions']) + 1}"
        st.session_state["chat_sessions"][session_name] = list(st.session_state["messages"])
        st.sidebar.success(f"Chat saved as: {session_name}")

    saved_sessions = list(st.session_state["chat_sessions"].keys())
    selected_session = st.sidebar.selectbox("📜 Load Previous Chat", [""] + saved_sessions)
    if selected_session and selected_session in st.session_state["chat_sessions"]:
        st.session_state["messages"] = list(st.session_state["chat_sessions"][selected_session])
        st.sidebar.success(f"Loaded: {selected_session}")

    if st.sidebar.button("🗑️ Clear Chat"):
        st.session_state["messages"] = []
        st.sidebar.warning("Chat history cleared!")

    # ✅ Dark Mode Toggle
    dark_mode = st.sidebar.toggle("🌙 Dark Mode", value=False)
    if dark_mode:
        st.markdown(
            """
            <style>
                body { background-color: #121212; color: white; }
                .stTextInput, .stButton { color: white !important; }
            </style>
            """,
            unsafe_allow_html=True,
        )
else:
    st.warning("🔒 Please log in to access the chatbot.")
