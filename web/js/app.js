// ===== Predefined voice list =====
const VOICES = {
    'ja-JP': {
        label: 'Japanese',
        voices: [
            { name: 'ja-JP-KeitaNeural', label: 'Keita', gender: 'Male' },
            { name: 'ja-JP-NanamiNeural', label: 'Nanami', gender: 'Female' },
        ]
    },
    'zh-CN': {
        label: 'Chinese (Mandarin)',
        voices: [
            { name: 'zh-CN-XiaoxiaoNeural', label: 'Xiaoxiao', gender: 'Female' },
            { name: 'zh-CN-YunxiNeural', label: 'Yunxi', gender: 'Male' },
            { name: 'zh-CN-XiaoyiNeural', label: 'Xiaoyi', gender: 'Female' },
            { name: 'zh-CN-YunjianNeural', label: 'Yunjian', gender: 'Male' },
        ]
    },
    'en-US': {
        label: 'English (US)',
        voices: [
            { name: 'en-US-JennyNeural', label: 'Jenny', gender: 'Female' },
            { name: 'en-US-GuyNeural', label: 'Guy', gender: 'Male' },
        ]
    },
    'en-GB': {
        label: 'English (UK)',
        voices: [
            { name: 'en-GB-SoniaNeural', label: 'Sonia', gender: 'Female' },
            { name: 'en-GB-RyanNeural', label: 'Ryan', gender: 'Male' },
        ]
    },
    'ko-KR': {
        label: 'Korean',
        voices: [
            { name: 'ko-KR-SunHiNeural', label: 'SunHi', gender: 'Female' },
            { name: 'ko-KR-InJoonNeural', label: 'InJoon', gender: 'Male' },
        ]
    }
};

// ===== Edge TTS backend API =====
const TTS_API_URL = '/api/tts';

// ===== Global state =====
let currentAudioBlob = null;
let audioPlayer = null;
let isPlaying = false;
let currentEngine = null; // 'edge' or 'webSpeech'

// ===== Page initialization =====
document.addEventListener('DOMContentLoaded', function () {
    audioPlayer = document.getElementById('audioPlayer');

    initLanguageSelect();
    initVoiceSelect();
    initSliders();
    initTextarea();

    audioPlayer.addEventListener('ended', function () {
        isPlaying = false;
        document.getElementById('playBtn').querySelector('.btn-text').textContent = 'Play';
    });
    audioPlayer.addEventListener('play', function () {
        isPlaying = true;
        document.getElementById('playBtn').querySelector('.btn-text').textContent = 'Pause';
    });
    audioPlayer.addEventListener('pause', function () {
        isPlaying = false;
        document.getElementById('playBtn').querySelector('.btn-text').textContent = 'Play';
    });
});

// ===== UI initialization =====
function initLanguageSelect() {
    const langSelect = document.getElementById('langSelect');
    for (const [code, lang] of Object.entries(VOICES)) {
        const option = document.createElement('option');
        option.value = code;
        option.textContent = lang.label;
        langSelect.appendChild(option);
    }
    langSelect.addEventListener('change', initVoiceSelect);
}

function initVoiceSelect() {
    const langCode = document.getElementById('langSelect').value;
    const voiceSelect = document.getElementById('voiceSelect');
    voiceSelect.innerHTML = '';
    const voices = VOICES[langCode].voices;
    for (const voice of voices) {
        const option = document.createElement('option');
        option.value = voice.name;
        option.textContent = `${voice.label} (${voice.gender})`;
        voiceSelect.appendChild(option);
    }
}

function initSliders() {
    const rateRange = document.getElementById('rateRange');
    const pitchRange = document.getElementById('pitchRange');
    const rateValue = document.getElementById('rateValue');
    const pitchValue = document.getElementById('pitchValue');

    rateRange.addEventListener('input', function () {
        rateValue.textContent = parseFloat(this.value).toFixed(1) + 'x';
    });
    pitchRange.addEventListener('input', function () {
        const val = parseInt(this.value);
        pitchValue.textContent = (val >= 0 ? '+' : '') + val + '%';
    });
}

function initTextarea() {
    const textarea = document.getElementById('textInput');
    const charCount = document.getElementById('charCount');
    charCount.textContent = textarea.value.length;
    textarea.addEventListener('input', function () {
        charCount.textContent = this.value.length;
    });
}

// ===== State control =====
function showLoading() {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('error').style.display = 'none';
    document.getElementById('synthesizeBtn').disabled = true;
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('synthesizeBtn').disabled = false;
}

function showError(message) {
    const el = document.getElementById('error');
    el.textContent = message;
    el.style.display = 'block';
}

function showEngineNotice(engine) {
    const el = document.getElementById('engineNotice');
    if (engine === 'edge') {
        el.textContent = 'Current engine: Microsoft Edge TTS';
    } else {
        el.textContent = 'Current engine: Browser built-in speech engine (Edge TTS unavailable, switched automatically)';
    }
    el.style.display = 'block';
}

function enablePlaybackButtons() {
    document.getElementById('playBtn').disabled = false;
    document.getElementById('stopBtn').disabled = false;
    document.getElementById('downloadBtn').disabled = false;
}

function disablePlaybackButtons() {
    document.getElementById('playBtn').disabled = true;
    document.getElementById('stopBtn').disabled = true;
    document.getElementById('downloadBtn').disabled = true;
}

// ===== Edge TTS backend call =====
async function callEdgeTTS(text, voice, rate, pitch) {
    // Convert slider values to the format expected by edge-tts.
    const ratePercent = Math.round((rate - 1) * 100);
    const rateStr = (ratePercent >= 0 ? '+' : '') + ratePercent + '%';
    const pitchStr = (pitch >= 0 ? '+' : '') + pitch + 'Hz';

    const response = await fetch(TTS_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: text,
            voice: voice,
            rate: rateStr,
            pitch: pitchStr
        })
    });

    if (!response.ok) {
        let message = 'Speech synthesis request failed';
        try {
            const err = await response.json();
            message = err.error || message;
        } catch (e) { /* ignore */ }
        throw new Error(message);
    }

    const blob = await response.blob();
    if (blob.size === 0) {
        throw new Error('No audio data received');
    }
    return blob;
}

// ===== Web Speech API fallback =====
function synthesizeWithWebSpeech(text, voice, rate, pitch) {
    return new Promise(function (resolve, reject) {
        if (!('speechSynthesis' in window)) {
            reject(new Error('Your browser does not support speech synthesis'));
            return;
        }

        // Web Speech API does not produce downloadable audio and only supports live playback.
        const utterance = new SpeechSynthesisUtterance(text);

        // Try to match a browser voice.
        const voices = speechSynthesis.getVoices();
        const langCode = document.getElementById('langSelect').value;
        const matchedVoice = voices.find(function (v) {
            return v.lang.startsWith(langCode);
        });
        if (matchedVoice) {
            utterance.voice = matchedVoice;
        }
        utterance.lang = langCode;
        utterance.rate = rate;
        utterance.pitch = 1 + pitch / 100; // Convert to the 0-2 range.

        utterance.onend = function () {
            resolve(null); // Web Speech does not return a blob.
        };
        utterance.onerror = function (e) {
            reject(new Error('Speech synthesis failed: ' + e.error));
        };

        speechSynthesis.speak(utterance);
        resolve('webSpeech'); // Return a marker immediately.
    });
}

// ===== Main synthesis flow =====
async function synthesize() {
    const text = document.getElementById('textInput').value.trim();
    if (!text) {
        showError('Please enter the text you want to convert');
        return;
    }

    const voice = document.getElementById('voiceSelect').value;
    const rate = parseFloat(document.getElementById('rateRange').value);
    const pitch = parseInt(document.getElementById('pitchRange').value);

    showLoading();
    document.getElementById('error').style.display = 'none';
    document.getElementById('engineNotice').style.display = 'none';

    try {
        // Try Edge TTS first.
        const blob = await callEdgeTTS(text, voice, rate, pitch);
        currentAudioBlob = blob;
        currentEngine = 'edge';
        showEngineNotice('edge');
        playAudioBlob(blob);
        enablePlaybackButtons();

        // Show the audio section.
        document.getElementById('audioSection').style.display = 'block';
    } catch (edgeError) {
        console.warn('Edge TTS backend call failed, switching to Web Speech API:', edgeError);

        try {
            // Fallback: Web Speech API
            currentAudioBlob = null;
            currentEngine = 'webSpeech';
            showEngineNotice('webSpeech');

            const result = await synthesizeWithWebSpeech(text, voice, rate, pitch);
            if (result === 'webSpeech') {
                // Web Speech is now playing.
                document.getElementById('stopBtn').disabled = false;
                document.getElementById('downloadBtn').disabled = true;
                document.getElementById('playBtn').disabled = true;
                document.getElementById('audioSection').style.display = 'none';
            }
        } catch (webError) {
            showError('Speech synthesis failed. Make sure the backend is running with python server.py. The browser built-in speech engine is also unavailable. Please try Chrome or Edge.');
        }
    } finally {
        hideLoading();
    }
}

// ===== Audio playback =====
function playAudioBlob(blob) {
    const url = URL.createObjectURL(blob);
    audioPlayer.src = url;
    audioPlayer.play();
    isPlaying = true;
}

function togglePlay() {
    if (!audioPlayer) return;

    if (currentEngine === 'webSpeech') {
        if (speechSynthesis.paused) {
            speechSynthesis.resume();
        } else if (speechSynthesis.speaking) {
            speechSynthesis.pause();
        }
        return;
    }

    if (isPlaying) {
        audioPlayer.pause();
    } else {
        audioPlayer.play();
    }
}

function stopAudio() {
    if (currentEngine === 'webSpeech') {
        speechSynthesis.cancel();
        return;
    }

    if (audioPlayer) {
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
        isPlaying = false;
        document.getElementById('playBtn').querySelector('.btn-text').textContent = 'Play';
    }
}

// ===== Download feature =====
function downloadAudio() {
    if (!currentAudioBlob) {
        showError('No downloadable audio file is available (the browser built-in engine does not support downloads)');
        return;
    }

    const url = URL.createObjectURL(currentAudioBlob);
    const a = document.createElement('a');
    a.href = url;

    // Use the first few characters of the text as the file name.
    const text = document.getElementById('textInput').value.trim();
    const fileName = text.substring(0, 20).replace(/[^\w\u4e00-\u9fff]/g, '_') || 'tts_audio';
    a.download = fileName + '.mp3';

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
