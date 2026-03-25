**This is a human write file(./architect.md) to make things controllable.**
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
    - [ChatGPT](https://chatgpt.com/)
    - there is a wanted page look at '.\Gateway\Front\page_referencee.png'
    - the avatar pic is at '.\Gateway\Front\xiexin-avatar.png'

## Interactive Components
- [comp-chat-box]an input box for type and send.
- nothing else for right now!

<!-- BACKEND -->
# Backend Architect
We'll discuss this later.<video controls src="Screen Recording 2026-03-25 155814.mp4" title="Title"></video>