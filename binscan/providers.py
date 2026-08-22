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

SYSTEM = """You estimate how full a parts drawer is from a photograph.

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


def _user_text(part_name, location):
    return (f"Drawer {location or '(unspecified)'} holds: {part_name}.\n"
            "How full is it?")


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


# ---------------------------------------------------------------- ollama ---
def ollama_available():
    try:
        r = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=4)
        names = [m["name"] for m in r.json().get("models", [])]
        return any(n.startswith(OLLAMA_MODEL.split(":")[0]) for n in names)
    except Exception:
        return False


def ollama_estimate(img_bytes, media, part_name, location):
    r = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": SYSTEM + "\n\n" + _user_text(part_name, location),
            "images": [base64.standard_b64encode(img_bytes).decode()],
            "stream": False,
            "options": {"temperature": 0},
        },
        timeout=180,
    )
    r.raise_for_status()
    return _parse(r.json().get("response", ""))


# ------------------------------------------------------------- anthropic ---
def anthropic_available():
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()) and \
        "PASTE" not in os.environ.get("ANTHROPIC_API_KEY", "")


def anthropic_estimate(img_bytes, media, part_name, location):
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1000,
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media,
                                             "data": base64.standard_b64encode(img_bytes).decode()}},
                {"type": "text", "text": _user_text(part_name, location)},
            ],
        }],
    )
    return _parse("".join(b.text for b in msg.content if getattr(b, "type", "") == "text"))


# ---------------------------------------------------------------- openai ---
def openai_available():
    return bool(os.environ.get("OPENAI_API_KEY", "").strip()) and \
        "PASTE" not in os.environ.get("OPENAI_API_KEY", "")


def openai_estimate(img_bytes, media, part_name, location):
    key = os.environ["OPENAI_API_KEY"]
    b64 = base64.standard_b64encode(img_bytes).decode()
    r = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": OPENAI_MODEL,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": [
                    {"type": "text", "text": _user_text(part_name, location)},
                    {"type": "image_url",
                     "image_url": {"url": f"data:{media};base64,{b64}"}},
                ]},
            ],
        },
        timeout=120,
    )
    r.raise_for_status()
    return _parse(r.json()["choices"][0]["message"]["content"])


PROVIDERS = {
    "ollama": (ollama_available, ollama_estimate, lambda: OLLAMA_MODEL),
    "anthropic": (anthropic_available, anthropic_estimate, lambda: ANTHROPIC_MODEL),
    "openai": (openai_available, openai_estimate, lambda: OPENAI_MODEL),
}


def status():
    return [{"name": n, "available": avail(), "model": model()}
            for n, (avail, _run, model) in PROVIDERS.items()]


def estimate(provider, img_bytes, media, part_name, location):
    if provider not in PROVIDERS:
        raise ValueError(f"unknown provider {provider}")
    avail, run, model = PROVIDERS[provider]
    if not avail():
        raise RuntimeError(f"{provider} is not configured")
    out = run(img_bytes, media, part_name, location)
    out["provider"] = provider
    out["model"] = model()
    return out
