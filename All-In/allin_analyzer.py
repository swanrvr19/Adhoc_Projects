#!/usr/bin/env python3
"""
All In Podcast Transcript Analyzer
====================================
Fetches the latest (or a specified) All In Podcast episode from YouTube,
then uses Claude to:
  1. Summarize key topics and takeaways
  2. Extract all companies/organizations mentioned

Usage:
    python allin_analyzer.py                      # Latest episode
    python allin_analyzer.py <video_id>           # Specific episode by ID
    python allin_analyzer.py <youtube_url>        # Specific episode by URL

Requirements:
    pip install anthropic youtube-transcript-api yt-dlp

Environment:
    ANTHROPIC_API_KEY  — your Anthropic API key (required)
    ANTHROPIC_MODEL    — model to use (optional, default: claude-opus-4-6)
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    sys.exit("Missing dependency: run  pip install anthropic")

try:
    import yt_dlp
except ImportError:
    sys.exit("Missing dependency: run  pip install yt-dlp")

try:
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
except ImportError:
    sys.exit("Missing dependency: run  pip install youtube-transcript-api")


CHANNEL_HANDLE = "UCESLZhusAkFfsNsApnjF_Cg"  # All-In with Chamath, Jason, Sacks & Friedberg
DEFAULT_MODEL   = "claude-opus-4-6"
MAX_TRANSCRIPT_CHARS = 150_000


def parse_video_id(arg: str) -> "str | None":
    match = re.search(r"(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})", arg)
    if match:
        return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", arg):
        return arg
    return None


def _channel_entries(n: int = 20) -> list:
    """Fetch the most recent n videos from the channel."""
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "playlist_items": f"1-{n}",
    }
    url = f"https://www.youtube.com/channel/{CHANNEL_HANDLE}/videos"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get("entries", [])


def get_latest_episode() -> "tuple[str, str]":
    print("Fetching latest episode ...")
    for entry in _channel_entries():
        title = entry.get("title", "")
        if any(skip in title.lower() for skip in ["d&d", "dungeons", "trailer", "#shorts"]):
            continue
        return entry["id"], title
    sys.exit("Could not find a podcast episode on the channel.")


def get_episode_by_title(search: str) -> "tuple[str, str]":
    """Find the episode whose title best matches the search string."""
    print(f"Searching for episode matching: '{search}' ...")
    entries = _channel_entries(50)
    search_lower = search.lower()

    # First pass: substring match
    for entry in entries:
        title = entry.get("title", "")
        if any(skip in title.lower() for skip in ["d&d", "dungeons", "trailer", "#shorts"]):
            continue
        if search_lower in title.lower():
            print(f"Found: {title}")
            return entry["id"], title

    # Second pass: all search words present (order-independent)
    words = search_lower.split()
    for entry in entries:
        title = entry.get("title", "")
        if any(skip in title.lower() for skip in ["d&d", "dungeons", "trailer", "#shorts"]):
            continue
        if all(w in title.lower() for w in words):
            print(f"Found: {title}")
            return entry["id"], title

    sys.exit(f"No episode found matching '{search}'. Try different keywords.")


def get_video_title(video_id: str) -> str:
    ydl_opts = {"quiet": True}
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get("title", video_id)
    except Exception:
        return video_id


def get_transcript(video_id: str) -> str:
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
        entries = [{"text": s.text} for s in fetched]
    except TranscriptsDisabled:
        sys.exit(f"Transcripts are disabled for video {video_id}.")
    except NoTranscriptFound:
        sys.exit(f"No transcript found for video {video_id}.")
    except Exception as e:
        sys.exit(f"Could not retrieve transcript for {video_id}: {e}")

    text = " ".join(entry["text"] for entry in entries)

    if len(text) > MAX_TRANSCRIPT_CHARS:
        print(f"  Transcript is {len(text):,} chars — trimming to {MAX_TRANSCRIPT_CHARS:,}.")
        text = text[:MAX_TRANSCRIPT_CHARS] + "\n\n[transcript truncated]"

    return text


SYSTEM_PROMPT = """\
You are an expert analyst of technology, venture capital, and business news.
You are given a full transcript from the All In Podcast. Your job is to produce a
structured analysis with two sections:
  1. A summary of the episode
  2. A list of every company or organisation mentioned

Be specific and accurate. Do not invent anything not present in the transcript."""

USER_TEMPLATE = """\
Episode title: {title}

Transcript:
{transcript}

---

Please respond with exactly the following structure (use Markdown):

## Episode Summary

Write 3–5 paragraphs covering the main topics discussed, the key arguments made by
the hosts, and any notable guests or news items.

## Key Takeaways

A bullet list (5–10 items) of the most important insights or conclusions.

## Companies & Organisations Mentioned

A table with two columns:
| Company / Organisation | Context |
|------------------------|---------|

List every company, startup, fund, institution, or named organisation that appears
in the transcript. For "Context", write one short phrase describing why it came up.
"""


def analyze(client: anthropic.Anthropic, title: str, transcript: str, model: str) -> str:
    print(f"Sending transcript to Claude ({model}) ...")
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_TEMPLATE.format(title=title, transcript=transcript)}],
    )
    return response.content[0].text


def save_markdown(title: str, video_id: str, analysis: str) -> Path:
    # Save output files alongside this script
    script_dir = Path(__file__).parent
    safe_title = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")[:60]
    date_str   = datetime.now().strftime("%Y-%m-%d")
    filename   = f"allin_{date_str}_{safe_title}.md"
    output     = script_dir / filename
    output.write_text(
        f"# All In Podcast — {title}\n\n"
        f"**YouTube:** <https://www.youtube.com/watch?v={video_id}>  \n"
        f"**Analyzed:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  \n\n"
        "---\n\n" + analysis + "\n",
        encoding="utf-8",
    )
    return output


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("Error: ANTHROPIC_API_KEY environment variable is not set.")

    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    client = anthropic.Anthropic(api_key=api_key)

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # If it looks like a video ID or URL, use it directly
        video_id = parse_video_id(arg)
        if video_id:
            print(f"Using specified video: {video_id}")
            title = get_video_title(video_id)
        else:
            # Treat the argument as a title search string
            video_id, title = get_episode_by_title(arg)
    else:
        video_id, title = get_latest_episode()

    print(f"Episode : {title}")
    print(f"URL     : https://www.youtube.com/watch?v={video_id}\n")

    print("Fetching transcript ...")
    transcript = get_transcript(video_id)
    print(f"Transcript: {len(transcript):,} characters\n")

    analysis = analyze(client, title, transcript, model)
    output_path = save_markdown(title, video_id, analysis)
    print(f"\n✓ Analysis saved to: {output_path}")


if __name__ == "__main__":
    main()
