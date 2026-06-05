#!/usr/bin/env python3
"""
Fetch and analyze an All-In Podcast transcript for a given date.

Default flow:
1. Resolve the All-In episode for the date from the official Libsyn RSS feed.
2. Search YouTube for the matching episode and fetch its captions as transcript text.
3. Summarize key transcript points and rank company mentions by frequency.

The script is standard-library only. If YouTube captions are unavailable, pass
--transcript-url or --transcript-file to analyze a transcript from another source.
If you only need a lightweight fallback report, pass --allow-rss-notes to analyze
the official episode show notes when a full transcript cannot be fetched.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import email.utils
import html
import json
import re
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import warnings
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


VENDOR_DIR = Path(__file__).with_name("vendor")
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))


RSS_URL = "https://allinchamathjason.libsyn.com/rss"
YOUTUBE_SEARCH_URL = "https://www.youtube.com/results"
YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@allin/videos"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

RSS_NAMESPACES = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
}

STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "also",
    "because",
    "before",
    "being",
    "between",
    "could",
    "doing",
    "first",
    "going",
    "have",
    "into",
    "just",
    "like",
    "look",
    "make",
    "market",
    "more",
    "much",
    "people",
    "really",
    "right",
    "said",
    "should",
    "some",
    "something",
    "than",
    "that",
    "their",
    "there",
    "these",
    "thing",
    "think",
    "this",
    "those",
    "through",
    "very",
    "want",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
    "years",
}

SIGNAL_WORDS = {
    "acquisition",
    "ai",
    "capital",
    "company",
    "competition",
    "consumer",
    "cost",
    "crypto",
    "data",
    "earnings",
    "economy",
    "enterprise",
    "growth",
    "inflation",
    "ipo",
    "jobs",
    "market",
    "margin",
    "model",
    "policy",
    "private",
    "public",
    "rate",
    "regulation",
    "revenue",
    "risk",
    "startup",
    "stock",
    "technology",
    "valuation",
}

STOP_TICKERS = {
    "AI",
    "API",
    "CEO",
    "CFO",
    "CPI",
    "CRM",  # Salesforce is counted through aliases.
    "CTO",
    "DC",
    "DOJ",
    "EU",
    "EV",
    "FTC",
    "GDP",
    "GPU",
    "IPO",
    "LLM",
    "NASA",
    "SEC",
    "SPAC",
    "TV",
    "UK",
    "US",
    "USA",
    "VC",
}

PERSON_AND_SHOW_NAMES = {
    "all in",
    "all-in",
    "besties",
    "bill gurley",
    "chamath",
    "chamath palihapitiya",
    "david friedberg",
    "david sacks",
    "friedberg",
    "jason",
    "jason calacanis",
    "sacks",
}

KNOWN_COMPANIES: Sequence[Dict[str, object]] = [
    {"name": "Apple", "ticker": "AAPL", "aliases": ["Apple", "iPhone", "App Store"]},
    {"name": "Microsoft", "ticker": "MSFT", "aliases": ["Microsoft", "Azure", "LinkedIn", "GitHub"]},
    {"name": "Nvidia", "ticker": "NVDA", "aliases": ["Nvidia", "NVIDIA", "CUDA"]},
    {"name": "Tesla", "ticker": "TSLA", "aliases": ["Tesla"]},
    {"name": "Meta", "ticker": "META", "aliases": ["Meta", "Facebook", "Instagram", "WhatsApp"]},
    {"name": "Alphabet", "ticker": "GOOGL", "aliases": ["Alphabet", "Google", "YouTube", "Gemini"]},
    {"name": "Amazon", "ticker": "AMZN", "aliases": ["Amazon", "AWS"]},
    {"name": "Palantir", "ticker": "PLTR", "aliases": ["Palantir"]},
    {"name": "Coinbase", "ticker": "COIN", "aliases": ["Coinbase"]},
    {"name": "Robinhood", "ticker": "HOOD", "aliases": ["Robinhood"]},
    {"name": "Uber", "ticker": "UBER", "aliases": ["Uber"]},
    {"name": "Airbnb", "ticker": "ABNB", "aliases": ["Airbnb"]},
    {"name": "Netflix", "ticker": "NFLX", "aliases": ["Netflix"]},
    {"name": "Block", "ticker": "SQ", "aliases": ["Block", "Square", "Cash App"]},
    {"name": "Shopify", "ticker": "SHOP", "aliases": ["Shopify"]},
    {"name": "Spotify", "ticker": "SPOT", "aliases": ["Spotify"]},
    {"name": "Snap", "ticker": "SNAP", "aliases": ["Snap", "Snapchat"]},
    {"name": "Reddit", "ticker": "RDDT", "aliases": ["Reddit"]},
    {"name": "DoorDash", "ticker": "DASH", "aliases": ["DoorDash"]},
    {"name": "Instacart", "ticker": "CART", "aliases": ["Instacart"]},
    {"name": "Circle", "ticker": "CRCL", "aliases": ["Circle", "USDC"]},
    {"name": "AMD", "ticker": "AMD", "aliases": ["AMD", "Advanced Micro Devices"]},
    {"name": "Intel", "ticker": "INTC", "aliases": ["Intel"]},
    {"name": "Oracle", "ticker": "ORCL", "aliases": ["Oracle"]},
    {"name": "Salesforce", "ticker": "CRM", "aliases": ["Salesforce"]},
    {"name": "Adobe", "ticker": "ADBE", "aliases": ["Adobe"]},
    {"name": "ServiceNow", "ticker": "NOW", "aliases": ["ServiceNow"]},
    {"name": "Snowflake", "ticker": "SNOW", "aliases": ["Snowflake"]},
    {"name": "CrowdStrike", "ticker": "CRWD", "aliases": ["CrowdStrike"]},
    {"name": "Palo Alto Networks", "ticker": "PANW", "aliases": ["Palo Alto Networks"]},
    {"name": "Broadcom", "ticker": "AVGO", "aliases": ["Broadcom", "VMware"]},
    {"name": "Taiwan Semiconductor", "ticker": "TSM", "aliases": ["TSMC", "Taiwan Semiconductor"]},
    {"name": "Arm", "ticker": "ARM", "aliases": ["Arm Holdings", "ARM"]},
    {"name": "Micron", "ticker": "MU", "aliases": ["Micron"]},
    {"name": "JPMorgan Chase", "ticker": "JPM", "aliases": ["JPMorgan", "JP Morgan", "Chase"]},
    {"name": "Goldman Sachs", "ticker": "GS", "aliases": ["Goldman", "Goldman Sachs"]},
    {"name": "BlackRock", "ticker": "BLK", "aliases": ["BlackRock"]},
    {"name": "Berkshire Hathaway", "ticker": "BRK.B", "aliases": ["Berkshire", "Berkshire Hathaway"]},
    {"name": "SpaceX", "ticker": None, "aliases": ["SpaceX", "Starlink"]},
    {"name": "OpenAI", "ticker": None, "aliases": ["OpenAI", "ChatGPT"]},
    {"name": "Anthropic", "ticker": None, "aliases": ["Anthropic", "Claude"]},
    {"name": "xAI", "ticker": None, "aliases": ["xAI", "Grok"]},
    {"name": "Stripe", "ticker": None, "aliases": ["Stripe"]},
    {"name": "Databricks", "ticker": None, "aliases": ["Databricks"]},
    {"name": "Anduril", "ticker": None, "aliases": ["Anduril"]},
    {"name": "Scale AI", "ticker": None, "aliases": ["Scale AI"]},
    {"name": "Perplexity", "ticker": None, "aliases": ["Perplexity"]},
    {"name": "CoreWeave", "ticker": "CRWV", "aliases": ["CoreWeave"]},
    {"name": "Polymarket", "ticker": None, "aliases": ["Polymarket"]},
]


@dataclass
class Episode:
    title: str
    published_at: dt.datetime
    link: str
    description: str
    audio_url: str
    duration: str


@dataclass
class CompanyMention:
    name: str
    ticker: Optional[str]
    count: int
    confidence: str
    source: str
    contexts: List[str]


def http_get(url: str, timeout: int = 30) -> Tuple[str, str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml,text/plain,application/json,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("content-type", "")
        final_url = response.geturl()
        raw = response.read()
    return raw.decode("utf-8", errors="replace"), final_url, content_type


def parse_date(value: str) -> dt.date:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%B %d %Y", "%b %d %Y"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise SystemExit(f"Could not parse date {value!r}. Use YYYY-MM-DD, like 2026-05-29.")


def clean_html(value: str) -> str:
    value = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.I)
    value = re.sub(r"<style[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</(p|div|li|h[1-6]|section|article)>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = re.sub(r"[ \t]{2,}", " ", value)
    return value.strip()


def fetch_episodes(rss_url: str = RSS_URL) -> List[Episode]:
    xml_text, _, _ = http_get(rss_url)
    root = ET.fromstring(xml_text)
    episodes: List[Episode] = []

    for item in root.findall("./channel/item"):
        title = text_or_empty(item.find("title"))
        pub_text = text_or_empty(item.find("pubDate"))
        published_at = email.utils.parsedate_to_datetime(pub_text)
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=dt.timezone.utc)
        link = text_or_empty(item.find("link"))
        description = text_or_empty(item.find("description"))
        content = text_or_empty(item.find("content:encoded", RSS_NAMESPACES))
        enclosure = item.find("enclosure")
        audio_url = enclosure.attrib.get("url", "") if enclosure is not None else ""
        duration = text_or_empty(item.find("itunes:duration", RSS_NAMESPACES))
        episodes.append(
            Episode(
                title=html.unescape(title),
                published_at=published_at,
                link=html.unescape(link),
                description=clean_html(content or description),
                audio_url=html.unescape(audio_url),
                duration=duration,
            )
        )

    return episodes


def text_or_empty(node: Optional[ET.Element]) -> str:
    return "" if node is None or node.text is None else node.text.strip()


def find_episode_for_date(episodes: Sequence[Episode], target_date: dt.date) -> Tuple[Episode, bool]:
    exact = [episode for episode in episodes if episode.published_at.date() == target_date]
    if exact:
        return exact[0], True

    if not episodes:
        raise SystemExit("No episodes were found in the RSS feed.")

    nearest = min(episodes, key=lambda episode: abs((episode.published_at.date() - target_date).days))
    return nearest, False


def extract_video_id(url: str) -> Optional[str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.endswith("youtu.be"):
        candidate = parsed.path.strip("/").split("/")[0]
        return candidate if re.fullmatch(r"[\w-]{11}", candidate) else None
    if "youtube.com" in parsed.netloc:
        query_id = urllib.parse.parse_qs(parsed.query).get("v", [None])[0]
        if query_id and re.fullmatch(r"[\w-]{11}", query_id):
            return query_id
        match = re.search(r"/(?:embed|shorts|live)/([\w-]{11})", parsed.path)
        if match:
            return match.group(1)
    if re.fullmatch(r"[\w-]{11}", url):
        return url
    return None


def resolve_youtube_video_id(episode: Episode, channel_url: str = YOUTUBE_CHANNEL_URL) -> str:
    try:
        candidates = fetch_youtube_channel_candidates(channel_url)
        best = best_video_candidate(episode, candidates)
        if best:
            return best[0]
    except Exception:
        pass

    return search_youtube_video_id(episode)


def fetch_youtube_channel_candidates(channel_url: str) -> List[Tuple[str, str]]:
    html_text, _, _ = http_get(channel_url)
    return extract_video_candidates(html_text)


def extract_video_candidates(page_html: str) -> List[Tuple[str, str]]:
    candidates: List[Tuple[str, str]] = []
    seen = set()
    pattern = re.compile(
        r'"videoId":"([\w-]{11})"(?:(?!"videoId").){0,2500}?"title":\{"runs":\[\{"text":"((?:\\"|[^"])*)"',
        flags=re.S,
    )
    for match in pattern.finditer(page_html):
        video_id = match.group(1)
        title = decode_json_fragment(match.group(2))
        if video_id in seen or not title:
            continue
        seen.add(video_id)
        candidates.append((video_id, title))

    if candidates:
        return candidates

    for video_id in re.findall(r'"videoId":"([\w-]{11})"', page_html):
        if video_id not in seen:
            seen.add(video_id)
            candidates.append((video_id, ""))
    return candidates


def decode_json_fragment(value: str) -> str:
    try:
        return json.loads(f'"{value}"')
    except json.JSONDecodeError:
        return html.unescape(value.replace(r"\/", "/").replace(r"\"", '"'))


def best_video_candidate(episode: Episode, candidates: Sequence[Tuple[str, str]]) -> Optional[Tuple[str, str]]:
    if not candidates:
        return None

    episode_title = normalize_match_text(episode.title)
    best: Optional[Tuple[float, Tuple[str, str]]] = None
    for candidate in candidates:
        _, title = candidate
        if not title:
            continue
        score = difflib.SequenceMatcher(None, episode_title, normalize_match_text(title)).ratio()
        if best is None or score > best[0]:
            best = (score, candidate)

    if best and best[0] >= 0.38:
        return best[1]
    return candidates[0]


def normalize_match_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def search_youtube_video_id(episode: Episode) -> str:
    query = f'All-In Podcast "{episode.title}"'
    url = f"{YOUTUBE_SEARCH_URL}?{urllib.parse.urlencode({'search_query': query})}"
    html_text, _, _ = http_get(url)

    video_ids: List[str] = []
    for video_id in re.findall(r'"videoId":"([\w-]{11})"', html_text):
        if video_id not in video_ids:
            video_ids.append(video_id)

    if not video_ids:
        raise RuntimeError("Could not find a YouTube video id for this episode.")

    return video_ids[0]


def fetch_youtube_transcript(video_id_or_url: str) -> Tuple[str, str]:
    video_id = extract_video_id(video_id_or_url) or video_id_or_url
    watch_url = f"https://www.youtube.com/watch?v={video_id}"

    library_transcript = fetch_youtube_transcript_with_library(video_id)
    if library_transcript:
        return library_transcript, watch_url

    watch_html, _, _ = http_get(watch_url)

    caption_tracks = extract_caption_tracks(watch_html)
    if not caption_tracks:
        raise RuntimeError("This YouTube video does not expose caption tracks.")

    track = choose_caption_track(caption_tracks)
    base_url = html.unescape(track["baseUrl"])
    transcript_url = add_query_param(base_url, "fmt", "json3")
    raw_transcript, _, content_type = http_get(transcript_url)

    if "json" in content_type or raw_transcript.lstrip().startswith("{"):
        transcript = parse_json3_transcript(raw_transcript)
    else:
        transcript = parse_xml_transcript(raw_transcript)

    if word_count(transcript) < 200:
        raise RuntimeError("Fetched captions, but the transcript was unexpectedly short.")

    return transcript, watch_url


def fetch_youtube_transcript_with_library(video_id: str) -> Optional[str]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from youtube_transcript_api import YouTubeTranscriptApi

        fetched = YouTubeTranscriptApi().fetch(video_id, languages=("en", "en-US", "en-GB"))
        chunks: List[str] = []
        for item in fetched:
            if isinstance(item, dict):
                text = item.get("text", "")
            else:
                text = getattr(item, "text", "")
            if text:
                chunks.append(str(text).replace("\n", " "))
        transcript = normalize_transcript(" ".join(chunks))
        return transcript if word_count(transcript) >= 200 else None
    except Exception:
        return None


def extract_caption_tracks(watch_html: str) -> List[Dict[str, object]]:
    match = re.search(r'"captionTracks":(\[.*?\])', watch_html)
    if not match:
        return []
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return []


def choose_caption_track(tracks: Sequence[Dict[str, object]]) -> Dict[str, object]:
    english = [
        track
        for track in tracks
        if str(track.get("languageCode", "")).lower().startswith("en")
    ]
    candidates = english or list(tracks)
    manual = [track for track in candidates if track.get("kind") != "asr"]
    return (manual or candidates)[0]


def add_query_param(url: str, key: str, value: str) -> str:
    separator = "&" if urllib.parse.urlparse(url).query else "?"
    return f"{url}{separator}{urllib.parse.quote(key)}={urllib.parse.quote(value)}"


def parse_json3_transcript(raw_json: str) -> str:
    payload = json.loads(raw_json)
    chunks: List[str] = []
    for event in payload.get("events", []):
        parts = event.get("segs") or []
        text = "".join(part.get("utf8", "") for part in parts)
        text = text.replace("\n", " ").strip()
        if text:
            chunks.append(text)
    return normalize_transcript(" ".join(chunks))


def parse_xml_transcript(raw_xml: str) -> str:
    root = ET.fromstring(raw_xml)
    chunks = [html.unescape(node.text or "") for node in root.findall(".//text")]
    return normalize_transcript(" ".join(chunks))


def fetch_generic_transcript(url: str) -> Tuple[str, str]:
    video_id = extract_video_id(url)
    if video_id:
        return fetch_youtube_transcript(video_id)

    text, final_url, content_type = http_get(url)
    if "json" in content_type:
        try:
            payload = json.loads(text)
            text = json.dumps(payload, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass

    if "<html" in text[:500].lower() or "<body" in text[:1000].lower():
        title_match = re.search(r"<title[^>]*>([\s\S]*?)</title>", text, flags=re.I)
        main_match = re.search(r"<(main|article)[^>]*>([\s\S]*?)</\1>", text, flags=re.I)
        text = clean_html(main_match.group(2) if main_match else text)
        if title_match:
            title = clean_html(title_match.group(1))
            text = f"{title}\n\n{text}"
    else:
        text = normalize_transcript(text)

    if word_count(text) < 200:
        raise RuntimeError("Fetched text is too short to look like a full transcript.")

    return text, final_url


def normalize_transcript(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text: str) -> List[str]:
    text = normalize_transcript(text)
    text = re.sub(r"\s+(?=\(?\d{1,2}:\d{2}\)?)", ". ", text)
    candidates = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])", text)
    return [sentence.strip() for sentence in candidates if len(sentence.split()) >= 7]


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def summarize_transcript(text: str, max_points: int = 6) -> List[str]:
    sentences = split_sentences(text)
    if not sentences:
        return ["Not enough transcript text to summarize."]

    words = [
        word
        for word in re.findall(r"\b[a-z][a-z]{3,}\b", text.lower())
        if word not in STOPWORDS
    ]
    frequencies = Counter(words)
    top_words = {word for word, _ in frequencies.most_common(30)}

    scored = []
    for index, sentence in enumerate(sentences):
        sentence_lower = sentence.lower()
        score = sum(min(frequencies[word], 7) for word in top_words if word in sentence_lower)
        score += sum(5 for word in SIGNAL_WORDS if re.search(rf"\b{re.escape(word)}\b", sentence_lower))
        score += 4 if re.search(r"\$?\b[A-Z]{2,5}(?:\.[A-Z])?\b", sentence) else 0
        score = score / max(1.0, len(sentence) / 180)
        scored.append((score, index, sentence))

    target_count = min(max_points, max(3, round(len(sentences) / 35)))
    selected = sorted(sorted(scored, reverse=True)[:target_count], key=lambda item: item[1])
    return [compress_sentence(sentence) for _, _, sentence in selected]


def compress_sentence(sentence: str) -> str:
    sentence = re.sub(r"^(Jason|Chamath|Sacks|Friedberg|David|Jcal|Speaker \d+)[:\s-]+", "", sentence, flags=re.I)
    return textwrap.shorten(sentence, width=280, placeholder="...")


def extract_company_mentions(text: str, top_n: int = 25) -> List[CompanyMention]:
    sentences = split_sentences(text)
    mentions: Dict[str, CompanyMention] = {}

    for company in KNOWN_COMPANIES:
        name = str(company["name"])
        ticker = company.get("ticker")
        aliases = [str(alias) for alias in company["aliases"]]
        count = 0
        contexts: List[str] = []

        for alias in aliases:
            pattern = re.compile(rf"\b{re.escape(alias)}\b", flags=re.I)
            matches = pattern.findall(text)
            count += len(matches)
            contexts.extend(find_contexts(sentences, pattern))

        if ticker:
            ticker_pattern = re.compile(rf"(?<![A-Za-z0-9])\$?{re.escape(str(ticker))}(?![A-Za-z0-9])")
            count += len(ticker_pattern.findall(text))
            contexts.extend(find_contexts(sentences, ticker_pattern))

        if count:
            mentions[name.lower()] = CompanyMention(
                name=name,
                ticker=str(ticker) if ticker else None,
                count=count,
                confidence="high",
                source="known aliases",
                contexts=dedupe(contexts)[:2],
            )

    add_loose_ticker_mentions(text, sentences, mentions)
    add_heuristic_company_mentions(text, sentences, mentions)

    ranked = sorted(mentions.values(), key=lambda mention: (-mention.count, mention.name.lower()))
    return ranked[:top_n]


def find_contexts(sentences: Sequence[str], pattern: re.Pattern[str]) -> List[str]:
    contexts = []
    for sentence in sentences:
        if pattern.search(sentence):
            contexts.append(textwrap.shorten(sentence, width=220, placeholder="..."))
            if len(contexts) >= 2:
                break
    return contexts


def dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def add_loose_ticker_mentions(
    text: str,
    sentences: Sequence[str],
    mentions: Dict[str, CompanyMention],
) -> None:
    ticker_counts = Counter()
    for raw in re.findall(r"(?<![A-Za-z0-9])\$?([A-Z]{2,5}(?:\.[A-Z])?)(?![A-Za-z0-9])", text):
        ticker = raw.upper()
        if ticker in STOP_TICKERS:
            continue
        known_ticker = any(mention.ticker == ticker for mention in mentions.values())
        if known_ticker:
            continue
        ticker_counts[ticker] += 1

    for ticker, count in ticker_counts.items():
        key = ticker.lower()
        pattern = re.compile(rf"(?<![A-Za-z0-9])\$?{re.escape(ticker)}(?![A-Za-z0-9])")
        mentions[key] = CompanyMention(
            name=ticker,
            ticker=ticker,
            count=count,
            confidence="medium" if count > 1 else "low",
            source="ticker pattern",
            contexts=find_contexts(sentences, pattern)[:2],
        )


def add_heuristic_company_mentions(
    text: str,
    sentences: Sequence[str],
    mentions: Dict[str, CompanyMention],
) -> None:
    phrase_counts = Counter()
    candidates_by_lower: Dict[str, str] = {}
    company_suffixes = {
        "AI",
        "Bank",
        "Capital",
        "Cloud",
        "Corp",
        "Energy",
        "Financial",
        "Holdings",
        "Labs",
        "Media",
        "Networks",
        "Partners",
        "Robotics",
        "Semiconductor",
        "Software",
        "Technologies",
        "Ventures",
    }

    phrase_pattern = re.compile(
        r"\b(?:[A-Z][A-Za-z0-9&.-]+|xAI)(?:\s+(?:[A-Z][A-Za-z0-9&.-]+|AI|Labs|Technologies|Capital|Ventures|Networks|Holdings)){0,3}\b"
    )
    for match in phrase_pattern.finditer(text):
        phrase = match.group(0).strip(" .,:;!?()[]")
        lowered = phrase.lower()
        if lowered in mentions or lowered in PERSON_AND_SHOW_NAMES:
            continue
        if len(phrase) < 4 or phrase.isupper():
            continue
        words = phrase.split()
        likely_company = len(words) >= 2 or words[-1] in company_suffixes
        if not likely_company:
            continue
        if words[0].lower() in {"and", "but", "for", "from", "that", "the", "this", "with"}:
            continue
        phrase_counts[lowered] += 1
        candidates_by_lower[lowered] = phrase

    for lowered, count in phrase_counts.items():
        if count < 2:
            continue
        phrase = candidates_by_lower[lowered]
        pattern = re.compile(rf"\b{re.escape(phrase)}\b")
        mentions[lowered] = CompanyMention(
            name=phrase,
            ticker=None,
            count=count,
            confidence="low",
            source="capitalized phrase heuristic",
            contexts=find_contexts(sentences, pattern)[:2],
        )


def load_transcript(args: argparse.Namespace, episode: Optional[Episode]) -> Tuple[str, str]:
    if args.transcript_file:
        path = Path(args.transcript_file)
        return path.read_text(encoding="utf-8"), str(path)

    if args.transcript_url:
        return fetch_generic_transcript(args.transcript_url)

    if args.youtube_url:
        return fetch_youtube_transcript(args.youtube_url)

    if not episode:
        raise RuntimeError("No episode was resolved. Provide --transcript-file, --transcript-url, or --youtube-url.")

    video_id = resolve_youtube_video_id(episode, args.youtube_channel_url)
    return fetch_youtube_transcript(video_id)


def print_report(
    episode: Optional[Episode],
    exact_date_match: Optional[bool],
    transcript_source: str,
    transcript: str,
    summary: Sequence[str],
    mentions: Sequence[CompanyMention],
    args: argparse.Namespace,
) -> None:
    print("\nAll-In Transcript Analysis")
    print("=" * 26)
    if episode:
        date_note = "" if exact_date_match else " (nearest RSS episode)"
        print(f"Episode: {episode.title}")
        print(f"Published: {episode.published_at.strftime('%Y-%m-%d %H:%M %Z')}{date_note}")
        if episode.duration:
            print(f"Duration: {episode.duration}")
        if episode.link:
            print(f"Episode link: {episode.link}")
    print(f"Text source: {transcript_source}")
    print(f"Text words: {word_count(transcript):,}")

    print("\nKey Points")
    print("-" * 10)
    for index, point in enumerate(summary, start=1):
        print(f"{index}. {point}")

    print("\nCompanies Discussed")
    print("-" * 19)
    if not mentions:
        print("No company mentions found.")
    else:
        for rank, mention in enumerate(mentions, start=1):
            ticker = f" ({mention.ticker})" if mention.ticker else ""
            print(f"{rank}. {mention.name}{ticker}: {mention.count} mentions [{mention.confidence}; {mention.source}]")
            for context in mention.contexts[: args.contexts]:
                print(f"   - {context}")


def write_json_report(
    path: str,
    episode: Optional[Episode],
    transcript_source: str,
    transcript: str,
    summary: Sequence[str],
    mentions: Sequence[CompanyMention],
) -> None:
    payload = {
        "episode": None
        if not episode
        else {
            "title": episode.title,
            "published_at": episode.published_at.isoformat(),
            "link": episode.link,
            "audio_url": episode.audio_url,
            "duration": episode.duration,
        },
        "transcript_source": transcript_source,
        "transcript_word_count": word_count(transcript),
        "summary": list(summary),
        "companies": [
            {
                "rank": rank,
                "name": mention.name,
                "ticker": mention.ticker,
                "mentions": mention.count,
                "confidence": mention.confidence,
                "source": mention.source,
                "contexts": mention.contexts,
            }
            for rank, mention in enumerate(mentions, start=1)
        ],
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch an All-In Podcast transcript by date, summarize it, and rank company mentions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("date", nargs="?", help="Episode publish date, e.g. 2026-05-29")
    parser.add_argument("--rss-url", default=RSS_URL, help="Podcast RSS feed URL")
    parser.add_argument("--youtube-channel-url", default=YOUTUBE_CHANNEL_URL, help="All-In YouTube videos page")
    parser.add_argument("--youtube-url", help="Direct YouTube URL or video id to use for captions")
    parser.add_argument("--transcript-url", help="Direct transcript URL to fetch instead of YouTube captions")
    parser.add_argument("--transcript-file", help="Local transcript text file to analyze")
    parser.add_argument("--max-summary-points", type=int, default=6, help="Maximum key points to print")
    parser.add_argument("--top-companies", type=int, default=25, help="Maximum company rows to print")
    parser.add_argument("--contexts", type=int, default=1, help="Context snippets per company")
    parser.add_argument(
        "--allow-rss-notes",
        action="store_true",
        help="If transcript fetching fails, analyze official RSS show notes instead",
    )
    parser.add_argument("--save-transcript", help="Optional path to save fetched transcript text")
    parser.add_argument("--json-out", help="Optional path to write a JSON report")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    episode: Optional[Episode] = None
    exact_date_match: Optional[bool] = None

    if args.date and not (args.transcript_file or args.transcript_url or args.youtube_url):
        target_date = parse_date(args.date)
        episodes = fetch_episodes(args.rss_url)
        episode, exact_date_match = find_episode_for_date(episodes, target_date)
        if not exact_date_match:
            delta = abs((episode.published_at.date() - target_date).days)
            if delta > 3:
                raise SystemExit(
                    f"No episode was published on {target_date}. Nearest RSS episode is "
                    f"{episode.published_at.date()} ({episode.title})."
                )
    elif args.date:
        target_date = parse_date(args.date)
        try:
            episodes = fetch_episodes(args.rss_url)
            episode, exact_date_match = find_episode_for_date(episodes, target_date)
        except Exception:
            episode, exact_date_match = None, None
    elif not (args.transcript_file or args.transcript_url or args.youtube_url):
        raise SystemExit("Provide a date or a transcript source. Example: python3 all_in_transcript_analyzer.py 2026-05-29")

    try:
        transcript, transcript_source = load_transcript(args, episode)
    except (urllib.error.URLError, RuntimeError, ET.ParseError, json.JSONDecodeError) as error:
        if args.allow_rss_notes and episode and word_count(episode.description) >= 40:
            transcript = episode.description
            transcript_source = "RSS episode notes fallback (not a full transcript)"
        else:
            raise SystemExit(
                "Could not fetch a full transcript automatically.\n"
                f"Reason: {error}\n\n"
                "Try one of these fallbacks:\n"
                "  --youtube-url https://www.youtube.com/watch?v=VIDEO_ID\n"
                "  --transcript-url https://example.com/transcript-page\n"
                "  --transcript-file ./episode.txt\n"
                "  --allow-rss-notes"
            )

    transcript = normalize_transcript(transcript)
    if args.save_transcript:
        Path(args.save_transcript).write_text(transcript, encoding="utf-8")

    summary = summarize_transcript(transcript, max_points=args.max_summary_points)
    mentions = extract_company_mentions(transcript, top_n=args.top_companies)

    print_report(episode, exact_date_match, transcript_source, transcript, summary, mentions, args)

    if args.json_out:
        write_json_report(args.json_out, episode, transcript_source, transcript, summary, mentions)
        print(f"\nJSON report written to {args.json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
