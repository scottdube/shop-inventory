# InvenTree plugins

Source of truth for the custom plugins running on the InvenTree instance.
They are deployed to `<INVENTREE_ROOT>/src/src/backend/InvenTree/plugins/`
and served from a symlink under `data/static/plugins/`.

## shop_status — dashboard widgets

Four widgets, all rendered from data the plugin computes server-side and
passes in `context`, so the JS makes no second API call:

| Widget | Shows |
|---|---|
| Needs Attention | put-away queue, unfiled items, lost stock |
| Orders & Projects | open POs and per-build allocation progress |
| **To Order** | short for open builds, below minimum, already listed |
| Catalog Health | counts, images, keywords coverage |

**To Order** exists because InvenTree's own Low Stock report structurally
cannot answer "what do I need to buy". Low Stock compares on-hand against
`minimum_stock`, so a part with no minimum set is never low however empty it
is — and only 14 of 812 component parts have one. The "short for open builds"
section derives demand from build BOMs instead, which needs no threshold.

Caveat baked into that section: demand comes from every build that is not
complete or cancelled. A build left Pending after the thing was physically
built keeps asking for its parts forever. BO-0008 did exactly that and
inflated the SHT31-D shortage from 2 to 5 until it was closed.

## shop_status — "Where to Buy" panel (part pages)

Answers the bench question: *where did this come from last, and who else sells
it.* Three blocks — last purchase, suppliers on file, and alternate vendors.

**Alternates are category-aware.** Half the catalogue is machine tooling, where
component distributors are useless. Routing is by the part's ROOT category:

| Root | Vendors |
|---|---|
| `Tooling`, `Equipment`, `Shop`, `Tools`, `Materials`, `Pneumatic` | Shars · Lakeshore · Haas · MSC · Tormach · Amazon |
| everything else | Octopart · LCSC · DigiKey · Mouser · Amazon |

Parts that are not `purchaseable` (the `Projects` assemblies) get no alternates
— they are built, not bought.

**The search term degrades in stated steps**, and the panel shows which rule
fired so a guess never looks like a lookup:

| Source | Rule |
|---|---|
| `MPN` | a real manufacturer part number — only 4 parts have one |
| `name` | first token, if part-number shaped (`MB10S`, `2N7002`, `LM2596`) |
| `guess` | first four words; category-level hits only |

### Two traps this code exists to avoid

**Purchase dates.** `PurchaseOrder.creation_date` is when the row was typed in.
For back-filled history that is months after the purchase, so `_last_bought()`
reads `issue_date` first and marks the fallback `(recorded)`. It also ignores
PENDING orders — otherwise the `TO-ORDER` shopping list reports itself as the
most recent purchase.

**The notes tables have three different column orders**, so they must be read
by header name, never by position:

```
| Date | Qty | Unit | Line total | Order |      Amazon import
| Date | Order | Qty | Unit |                   Lakeshore and friends
| Date | Quote | Order | Qty | Unit |           Tormach
```

Reading by position turned a $69.49 threadmill into "$1" (it had picked up the
quantity column) and skipped every Tormach table because their order number is
not numeric. A zero-priced row also loses to a real one — several parts carry a
$0 replacement line dated *after* the actual purchase. All 460 parts carrying a
table now parse.

## Deploying a change

    itq push plugins/shop_status/__init__.py <REMOTE>/plugins/shop_status/__init__.py
    itq push plugins/shop_status/static/shop_status.js <REMOTE>/plugins/shop_status/static/shop_status.js
    ssh <HOST> launchctl kickstart -k gui/$(id -u)/com.inventree.server

Then VERIFY the served file matches disk — see TRAPS.md. A `kill -HUP` is not
enough and fails in a way that looks like success.
