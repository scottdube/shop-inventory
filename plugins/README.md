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

## Deploying a change

    itq push plugins/shop_status/__init__.py <REMOTE>/plugins/shop_status/__init__.py
    itq push plugins/shop_status/static/shop_status.js <REMOTE>/plugins/shop_status/static/shop_status.js
    ssh <HOST> launchctl kickstart -k gui/$(id -u)/com.inventree.server

Then VERIFY the served file matches disk — see TRAPS.md. A `kill -HUP` is not
enough and fails in a way that looks like success.
