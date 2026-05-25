from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import re
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="YouTube Video Summarizer")
app.mount("/static", StaticFiles(directory="static"), name="static")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ytt_api = YouTubeTranscriptApi()


class VideoRequest(BaseModel):
    url: str


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        r"(?:embed\/)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Could not extract video ID from URL")


def format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def get_transcript(video_id: str):
    """Fetch transcript from YouTube."""
    try:
        return ytt_api.fetch(video_id, languages=["en"])
    except NoTranscriptFound:
        pass
    except TranscriptsDisabled:
        raise HTTPException(status_code=400, detail="Transcripts are disabled for this video.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch transcript: {str(e)}")
    try:
        transcript_list = ytt_api.list(video_id)
        return transcript_list.find_transcript(
            [t.language_code for t in transcript_list]
        ).fetch()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No transcript found for this video: {str(e)}")


def build_transcript_text(transcript_list: list) -> str:
    """Build readable transcript with timestamps."""
    lines = []
    for entry in transcript_list:
        ts = format_timestamp(entry.start)
        lines.append(f"[{ts}] {entry.text}")
    return "\n".join(lines)


def summarize_with_openai(transcript_text: str) -> dict:
    """Send transcript to OpenAI and get structured summary."""
    system_prompt = """You are an expert video summarizer. Given a YouTube video transcript with timestamps, produce a structured summary in valid JSON with this exact schema:

{
  "title_guess": "A short descriptive title for the video",
  "overview": "2-3 sentence high-level summary of the entire video",
  "key_points": [
    {
      "timestamp": "MM:SS or HH:MM:SS",
      "title": "Short title for this point",
      "summary": "1-2 sentence explanation of this key point"
    }
  ],
  "topics": ["topic1", "topic2", "topic3"],
  "duration_note": "Approximate duration or coverage note"
}

Rules:
- Extract 5-10 key points with accurate timestamps from the transcript
- Timestamps must match actual moments in the transcript
- Be concise but informative
- Return ONLY valid JSON, no markdown, no extra text"""

    # Truncate very long transcripts to fit context window
    max_chars = 60000
    if len(transcript_text) > max_chars:
        transcript_text = transcript_text[:max_chars] + "\n[Transcript truncated for length]"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Summarize this transcript:\n\n{transcript_text}"}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )

    import json
    content = response.choices[0].message.content
    return json.loads(content)


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/summarize")
async def summarize(request: VideoRequest):
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required.")

    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    transcript_list = get_transcript(video_id)
    transcript_text = build_transcript_text(transcript_list)
    summary = summarize_with_openai(transcript_text)

    return {
        "video_id": video_id,
        "video_url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "summary": summary
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
