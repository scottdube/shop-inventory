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
        rows(o.short, o.short_n ?? 0, 'Every build is covered.', '/web/part/') +
        head('Below minimum', o.floor_n ?? 0, 'warn') +
        rows(o.floor, o.floor_n ?? 0, 'Nothing under its floor.', '/web/part/') +
        head('On the list', o.listed_n ?? 0) +
        rows(o.listed, o.listed_n ?? 0, 'Nothing written down yet.',
             '/web/purchasing/'));
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
    shell(target,
        cell(s.parts, 'parts') +
        cell(s.stock, 'stock items') +
        cell(s.uncounted, 'never counted', 'warn') +
        cell(s.no_image, 'no image', 'warn') +
        cell(s.no_keywords, 'no keywords', 'warn') +
        cell(s.free_drawers, 'drawers free', 'good'),
        'stats');
}
