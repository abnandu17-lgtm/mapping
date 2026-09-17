# CSP Outcome Mapping Generator

A Streamlit application that generates a CSP Outcome Mapping PDF from an
uploaded Community Service Project (CSP) project-book PDF.

## Core architecture

### Fixed for every project

- Section 1: CO1–CO5
- Section 2: CO → PO/PSO mapping
- Section 3: WK1–WK9 → PO/PSO mapping
- SDG catalogue: fixed SDG 1–17 descriptions

Sections 1–3 never analyze the uploaded project.

### Dynamic from the uploaded CSP book

Only the uploaded CSP project book determines the project-specific Section 4.

The application:

1. Extracts the complete PDF text with page markers.
2. Sends the project-book content to Gemini.
3. Gemini identifies distinct substantive project components from the actual book.
4. Every component must be supported by evidence from the uploaded book.
5. No predefined project-component keyword list is used.
6. No project-domain fallback components are used.
7. Gemini maps the generated components to relevant SDGs from the fixed SDG 1–17 catalogue.
8. Unsupported components or SDGs are not fabricated just to reach a target count.

This means a different CSP book can produce completely different project
components without modifying the component detector source code.

## Gemini API Free Tier

This project uses Google's Gemini API instead of the OpenAI API.

Create an API key in Google AI Studio:

https://aistudio.google.com/apikey

### Easiest local setup

The ZIP already contains `.streamlit/gemini_api_key.txt`. Open it and replace:

```text
YOUR_GEMINI_API_KEY_HERE
```

with your real Gemini API key. You do not need to edit `config.toml`.

### Streamlit deployment

For Streamlit Community Cloud, configure:

```toml
GEMINI_API_KEY = "your-gemini-api-key"
GEMINI_MODEL = "gemini-2.0-flash"
```

in the app's Secrets settings.

Use a Gemini model available to your account's Free Tier. Google controls
Free Tier rate limits and quotas; this application does not bypass them.

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Security

Never commit `.streamlit/secrets.toml` or your API key to GitHub.

Recommended `.gitignore` entries:

```text
.streamlit/secrets.toml
__pycache__/
*.pyc
.env
.venv/
```
