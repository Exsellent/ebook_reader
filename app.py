import asyncio
import tempfile
import os
import threading
import zipfile
import xml.etree.ElementTree as ET
import re
from flask import Flask, render_template, request, jsonify, send_file
import edge_tts
from deep_translator import GoogleTranslator

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB upload limit

# ── helpers ──────────────────────────────────────────────────────────────────

def cleanup_file(path: str, delay: int = 300):
    def _del():
        import time
        time.sleep(delay)
        try:
            os.unlink(path)
        except Exception:
            pass
    threading.Thread(target=_del, daemon=True).start()


def rate_str(value: int) -> str:
    return f"+{value}%" if value >= 0 else f"{value}%"


def pitch_str(value: int) -> str:
    return f"+{value}Hz" if value >= 0 else f"{value}Hz"


def clean_text(text: str) -> str:
    """Normalise whitespace inside a paragraph."""
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ── EPUB parser ───────────────────────────────────────────────────────────────

def parse_epub(file_bytes: bytes) -> dict:
    """Extract title and paragraphs from an EPUB file (bytes)."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("beautifulsoup4 is not installed. Run: pip install beautifulsoup4")

    fd, tmp = tempfile.mkstemp(suffix=".epub")
    try:
        os.write(fd, file_bytes)
        os.close(fd)

        with zipfile.ZipFile(tmp, "r") as z:
            names = z.namelist()

            # --- find OPF manifest via META-INF/container.xml ---
            container_xml = None
            for name in names:
                if name.endswith("container.xml"):
                    container_xml = z.read(name).decode("utf-8", errors="replace")
                    break

            opf_path = None
            if container_xml:
                root = ET.fromstring(container_xml)
                for el in root.iter():
                    if el.tag.endswith("rootfile"):
                        opf_path = el.get("full-path")
                        break

            # --- read spine order from OPF ---
            spine_ids = []
            manifest  = {}
            title     = ""
            if opf_path:
                opf_xml = z.read(opf_path).decode("utf-8", errors="replace")
                opf = ET.fromstring(opf_xml)

                for el in opf.iter("{http://purl.org/dc/elements/1.1/}title"):
                    title = el.text or ""
                    break

                for el in opf.iter():
                    if el.tag.endswith("item"):
                        item_id   = el.get("id", "")
                        item_href = el.get("href", "")
                        media     = el.get("media-type", "")
                        if "html" in media or item_href.endswith((".html", ".xhtml", ".htm")):
                            manifest[item_id] = item_href

                for el in opf.iter():
                    if el.tag.endswith("itemref"):
                        spine_ids.append(el.get("idref", ""))

            opf_dir = os.path.dirname(opf_path) if opf_path else ""

            def full_path(href):
                # handle relative paths like ../Text/chapter1.xhtml
                if opf_dir:
                    base = opf_dir.rstrip("/")
                    joined = base + "/" + href
                    # resolve ../ segments
                    parts = []
                    for seg in joined.split("/"):
                        if seg == "..":
                            if parts:
                                parts.pop()
                        elif seg and seg != ".":
                            parts.append(seg)
                    return "/".join(parts)
                return href

            paragraphs = []
            visited    = set()

            def extract_html(html_bytes):
                soup = BeautifulSoup(html_bytes, "html.parser")
                for tag in soup(["script", "style", "nav", "aside", "figure", "figcaption"]):
                    tag.decompose()
                for el in soup.find_all(["p", "div"]):
                    # skip divs that only contain block children (layout wrappers)
                    if el.name == "div" and el.find(["p", "div"]):
                        continue
                    txt = clean_text(el.get_text(" ", strip=True))
                    if len(txt) > 25:
                        paragraphs.append(txt)

            if spine_ids and manifest:
                for sid in spine_ids:
                    href = manifest.get(sid)
                    if not href:
                        continue
                    fp = full_path(href)
                    if fp in visited:
                        continue
                    visited.add(fp)
                    try:
                        extract_html(z.read(fp))
                    except KeyError:
                        try:
                            extract_html(z.read(href))
                        except KeyError:
                            pass
            else:
                # fallback: all HTML files alphabetically
                for name in sorted(names):
                    if name.endswith((".html", ".xhtml", ".htm")) and name not in visited:
                        visited.add(name)
                        extract_html(z.read(name))

    finally:
        os.unlink(tmp)

    # deduplicate consecutive identical paragraphs
    deduped = []
    for p in paragraphs:
        if not deduped or p != deduped[-1]:
            deduped.append(p)

    return {"title": title, "paragraphs": deduped}


# ── FB2 parser ────────────────────────────────────────────────────────────────

def parse_fb2(file_bytes: bytes) -> dict:
    """Extract title and paragraphs from an FB2 file (bytes)."""
    # Detect encoding from XML declaration
    raw = file_bytes
    encoding = "utf-8"
    m = re.search(rb'encoding=["\']([^"\']+)["\']', raw[:200])
    if m:
        encoding = m.group(1).decode("ascii", errors="replace")

    text = raw.decode(encoding, errors="replace")

    # Strip all namespace declarations so ElementTree tags are plain
    text = re.sub(r'\sxmlns(?::\w+)?="[^"]+"', "", text)
    # Also strip namespace prefixes from tags
    text = re.sub(r'<(/?)[\w]+:([\w\-]+)', r'<\1\2', text)

    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise RuntimeError(f"FB2 parse error: {e}")

    # --- title ---
    title = ""
    for el in root.iter("book-title"):
        t = (el.text or "").strip()
        if t:
            title = t
            break

    # --- collect paragraphs ---
    paragraphs = []

    def node_text(el) -> str:
        parts = []
        if el.text:
            parts.append(el.text)
        for child in el:
            parts.append(node_text(child))
            if child.tail:
                parts.append(child.tail)
        return " ".join(p for p in parts if p)

    for body in root.iter("body"):
        if body.get("name") in ("notes", "footnotes", "comments", "note"):
            continue
        for el in body.iter():
            tag = el.tag.lower()
            if tag == "p":
                txt = clean_text(node_text(el))
                if len(txt) > 15:
                    paragraphs.append(txt)
            elif tag in ("title", "subtitle"):
                txt = clean_text(node_text(el))
                if txt and len(txt) < 300:
                    paragraphs.append(f"\u2014 {txt} \u2014")

    return {"title": title, "paragraphs": paragraphs}


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/voices")
def get_voices():
    async def _fetch():
        return await edge_tts.list_voices()

    voices = asyncio.run(_fetch())
    grouped: dict[str, list] = {}
    for v in sorted(voices, key=lambda x: x["Locale"]):
        locale = v["Locale"]
        grouped.setdefault(locale, []).append({
            "name":    v["ShortName"],
            "display": v["FriendlyName"],
            "gender":  v["Gender"],
            "locale":  locale,
        })
    return jsonify(grouped)


@app.route("/api/upload", methods=["POST"])
def upload():
    """Parse EPUB or FB2 and return {title, paragraphs}."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f     = request.files["file"]
    fname = (f.filename or "").lower()
    data  = f.read()

    try:
        if fname.endswith(".epub"):
            result = parse_epub(data)
        elif fname.endswith(".fb2"):
            result = parse_fb2(data)
        else:
            return jsonify({"error": "Unsupported format. Please use .epub or .fb2"}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    if not result["paragraphs"]:
        return jsonify({"error": "No readable text found in the file."}), 400

    return jsonify(result)


@app.route("/api/tts", methods=["POST"])
def tts():
    data  = request.get_json(force=True)
    text  = (data.get("text")  or "").strip()
    voice = data.get("voice",  "en-US-AriaNeural")
    rate  = rate_str(int(data.get("rate",  0)))
    pitch = pitch_str(int(data.get("pitch", 0)))

    if not text:
        return jsonify({"error": "No text"}), 400

    async def _gen():
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        await comm.save(path)
        return path

    try:
        path = asyncio.run(_gen())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    cleanup_file(path, delay=600)
    return send_file(path, mimetype="audio/mpeg")


@app.route("/api/translate", methods=["POST"])
def translate():
    data   = request.get_json(force=True)
    text   = (data.get("text")   or "").strip()
    source = data.get("source",  "auto")
    target = data.get("target",  "ru")

    if not text:
        return jsonify({"translated": ""})

    MAX = 4500

    def _translate_chunk(chunk: str) -> str:
        return GoogleTranslator(source=source, target=target).translate(chunk) or ""

    try:
        if len(text) <= MAX:
            return jsonify({"translated": _translate_chunk(text)})

        chunks, buf = [], ""
        for sentence in text.split(". "):
            candidate = buf + sentence + ". "
            if len(candidate) > MAX and buf:
                chunks.append(buf.strip())
                buf = sentence + ". "
            else:
                buf = candidate
        if buf:
            chunks.append(buf.strip())

        translated = " ".join(_translate_chunk(c) for c in chunks if c)
        return jsonify({"translated": translated})

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import webbrowser

    def _open():
        import time
        time.sleep(1.5)
        webbrowser.open("http://localhost:5000")

    threading.Thread(target=_open, daemon=True).start()
    print("\n🔊  ReadAloud starting → http://localhost:5000\n")
    app.run(debug=False, port=5000, host="0.0.0.0")
