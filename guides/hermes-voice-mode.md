---
title: Use Voice Mode with Hermes
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [guide, voice, hermes, tts, stt, accessibility]
sources: [https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes]
confidence: high
---

# Use Voice Mode with Hermes

**Source:** [Hermes Agent Docs – Use Voice Mode](https://hermes-agent.nousresearch.com/docs/guides/use-voice-mode-with-hermes)

## Three Voice Experiences

| Mode | Best for | Platform |
|------|----------|----------|
| Interactive microphone loop | Personal hands-free (coding, research) | CLI |
| Voice replies in chat | Spoken responses alongside text | Telegram, Discord |
| Live voice channel bot | Group/personal live conversation | Discord voice channels |

## Step 1: Install Extras

```bash
cd ~/.hermes/hermes-agent
uv pip install -e ".[voice]"       # CLI mic + playback
uv pip install -e ".[messaging]"   # Telegram/Discord
uv pip install -e ".[tts-premium]" # ElevenLabs
uv pip install -e ".[all]"         # everything
```

## Step 2: System Dependencies

| Package | Role |
|---------|------|
| `portaudio` | Microphone input/playback (CLI) |
| `ffmpeg` | Audio conversion |
| `opus` | Discord voice codec |
| `espeak-ng` | Phonemizer for NeuTTS |

## Step 3: Configure

```yaml
voice:
  record_key: "ctrl+b"
  max_recording_seconds: 120
  auto_tts: false
  beep_enabled: true
  silence_threshold: 200
  silence_duration: 3.0

stt:
  provider: "local"          # local | groq | openai

tts:
  provider: "edge"           # edge | neutts | elevenlabs | mistral
  edge:
    voice: "en-US-AriaNeural"
```

## CLI Voice Mode

```bash
hermes        # start
/voice on     # enable voice
```

- **Record key:** Ctrl+B (default)
- **Workflow:** Press key → speak → silence detection stops → Hermes responds

### Commands
```
/voice          # toggle
/voice on/off
/voice tts      # speak every reply
/voice status
```

### Tuning
| Parameter | What it does |
|-----------|-------------|
| `silence_threshold` | Higher = less sensitive (e.g. 250) |
| `silence_duration` | Increase to 4.0 if you pause often |
| `record_key` | e.g. "ctrl+space" |

## Voice Replies in Telegram/Discord

```bash
hermes gateway     # start gateway
```

Then in chat: `/voice on` (speak only when user sent voice) or `/voice tts` (speak every reply).

### Modes
| Mode | Meaning |
|------|---------|
| `off` | Text only |
| `voice_only` | Speak only when user sent voice |
| `all` | Speak every reply |

## Provider Recommendations

| Service | Type | Notes |
|---------|------|-------|
| `local` | STT | Best default: privacy, free |
| `groq` | STT | Very fast cloud transcription |
| `edge` | TTS | Free, good for most |
| `neutts` | TTS | Free, local/on-device |
| `elevenlabs` | TTS | Best quality |
| `mistral` | TTS | Multilingual, native Opus |

See [[hermes-soul]], [[hermes-gateway-internals]], [[hermes-build-plugin]].
