"""Find, verify and attach component datasheets.

Datasheets were being fetched one at a time by hand, and twice the wrong file
nearly got attached to the right part. This is the same shape as
attach_datasheet.py, but it resolves the URL itself and — the important bit —
**proves the PDF is about the part before filing it**.

    itq run scripts/datasheets.py --list
    itq run scripts/datasheets.py --fetch                 # dry run
    itq run scripts/datasheets.py --fetch --commit
    itq run scripts/datasheets.py --from-dir /tmp/ds --commit

Three sources, tried in order:

1. **A manufacturer URL pattern** for vendors that publish predictably (TI,
   Vishay, Bosch, Microchip, Pololu). Free, no key, ~5/8 hit rate measured.
2. **The Mouser Search API**, if a key is configured. Given an MPN it returns a
   datasheet URL *and* an image URL. Key-only auth, no OAuth, instant access.
   Sign-up is NOT on the api-hub landing page: it is
   `mouser.com/en/MyMouser/MouserSearchApplication.aspx`, reachable only via
   Search API -> "Learn More" -> "Sign Up for Search API".
   Limits: 30 calls/min, 1,000/day, 50 results per call. Throttled below.
3. **`--from-dir`**, a directory of PDFs already downloaded by hand or by a
   driven browser. This is the escape hatch for vendors that fingerprint
   scripted clients (st.com kills curl's HTTP/2 stream outright), and it is why
   this tool is useful before anyone has an API key.

**The key is NEVER stored in this repo.** It is read from
`~/.config/shop-inventory/keys.json`, outside the tree entirely, because this
repo is public and a gitignore is one `git add -f` away from failing.

    {"mouser_api_key": "..."}

## Why the marker check exists

A PDF that is a real PDF can still be the wrong document — a family datasheet
for a different series, or a vendor's "product not found" page rendered to PDF.
`attach_datasheet.py` checks magic bytes, which catches HTML-as-PDF but not
wrong-part-as-PDF. This also greps the decompressed text for the part number
and refuses if absent. A datasheet filed against the wrong part is worse than
no datasheet, because it reads as authoritative.
"""
import argparse, json, os, re, sys, tempfile, time, urllib.request, urllib.error, zlib
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()

from django.core.files import File
from django.contrib.auth import get_user_model
from common.models import Attachment
from part.models import Part, PartCategory

KEYS = os.path.expanduser("~/.config/shop-inventory/keys.json")
UA = {"User-Agent": "Mozilla/5.0"}

# Vendors that publish at a predictable path. Measured 2026-08-21: these five
# served real PDFs unauthenticated; onsemi, Diodes Inc, Toshiba, SMC and Mouser's
# CDN all refused, so they are deliberately absent rather than optimistically
# listed. {} is the lowercased MPN.
PATTERNS = [
    "https://www.ti.com/lit/ds/symlink/{}.pdf",
    "https://www.vishay.com/docs/{}.pdf",
]
# Exact overrides win over patterns: family sheets, odd filenames, mirrors.
EXACT = {
    "BME280":  "https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf",
    "VL53L1X": "https://www.pololu.com/file/0J1506/vl53l1x.pdf",
    "VL53L4CD": "https://www.pololu.com/file/0J1918/vl53l4cd.pdf",
}

BAD = re.compile(r'["″\']|\bmm\b|\bawg\b|\bpcs?\b|\bpack\b|\bkit\b|\bassort', re.I)
MPN_RE = re.compile(
    r"\b(?=[A-Z0-9][A-Z0-9\-]{3,})(?=[A-Z0-9\-]*[0-9])(?=[A-Z0-9\-]*[A-Z])"
    r"[A-Z][A-Z0-9]*[0-9][A-Z0-9\-]*\b")


def load_cfg():
    try:
        with open(KEYS) as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"  ! {KEYS} unreadable: {type(e).__name__}")
        return {}


def check_ip(cfg):
    """Warn if our egress IP has drifted from the one registered with Mouser.

    The Search API application form REQUIRES an IP literal for the calling host
    and will not take a hostname, so a DDNS setup cannot be registered honestly
    — you pin whatever the address is that day. Both sites here are dynamic.

    If Mouser enforces that IP, a lease change turns every call into an auth
    failure, which reads as "the API is broken" rather than "the address moved".
    Recording the registered value and comparing costs one HTTP call and makes
    that failure self-diagnosing. Store it as "mouser_registered_ips": [...]
    alongside the key.
    """
    want = cfg.get("mouser_registered_ips")
    if not want:
        return
    try:
        now = urllib.request.urlopen("https://api.ipify.org", timeout=10).read().decode().strip()
    except Exception:
        print("  ! could not determine egress IP — skipping drift check")
        return
    if now not in want:
        print(f"  !! EGRESS IP DRIFTED: now {now}, registered {', '.join(want)}")
        print("     If Mouser calls start failing auth, this is why — both sites")
        print("     are dynamic. Update the application or the config, not the code.")


def candidates():
    """Parts that could plausibly have a datasheet and do not have one.

    Excludes passives and kits on purpose. 128 of the Electronics parts are
    capacitors, resistors and LEDs out of assortment kits: no manufacturer, no
    datasheet, and their useful facts are already recorded. Queueing them would
    manufacture failures, not information.
    """
    have = set(Attachment.objects.filter(model_type="part")
               .values_list("model_id", flat=True))
    try:
        root = PartCategory.objects.get(name="Electronics")
        pool = Part.objects.filter(category__in=root.get_descendants(include_self=True))
    except PartCategory.DoesNotExist:
        pool = Part.objects.all()
    skip_cats = {"Capacitors", "Resistors", "LEDs"}
    out = []
    for p in pool.select_related("category"):
        if p.pk in have or (p.category and p.category.name in skip_cats):
            continue
        head = p.name.split(",")[0]
        if BAD.search(head):
            continue
        m = MPN_RE.search(head.upper())
        if m and len(m.group()) >= 4:
            out.append((p, m.group()))
    return out


def get(url, timeout=45):
    try:
        return urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=timeout).read()
    except Exception:
        return None


def pdf_text(data, cap=600_000):
    """Rough text extraction — enough to look for a part number."""
    out = b""
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        try:
            out += zlib.decompress(m.group(1))
        except Exception:
            out += m.group(1)
        if len(out) > cap:
            break
    return out.decode("latin-1", "ignore")


def readable(txt):
    """How much of this looks like actual prose rather than decompressed binary?

    pdf_text() inflates every stream, and most of a datasheet's bytes are fonts,
    images and colour profiles — not text. Counting ASCII words is the cheapest
    way to tell "I read the document" from "I read its JPEGs".
    """
    return len(re.findall(r"[A-Za-z]{4,}", txt))


def verify(data, mpn):
    """Is this a real PDF, and is it about this part?

    THREE outcomes, not two. An earlier version had only accept/reject, and it
    rejected the correct HUBER+SUHNER RG178 sheet — not because the document was
    wrong but because its text is encoded in a way this crude extractor cannot
    read, so the marker could not be found. **A check that cannot distinguish
    "the answer is no" from "I could not look" produces false negatives that are
    indistinguishable from true ones**, which is worse than not checking, because
    it is trusted.

    Returns (state, reason) where state is "ok", "no" or "unknown".
    """
    if not data or data[:4] != b"%PDF":
        return "no", "not a PDF"
    stem = re.sub(r"[^A-Z0-9]", "", mpn.upper())[:6]
    if len(stem) < 4:
        return "unknown", "MPN too short to be a distinctive marker"
    txt = pdf_text(data)
    words = readable(txt)
    if words < 200:
        return "unknown", f"text not extractable ({words} words) — cannot verify"
    if stem in re.sub(r"[^A-Z0-9]", "", txt.upper()):
        return "ok", f"marker {stem} found in {words} words"
    return "no", f"marker {stem} ABSENT in {words} readable words — wrong document"


def mouser_lookup(mpn, key):
    """Resolve a datasheet URL from an MPN via the Mouser Search API.

    Two things learned the hard way on 2026-08-21:

    **Use the keyword endpoint, not partnumber.** `search/partnumber` happily
    returns 50 hits for BC337 with `DataSheetUrl` empty on every one;
    `search/keyword` returns fewer but populated. Same catalogue, different
    field completeness, and the partnumber endpoint gives no hint that it is
    withholding anything.

    **Never take the first result.** `DataSheetUrl` is blank on most rows even
    in a good response — for BC337 the onsemi entry is empty and the NXP one
    carries the sheet. Scan them all, and prefer an exact MPN match so a
    near-miss part number does not supply the document.
    """
    wait = _MOUSER_GAP - (time.monotonic() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.monotonic()

    body = json.dumps({"SearchByKeywordRequest": {
        "keyword": mpn, "records": 50, "startingRecord": 0}}).encode()
    req = urllib.request.Request(
        f"https://api.mouser.com/api/v1/search/keyword?apiKey={key}",
        data=body, headers={**UA, "Content-Type": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    except urllib.error.HTTPError as e:
        return None, f"mouser HTTP {e.code}"
    except Exception as e:
        return None, f"mouser {type(e).__name__}"

    errs = [e.get("Message") for e in (d.get("Errors") or []) if e.get("Message")]
    if errs:
        return None, f"mouser error: {errs[0]}"

    parts = (d.get("SearchResults") or {}).get("Parts") or []
    if not parts:
        return None, "mouser: no results"

    key_norm = re.sub(r"[^A-Z0-9]", "", mpn.upper())
    exact, loose = [], []
    for pt in parts:
        u = (pt.get("DataSheetUrl") or "").strip()
        if not u:
            continue
        got = re.sub(r"[^A-Z0-9]", "", (pt.get("ManufacturerPartNumber") or "").upper())
        (exact if got == key_norm else loose).append((u, pt.get("Manufacturer") or "?"))
    for pool, how in ((exact, "exact"), (loose, "near")):
        if pool:
            u, mfr = pool[0]
            return u, f"mouser/{how}:{mfr}"
    return None, f"mouser: {len(parts)} hits, none carry a datasheet URL"


def sources(mpn, key):
    if mpn.upper() in EXACT:
        yield EXACT[mpn.upper()], "exact"
    for pat in PATTERNS:
        yield pat.format(mpn.lower()), "pattern"
    if key:
        u, why = mouser_lookup(mpn, key)
        yield (u, why) if u else (None, why)


def attach(part, mpn, data, comment, who):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as t:
        t.write(data)
        tmp = t.name
    try:
        with open(tmp, "rb") as fh:
            Attachment.objects.create(
                model_type="part", model_id=part.pk,
                attachment=File(fh, name=f"{mpn}.pdf"),
                comment=comment, upload_user=who)
    finally:
        os.unlink(tmp)
    return Attachment.objects.filter(
        model_type="part", model_id=part.pk,
        attachment__endswith=f"{mpn}.pdf").exists()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="show candidates and exit")
    ap.add_argument("--urls", action="store_true",
                    help="resolve and print MPN<TAB>URL, for a browser to fetch")
    ap.add_argument("--fetch", action="store_true", help="try to resolve and download")
    ap.add_argument("--from-dir", help="attach PDFs already downloaded; matched by MPN in filename")
    ap.add_argument("--commit", action="store_true", help="actually write (default: dry run)")
    ap.add_argument("--allow-unverified", action="store_true",
                    help="attach PDFs whose text could not be read (marker check "
                         "inconclusive, NOT failed). The attachment says so.")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    cands = candidates()
    if a.limit:
        cands = cands[:a.limit]
    cfg = load_cfg()
    key = cfg.get("mouser_api_key")
    check_ip(cfg)

    if a.urls:
        # Mouser resolves the URL fine from here, but its specsheet host returns
        # 200-with-HTML to curl — fingerprinting, verified from both sites. The
        # bytes have to come through a real browser. So: resolve here, fetch
        # there, attach with --from-dir. Three steps because the middle one
        # cannot be done from a shell, not because it is elegant.
        if not key:
            print(f"  no Mouser key at {KEYS}")
            return
        for p, mpn in cands:
            u, why = mouser_lookup(mpn, key)
            if u:
                print(f"{mpn}\t{u}")
            else:
                print(f"#{mpn}\t{why}")
        return

    if a.list or not (a.fetch or a.from_dir):
        print(f"  {len(cands)} parts could have a datasheet and do not\n")
        for p, mpn in cands:
            print(f"    #{p.pk:<5} {mpn:<16} {p.name[:56]}")
        print(f"\n  mouser key: {'configured' if key else f'NONE — put one in {KEYS}'}")
        print("  run with --fetch (add --commit to write), or --from-dir DIR")
        return

    if a.fetch and not key:
        print(f"  note: no Mouser key at {KEYS} — patterns and exact URLs only.\n")

    who = get_user_model().objects.filter(is_superuser=True).first()
    ok = bad = 0
    for p, mpn in cands:
        data = origin = None
        if a.from_dir:
            want = mpn.lower().replace("-", "")
            for fn in sorted(os.listdir(a.from_dir)):
                # Skip macOS AppleDouble sidecars and other dotfiles. `._X.pdf`
                # sorts BEFORE `X.pdf`, matches the same MPN, and is 4KB of
                # resource fork — so a naive first-match loop picks the junk
                # file, fails verification, and abandons a part whose real
                # datasheet is sitting right next to it.
                if fn.startswith("."):
                    continue
                if want not in re.sub(r"[^a-z0-9]", "", fn.lower()):
                    continue
                blob = open(os.path.join(a.from_dir, fn), "rb").read()
                if blob[:4] != b"%PDF":
                    continue                      # keep looking, do not give up
                data, origin = blob, f"local:{fn}"
                break
        tried = []
        if data is None and a.fetch:
            for url, why in sources(mpn, key):
                if url is None:
                    tried.append(why)          # a source explaining its own failure
                    continue
                d = get(url)
                if d and d[:4] == b"%PDF":
                    data, origin = d, f"{why}:{url.split('/')[2]}"
                    break
                tried.append(f"{why}:{'no response' if d is None else 'not a PDF'}")
        if data is None:
            # Say WHY. A flat "no source" hid a wrong-endpoint bug for a whole
            # run: the API was answering fine and the script looked broken.
            print(f"  --   #{p.pk:<5} {mpn:<16} {'; '.join(tried[-2:]) or 'no source'}")
            bad += 1
            continue

        state, reason = verify(data, mpn)
        if state == "no":
            print(f"  --   #{p.pk:<5} {mpn:<16} REJECTED: {reason} ({origin})")
            bad += 1
            continue
        if state == "unknown" and not a.allow_unverified:
            print(f"  ??   #{p.pk:<5} {mpn:<16} UNVERIFIED: {reason} ({origin})")
            print(f"       -> re-run with --allow-unverified to attach it anyway")
            bad += 1
            continue
        if not a.commit:
            print(f"  dry  #{p.pk:<5} {mpn:<16} {len(data)//1024:>5} KB  {reason}  [{origin}]")
            ok += 1
            continue
        flag = "" if state == "ok" else "**NOT CONTENT-VERIFIED** — "
        comment = (f"{flag}Datasheet for {mpn}, via {origin}. {reason}. "
                   f"If this part is a MODULE or breakout, this sheet describes the "
                   f"chip on it, not the board — check before trusting a pinout.")
        if attach(p, mpn, data, comment, who):
            print(f"  ok   #{p.pk:<5} {mpn:<16} {len(data)//1024:>5} KB  {reason}")
            ok += 1
        else:
            print(f"  FAIL #{p.pk:<5} {mpn:<16} attach did not stick")
            bad += 1

    verb = "would attach" if not a.commit else "attached"
    print(f"\n  {verb} {ok}, unresolved {bad}")
    n = Attachment.objects.filter(model_type="part").values("model_id").distinct().count()
    print(f"  parts with an attachment: {n}")


if __name__ == "__main__":
    main()
