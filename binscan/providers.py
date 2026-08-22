"""Vision providers for binscan.

Three backends behind one interface, because the point is to MEASURE which is
good enough rather than assume:

  ollama     local, free, private, no network. qwen2.5vl:7b on the M4.
  anthropic  Claude vision. Best accuracy, pay-as-you-go, ~$0.003-0.015/photo.
  openai     GPT vision, if credits exist there.

All three take the same prompt and must return the same JSON shape, so results
are directly comparable on the same photograph. Each is optional: a provider
with no key configured simply reports itself unavailable rather than breaking
the app.

Two jobs share that one call path:

  estimate()  how full is this drawer      - vision is mediocre at it, measured
  identify()  what TEXT is visible in it   - vision is good at it

identify() deliberately does NOT ask the model which part this is. It asks what
is PRINTED on the tag, and the matching against the catalogue happens in Python
where it can be audited. A model asked to pick from a candidate list will always
pick something; a model asked to read a number either reads it or does not.
"""

import base64
import json
import os
import re

import httpx

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5vl:7b")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o")

ESTIMATE_SYSTEM = """You estimate how full a parts drawer is from a photograph.

You are NOT identifying the part - the drawer address already determines that,
and you will be told what it holds. Your only job is quantity.

Rules that matter:
- If parts are HEAPED or overlapping you can only see the top layer. Say so and
  use LOW confidence. A pile of 200 small parts looks much like a pile of 150.
- Single layer, spread out, or countable taped strips: MEDIUM or HIGH confidence.
- Taped/bandolier strips: count strips and multiply. Show the arithmetic.
- Empty or nearly empty is the most useful and most reliable answer you can give.
- Never invent precision. A confident "about 50" beats a fake "53".

Respond with ONLY this JSON object, no prose and no code fences:
{"bucket":"empty|few|some|many|full","count":0,"confidence":"low|medium|high","reasoning":"one sentence"}"""

IDENTIFY_SYSTEM = """You READ TEXT from a photograph of an open parts drawer.

You are NOT identifying the part and NOT counting. Do not infer what the
fastener is from how it looks. Report only what is legibly WRITTEN, and the
matching happens elsewhere.

Look for, in this order of usefulness:
1. A McMaster-Carr bag tag. Their part numbers look like 91290A326 or 3014T954 -
   digits, a letter, digits. Transcribe it EXACTLY, character for character.
2. Any other printed or handwritten label: a Brady label on the drawer front, a
   marker-written bag, a vendor barcode label.
3. Any text stamped on the parts themselves (a head marking, a grade stamp).

Rules that matter:
- Transcribe, never correct. If it reads 91290A32 with the last digit obscured,
  give "91290A32" and say it was cut off. A plausible completion is worse than
  a short answer, because a wrong part number matches a real and different part.
- If you cannot read a character, use "?" in its place rather than guessing.
- Empty string for anything not present. Absence is a useful, honest answer.
- descriptors is the ONE place you may say what you see rather than read - "M6
  socket head, black oxide" - and it is treated as a weak hint, never as proof.

Respond with ONLY this JSON object, no prose and no code fences:
{"tag":"","labels":[],"markings":[],"descriptors":"","legible":"none|partial|clear","reasoning":"one sentence"}"""


def _user_text(part_name, location):
    return (f"Drawer {location or '(unspecified)'} holds: {part_name}.\n"
            "How full is it?")


def _identify_text(cabinet):
    hint = {"B1": "This cabinet holds METRIC fasteners only.",
            "B2": "This cabinet holds IMPERIAL fasteners only."}.get(cabinet, "")
    return (f"Drawer in cabinet {cabinet or '(unspecified)'}. {hint}\n"
            "What text can you read in this photo?")


def _parse(text):
    """Models wrap JSON in prose or fences no matter how firmly you ask."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"no JSON found in: {text[:200]}")
    d = json.loads(m.group(0))
    return {
        "bucket": str(d.get("bucket", "?")).lower(),
        "count": d.get("count"),
        "confidence": str(d.get("confidence", "low")).lower(),
        "reasoning": d.get("reasoning", ""),
    }


def _strlist(v):
    """Models return a bare string as often as a list, whatever the schema says."""
    if v is None:
        return []
    if isinstance(v, str):
        v = [v]
    return [str(x).strip() for x in v if str(x).strip()]


def _parse_identify(text):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"no JSON found in: {text[:200]}")
    d = json.loads(m.group(0))
    return {
        "tag": str(d.get("tag", "") or "").strip(),
        "labels": _strlist(d.get("labels")),
        "markings": _strlist(d.get("markings")),
        "descriptors": str(d.get("descriptors", "") or "").strip(),
        "legible": str(d.get("legible", "none")).lower(),
        "reasoning": d.get("reasoning", ""),
    }


# ---------------------------------------------------------------- ollama ---
def ollama_available():
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=4)
        names = [m["name"] for m in r.json().get("models", [])]
        return any(n.startswith(OLLAMA_MODEL.split(":")[0]) for n in names)
    except Exception:
        return False


def ollama_raw(img_bytes, media, system, user):
    r = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": system + "\n\n" + user,
            "images": [base64.standard_b64encode(img_bytes).decode()],
            "stream": False,
            "options": {"temperature": 0},
        },
        timeout=180,
    )
    r.raise_for_status()
    return r.json().get("response", "")


# ------------------------------------------------------------- anthropic ---
def anthropic_available():
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()) and \
        "PASTE" not in os.environ.get("ANTHROPIC_API_KEY", "")


def anthropic_raw(img_bytes, media, system, user):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1000,
        system=system,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media,
                                             "data": base64.standard_b64encode(img_bytes).decode()}},
                {"type": "text", "text": user},
            ],
        }],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


# ---------------------------------------------------------------- openai ---
def openai_available():
    return bool(os.environ.get("OPENAI_API_KEY", "").strip()) and \
        "PASTE" not in os.environ.get("OPENAI_API_KEY", "")


def openai_raw(img_bytes, media, system, user):
    key = os.environ["OPENAI_API_KEY"]
    b64 = base64.standard_b64encode(img_bytes).decode()
    r = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": OPENAI_MODEL,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": [
                    {"type": "text", "text": user},
                    {"type": "image_url",
                     "image_url": {"url": f"data:{media};base64,{b64}"}},
                ]},
            ],
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


PROVIDERS = {
    "ollama": (ollama_available, ollama_raw, lambda: OLLAMA_MODEL),
    "anthropic": (anthropic_available, anthropic_raw, lambda: ANTHROPIC_MODEL),
    "openai": (openai_available, openai_raw, lambda: OPENAI_MODEL),
}


def status():
    return [{"name": n, "available": avail(), "model": model()}
            for n, (avail, _run, model) in PROVIDERS.items()]


def _run(provider, img_bytes, media, system, user):
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider}")
    avail, run, model = PROVIDERS[provider]
    if not avail():
        raise RuntimeError(f"{provider} is not configured")
    return run(img_bytes, media, system, user), model()


def estimate(provider, img_bytes, media, part_name, location):
    raw, model = _run(provider, img_bytes, media,
                      ESTIMATE_SYSTEM, _user_text(part_name, location))
    out = _parse(raw)
    out["provider"] = provider
    out["model"] = model
    return out


def identify(provider, img_bytes, media, cabinet):
    """Read whatever text is legible. Matching happens in app.py, not here."""
    raw, model = _run(provider, img_bytes, media,
                      IDENTIFY_SYSTEM, _identify_text(cabinet))
    out = _parse_identify(raw)
    out["provider"] = provider
    out["model"] = model
    return out
