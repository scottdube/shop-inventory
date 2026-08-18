"""Put footprint back into electrolytic part identity. Reverses unsize_caps.py.

Rationale, from Scott: with KiCad integration, footprint IS identity. A 4x7
radial and a 5x11 have different lead pitch and keep-out. If the schematic maps
to one and stock is the other, it surfaces when the boards arrive and the parts
will not sit down. "Do I have a 1uF 50V?" is answered perfectly well by a search
returning two sized results, so nothing is lost by keeping them distinct.

The three SparkFun-sourced parts have NO known body size. They are restored as
their own parts and flagged unverified rather than being asserted to match a
kit's footprint - asserting an unmeasured footprint is the exact failure above.
"""
import argparse, os, re, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "InvenTree.settings")
django.setup()
from part.models import Part

ap = argparse.ArgumentParser()
ap.add_argument("--commit", action="store_true")
a = ap.parse_args()

# folded twins -> (restored name, active)
FOLDED = {
    679: "Capacitor Electrolytic 4.7uF 50V (4x7)",
    683: "Capacitor Electrolytic 47uF 16V (4x7)",
    684: "Capacitor Electrolytic 47uF 25V (5x7)",
}
# SparkFun kit parts: body size genuinely unknown
UNVERIFIED = {
    693: "Capacitor Electrolytic 1uF 50V",
    694: "Capacitor Electrolytic 10uF 25V",
    695: "Capacitor Electrolytic 100uF 25V",
}
HELD = re.compile(r"Body sizes held:\s*(.+?)\.\s*Kit homes:", re.S)
SUFFIX = re.compile(r"\s*\n*Body sizes held:.*?(?:check stock locations\.)", re.S)
KITSZ = re.compile(r"\s*\n*Kit body size:.*?(?:check the stock locations\.)", re.S)

restored = resized = flagged = 0

for pk, name in FOLDED.items():
    p = Part.objects.filter(pk=pk).first()
    if not p:
        continue
    print(f"  restore  #{pk}  -> {name}")
    restored += 1
    if a.commit:
        p.name, p.active = name[:100], True
        p.notes = re.sub(r"\n*\*\*MERGED\*\*.*$", "", p.notes or "", flags=re.S).strip()
        p.save()

for pk, name in UNVERIFIED.items():
    p = Part.objects.filter(pk=pk).first()
    if not p:
        continue
    print(f"  restore  #{pk}  -> {name}   [FOOTPRINT UNVERIFIED]")
    flagged += 1
    if a.commit:
        p.name, p.active = name[:100], True
        p.notes = (re.sub(r"\n*\*\*MERGED\*\*.*$", "", p.notes or "", flags=re.S).strip()
                   + "\n\n**BODY SIZE UNVERIFIED.** From the SparkFun kit, which "
                     "lists no dimensions. Measure the lead pitch and body before "
                     "using this in a layout — do not assume it matches a kit part "
                     "of the same value.")
        p.save()

for p in Part.objects.filter(name__icontains="Capacitor Electrolytic", active=True):
    if p.pk in FOLDED or p.pk in UNVERIFIED or "(" in p.name:
        continue
    m = HELD.search(p.notes or "")
    if not m:
        print(f"  ?? #{p.pk} {p.name}: no recorded size, left alone")
        continue
    size = m.group(1).split(",")[0].strip()
    print(f"  resize   #{p.pk:<4} {p.name}  ->  ({size})")
    resized += 1
    if a.commit:
        p.notes = KITSZ.sub("", SUFFIX.sub("", p.notes or "")).strip()
        p.name = f"{p.name} ({size})"[:100]
        p.save()

print(f"\n{'WROTE' if a.commit else 'DRY RUN - nothing written'}")
print(f"  twins restored: {restored}   resized: {resized}   flagged unverified: {flagged}")
