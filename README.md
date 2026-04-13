# 🔊 ReadAloud — E-Book Reader with Edge TTS

A desktop-class web application for reading books aloud using **Microsoft Edge neural voices** — the same
high-quality voices used in Edge browser, but free and without ads.

## Features

| Feature                   | Details                                              |
|---------------------------|------------------------------------------------------|
| 🔊 **Neural TTS**         | 300+ voices via `edge-tts` (Aria, Guy, Jenny, Ryan…) |
| 📖 **Paragraph mode**     | Paragraphs preserved; highlighted during playback    |
| ⏯ **Full controls**       | Play, Pause, Stop, Prev, Next, Rewind, click-to-jump |
| 🌍 **Translation**        | Google Translate (free) for 15 languages             |
| ⚡ **Audio preloading**    | Next paragraph pre-fetched for smooth playback       |
| ⌨️ **Keyboard shortcuts** | Space, ←/→ arrows, R to rewind, Esc to stop          |
| 🌙 **Dark / Light theme** | Toggle anytime                                       |
| 🔡 **Font size**          | 14–32 px slider                                      |
| 🎚 **Speed & Pitch**      | Rate −50%…+100%, Pitch −10…+10 Hz                    |

## Quick Start

### Windows
```
run.bat
```

### Linux / macOS
```bash
chmod +x run.sh
./run.sh
```

### Manual
```bash
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000** in your browser.

## Requirements

- Python 3.12+
- Internet connection (Edge TTS and Google Translate require internet)

## Usage

1. Paste your book/article text in the import screen
2. Optionally enter a title
3. Click **Start Reading**
4. Select your preferred voice from the Settings panel (⚙️)
5. Press **Play** or **Space** to begin

## Keyboard Shortcuts

| Key           | Action                    |
|---------------|---------------------------|
| `Space`       | Play / Pause              |
| `→`           | Next paragraph            |
| `←`           | Previous paragraph        |
| `R`           | Restart current paragraph |
| `Esc`         | Stop                      |

## Voice Recommendations

**English**: `en-US-AriaNeural` (female), `en-US-GuyNeural` (male), `en-GB-RyanNeural` (British male)

**Russian TTS**: Try `ru-RU-SvetlanaNeural` or `ru-RU-DmitryNeural` for Russian-language books.

## Translation Notes

- Uses **Google Translate** via the free `deep-translator` library (no API key needed)
- Limit: ~5000 characters per paragraph (longer paragraphs are split automatically)
- Results are cached per session — no repeated requests for the same paragraph

## Project Structure

```
ebook_reader/
├── app.py               Flask backend
├── templates/
│   └── index.html       Full UI (HTML + CSS + JS)
├── requirements.txt
├── run.bat              Windows launcher
├── run.sh               Linux/Mac launcher
└── README.md
```
