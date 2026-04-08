#!/usr/bin/env python3
"""
Online Text-to-Speech Tool - Local Server
Provides static file hosting + Edge TTS API proxy
Usage: python server.py
Dependencies: pip install flask edge-tts
"""

import asyncio
import io
import os
import random
import sys
import time

try:
    from flask import Flask, request, jsonify, send_from_directory
except ImportError:
    print("Error: missing Flask dependency")
    print("Please run: pip install flask")
    sys.exit(1)

try:
    import edge_tts
except ImportError:
    print("Error: missing edge-tts dependency")
    print("Please run: pip install edge-tts")
    sys.exit(1)

# Restrict static files to the web subdirectory to avoid exposing source files.
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

def get_int_env(name, default):
    """Read an integer environment variable with fallback to a default value."""
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        print(f"Warning: environment variable {name}={value} is not an integer. Using default {default}")
        return default


def get_float_env(name, default):
    """Read a float environment variable with fallback to a default value."""
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        print(f"Warning: environment variable {name}={value} is not a float. Using default {default}")
        return default


# Limit configuration (<= 0 means unlimited)
MAX_TEXT_LENGTH = get_int_env("MAX_TEXT_LENGTH", 0)
MAX_REQUESTS_PER_HOUR = get_int_env("MAX_REQUESTS_PER_HOUR", 0)

# Segmentation and retry configuration
TTS_SEGMENT_MAX_LENGTH = get_int_env("TTS_SEGMENT_MAX_LENGTH", 1200)
MAX_SEGMENTS_PER_REQUEST = get_int_env("MAX_SEGMENTS_PER_REQUEST", 0)
TTS_RETRY_MAX_ATTEMPTS = max(get_int_env("TTS_RETRY_MAX_ATTEMPTS", 4), 1)
TTS_RETRY_BASE_DELAY_SECONDS = max(get_float_env("TTS_RETRY_BASE_DELAY_SECONDS", 0.8), 0.0)
TTS_RETRY_MAX_DELAY_SECONDS = max(
    get_float_env("TTS_RETRY_MAX_DELAY_SECONDS", 8.0),
    TTS_RETRY_BASE_DELAY_SECONDS,
)
TTS_RETRY_JITTER_SECONDS = max(get_float_env("TTS_RETRY_JITTER_SECONDS", 0.2), 0.0)

# Request timestamps grouped by client IP
request_log = {}

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


def check_rate_limit(ip):
    """Check whether the given IP exceeds the rate limit and return (allowed, used_count)."""
    if MAX_REQUESTS_PER_HOUR <= 0:
        return True, 0

    now = time.time()
    one_hour_ago = now - 3600
    timestamps = request_log.get(ip, [])
    # Remove expired records.
    timestamps = [t for t in timestamps if t > one_hour_ago]
    request_log[ip] = timestamps
    return len(timestamps) < MAX_REQUESTS_PER_HOUR, len(timestamps)


@app.route("/api/tts", methods=["POST"])
def tts():
    data = request.get_json(silent=True)
    if not data:
        return jsonify(error="Invalid request format"), 400

    text = data.get("text", "").strip()
    voice = data.get("voice", "zh-CN-XiaoxiaoNeural")
    rate = data.get("rate", "+0%")
    pitch = data.get("pitch", "+0Hz")

    if not text:
        return jsonify(error="Text content cannot be empty"), 400

    if MAX_TEXT_LENGTH > 0 and len(text) > MAX_TEXT_LENGTH:
        return jsonify(error=f"Text content cannot exceed {MAX_TEXT_LENGTH} characters"), 400

    client_ip = request.remote_addr
    allowed, used = check_rate_limit(client_ip)
    if not allowed:
        return jsonify(error=f"The limit of {MAX_REQUESTS_PER_HOUR} conversions per hour has been reached. Please try again later"), 429

    try:
        audio_data = asyncio.run(synthesize(text, voice, rate, pitch))
        # Record the request only after a successful synthesis.
        request_log.setdefault(client_ip, []).append(time.time())
        return audio_data, 200, {"Content-Type": "audio/mpeg"}
    except Exception as e:
        print(f"TTS synthesis error: {e}")
        return jsonify(error=f"Speech synthesis failed: {e}"), 500


async def synthesize(text, voice, rate, pitch):
    segments = split_text_for_queue(text)
    if MAX_SEGMENTS_PER_REQUEST > 0 and len(segments) > MAX_SEGMENTS_PER_REQUEST:
        raise ValueError(
            f"The text was split into {len(segments)} segments, which exceeds the limit of {MAX_SEGMENTS_PER_REQUEST}"
        )

    if len(segments) > 1:
        print(f"TTS segment queue: {len(segments)} segments will be synthesized sequentially")

    queue = asyncio.Queue()
    for idx, segment in enumerate(segments, start=1):
        await queue.put((idx, segment))

    merged_audio = io.BytesIO()
    while not queue.empty():
        idx, segment = await queue.get()
        segment_audio = await synthesize_with_retry(
            segment,
            voice,
            rate,
            pitch,
            idx,
            len(segments),
        )
        if idx > 1:
            segment_audio = strip_id3v2_header(segment_audio)
        merged_audio.write(segment_audio)
        queue.task_done()

    return merged_audio.getvalue()


def split_text_for_queue(text):
    """Split long text into a queue along semantic boundaries to avoid oversized requests."""
    if TTS_SEGMENT_MAX_LENGTH <= 0 or len(text) <= TTS_SEGMENT_MAX_LENGTH:
        return [text]

    boundary_chars = ("\n", "。", "！", "？", ".", "!", "?", "；", ";", "，", ",", " ")
    segments = []
    start = 0
    total_len = len(text)

    while start < total_len:
        end = min(start + TTS_SEGMENT_MAX_LENGTH, total_len)
        split = end

        if end < total_len:
            best = -1
            for ch in boundary_chars:
                pos = text.rfind(ch, start, end)
                if pos > best:
                    best = pos
            if best >= start:
                split = best + 1

        if split <= start:
            split = end

        segment = text[start:split].strip()
        if segment:
            segments.append(segment)
        start = split

    return segments


async def synthesize_with_retry(text, voice, rate, pitch, segment_index, total_segments):
    """Synthesize a single segment with exponential backoff retries."""
    for attempt in range(1, TTS_RETRY_MAX_ATTEMPTS + 1):
        try:
            return await synthesize_once(text, voice, rate, pitch)
        except Exception as e:
            if attempt >= TTS_RETRY_MAX_ATTEMPTS:
                raise RuntimeError(
                    f"Segment {segment_index}/{total_segments} failed after {TTS_RETRY_MAX_ATTEMPTS} attempts: {e}"
                ) from e

            delay = min(
                TTS_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
                TTS_RETRY_MAX_DELAY_SECONDS,
            )
            if TTS_RETRY_JITTER_SECONDS > 0:
                delay += random.uniform(0, TTS_RETRY_JITTER_SECONDS)

            print(
                f"Segment {segment_index}/{total_segments} failed on attempt {attempt}; "
                f"retrying in {delay:.2f}s: {e}"
            )
            await asyncio.sleep(delay)


async def synthesize_once(text, voice, rate, pitch):
    """Call Edge TTS for a single text segment."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])
    return buffer.getvalue()


def strip_id3v2_header(audio_data):
    """Remove the ID3v2 header from segmented MP3 data to avoid duplicate headers after concatenation."""
    if len(audio_data) < 10 or audio_data[:3] != b"ID3":
        return audio_data

    tag_size = (
        ((audio_data[6] & 0x7F) << 21)
        | ((audio_data[7] & 0x7F) << 14)
        | ((audio_data[8] & 0x7F) << 7)
        | (audio_data[9] & 0x7F)
    )
    header_end = 10 + tag_size
    if header_end >= len(audio_data):
        return audio_data
    return audio_data[header_end:]


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)

    print("Text-to-speech service started")
    print(f"Access URL: http://localhost:{port}")
    if MAX_TEXT_LENGTH <= 0:
        print("Text length limit: unlimited")
    else:
        print(f"Text length limit: {MAX_TEXT_LENGTH} characters")
    if MAX_REQUESTS_PER_HOUR <= 0:
        print("Request rate limit: unlimited")
    else:
        print(f"Request rate limit: {MAX_REQUESTS_PER_HOUR} requests per hour")
    if TTS_SEGMENT_MAX_LENGTH <= 0:
        print("Segmented synthesis: disabled")
    else:
        print(f"Segmented synthesis: up to {TTS_SEGMENT_MAX_LENGTH} characters per segment")
    if MAX_SEGMENTS_PER_REQUEST <= 0:
        print("Segment count limit: unlimited")
    else:
        print(f"Segment count limit: {MAX_SEGMENTS_PER_REQUEST}")
    print(
        "Automatic retry: "
        f"up to {TTS_RETRY_MAX_ATTEMPTS} attempts, "
        f"base backoff {TTS_RETRY_BASE_DELAY_SECONDS}s, "
        f"max backoff {TTS_RETRY_MAX_DELAY_SECONDS}s, "
        f"jitter {TTS_RETRY_JITTER_SECONDS}s"
    )
    print("Press Ctrl+C to stop the service")
    app.run(host="0.0.0.0", port=port, debug=False)
