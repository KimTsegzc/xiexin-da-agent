**This is a human write place to make things controllable.**
**AI agents should read to understand.**
**No AI should/could/would make any change.**

<!-- STATEMENT -->
# This is md file that claims ways of building whole project.
# a vission and scope statement is at ./readme.md.

<!-- Directories -->
# Directories
It has:
1. **Memo:** contains ./Memo/metadata, some metadata like Dict.json a mapping for columns to select and rename. and other groups xlsx may be packed up here.
2. **Skills:** ./Skills/sudo-name-skill kebab-case named skill folders, with a .md file to anounce it which has name same as skill(constraint with JSON Schema for input and output),  a scripts, an input and a output foder inside.
3. **Gateway:** has ./Gateway/LLM provides LLM service. ./Gateway/Front as UI page.
4. **controller.py** main controlling process, **Human built, AI can read but never make any change**.


<!-- FRONTEND -->
# Frontend Architect
## main and only page
Let's make this a chatbot-like UI.

## style and reference
- **farmework:** Streamlit
- **Style:** Conversational UI/UX
- **UI Reference:** 
    1. [ChatGPT](https://chatgpt.com/)
    2. [Gemini](https://gemini.google.com/)
    3. [Claude](https://claude.ai/)

## Interactive Components
- [comp-chat-box]an input box for type and send.


<!-- BACKEND -->
# Backend Architect
We'll discuss this later.