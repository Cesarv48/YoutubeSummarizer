# YouTube Video Summarizer

AI-powered YouTube video summarizer built with **FastAPI**, **OpenAI GPT-4o-mini**, and the **YouTube Transcript API**.

## Features
- Paste any YouTube URL → get a structured summary instantly
- Key points with accurate timestamps
- High-level video overview
- Clean, dark-mode UI served by FastAPI

## Tech Stack
| Backend | Python 3.10+ · FastAPI · Uvicorn |
| AI | OpenAI GPT-4o-mini |
| Transcript | youtube-transcript-api |
| Frontend | HTML/CSS/JS |

## Setup

### 1. Clone / copy the project
```bash
cd YoutubeSummarizer
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your OpenAI API key
```bash
Edit .env and replace `your_openai_api_key_here` with your actual key
```

### 5. Run the server
```bash
uvicorn main:app --reload --port 8000
```

### 6. Open the app
Visit `http://localhost:8000` in your browser.

## Notes
- Videos **must have captions/transcripts enabled** on YouTube (auto-generated captions work).
- Very long videos (3h+) have their transcripts trimmed to fit the OpenAI context window.
- Cost per summary: ~$0.001–0.005 using GPT-4o-mini.
