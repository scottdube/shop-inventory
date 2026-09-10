import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'InvenTree.settings')
django.setup()
from part.models import Part

NOTES = """CATALOGUED 2026-09-10 after Scott asked whether the shop had one. It was not in InvenTree; it is demonstrably in the shop.

PROVENANCE — SETTLED 2026-09-10 from the Amazon order page (Scott pulled it up):

  Order 113-1305022-6114620, placed 2026-05-24, delivered 2026-05-25.
  "Current Monitor Power Management Evaluation Board, NRF-PPK2 Nordic
  Semiconductor", sold by MaguireStore. $179.99 (paid $136.27 after
  $56.32 of rewards points). Return window closed 2026-06-24.

That is TWO DAYS before the writeup below, which closes the loop: the instrument arrived, and the first thing it did was the measurement Scott published.

EVIDENCE OF USE — Scott's writeup to the vHOTS Small Computers group, 2026-05-27, on XIAO ESP32-C6 deep-sleep current:

  "Powered via the 3V3 pin from a Nordic PPK2 in Source Meter mode at
   3.300 V... watching the PPK2 trace for changes in the sleep-floor
   current."

It produced the 15.66 / 89.51 / 333.77 uA matrix that disproved the Seeed forum "voltage trap" theory, and he offered to bring it to a meeting for a live demo. So it is owned, working, and in regular use.

WHY IT TOOK A DAY TO FIND, worth remembering because the same trap will recur. Every mail search failed: nothing matched PPK2, "Power Profiler", PPK-2 or nRF-PPK2 across the whole mailbox, including a targeted sweep of Amazon order mail. The reason is that the Amazon LISTING TITLE leads with "Current Monitor Power Management Evaluation Board" and buries the model as "NRF-PPK2" — and Amazon truncates subjects, so the order confirmation never showed a searchable string. Searching the product NAME found nothing; the ORDER PAGE found it immediately.

Two wrong dates were also worked in good faith before the right one: Scott first recalled "this winter", then "april I think". Both were searched to exhaustion and both were empty, because the answer was late May. A remembered date is a lead, not a filter — do not let it bound the search window.

Ordinarily a DigiKey/Mouser/Nordic part; the one DigiKey order in the window (invoice 120874634, 2026-02-16, $41.71) is unrelated.

LOCATION NOT YET SET. Scott has not said where it physically lives; it is not being filed by assumption."""

p = Part.objects.get(pk=1184)
p.notes = NOTES
p.save()
p.refresh_from_db()
ok = "NO PURCHASE RECORD FOUND" not in p.notes and "113-1305022-6114620" in p.notes
print(f"notes written: {len(p.notes)} chars   stale-paragraph-gone={ok}")
