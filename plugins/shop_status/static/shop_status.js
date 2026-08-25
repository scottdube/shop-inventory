/* Shop Status dashboard widgets. Pure render — the plugin passes everything
   in data.context, so there is no second round-trip.

   Colors come from Mantine's own CSS variables (with fallbacks) so these
   widgets follow InvenTree's light/dark switch instead of fighting it. */

const CSS = `
.ss{
  --fg: var(--mantine-color-text, #1a1b1e);
  --dim: var(--mantine-color-dimmed, #868e96);
  --line: var(--mantine-color-default-border, rgba(128,128,128,.22));
  --hover: var(--mantine-color-default-hover, rgba(128,128,128,.09));
  --warn:#c77a20; --bad:#c0392b; --good:#2f9e5f;
  --link: var(--mantine-primary-color-filled, #1971c2);
  font:13px/1.4 var(--mantine-font-family, ui-sans-serif, system-ui, sans-serif);
  color:var(--fg); height:100%; display:flex; flex-direction:column;
  gap:.15rem; overflow:auto;
}
.ss::-webkit-scrollbar{width:6px}
.ss::-webkit-scrollbar-thumb{background:var(--line);border-radius:3px}

.ss .sec{display:flex;align-items:center;gap:.5rem;
  padding:.5rem 0 .3rem;font-size:.68rem;font-weight:600;letter-spacing:.09em;
  text-transform:uppercase;color:var(--dim)}
.ss .sec:first-child{padding-top:.1rem}
.ss .sec .bar{width:3px;height:.85rem;border-radius:2px;background:var(--dim);flex:none}
.ss .sec.warn .bar{background:var(--warn)} .ss .sec.bad .bar{background:var(--bad)}
.ss .sec .sp{flex:1}
.ss .pill{font-size:.7rem;font-weight:700;letter-spacing:0;padding:.05rem .42rem;
  border-radius:999px;font-variant-numeric:tabular-nums;
  background:var(--hover);color:var(--dim)}
.ss .sec.warn .pill{background:rgba(199,122,32,.14);color:var(--warn)}
.ss .sec.bad  .pill{background:rgba(192,57,43,.14);color:var(--bad)}
.ss .sec.done .pill{background:rgba(47,158,95,.14);color:var(--good)}

.ss .rows{display:grid;grid-template-columns:auto minmax(0,1fr) auto;
  align-items:baseline;column-gap:.6rem}
.ss .rows > a{display:contents;color:inherit;text-decoration:none}
.ss .q{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;
  color:var(--dim);padding:.26rem 0}
.ss .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:.26rem 0}
.ss .w{color:var(--dim);font-size:.76rem;white-space:nowrap;padding:.26rem 0;
  text-align:right}
.ss .rows > a:hover .nm{color:var(--link);text-decoration:underline}
.ss .rows > a:hover .q,.ss .rows > a:hover .w{color:var(--fg)}
.ss .more{grid-column:1/-1;font-size:.75rem;color:var(--link);
  text-decoration:none;padding:.3rem 0 .1rem}
.ss .more:hover{text-decoration:underline}
.ss .none{color:var(--dim);font-size:.78rem;padding:.15rem 0 .3rem}

/* build progress */
.ss .prog{grid-column:2/-1;height:3px;border-radius:2px;background:var(--hover);
  margin:0 0 .3rem;overflow:hidden}
.ss .prog i{display:block;height:100%;background:var(--warn);border-radius:2px}
.ss .prog.full i{background:var(--good)}

/* where to buy — vendor chips and the last-purchase line */
.ss .chips{display:flex;flex-wrap:wrap;gap:.35rem;padding:.15rem 0 .35rem}
.ss .chip{display:inline-block;padding:.22rem .6rem;border-radius:999px;
  border:1px solid var(--line);color:var(--link);text-decoration:none;
  font-size:.78rem;white-space:nowrap}
.ss .chip:hover{background:var(--hover);border-color:var(--link)}
.ss .buy{display:flex;align-items:baseline;gap:.5rem;flex-wrap:wrap;
  padding:.2rem 0 .4rem}
.ss .buy .who{font-weight:650}
.ss .buy .amt{font-variant-numeric:tabular-nums;font-weight:650}
.ss .buy a{color:var(--link);text-decoration:none}
.ss .buy a:hover{text-decoration:underline}
.ss .term{font-size:.72rem;color:var(--dim);padding:0 0 .3rem}
.ss .term code{font-family:var(--mantine-font-family-monospace, ui-monospace, monospace);
  background:var(--hover);padding:.05rem .3rem;border-radius:3px;color:var(--fg)}
.ss .caveat{font-size:.72rem;color:var(--warn);padding:0 0 .3rem}

/* stats strip */
.ss.stats{flex-direction:row;flex-wrap:wrap;align-content:center;
  justify-content:space-around;gap:.8rem 1rem;overflow:hidden;padding:.2rem 0}
.ss .stat{text-align:center;min-width:5.5rem}
.ss .stat b{display:block;font-size:1.7rem;font-weight:650;line-height:1.05;
  font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.ss .stat.warn b{color:var(--warn)} .ss .stat.good b{color:var(--good)}
.ss .stat span{display:block;margin-top:.15rem;font-size:.66rem;
  letter-spacing:.07em;text-transform:uppercase;color:var(--dim)}
`;

const esc = (s) => String(s ?? '').replace(/[&<>"]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function shell(target, html, extra = '') {
    target.innerHTML = `<style>${CSS}</style><div class="ss ${extra}">${html}</div>`;
}

/* A section header: colored bar, label, count pill. Tone goes green when the
   count is zero — an empty put-away queue is good news, not neutral news. */
function head(label, n, tone) {
    const t = (n === 0) ? 'done' : (tone || '');
    return `<div class="sec ${t}"><span class="bar"></span>` +
        `<span>${esc(label)}</span><span class="sp"></span>` +
        `<span class="pill">${n}</span></div>`;
}

function rows(items, n, empty, more) {
    if (!items || !items.length) return `<div class="none">${esc(empty)}</div>`;
    const body = items.map((i) =>
        `<a href="${esc(i.url)}" title="${esc(i.name)}">` +
        `<span class="q">${esc(i.qty)}</span>` +
        `<span class="nm">${esc(i.name)}</span>` +
        `<span class="w">${esc(i.where)}</span></a>`).join('');
    const rest = n - items.length;
    const tail = (rest > 0 && more)
        ? `<a class="more" href="${esc(more)}">${rest} more →</a>` : '';
    return `<div class="rows">${body}${tail}</div>`;
}

export function renderQueue(target, data) {
    const secs = data?.context?.sections ?? [];
    shell(target, secs.map((s) =>
        head(s.label, s.n, s.tone) + rows(s.items, s.n, s.empty, s.url)
    ).join(''));
}

export function renderOrders(target, data) {
    const c = data?.context ?? {};
    const pos = c.pos ?? [], builds = c.builds ?? [];

    const poHtml = pos.length
        ? `<div class="rows">${pos.map((p) =>
            `<a href="/web/purchasing/purchase-order/${p.pk}/" title="${esc(p.desc)}">` +
            `<span class="q">${esc(p.ref.replace('PO-', ''))}</span>` +
            `<span class="nm">${esc(p.desc)}</span>` +
            `<span class="w">${esc(p.age)}</span></a>`).join('')}</div>`
        : '<div class="none">Nothing outstanding.</div>';

    /* Each build gets a bar as well as a ratio: at a glance you see which
       project is starved for parts without reading the numbers. */
    const bHtml = builds.length
        ? `<div class="rows">${builds.map((b) => {
            const pct = b.total ? Math.round((b.done / b.total) * 100) : 0;
            return `<a href="/web/manufacturing/build-order/${b.pk}/" title="${esc(b.name)}">` +
                `<span class="q">${b.done}/${b.total}</span>` +
                `<span class="nm">${esc(b.name)}</span>` +
                `<span class="w">${esc(b.ref)}</span></a>` +
                `<div class="prog ${pct === 100 ? 'full' : ''}"><i style="width:${pct}%"></i></div>`;
        }).join('')}</div>`
        : '<div class="none">No active projects.</div>';

    shell(target,
        head('Open orders', pos.length, 'warn') + poHtml +
        head('Projects — parts allocated', builds.length) + bHtml);
}

/* What to buy. Three sections because they answer different questions:
   what an open build cannot start without, what has fallen through a restock
   floor, and what is already written down. The first is the one InvenTree's
   Low Stock report cannot show — that report only knows parts with a
   minimum_stock set, so a part with no minimum is never low however empty. */
export function renderToOrder(target, data) {
    const o = data?.context?.order ?? {};
    shell(target,
        head('Short for open builds', o.short_n ?? 0, 'bad') +
        rows(o.short, o.short_n ?? 0, 'Every build is covered.',
             '/web/part/category/index/parts') +
        head('Below minimum', o.floor_n ?? 0, 'warn') +
        rows(o.floor, o.floor_n ?? 0, 'Nothing under its floor.',
             '/web/part/category/index/parts') +
        head('On the list', o.listed_n ?? 0) +
        rows(o.listed, o.listed_n ?? 0, 'Nothing written down yet.',
             '/web/purchasing/index/purchaseorders/'));
}

/* Where to buy. Answers the bench question: where did this come from last,
   and who else sells it. The search term and the rule that produced it are
   both shown — a term guessed from the part name should not look like a
   catalogue lookup. */
export function renderBuy(target, data) {
    const c = data?.context ?? {};
    const last = c.last, sups = c.sups ?? [], alts = c.alts ?? [];

    let html = head('Bought last', last ? 1 : 0, last ? '' : 'warn');
    if (last) {
        const who = last.url
            ? `<a href="${esc(last.url)}">${esc(last.who)}</a>`
            : esc(last.who);
        html += `<div class="buy"><span class="who">${who}</span>` +
            `<span>${esc(last.when)}</span>` +
            (last.price ? `<span class="amt">${esc(last.price)}</span>` : '') +
            `<span class="sp"></span><span class="w">${esc(last.ref)}</span></div>`;
        if (last.src === 'notes') {
            html += `<div class="caveat">From the imported order history, ` +
                `not a receipted purchase order.</div>`;
        }
    } else {
        html += '<div class="none">No purchase on record.</div>';
    }

    html += head('Suppliers on file', sups.length);
    html += sups.length
        ? `<div class="chips">${sups.map((s) => s.url
            ? `<a class="chip" href="${esc(s.url)}" target="_blank" rel="noopener"` +
              ` title="${esc(s.sku)}">${esc(s.who)}</a>`
            : `<span class="chip" style="color:var(--dim)"` +
              ` title="no link on file">${esc(s.who)}</span>`).join('')}</div>`
        : '<div class="none">No supplier recorded.</div>';

    if (c.how === 'notbuyable') {
        html += head('Alternates', 0);
        html += '<div class="none">Built, not bought — nothing to shop for.</div>';
    } else {
        html += head('Alternates', alts.length);
        html += `<div class="chips">${alts.map((a) =>
            `<a class="chip" href="${esc(a.url)}" target="_blank" rel="noopener">` +
            `${esc(a.who)}</a>`).join('')}</div>`;
        const why = { MPN: 'manufacturer part number',
                      name: 'part number from the name',
                      guess: 'guessed from the name — expect category-level hits' };
        html += `<div class="${c.how === 'guess' ? 'caveat' : 'term'}">` +
            `Searching <code>${esc(c.term)}</code> · ${esc(why[c.how] ?? c.how)}</div>`;
    }

    shell(target, html);
}

export function renderStats(target, data) {
    const s = data?.context?.stats ?? {};
    const cell = (v, label, tone) =>
        `<div class="stat ${v ? (tone || '') : ''}">` +
        `<b>${v ?? '-'}</b><span>${esc(label)}</span></div>`;
    // have/eligible, never have/total. Most of this catalogue is passives,
    // hardware and tooling that cannot have a datasheet at all, so a bare
    // "missing" count would read in the hundreds and mean nothing. The
    // denominator is the set that COULD have one.
    const cellT = (v, label, tone, tip) =>
        `<div class="stat ${v ? (tone || '') : ''}" title="${esc(tip)}">` +
        `<b>${v ?? '-'}</b><span>${esc(label)}</span></div>`;
    const ratio = (have, elig, label) => {
        if (!elig) return '';
        const done = have >= elig;
        return `<div class="stat ${done ? 'good' : 'warn'}" ` +
               `title="${have} of ${elig} parts that could have a datasheet">` +
               // .stat span is display:block for the label underneath, so a
               // nested span breaks the line. Force it inline and size it
               // relative to the numeral so it reads as one figure.
               `<b>${have}<span style="display:inline;font-size:.6em;` +
               `opacity:.5;font-weight:500">/${elig}</span></b>` +
               `<span>${esc(label)}</span></div>`;
    };
    shell(target,
        cell(s.parts, 'parts') +
        cell(s.stock, 'stock items') +
        cell(s.uncounted, 'never counted', 'warn') +
        cell(s.no_image, 'no image', 'warn') +
        cell(s.no_keywords, 'no keywords', 'warn') +
        ratio(s.ds_have, s.ds_eligible, 'datasheets') +
        // Two different populations, so two different nouns. "Confirmed
        // empty" counts ANY location a human has looked into — 17 today, of
        // which three are Mobile Cart trays, not drawers. "Unchecked" counts
        // bin-wall drawers only, because those are the ones worth sweeping.
        // Calling both "drawers" made the first number wrong.
        cellT(s.free_drawers, 'loc. confirmed empty', 'good',
              'Any location whose description says VERIFIED EMPTY — a person looked in it. Includes non-drawer locations.') +
        cellT(s.unchecked_drawers, 'drawers unchecked', 'warn',
              'Bin-wall drawers with no stock rows that nobody has opened. Not free space — unknown space.'),
        'stats');
}

/* ==================================================================
   The instrument panel.  docs/DASHBOARD.md carries the argument; the
   short version is the principle everything below serves:

       make normal look uniform, so abnormal breaks the pattern.

   Three round gauges read by needle ANGLE, not by number — a healthy
   set points the same way and the eye finds the odd one before it
   reads a figure.  The value is in a drum counter in the dead zone at
   the bottom of the sweep: present, never in the scan path.

   Deliberately a depicted object in its own single dark-panel theme
   rather than following Mantine's light/dark. It is an instrument face,
   and an instrument face that restyles itself stops being one.
   ================================================================== */

const PANEL_CSS = `
.sp{--met:#9aa1a5;--metd:#6b7276;--face:#0d1012;--needle:#f7fafc;
  font-family:var(--mantine-font-family-monospace, ui-monospace, "IBM Plex Mono", monospace);
  background:var(--met);border:1px solid var(--metd);border-radius:8px;
  box-shadow:inset 0 1px 0 #b6bcbf, inset 0 -1px 0 #7d8488;
  padding:.75rem .8rem;height:100%;overflow:auto}
.sp::-webkit-scrollbar{width:7px}
.sp::-webkit-scrollbar-thumb{background:#7d8488;border-radius:4px}
.sp .plabel{font-size:.58rem;letter-spacing:.19em;color:#1e2427;text-transform:uppercase;
  margin-bottom:.7rem;display:flex;gap:.75rem;flex-wrap:wrap;font-weight:700;align-items:baseline}
.sp .plabel .sp2{flex:1}
.sp .rule{margin-top:1rem;padding-top:.85rem;border-top:1px solid #757c80}

/* --- annunciator: Korry pushbuttons, flashing until pressed --- */
.sp .annun{display:grid;grid-template-columns:repeat(auto-fit,minmax(8.5rem,1fr));gap:.55rem}
.sp .lampwrap{position:relative}
.sp .lamp{width:100%;display:block;border:1px solid #0f1214;border-radius:4px;
  background:linear-gradient(180deg,#3d4448 0%,#2f3538 52%,#23282b 100%);color:#7f888d;
  /* bottom padding is the link's room: the 'open' anchor is positioned over the
     button (a link cannot nest inside one) and would otherwise sit on the label */
  padding:.45rem .5rem 1.05rem;font:inherit;font-size:.6rem;letter-spacing:.08em;text-align:center;
  text-transform:uppercase;font-weight:700;line-height:1.25;cursor:pointer;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.16), inset 1px 0 0 rgba(255,255,255,.07),
    inset -1px 0 0 rgba(0,0,0,.3), 0 3px 0 #1a1e20, 0 5px 7px rgba(0,0,0,.4);
  transition:transform .06s, box-shadow .06s}
.sp .lamp:active{transform:translateY(3px);
  box-shadow:inset 0 2px 4px rgba(0,0,0,.55), 0 0 0 #1a1e20, 0 1px 2px rgba(0,0,0,.4)}
.sp .lamp b{display:block;font-size:.95rem;letter-spacing:0;margin-bottom:.1rem}
.sp .lamp .g{font-size:.78rem;display:block;line-height:1}
.sp .lamp.caution{background:linear-gradient(180deg,#ffe95c 0%,#f2c800 50%,#cfa800 100%);
  color:#161200;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.72), inset 0 -3px 3px rgba(140,105,0,.35),
    0 3px 0 #8c7200, 0 5px 8px rgba(0,0,0,.42), 0 0 14px rgba(242,200,0,.42)}
.sp .lamp.warning{background:linear-gradient(180deg,#f4574b 0%,#d81f16 50%,#ac150d 100%);
  color:#ffffff;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.5), inset 0 -3px 3px rgba(95,10,6,.4),
    0 3px 0 #6d0c07, 0 5px 8px rgba(0,0,0,.42), 0 0 14px rgba(216,31,22,.42)}
/* lit and unacknowledged flashes; pressing stops the flash, never the lamp */
.sp .lamp.lit[data-ack="false"]{animation:sp-korry 1.1s steps(1,end) infinite}
@keyframes sp-korry{50%{filter:brightness(.32) saturate(.5)}}
.sp .lamp .ack{display:block;font-size:.48rem;letter-spacing:.06em;opacity:.75;margin-top:.22rem}
.sp .lamp:focus-visible{outline:3px solid #fff;outline-offset:2px}
@media (prefers-reduced-motion: reduce){
  .sp .lamp.lit[data-ack="false"]{animation:none;outline:3px solid #fff;outline-offset:-5px}
}
.sp .lampgo{position:absolute;left:0;right:0;bottom:.3rem;text-align:center;
  font-size:.5rem;letter-spacing:.05em;
  color:inherit;opacity:.65;text-decoration:underline;text-underline-offset:2px}
.sp .lamp.lit + .lampgo{color:#161200}
.sp .lamp.warning.lit + .lampgo{color:#fff}
.sp .lampgo:hover{opacity:1}
.sp .lamp.off{background:linear-gradient(180deg,#3d4448 0%,#2f3538 52%,#23282b 100%);color:#c8ced2}

/* --- the three engines --- */
/* A cluster, not a row of widgets. Three engine instruments on a 727 sit
   side by side precisely so the needles can be compared without moving your
   eyes — spread across a metre of panel they are three separate gauges and the
   pattern-break trick stops working. Big enough to read the needle angle from
   standing, which is where this gets read from. */
.sp .engines{display:flex;flex-wrap:wrap;justify-content:center;
  gap:.4rem clamp(1rem,3vw,2.6rem)}
.sp .eng{text-align:center;width:min(15rem,90vw)}
.sp .eng svg{display:block;margin:0 auto;filter:drop-shadow(0 4px 5px rgba(0,0,0,.42))}
.sp .eng .nm{font-size:.78rem;letter-spacing:.16em;color:#101416;margin-top:.45rem;font-weight:700}
.sp .eng .sub{font-size:.66rem;color:#2b3236;margin-top:.15rem;letter-spacing:.02em}
.sp .eng .note{font-size:.6rem;color:#454d52;margin-top:.1rem}
.sp .eng .fresh{font-size:.58rem;color:#4a5256;margin-top:.1rem;font-style:italic}
.sp .eng .tgt{font-size:.62rem;color:#3c4448;margin-top:.2rem;letter-spacing:.04em}
.sp .eng .tgt b{font-variant-numeric:tabular-nums;color:#12171a}
.sp .eng .saveerr{font-size:.52rem;color:#7a1109;font-weight:700;margin-top:.1rem}
.sp .bug{cursor:grab;touch-action:none}
.sp .bug:active{cursor:grabbing}
.sp .bug:hover polygon,.sp .bug:focus-visible polygon{fill:#4da3ff;stroke:#f2f6fa;stroke-width:1.1}
.sp .bug:focus{outline:none}
.sp .eng a.dial:hover .dialface{stroke:#7fb2ea}

/* --- sources: last read that PROVED something --- */
/* One line each. These are a check that the readings above are current, not a
   readout in their own right — three lines and a card apiece gave them more of
   the panel than the instruments. The proof line lives in the tooltip now. */
.sp .sources{display:flex;flex-wrap:wrap;gap:.4rem}
.sp .src{position:relative;display:flex;align-items:baseline;gap:.5rem;
  text-decoration:none;border-radius:3px;border:1px solid #0f1214;
  padding:.24rem .55rem;
  background:linear-gradient(180deg,#20262a 0%,#171c1f 100%);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.1), 0 1px 0 #121618}
.sp .src .sname{font-size:.55rem;letter-spacing:.14em;text-transform:uppercase;
  color:#9aa4ab;font-weight:700}
.sp .src .stime{font-size:.72rem;color:#eef3f6;font-weight:600;
  font-variant-numeric:tabular-nums}
.sp .src.flagged .stime{color:#5b646a}
.sp .src.out .stime{color:#f2c800}
.sp .offflag{transform:rotate(-4deg);
  background:repeating-linear-gradient(135deg,#d81f16 0 5px,#a4150e 5px 10px);
  color:#fff;font-size:.5rem;font-weight:700;letter-spacing:.13em;
  padding:.06rem .35rem;border:1px solid #121618;border-radius:2px}
.sp .foot{font-size:.52rem;color:#2b3236;letter-spacing:.06em;margin-top:.7rem;
  display:flex;gap:.6rem;flex-wrap:wrap}
`;

/* --- tooltips -----------------------------------------------------
   A lamp whose meaning has to be remembered gets pressed without being
   read, so every readout says what it measures on hover AND on keyboard
   focus. The element lives on <body> rather than inside the panel: the
   widget scrolls and clips, and a tooltip cut in half is worse than none.
   Positioned fixed, flipped above/below by available room. */

const TIP_CSS = `
#sp-tip{position:fixed;z-index:9999;max-width:26rem;pointer-events:none;
  opacity:0;transition:opacity .09s;
  background:#11171c;color:#dfe7ee;border:1px solid #39434c;border-radius:5px;
  padding:.5rem .65rem;box-shadow:0 6px 18px rgba(0,0,0,.45);
  font:12.5px/1.5 var(--mantine-font-family, ui-sans-serif, system-ui, sans-serif)}
#sp-tip[data-show="1"]{opacity:1}
#sp-tip b{display:block;margin-bottom:.28rem;color:#fff;font-size:11.5px;
  letter-spacing:.03em;font-family:var(--mantine-font-family-monospace, ui-monospace, monospace)}
`;

function tipElement() {
    let el = document.getElementById('sp-tip');
    if (!el) {
        const st = document.createElement('style');
        st.textContent = TIP_CSS;
        document.head.appendChild(st);
        el = document.createElement('div');
        el.id = 'sp-tip';
        el.setAttribute('role', 'tooltip');
        document.body.appendChild(el);
    }
    return el;
}

function wireTips(root) {
    const el = tipElement();
    const hide = () => el.setAttribute('data-show', '0');

    const show = (host) => {
        const body = host.getAttribute('data-tip');
        const head = host.getAttribute('data-tiphead');
        if (!body && !head) return;
        el.innerHTML = (head ? `<b>${esc(head)}</b>` : '') + esc(body || '');
        el.setAttribute('data-show', '1');

        const r = host.getBoundingClientRect();
        const t = el.getBoundingClientRect();
        const above = r.top > t.height + 12;
        let x = r.left + r.width / 2 - t.width / 2;
        x = Math.max(8, Math.min(x, window.innerWidth - t.width - 8));
        el.style.left = `${Math.round(x)}px`;
        el.style.top = `${Math.round(above ? r.top - t.height - 8 : r.bottom + 8)}px`;
    };

    root.querySelectorAll('[data-tip]').forEach((host) => {
        host.addEventListener('mouseenter', () => show(host));
        host.addEventListener('focusin', () => show(host));
        host.addEventListener('mouseleave', hide);
        host.addEventListener('focusout', hide);
    });
    window.addEventListener('scroll', hide, true);
}

/* --- dial geometry ------------------------------------------------
   0% sits at 135deg and the sweep runs 270deg clockwise to 100% at
   45deg, leaving the dead zone at the bottom for the counter window. */
const A0 = 135, SWEEP = 270, CX = 60, CY = 60;
const ang = (v) => (A0 + (SWEEP * Math.max(0, Math.min(100, v)) / 100)) * Math.PI / 180;
const px = (v, r) => [CX + r * Math.cos(ang(v)), CY + r * Math.sin(ang(v))];
const f2 = (n) => n.toFixed(2);

/* Value under a pointer, for the draggable bug. Beyond either end of the
   sweep the bug snaps to the nearer end rather than jumping across the
   dead zone. */
function valueAt(cx, cy, x, y) {
    let a = (Math.atan2(y - cy, x - cx) * 180 / Math.PI - A0 + 720) % 360;
    if (a > SWEEP) return (a < SWEEP + (360 - SWEEP) / 2) ? 100 : 0;
    return Math.round(a / SWEEP * 100);
}

function arc(from, to, color) {
    const [x1, y1] = px(from, 48), [x2, y2] = px(to, 48);
    const big = (to - from) / 100 * SWEEP > 180 ? 1 : 0;
    return `<path d="M${f2(x1)},${f2(y1)} A48,48 0 ${big} 1 ${f2(x2)},${f2(y2)}"
        fill="none" stroke="${color}" stroke-width="4"/>`;
}

function ticks() {
    let out = '';
    for (let v = 0; v <= 100; v += 5) {
        const major = v % 20 === 0;
        const [x1, y1] = px(v, 44), [x2, y2] = px(v, major ? 36 : 41);
        out += `<line x1="${f2(x1)}" y1="${f2(y1)}" x2="${f2(x2)}" y2="${f2(y2)}"
            stroke="${major ? '#e8edf1' : '#79838c'}" stroke-width="${major ? 2 : 1}"/>`;
        // 0 and 100 get no numeral: both land on the counter window, and the
        // ends of a 270-degree sweep are the two points on the dial nobody has
        // to be told. The drum carries the exact value anyway.
        if (major && v !== 0 && v !== 100) {
            const [lx, ly] = px(v, 30);
            out += `<text x="${f2(lx)}" y="${f2(ly + 2.6)}" text-anchor="middle" fill="#aeb8c1"
                font-size="7.5" font-family="inherit">${v}</text>`;
        }
    }
    return out;
}

function gaugeSvg(g) {
    const off = !!g.off;
    const [nx1, ny1] = px(g.value ?? 0, -11), [nx2, ny2] = px(g.value ?? 0, 40);
    const [bx, by] = px(g.target, 52);
    const bugAng = (A0 + SWEEP * g.target / 100);
    const label = off ? `${g.name} — no reading, OFF flag shown`
                      : `${g.name} ${g.value} percent, target ${g.target}`;

    // needle only when there is a reading. An instrument that has lost its
    // signal drops a flag; it does not park the needle at zero and let that
    // read as "none".
    const needle = off ? '' : `
        <line x1="${f2(nx1)}" y1="${f2(ny1)}" x2="${f2(nx2)}" y2="${f2(ny2)}"
              stroke="var(--needle,#f7fafc)" stroke-width="2.8" stroke-linecap="round"/>
        <circle cx="60" cy="60" r="6.5" fill="#616a72" stroke="#2b3136" stroke-width="1.5"/>
        <circle cx="60" cy="60" r="2" fill="#0d1012"/>`;

    const flag = off ? `
        <g transform="rotate(-9 60 56)">
          <rect x="26" y="47" width="68" height="18" rx="2" fill="#c2231a" stroke="#121618"/>
          <text x="60" y="60" text-anchor="middle" fill="#fff" font-size="11"
                font-weight="700" font-family="inherit" letter-spacing="2">OFF</text>
        </g>` : '';

    return `<svg width="200" height="200" viewBox="0 0 120 120" role="img" aria-label="${esc(label)}">
      <circle cx="60" cy="60" r="58" fill="#2c3237" stroke="#4d565d" stroke-width="1"/>
      <circle cx="18" cy="18" r="1.7" fill="#14181b"/><circle cx="102" cy="18" r="1.7" fill="#14181b"/>
      <circle cx="18" cy="102" r="1.7" fill="#14181b"/><circle cx="102" cy="102" r="1.7" fill="#14181b"/>
      <a class="dial" href="${esc(g.url)}" data-nav="${esc(g.url)}">
        <circle class="dialface" cx="60" cy="60" r="51" fill="var(--face,#0d1012)"
                stroke="#0a0c0d" stroke-width="2"/>
      </a>
      ${arc(0, 40, '#c2231a')}${arc(40, 80, '#e8be00')}${arc(80, 100, '#0f9d58')}
      ${ticks()}
      <rect x="41" y="77" width="38" height="17" rx="2" fill="#05080a" stroke="#464e55"/>
      <text x="60" y="89.5" text-anchor="middle" fill="${off ? '#5b646a' : '#f4f7f9'}"
            font-size="12" font-weight="600" font-family="inherit" class="drum">${off ? '--' : g.value + '%'}</text>
      ${needle}${flag}
      <ellipse cx="44" cy="38" rx="27" ry="17" fill="#fff" opacity=".05" transform="rotate(-30 44 38)"/>
      <g class="bug" tabindex="0" role="slider" aria-valuemin="0" aria-valuemax="100"
         aria-valuenow="${g.target}" aria-label="${esc(g.name)} target, drag or use arrow keys"
         data-key="${esc(g.setting)}" data-gauge="${esc(g.key)}">
        <circle class="bughit" cx="${f2(bx)}" cy="${f2(by)}" r="9" fill="transparent"/>
        <polygon points="-4.6,-3.4 5.2,0 -4.6,3.4" fill="#ffffff" stroke="#0a0c0d" stroke-width=".8"
                 transform="translate(${f2(bx)},${f2(by)}) rotate(${f2(bugAng + 180)})"/>
      </g>
    </svg>`;
}

function gaugeCard(g) {
    return `<div class="eng" data-gauge="${esc(g.key)}"
       data-tiphead="${esc(g.name)} — ${esc(g.off ? 'no reading (OFF)' : g.value + '%')} · ${esc(g.sub)}"
       data-tip="${esc((g.tip || '') + (g.exact
           ? `  The dial opens ${g.exact}.`
           : '  No API filter reproduces this set, so the dial opens the whole'
             + ' list rather than the rows behind the number.'))}">
      ${gaugeSvg(g)}
      <div class="nm">${esc(g.name)}</div>
      <div class="sub">${esc(g.sub)}</div>
      ${g.note ? `<div class="note">${esc(g.note)}</div>` : ''}
      ${g.fresh ? `<div class="fresh">${esc(g.fresh)}</div>` : ''}
      <div class="tgt">▼ target <b class="tv">${g.target}</b>%</div>
      <div class="saveerr" hidden>target not saved</div>
    </div>`;
}

/* Glyph as well as colour, always: red and yellow are the pair most likely
   to be confused, so neither state is ever carried by hue alone. */
function lampEl(l) {
    const off = !!l.off;
    const lit = !off && !!l.n;
    const glyph = off ? '⌧' : (lit ? (l.tone === 'warning' ? '■' : '▲') : '·');
    const cls = ['lamp', off ? 'off' : (lit ? `lit ${l.tone}` : '')].join(' ');
    const n = off ? '—' : `${l.n}${l.unit && l.n ? l.unit : ''}`;
    const ackLine = off ? '<span class="ack">no reading</span>'
        : (lit && l.ack ? `<span class="ack">✓ ack ${esc(l.ack_age)}</span>` : '');
    // "open 43" promises the 43 rows this lamp counted. "open list" promises
    // nothing but the table, which is what you get when no API filter matches
    // the lamp — better said out loud than discovered by clicking.
    const go = (l.exact && lit) ? `open ${l.n} →` : 'open list →';
    return `<div class="lampwrap">
      <button class="${cls}" data-lamp="${esc(l.key)}" data-n="${off ? '' : l.n}"
              data-ack="${l.ack ? 'true' : 'false'}"
              data-tiphead="${esc(l.label)} — ${esc(n)} · ${esc(l.why)}"
              data-tip="${esc((l.tip || '') + (lit
                  ? (l.exact
                      ? '  The link opens exactly these rows.'
                      : '  No API filter matches this set, so the link opens the'
                        + ' whole list — the rows are not singled out.')
                  : ''))}"
              aria-pressed="${l.ack ? 'true' : 'false'}">
        <span class="g" aria-hidden="true">${glyph}</span><b>${esc(n)}</b>${esc(l.label)}${ackLine}
      </button>
      <a class="lampgo" href="${esc(l.url)}" data-nav="${esc(l.url)}">${esc(go)}</a>
    </div>`;
}

function sourceEl(s) {
    const cls = 'src' + (s.off ? ' flagged' : (s.out ? ' out' : ''));
    return `<a class="${cls}" href="/web/part/" data-nav="/web/part/"
       data-tip="${esc(s.tip || '')}" data-tiphead="${esc(s.name)} — ${esc(s.proof)}">
      <span class="sname">${esc(s.name)}</span>
      <span class="stime">${esc(s.time)}</span>
      ${s.off ? '<span class="offflag">OFF</span>' : ''}
    </a>`;
}

export function renderPanel(target, data) {
    const p = data?.context?.panel;
    if (!p) {
        target.innerHTML = `<style>${CSS}</style><div class="ss">` +
            '<div class="none">Panel data unavailable — see the server log.</div></div>';
        return;
    }

    target.innerHTML = `<style>${CSS}${PANEL_CSS}</style><div class="sp">
      <div class="plabel"><span>Annunciator</span><span>·</span>
        <span>lit lamps flash until pressed · pressing silences, never clears</span>
        <span class="sp2"></span><span>read ${esc(p.measured)}</span></div>
      <div class="annun">${p.lamps.map(lampEl).join('')}</div>

      <div class="plabel rule"><span>Shop systems</span><span>·</span><span>coverage %</span>
        <span>·</span><span>red 0–40</span><span>yellow 40–80</span><span>green 80–100</span>
        <span>·</span><span>▼ bug = target, drag or arrow-key it</span></div>
      <div class="engines">${p.gauges.map(gaugeCard).join('')}</div>

      <div class="plabel rule"><span>Sources</span><span>·</span>
        <span>last read that actually proved something</span>
        <span class="sp2"></span><span>aged out after ${p.stale_h}h</span></div>
      <div class="sources">${p.sources.map(sourceEl).join('')}</div>

      <div class="foot"><span>normal is three needles at the same angle</span><span>·</span>
        <span>an OFF flag is a missing reading, not a zero</span></div>
    </div>`;

    wirePanel(target, data, p);
    wireTips(target);
}

/* ---------------- interaction -------------------------------------
   Both writes go to plugin settings through the authenticated api the
   host handed us. A write that fails says so on the instrument rather
   than leaving a moved bug that did not stick. */
function localStamp() {
    const d = new Date();
    const p2 = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}` +
        `T${p2(d.getHours())}:${p2(d.getMinutes())}:${p2(d.getSeconds())}`;
}

function wirePanel(target, data, p) {
    const api = data?.api;
    const navigate = data?.navigate;
    const setting = (key, value) =>
        api ? api.patch(`/api/plugins/shopstatus/settings/${key}/`, { value })
            : Promise.reject(new Error('no api'));

    // In-app routing where the host offers it; the anchors stay real anchors
    // so middle-click and copy-link still work.
    target.querySelectorAll('[data-nav]').forEach((el) => {
        el.addEventListener('click', (ev) => {
            const to = el.getAttribute('data-nav');
            if (!navigate || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.button !== 0) return;
            ev.preventDefault();
            navigate(to.replace(/^\/web/, ''));
        });
    });

    /* --- lamps: press to silence ---------------------------------- */
    // Seed from what the server already holds, timestamps included. Writing the
    // whole map back with at:null would quietly reset every other lamp's ack
    // age — and the age is the signal ("acknowledged for six weeks").
    const acks = {};
    p.lamps.forEach((l) => { if (l.ack) acks[l.key] = { n: l.n, at: l.ack_at ?? null }; });

    target.querySelectorAll('.lamp').forEach((btn) => {
        btn.addEventListener('click', () => {
            const key = btn.dataset.lamp;
            const raw = btn.dataset.n;
            if (raw === '' || Number(raw) === 0) return;   // nothing to silence
            const on = btn.dataset.ack !== 'true';
            btn.dataset.ack = on ? 'true' : 'false';
            btn.setAttribute('aria-pressed', on ? 'true' : 'false');
            let line = btn.querySelector('.ack');
            if (on && !line) {
                line = document.createElement('span');
                line.className = 'ack';
                btn.appendChild(line);
            }
            if (line) line.textContent = on ? '✓ ack today' : '';
            if (on) acks[key] = { n: Number(raw), at: localStamp() };
            else delete acks[key];
            setting('ACK_STATE', JSON.stringify(acks)).catch(() => {
                if (line) line.textContent = 'ack not saved';
            });
        });
    });

    /* --- bugs: drag or arrow-key the target ----------------------- */
    target.querySelectorAll('.bug').forEach((bug) => {
        const svg = bug.closest('svg');
        const card = bug.closest('.eng');
        const err = card.querySelector('.saveerr');
        const readout = card.querySelector('.tv');
        let val = Number(bug.getAttribute('aria-valuenow'));

        const paint = (v) => {
            const a = (A0 + SWEEP * v / 100);
            const rad = a * Math.PI / 180;
            const bx = CX + 52 * Math.cos(rad), by = CY + 52 * Math.sin(rad);
            bug.querySelector('.bughit').setAttribute('cx', f2(bx));
            bug.querySelector('.bughit').setAttribute('cy', f2(by));
            bug.querySelector('polygon').setAttribute(
                'transform', `translate(${f2(bx)},${f2(by)}) rotate(${f2(a + 180)})`);
            bug.setAttribute('aria-valuenow', v);
            readout.textContent = v;
        };

        const commit = () => {
            err.hidden = true;
            setting(bug.dataset.key, val).catch(() => { err.hidden = false; });
        };

        // Pointer position in the SVG's own 120x120 space, so the maths does
        // not care what size the gauge is drawn at.
        const local = (ev) => {
            const r = svg.getBoundingClientRect();
            return [(ev.clientX - r.left) / r.width * 120, (ev.clientY - r.top) / r.height * 120];
        };

        bug.addEventListener('pointerdown', (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            bug.setPointerCapture(ev.pointerId);
            const move = (e) => {
                const [x, y] = local(e);
                val = valueAt(CX, CY, x, y);
                paint(val);
            };
            const up = (e) => {
                bug.releasePointerCapture(ev.pointerId);
                bug.removeEventListener('pointermove', move);
                bug.removeEventListener('pointerup', up);
                commit();
            };
            bug.addEventListener('pointermove', move);
            bug.addEventListener('pointerup', up);
        });

        // Drag-only is unusable from a keyboard, so the same control takes
        // arrow keys — 1 a step, 10 with page keys, ends with home/end.
        bug.addEventListener('keydown', (ev) => {
            const step = { ArrowLeft: -1, ArrowDown: -1, ArrowRight: 1, ArrowUp: 1,
                           PageDown: -10, PageUp: 10 }[ev.key];
            let next = null;
            if (step !== undefined) next = val + step;
            else if (ev.key === 'Home') next = 0;
            else if (ev.key === 'End') next = 100;
            if (next === null) return;
            ev.preventDefault();
            val = Math.max(0, Math.min(100, next));
            paint(val);
            commit();
        });
    });
}
