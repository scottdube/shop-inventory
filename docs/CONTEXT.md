# Protecting context

Long sessions get compacted. Anything that lives only in the conversation is
gone — and what gets lost is never the code, which is on disk, but the
*reasoning*: why an approach was abandoned, what was already ruled out, what a
correction taught. That is the expensive part to rediscover.

The 2026-08-20 session is the case in point: an evening spent proving that
`brother_ql` cannot drive this printer produced almost no code, and would have
left no trace at all if the eliminations had not been written down. Someone —
including me, next month — would have started with the obvious approach and
lost the same evening.

## The rule

**Write it down in the same turn it is learned, not at the end of the session.**

End-of-session capture fails in the exact case it matters: the session that runs
long, gets compacted, or stops unexpectedly.

## Triggers — capture immediately when any of these happen

| Trigger | Goes where |
|---|---|
| A correction lands ("not true", "that's wrong", "you're overstating it") | `TRAPS.md` |
| Something surprising is established **by test** rather than inferred | `TRAPS.md` |
| An approach is ruled out | the subsystem doc — *with what eliminated it* |
| A decision is made for a reason that is not obvious from the result | commit message, and the doc if it will outlive the change |
| A precedent or convention is set | subsystem doc + memory |
| Something is deliberately **not** done | a note on the record itself, saying why |
| A physical fact is reported that is not derivable from the database | the part / location notes |

That last one matters more than it looks. "The roll is 62 mm × 5 m", "there are
14 in the bag", "A3 rows 1–3 are empty" — none of it can be recovered from the
data, and all of it came from someone standing in the shop looking at it.

## Commit as the primary record

Commit at every milestone, not at the end. The message is the artifact: state
what changed, and **why the obvious alternative was not chosen**. A diff shows
what; only the message shows what was ruled out.

Commits are cheap; a lost explanation is not.

## "Checkpoint"

Say **`checkpoint`** at any point and everything not yet on disk gets flushed:
pending traps written, docs updated, work committed, memory updated. Use it
before a long tool run, when a phase completes, or whenever the session has been
going a while and it is unclear what has been captured.

It should rarely find much. If a checkpoint turns up a lot of uncaptured
material, the triggers above were not being followed.

## Parking is allowed — hiding is not

Some things are not worth stopping for. Cataloguing a handful of plastic filler
buttons mid-session costs more than the record is worth, and a session that
stalls on trivia is a session that does not finish. So park it.

The rule that keeps parking honest: **a parking spot is a QUEUE, not a home.**

- It is a real, addressable location — not a pile, not "on the bench"
- Its description says what went in, when, and that it is **not counted**
- Nothing in it ever gets a `default_location` pointing there
- It is flagged in `metadata` so one query finds every one of them

As of 2026-08-21 there are five:

| Spot | Holds |
|---|---|
| `SLN/Triage` | anything homeless and bulky — a 21×15×6in tote |
| `A2-R8C5` | pre-sort: machine-threaded (takes a nut) |
| `A2-R8C6` | pre-sort: self-threading (pointed end) |
| `A2-R8C7` | pre-sort: nuts & washers |
| `A2-R8C8` | pre-sort: everything else |

Find them all with `metadata.unsorted`, or by searching locations for
`pre-sort`.

The difference between parking and hiding is whether the backlog can be
*listed*. A pile on a table is invisible to every query; a flagged location
shows up the moment anyone asks. Neither is sorted — but only one of them
admits it, and admitting it is what eventually gets it done.

**An empty location is invisible to a Parts or Stock search.** Scott, trying to
look up which pre-sort bucket was which: *"When I type that bin location... it
doesn't turn up anything. I've tried it in stock, and I've tried it in parts."*
Correct, and it always will be — those views list parts and stock items, and a
parking spot deliberately has neither. The information lives on the LOCATION.

So a parking spot needs both of these to be usable, or it is a write-only
record:

- **Search:** Stock → **Locations**. Searching `pre-sort` returns all four
  buckets at once, which is why that phrase is in every one of their
  descriptions. Pick a distinctive shared string when creating a bank of them.
- **At the cabinet:** scan the drawer. The barcode resolves to the location
  page and the description is the first thing on it. This is the whole point of
  addressing drawers, and it costs nothing extra — but it only works once the
  label is physically ON, so a parking spot should be near the front of the
  labelling queue rather than the back.

Do not create a Part with a made-up quantity to represent parked contents.
"Assorted hardware, qty 1" is a fiction that reads like a fact. The location
description carries the truth until someone counts.

## What does NOT go in

- Anything the repo already records — code structure, git history, file layout
- Blow-by-blow narration of a session; capture *conclusions*, not transcripts
- Speculation and provisional plans. Record what was decided and what was
  learned. A policy nobody has decided on yet is not context worth protecting —
  it is a guess that will later be mistaken for a decision.

## Data does not belong in code

In a repo that is public — or might ever become public, or has a public sibling —
literals like order numbers, real email addresses, tokens and street addresses do
not belong in source. Scripts should read them from a gitignored file at runtime.

`shop-inventory` is **public**. On 2026-08-20 it was found to contain 22 Amazon
order numbers with dates and amounts, a vendor PO number and a vendor email,
hardcoded as literals in two spent one-shot migration scripts. They had been
public for weeks. Scrubbing needed a full history rewrite and a force-push, which
reduces future exposure but cannot undo past exposure — and old objects can
survive in GitHub's storage and in any existing clone or fork.

Git has no per-file privacy. The options are: keep the data out of the repo
(simplest, and right when the data has no ongoing value), encrypt named files
with git-crypt or SOPS, split public code from a private data repo, or make the
whole repo private.

Before any first push of a repo, and before adding data to a public one, grep for
order numbers, emails, tokens, internal IPs and street addresses.
