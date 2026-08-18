# Club inventory sharing — a sketch

The idea: members of a hands-on tech club each run (or contribute to) a parts
inventory, and the club gains a shared answer to the two questions that
actually matter at 9pm on a project night:

1. **"Does anyone have a ___ I can borrow/buy?"**
2. **"Before I order 10 of these — does someone already have 200?"**

## Three architectures, in increasing order of ambition

### 1. The parts commons (start here)
Each member exports their catalog periodically — InvenTree has CSV/data
exporters built in; members without InvenTree contribute a spreadsheet with
the same columns (`name, keywords, category, quantity, owner, notes`).

A shared repo (or one member's server) merges them into a single searchable
page. Ownership is a column, not a permission problem. No accounts, no
uptime obligations, no privacy questions beyond "what columns do I export."

- Effort: an afternoon.
- Weakness: staleness between exports — acceptable for "does anyone have."

### 2. Read-only federation
Members who run InvenTree expose a read-only API token over a shared VPN
(Tailscale is the easy button) or tunnels. A small aggregator queries
`/api/part/?search=` across all instances live and merges results.

- Effort: a weekend, mostly VPN wrangling.
- Gains: live quantities.
- Costs: everyone's server has to be up; everyone must be comfortable with
  read access to their full catalog (including costs, if not filtered).

### 3. One shared instance
A single club InvenTree; each member is a top-level StockLocation
(`Members/Alice/...`). InvenTree's user/role system handles who can edit what.

- Gains: one search box, loans trackable as stock transfers between member
  locations, club consumables manageable for real.
- Costs: someone hosts and maintains it; members give up autonomy; migration
  of existing personal instances is real work.

## The loan problem

Whatever the architecture, borrowing is the feature that pays. In InvenTree
terms a loan is just a stock transfer to a location named after the borrower —
which means the "who has my stuff" report is free. In the commons model it's
a `notes` column and honor.

## The founding rule: opt-in only

Nothing enters the commons except by a member's deliberate export. This one
rule does most of the privacy work:

- **Opt-in membership** — participating means running (or handing over) an
  export; not participating means doing nothing. There is no "your data was
  included by default" conversation.
- **Opt-in rows** — the export script filters by category, so a participating
  member shares exactly the shelves they intend to and nothing else.
- **Revocable** — remove your file from the repo and your data is gone from
  the next merge.

## Privacy defaults worth agreeing up front

- Export part identity, quantity, and owner — **not** purchase prices, not
  order history, unless a member opts in.
- Personal categories (household, medical, anything non-shop) never leave the
  member's instance. Automate the filter; don't rely on remembering.

## A club-sized starter project

The LLM search plugin from the main roadmap is also the natural front end
here: "does anyone in the club have a 3.3V level shifter" is the same query
translation problem, aimed at the merged catalog instead of one instance.
