"""Replay logged drawer photos through additional models.

A valid comparison needs the SAME images, not new drawers -- otherwise you are
measuring the drawers as much as the models. Every run kept its photo, so the
existing log can be re-scored against any model without going back to the shop.

Identical prompt for every model (imported from providers, not re-typed), so the
only variable is the model itself. Appends to the same log record, skipping any
model already scored for that photo, so it is safe to re-run.

Usage:  ./venv/bin/python replay.py claude-haiku-4-5 claude-sonnet-5
"""

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path.home() / "binscan"))
import providers  # noqa: E402

import anthropic  # noqa: E402

HOME = pathlib.Path.home() / "binscan"
LOG = HOME / "log.jsonl"
SHOTS = HOME / "shots"

MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
         ".png": "image/png", ".webp": "image/webp"}


def load():
    return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]


def save(rows):
    with LOG.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def score(client, model, img, media, part, loc):
    import base64
    msg = client.messages.create(
        model=model,
        max_tokens=1000,
        system=providers.SYSTEM,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": media,
                                         "data": base64.standard_b64encode(img).decode()}},
            {"type": "text", "text": providers._user_text(part, loc)},
        ]}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    out = providers._parse(text)
    out["provider"] = f"anthropic:{model.replace('claude-', '')}"
    out["model"] = model
    return out


def main(models):
    client = anthropic.Anthropic()
    rows = load()
    added = 0

    for r in rows:
        photo = r.get("photo")
        if not photo:
            continue
        p = SHOTS / photo
        if not p.exists():
            continue
        img = p.read_bytes()
        media = MEDIA.get(p.suffix.lower(), "image/jpeg")
        have = {x.get("model") for x in r.get("results", [])}

        for model in models:
            if model in have:
                continue
            try:
                r.setdefault("results", []).append(
                    score(client, model, img, media,
                          r.get("part") or "unknown part", r.get("location") or ""))
                added += 1
            except Exception as e:
                r.setdefault("results", []).append(
                    {"provider": f"anthropic:{model}", "model": model,
                     "error": str(e)[:200]})
            time.sleep(0.4)

    save(rows)
    print(f"scored {added} new (photo, model) pair(s) across {len(rows)} run(s)\n")

    # ---- comparison, only where ground truth exists ----------------------
    truth = [r for r in rows if r.get("actual") is not None]
    if not truth:
        print("no ground truth recorded yet - nothing to score against")
        return

    models_seen = []
    for r in truth:
        for x in r.get("results", []):
            m = x.get("model") or x.get("provider")
            if m and m not in models_seen:
                models_seen.append(m)

    print(f"{'photo':<10} {'actual':>7}  " + "".join(f"{m[-22:]:<26}" for m in models_seen))
    print("-" * (19 + 26 * len(models_seen)))
    err = {m: [] for m in models_seen}
    for r in truth:
        by = {(x.get("model") or x.get("provider")): x for x in r.get("results", [])}
        line = f"{r['id']:<10} {r['actual']:>7}  "
        for m in models_seen:
            x = by.get(m)
            if not x or x.get("error"):
                line += f"{'-':<26}"
                continue
            c = x.get("count")
            d = abs(float(c) - float(r["actual"])) if isinstance(c, (int, float)) else None
            if d is not None:
                err[m].append(d)
            line += f"{str(c) + ' (' + x.get('confidence','?')[:4] + ') ±' + (f'{d:g}' if d is not None else '?'):<26}"
        print(line)

    print("\nmean absolute error:")
    for m in models_seen:
        e = err[m]
        print(f"  {m:<34} {sum(e)/len(e):.1f}   (n={len(e)})" if e else f"  {m:<34} no data")


if __name__ == "__main__":
    main(sys.argv[1:] or ["claude-haiku-4-5", "claude-sonnet-5"])
