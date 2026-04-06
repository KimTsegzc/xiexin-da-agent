# Prompt Engineering

This directory is the home of prompt engineering assets.

- `soul.md`: system prompt persona and behavior constraints.
- `welcome.py`: hero welcome text generator via `qwen-turbo`; prompt and generation parameters are self-contained in this module.

Model service config:

- API key and base URL are unified in `Backend/settings.py`.
- Welcome generation model is fixed to `qwen-turbo` in `welcome.py`.

Rule:

- Keep prompt assets and prompt-generation logic here.
- Transport and API layers should only import and consume outputs from this directory.
