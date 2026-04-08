# Online Text-to-Speech Tool

A free online text-to-speech (TTS) tool based on Microsoft Edge TTS speech synthesis technology. It supports multiple languages and voice roles, with online playback and MP3 download.

## Features

- **High-quality voices**: Uses Microsoft Neural TTS technology to generate natural speech close to human voices
- **Multilingual support**: Supports Chinese, English, Japanese, Korean, and more
- **Multiple voice roles**: Each language provides multiple male and female voice options
- **Adjustable parameters**: Freely adjust speaking rate (0.5x - 2.0x) and pitch (-50% to +50%)
- **MP3 download**: Synthesized audio can be downloaded directly as an MP3 file
- **Dual-engine fallback**: Automatically switches to the browser's built-in Web Speech API when Edge TTS is unavailable
- **Responsive design**: Adapts to desktops, tablets, phones, and other devices

## Live Preview

https://text2voice.cc

## Supported Voices

| Language | Voice Name | Role | Gender |
|------|---------|------|------|
| Chinese (Mandarin) | zh-CN-XiaoxiaoNeural | Xiaoxiao | Female |
| Chinese (Mandarin) | zh-CN-YunxiNeural | Yunxi | Male |
| Chinese (Mandarin) | zh-CN-XiaoyiNeural | Xiaoyi | Female |
| Chinese (Mandarin) | zh-CN-YunjianNeural | Yunjian | Male |
| English (US) | en-US-JennyNeural | Jenny | Female |
| English (US) | en-US-GuyNeural | Guy | Male |
| English (UK) | en-GB-SoniaNeural | Sonia | Female |
| English (UK) | en-GB-RyanNeural | Ryan | Male |
| Japanese | ja-JP-NanamiNeural | Nanami | Female |
| Japanese | ja-JP-KeitaNeural | Keita | Male |
| Korean | ko-KR-SunHiNeural | SunHi | Female |
| Korean | ko-KR-InJoonNeural | InJoon | Male |

## Quick Start

### 1. Install Dependencies

```bash
pip install flask edge-tts
```

### 2. Start the Server

```bash
python server.py
```

By default, the app starts at `http://localhost:8000`. You can also specify a port:

```bash
python server.py 3000
```

### 3. Usage

Open `http://localhost:8000` in your browser, enter text, choose a voice, and click "Start Conversion".

## File Structure

```text
web_text2voice/
├── index.html          # Main page
├── about.html          # About page
├── privacy.html        # Privacy policy page
├── server.py           # Flask backend service
├── css/
│   └── style.css       # Stylesheet
├── js/
│   └── app.js          # Frontend logic
└── README.md           # Project documentation
```

## Technical Architecture

```text
Browser (HTML/CSS/JS)
    │
    │  POST /api/tts  {text, voice, rate, pitch}
    ▼
Flask Server (server.py)
    │
    │  WebSocket (edge-tts Python package)
    ▼
Microsoft Edge TTS Service
    │
    │  MP3 audio data
    ▼
Browser playback / download
```

- **Frontend**: HTML5 + CSS3 + vanilla JavaScript, responsible for UI interaction and audio playback
- **Backend**: Flask provides static file serving and the `/api/tts` endpoint
- **Speech synthesis**: Uses the `edge-tts` Python package to call Microsoft Edge TTS services
- **Fallback**: When the backend is unavailable, the frontend automatically switches to the browser's built-in Web Speech API (download is not supported)

## API

### POST /api/tts

Synthesizes speech audio.

**Request Body** (JSON):

```json
{
    "text": "Hello, world",
    "voice": "zh-CN-XiaoxiaoNeural",
    "rate": "+0%",
    "pitch": "+0Hz"
}
```

| Parameter | Type | Description |
|------|------|------|
| text | string | Text content to synthesize (required) |
| voice | string | Voice role name, default is `zh-CN-XiaoxiaoNeural` |
| rate | string | Speaking rate, such as `+0%`, `+50%`, `-25%` |
| pitch | string | Pitch, such as `+0Hz`, `+10Hz`, `-10Hz` |

**Response**: MP3 binary audio data in `audio/mpeg` format.

**Error Response** (JSON):

```json
{
    "error": "Error message"
}
```

## FAQ

### Nothing happens after clicking "Start Conversion"

Make sure you started the backend service with `python server.py` instead of opening `index.html` directly by double-clicking it. Edge TTS requires a backend proxy to call Microsoft's service.

### It says "Switched to the browser's built-in speech engine"

This means the backend service is unavailable or the network cannot access Microsoft's TTS service. In that case, the app automatically falls back to the browser's Web Speech API, but MP3 download is not supported.

### Speech synthesis is slow

Synthesis speed depends on text length and network conditions. For longer text, segmented synthesis is recommended.

## Notes

- This tool uses the public Microsoft Edge TTS interface and is intended only for personal learning and non-commercial use
- Do not use synthesized speech for fraud, impersonation, or other illegal activities
- Service availability depends on the status of Microsoft's services

## References

- [Text-to-Speech Tool](https://my-web-tool-1f793.web.app/)
- [Text-to-Speech AI Tool](text2-voice.vercel.app)
