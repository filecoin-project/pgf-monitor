import marimo

__generated_with = "unknown"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def kernel_page(KERNEL_CSS, PAGE_HTML, mo):
    # mo.Html, NOT mo.md: mo.md strips only the COMMON leading whitespace, and the page HTML
    # starts at column 0, so the stylesheet's indentation survives and markdown renders the whole
    # <style> block as an indented code block. The mockup uses mo.Html for the same reason.
    mo.Html(KERNEL_CSS + PAGE_HTML)
    return


@app.cell(hide_code=True)
def compose_page(REGISTRY, build_public_page):
    PAGE_HTML = build_public_page(REGISTRY)
    return (PAGE_HTML,)


@app.cell(hide_code=True)
def stylesheet():
    # filpgf.io design tokens, carried from the kernel-filecoin-pgf mockup and
    # namespaced (.kpage, --k-*) so nothing leaks into the marimo chrome.
    KERNEL_CSS = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

        .kpage{
          --k-ink:#0A1020; --k-ink-2:#3C4759; --k-ink-3:#6B7688; --k-muted:#6B7688;
          --k-paper:#FFFFFF; --k-paper-2:#F4F6FA; --k-paper-3:#E8EEF5;
          --k-rule:#E2E7EF; --k-rule-soft:#EEF1F6; --k-grid:#EEF1F6;
          --k-fil:#0090FF; --k-fil-deep:#0057C2; --k-fil-wash:#EAF4FF;
          --k-accent:#0090FF; --k-wash:#EAF4FF;

          --k-t1:#D2593C; --k-t1-wash:#FBEEEA;
          --k-t2:#C4890F; --k-t2-wash:#FCF4E4;
          --k-t3:#2C8073; --k-t3-wash:#E9F4F1;
          --k-t4:#6A44CF; --k-t4-wash:#F1ECFC;

          --k-good:#1A7F4B; --k-bad:#D2593C; --k-warn:#C4890F; --k-none:#DDE3EC;
          --k-skip:#C3CCDA;
          --k-go:#1A7F4B; --k-wait:#C98A00;

          --k-display:'Archivo',system-ui,sans-serif;
          --k-body:'Inter',system-ui,sans-serif;
          --k-mono:'IBM Plex Mono',ui-monospace,monospace;
          --k-wrap:1180px; --k-gutter:28px; --k-prose:900px;

          /* The page is a self-contained document inside the notebook cell: `clip`
             (not `hidden`) keeps the rounded corners without turning this into a
             scroll container, which would kill the sticky nav. */
          width:100%; max-width:100%; overflow:clip;
          border:1px solid var(--k-rule); border-radius:14px;
          background:var(--k-paper); color:var(--k-ink);
          font-family:var(--k-body); font-size:16px; line-height:1.6;
          -webkit-font-smoothing:antialiased; text-align:left;
        }
        .kpage *{box-sizing:border-box}
        .kpage a{color:inherit}
        /* marimo's own stylesheet sets `svg{display:block}`, which drops every inline
           icon onto its own line once exported. Charts and the yes/no ticks re-assert
           block below and outrank this rule on specificity. */
        .kpage svg{display:inline-block;vertical-align:middle}
        .kpage .wrap{max-width:var(--k-wrap);margin:0 auto;padding:0 var(--k-gutter)}
        .kpage a:focus-visible,.kpage summary:focus-visible{outline:2px solid var(--k-fil);outline-offset:3px;border-radius:3px}

        .kpage .eyebrow{font-family:var(--k-mono);font-size:11px;font-weight:500;letter-spacing:.14em;text-transform:uppercase;color:var(--k-fil-deep);display:flex;align-items:center;gap:10px;margin:0 0 18px}
        .kpage .eyebrow::after{content:"";height:1px;flex:1;background:var(--k-rule);max-width:120px}
        .kpage h1,.kpage h2,.kpage h3{font-family:var(--k-display);font-weight:700;letter-spacing:-.025em;line-height:1.05;margin:0;color:var(--k-ink)}
        .kpage h2{font-size:clamp(28px,3.3vw,40px)}
        .kpage h3{font-size:18px;letter-spacing:-.015em;line-height:1.25}
        .kpage .lede{color:var(--k-ink-2);font-size:16.5px;max-width:var(--k-prose);margin:16px 0 0}
        .kpage p{margin:0}

        /* nav */
        .kpage .nav{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.92);backdrop-filter:saturate(1.6) blur(10px);border-bottom:1px solid var(--k-rule)}
        .kpage .nav-in{display:flex;align-items:center;gap:18px;height:58px}
        .kpage .crumb{font-family:var(--k-mono);font-size:13.5px;text-decoration:none;white-space:nowrap;flex:none;color:var(--k-ink-3)}
        .kpage .crumb b{color:var(--k-ink);font-weight:600}
        .kpage .crumb .fil{color:var(--k-fil)}
        .kpage .nav-links{display:flex;gap:20px;margin-left:auto;align-items:center;overflow-x:auto;scrollbar-width:none}
        .kpage .nav-links::-webkit-scrollbar{display:none}
        .kpage .nav-links a{font-size:14px;color:var(--k-ink-2);text-decoration:none;padding:4px 0;border-bottom:1px solid transparent;white-space:nowrap}
        .kpage .nav-links a:hover{color:var(--k-ink);border-bottom-color:var(--k-fil)}
        .kpage .nav-cta{font-size:13.5px;font-weight:500;text-decoration:none;color:#fff!important;background:var(--k-ink);padding:8px 15px;border-radius:7px;flex:none}
        .kpage .nav-cta:hover{background:var(--k-fil-deep)}

        /* hero */
        .kpage .hero{padding:64px 0 0;border-bottom:1px solid var(--k-rule)}
        .kpage .hero h1{font-size:clamp(34px,5vw,58px);max-width:17ch}
        .kpage .hero .lede{font-size:18px;max-width:var(--k-prose)}

        /* substitutability ladder */
        .kpage .ladder{margin-top:46px;padding-bottom:8px}
        .kpage .ladder-h{display:grid;grid-template-columns:8px minmax(0,1.5fr) 118px 128px minmax(0,1.35fr);gap:18px;padding-bottom:9px;border-bottom:1px solid var(--k-ink);font-family:var(--k-mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--k-ink-3)}
        .kpage .rung{display:grid;grid-template-columns:8px minmax(0,1.5fr) 118px 128px minmax(0,1.35fr);gap:18px;padding:17px 0;border-bottom:1px solid var(--k-rule-soft);align-items:center;text-decoration:none}
        .kpage .rung:hover{background:var(--k-paper-2)}
        .kpage .rung-bar{width:8px;height:34px;border-radius:2px}
        .kpage .rung-n{display:block;font-family:var(--k-display);font-weight:700;font-size:17px;letter-spacing:-.02em}
        .kpage .rung-s{display:block;font-size:12.5px;color:var(--k-ink-3);margin-top:3px}
        .kpage .rung-c{display:block;font-family:var(--k-mono);font-size:19px;font-weight:600;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
        .kpage .rung-cl{display:block;font-family:var(--k-mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--k-ink-3);margin-top:3px}
        .kpage .rung-p{font-size:13px;color:var(--k-ink-2);line-height:1.4}
        @media(max-width:900px){
          .kpage .ladder-h{display:none}
          .kpage .rung{grid-template-columns:8px 1fr;gap:14px;align-items:start}
          .kpage .rung-bar{height:100%;min-height:52px}
          .kpage .rung>*:nth-child(3),.kpage .rung>*:nth-child(4),.kpage .rung>*:nth-child(5){grid-column:2}
        }

        /* sections */
        .kpage .sec{padding:76px 0;border-bottom:1px solid var(--k-rule)}
        .kpage .sec-alt{background:var(--k-paper-2)}
        .kpage .sec-head{max-width:var(--k-prose);margin-bottom:42px}

        /* provenance banner */
        .kpage .prov-bar{background:var(--k-paper-2);border-bottom:1px solid var(--k-rule)}
        .kpage .prov-in{display:flex;gap:14px;align-items:flex-start;padding:15px 0}
        .kpage .prov-in svg{flex:none;margin-top:2px;color:var(--k-t2)}
        .kpage .prov-in div{font-size:13px;color:var(--k-ink-3)}
        .kpage .prov-in b{color:var(--k-ink)}
        .kpage .mono{font-family:var(--k-mono)}

        /* objective split */
        .kpage .split{display:grid;grid-template-columns:1.15fr 1fr;gap:52px;align-items:start}
        .kpage .split p{color:var(--k-ink-2);margin:0 0 14px}
        .kpage .panel{background:var(--k-paper);border:1px solid var(--k-rule);border-radius:12px;padding:26px}
        .kpage .panel-t{font-family:var(--k-mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--k-ink-3);margin-bottom:14px}
        .kpage .yn{display:grid;gap:11px;margin:0;padding:0;list-style:none}
        .kpage .yn li{display:grid;grid-template-columns:18px 1fr;gap:11px;font-size:14.5px;color:var(--k-ink-2);align-items:start}
        .kpage .yn i{font-style:normal;font-weight:600;line-height:1.5;display:block}
        .kpage .yn i svg{display:block;margin-top:6px}
        .kpage .yn .y i{color:var(--k-go)}
        .kpage .yn .n i{color:var(--k-t1)}
        .kpage .yn+.panel-t{margin-top:26px;padding-top:22px;border-top:1px solid var(--k-rule-soft)}
        @media(max-width:880px){.kpage .split{grid-template-columns:1fr;gap:32px}}

        /* timeline */
        .kpage .round{display:flex;gap:20px;align-items:center;flex-wrap:wrap;background:var(--k-ink);color:#fff;border-radius:12px;padding:22px 26px;margin-bottom:36px}
        .kpage .round-k{font-family:var(--k-mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:#8FC8FF}
        .kpage .round-v{font-family:var(--k-display);font-weight:700;font-size:23px;letter-spacing:-.02em;margin-top:5px}
        .kpage .round p{margin:6px 0 0;font-size:14px;color:#C3CCD9;max-width:52ch}
        .kpage .round a{margin-left:auto;background:#fff;color:var(--k-ink);text-decoration:none;font-size:13.5px;font-weight:500;padding:10px 18px;border-radius:8px;white-space:nowrap}
        .kpage .round a:hover{background:var(--k-fil-wash)}
        .kpage .tl{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;border-top:2px solid var(--k-rule);gap:0}
        .kpage .tl-i{padding:16px 14px 0 0;position:relative}
        .kpage .tl-i::before{content:"";position:absolute;top:-7px;left:0;width:12px;height:12px;border-radius:50%;background:var(--k-paper);border:2px solid var(--k-rule)}
        .kpage .tl-i.done::before{background:var(--k-go);border-color:var(--k-go)}
        .kpage .tl-i.now::before{background:var(--k-fil);border-color:var(--k-fil);box-shadow:0 0 0 4px var(--k-fil-wash)}
        .kpage .tl-d{font-family:var(--k-mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--k-ink-3)}
        .kpage .tl-t{font-size:14px;font-weight:600;margin-top:5px;letter-spacing:-.01em;text-wrap:balance}
        .kpage .tl-i.now .tl-t{color:var(--k-fil-deep)}
        @media(max-width:900px){
          .kpage .tl{grid-auto-flow:row;grid-auto-columns:auto;border-top:0;border-left:2px solid var(--k-rule);padding-left:22px}
          .kpage .tl-i{padding:0 0 20px}
          .kpage .tl-i::before{top:2px;left:-29px}
        }

        /* tier cards */
        .kpage .tiers{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}
        .kpage .tier{border:1px solid var(--k-rule);border-radius:12px;overflow:hidden;background:var(--k-paper);display:flex;flex-direction:column}
        .kpage .tier-band{padding:13px 22px;color:#fff;font-family:var(--k-mono);font-size:11.5px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;display:flex;justify-content:space-between;gap:12px;align-items:center}
        .kpage .tier-band em{font-style:normal;font-weight:400;text-transform:none;letter-spacing:.02em;opacity:.85;font-size:11px}
        .kpage .tier-b{padding:22px;flex:1}
        .kpage .tier-lab{font-family:var(--k-display);font-weight:600;font-size:15.5px;letter-spacing:-.015em;margin-bottom:9px}
        .kpage .tier-b p{margin:0;color:var(--k-ink-2);font-size:14px}
        .kpage .tier-rows{margin-top:18px;padding-top:16px;border-top:1px solid var(--k-rule-soft);display:grid;gap:11px}
        .kpage .tier-row{display:grid;grid-template-columns:74px 1fr;gap:12px;align-items:start}
        .kpage .tier-k{font-family:var(--k-mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--k-ink-3);padding-top:2px}
        .kpage .tier-v{font-size:13.5px;color:var(--k-ink-2);line-height:1.45}
        @media(max-width:820px){.kpage .tiers{grid-template-columns:1fr}}

        /* view switch — radio + :checked, so it survives static export with no JS */
        .kpage .kviews > input[type="radio"]{display:none}
        .kpage .viewbar{display:flex;gap:2px;margin:0 0 30px;border-bottom:1px solid var(--k-rule)}
        .kpage .viewbar label{display:inline-flex;align-items:center;gap:9px;cursor:pointer;
          font-family:var(--k-mono);font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;
          color:var(--k-ink-3);padding:12px 18px;border-bottom:2px solid transparent;
          margin-bottom:-1px;white-space:nowrap;user-select:none}
        .kpage .viewbar label:hover{color:var(--k-ink);background:var(--k-paper-3)}
        .kpage .viewbar label b{font-weight:500;font-size:10px;letter-spacing:.04em;
          background:var(--k-paper-3);color:var(--k-ink-3);border-radius:20px;padding:2px 8px}
        .kpage .vpanel{display:none}
        .kpage #kv-fn:checked ~ .wrap .viewbar label[for="kv-fn"],
        .kpage #kv-pr:checked ~ .wrap .viewbar label[for="kv-pr"]{color:var(--k-ink);
          border-bottom-color:var(--k-fil)}
        .kpage #kv-fn:checked ~ .wrap .viewbar label[for="kv-fn"] b,
        .kpage #kv-pr:checked ~ .wrap .viewbar label[for="kv-pr"] b{background:var(--k-fil-wash);
          color:var(--k-fil-deep)}
        .kpage #kv-fn:checked ~ .vpanel.v-fn,
        .kpage #kv-pr:checked ~ .vpanel.v-pr{display:block}

        /* project view */
        .kpage .ftrack{height:4px;max-width:250px;background:var(--k-paper-3);border-radius:2px;
          overflow:hidden;margin-top:10px}
        .kpage .fbar{display:block;height:100%;background:var(--k-fil);border-radius:2px}
        .kpage .pmoney{font-family:var(--k-mono);font-weight:600;color:var(--k-ink)}
        .kpage .pfns{margin-top:18px;padding-top:16px;border-top:1px solid var(--k-rule-soft)}
        .kpage .pfns .chips{display:flex;flex-wrap:wrap;gap:7px;margin-top:9px}
        .kpage .pfns .chips span{font-size:12.5px;color:var(--k-ink-2);background:var(--k-paper-2);
          border:1px solid var(--k-rule);border-radius:7px;padding:5px 10px;line-height:1.35}
        .kpage .pfns .chips span i{font-style:normal;font-family:var(--k-mono);font-size:9px;
          letter-spacing:.08em;text-transform:uppercase;margin-right:7px}
        /* requested-but-unmeasurable reads quieter than the funded functions above it */
        .kpage .pfns.asks .chips span{font-family:var(--k-mono);font-size:11.5px;
          color:var(--k-ink-3);background:transparent;border-style:dashed}
        /* proposals sit apart from the committed cards, never beside them */
        .kpage .cards.proposed{opacity:.86}
        .kpage .cards.proposed .card{border-style:dashed}

        /* function inventory */
        .kpage .fgroup{margin-top:34px}
        .kpage .fgroup:first-child{margin-top:0}
        .kpage .fg-h{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;padding-bottom:11px;border-bottom:1px solid var(--k-ink)}
        .kpage .fg-n{font-family:var(--k-mono);font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase}
        .kpage .fg-c{font-family:var(--k-mono);font-size:11.5px;color:var(--k-ink-3);margin-left:auto}
        .kpage .dom{font-family:var(--k-mono);font-size:10.5px;letter-spacing:.11em;text-transform:uppercase;color:var(--k-ink-3);margin:22px 0 10px}
        .kpage details.fn{display:block;border:1px solid var(--k-rule);border-radius:10px;background:var(--k-paper);margin-bottom:9px}
        .kpage details.fn>summary{display:grid;grid-template-columns:minmax(0,1fr) 190px 104px 16px;gap:18px;
          align-items:center;padding:16px 18px;cursor:pointer;list-style:none}
        .kpage details.fn>summary::-webkit-details-marker{display:none}
        .kpage details.fn>summary::marker{content:""}
        .kpage details.fn>summary:hover{background:var(--k-paper-2);border-radius:9px}
        .kpage details.fn[open]{border-color:var(--k-ink-3)}
        .kpage details.fn[open]>summary{border-bottom:1px solid var(--k-rule-soft);border-radius:9px 9px 0 0}
        .kpage details.fn[open]>summary:hover{background:none}
        .kpage .fn-cat{font-family:var(--k-mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--k-ink-3)}
        .kpage .fn-t{font-weight:600;font-size:15px;letter-spacing:-.01em;margin-top:5px;line-height:1.35}
        .kpage .fn-m{font-size:12.5px;color:var(--k-ink-3);margin-top:5px}
        .kpage .fn-m .none{color:var(--k-t1)}
        .kpage .fn-m .quiet{color:var(--k-ink-3)}
        .kpage .fn-s{text-align:right}
        .kpage .fn-p{font-family:var(--k-mono);font-size:19px;font-weight:600;font-variant-numeric:tabular-nums;letter-spacing:-.03em;line-height:1}
        .kpage .fn-l{font-family:var(--k-mono);font-size:9.5px;letter-spacing:.09em;color:var(--k-ink-3);margin-top:5px}
        .kpage .pill{font-family:var(--k-mono);font-size:10px;letter-spacing:.04em;padding:3px 8px;border-radius:20px;border:1px solid;display:inline-flex;align-items:center;gap:5px;margin-top:7px;white-space:nowrap}
        .kpage .pill.ok{color:var(--k-go);border-color:#A8D5BC}
        .kpage .pill.nm{color:var(--k-ink-3);border-color:var(--k-rule)}
        .kpage .pill.bad{color:var(--k-bad);border-color:#EFC4B8}
        .kpage .pill.gap{color:var(--k-warn);border-color:#E7CE92}
        .kpage .car{color:var(--k-ink-3);transition:transform .18s;justify-self:end;display:flex;align-items:center}
        .kpage details.fn[open] .car{transform:rotate(180deg);color:var(--k-ink)}
        .kpage .flag{font-family:var(--k-mono);font-size:10.5px;letter-spacing:.02em}
        .kpage .flag.solo{color:var(--k-t2)}
        .kpage .flag.bad{color:var(--k-t1)}
        .kpage .fn-rowstrip{min-width:0}
        .kpage .rowcad{font-family:var(--k-mono);font-size:9px;letter-spacing:.04em;line-height:1.4;color:var(--k-ink-3);margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

        /* expanded detail panel */
        .kpage .fn-d{padding:18px}
        .kpage .fn-purpose{font-size:14.5px;color:var(--k-ink-2);margin:0;max-width:var(--k-prose)}
        .kpage .fn-grid{display:flex;flex-wrap:wrap;gap:14px 34px;margin-top:17px;padding-top:16px;border-top:1px solid var(--k-rule-soft)}
        .kpage .fm-k{font-family:var(--k-mono);font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--k-ink-3)}
        .kpage .fm-v{font-size:14.5px;margin-top:6px;color:var(--k-ink)}
        .kpage .fm-v.num{font-family:var(--k-mono);font-variant-numeric:tabular-nums;font-weight:500}
        .kpage .fm-v.dim,.kpage .fm-v .dim{color:var(--k-ink-3);font-family:var(--k-mono);font-size:13px}
        @media(max-width:820px){
          .kpage details.fn>summary{grid-template-columns:1fr 14px;gap:10px}
          .kpage details.fn>summary>.fn-s{grid-column:1;order:3;text-align:left}
          .kpage details.fn>summary>.fn-rowstrip{grid-column:1;order:2}
          .kpage .fn-grid{gap:14px 22px}
        }
        .kpage .note{font-family:var(--k-mono);font-size:11.5px;color:var(--k-ink-3);margin-top:16px;padding:12px 14px;background:var(--k-paper-3);border-radius:8px}

        /* metric cards */
        .kpage .sla-notice{display:flex;gap:10px;align-items:flex-start;padding:13px 16px;margin-bottom:20px;
          border:1px solid #E7CE92;background:var(--k-t2-wash);border-radius:8px;font-size:13.5px;color:var(--k-ink-2)}
        .kpage .sla-notice b{color:var(--k-ink)}
        .kpage .mets.two{grid-template-columns:repeat(2,1fr)}
        @media(max-width:560px){.kpage .mets.two{grid-template-columns:1fr}}
        .kpage .mets{display:grid;grid-template-columns:repeat(3,1fr);gap:0;background:var(--k-paper);border:1px solid var(--k-rule);border-width:1px 0 0 1px}
        @media(max-width:860px){.kpage .mets{grid-template-columns:repeat(2,1fr)}}
        @media(max-width:560px){.kpage .mets{grid-template-columns:1fr}}
        .kpage .met{background:var(--k-paper);padding:22px 20px 24px;border:1px solid var(--k-rule);border-width:0 1px 1px 0}
        .kpage .met-v{font-family:var(--k-mono);font-size:clamp(23px,2.6vw,30px);font-weight:600;letter-spacing:-.03em;font-variant-numeric:tabular-nums;line-height:1}
        .kpage .met-k{font-size:13px;color:var(--k-ink-2);margin-top:9px}
        .kpage .met-d{font-family:var(--k-mono);font-size:10.5px;color:var(--k-ink-3);margin-top:6px}
        .kpage .met-d.warn{color:var(--k-t2)}
        .kpage .met-d.bad{color:var(--k-t1)}

        /* glossary */
        .kpage .terms{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--k-rule);border:1px solid var(--k-rule)}
        .kpage .term{background:var(--k-paper);padding:22px}
        .kpage .term dt{font-family:var(--k-display);font-weight:700;font-size:15.5px;letter-spacing:-.015em}
        .kpage .term dd{margin:8px 0 0;color:var(--k-ink-2);font-size:14px}
        .kpage .term dd b{font-weight:600;color:var(--k-ink)}
        @media(max-width:820px){.kpage .terms{grid-template-columns:1fr}}

        .kpage #k-terms{border-bottom:0}
        .kpage .foot{padding:42px 0;font-size:13.5px;color:var(--k-ink-3)}
        .kpage .foot-in{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;align-items:center}
        .kpage .foot a{color:var(--k-ink-2);text-decoration:none;margin-left:20px}
        .kpage .foot a:hover{color:var(--k-fil-deep)}
        .kpage .foot-links{margin-left:auto}
        @media(max-width:640px){.kpage .foot-links{margin-left:0}.kpage .foot a{margin:0 18px 0 0}}
        .kpage .btn{display:inline-block;background:var(--k-ink);color:#fff;text-decoration:none;font-size:14px;font-weight:500;padding:11px 20px;border-radius:8px;margin-top:20px}
        .kpage .btn:hover{background:var(--k-fil-deep)}

        /* ============ monitoring components (drill-down) ============ */
        .kpage .chip{display:inline-flex;align-items:center;gap:5px;font-family:var(--k-mono);font-size:10px;letter-spacing:.04em;padding:3px 9px;border-radius:20px;border:1px solid;white-space:nowrap}
        .kpage .chip.c-good{color:var(--k-good);border-color:#A8D5BC;background:#F1F8F4}
        .kpage .chip.c-bad{color:var(--k-bad);border-color:#EFC4B8;background:#FBEEEA}
        .kpage .chip.c-warn{color:var(--k-warn);border-color:#E7CE92;background:#FCF4E4}
        .kpage .chip.c-none{color:var(--k-ink-3);border-color:var(--k-rule);background:var(--k-paper-2)}
        .kpage .chip.c-acc{color:var(--k-fil-deep);border-color:#B7DBFF;background:var(--k-fil-wash)}

        .kpage .strip{display:flex;gap:1.5px;align-items:stretch;height:26px;width:100%}
        .kpage .strip.sm{height:15px;gap:1px}
        .kpage .strip i{flex:1 1 0;min-width:0;border-radius:1.5px;background:var(--k-none)}
        .kpage .strip i[data-o="p"]{background:var(--k-good)}
        .kpage .strip i[data-o="f"]{background:var(--k-bad)}
        .kpage .strip i[data-o="i"]{background:var(--k-warn)}
        /* Public-page additions to the shared sheet: nothing here is scored, so a bar is either a reading that landed (blue), a day the source gave no defensible number (amber), or a day OUR OWN platform was down (slate, and outside every denominator). Grey stays "no reading expected yet". */
        .kpage .strip i[data-o="u"]{background:var(--k-fil)}
        .kpage .strip i[data-o="x"]{background:var(--k-skip)}
        .kpage .axis{display:flex;justify-content:space-between;gap:12px;font-family:var(--k-mono);font-size:9.5px;letter-spacing:.06em;color:var(--k-ink-3);margin-top:7px}

        .kpage .metrics-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:26px 0 14px;padding-bottom:9px;border-bottom:1px solid var(--k-rule)}
        .kpage .metrics-head h4{font-family:var(--k-display);font-weight:700;font-size:14px;letter-spacing:-.01em;margin:0;text-transform:none}
        .kpage .metrics-head span{font-family:var(--k-mono);font-size:10.5px;letter-spacing:.06em;color:var(--k-ink-3);margin-left:auto}
        .kpage .cards{display:grid;gap:14px}
        .kpage .card{border:1px solid var(--k-rule);border-radius:10px;background:var(--k-paper);padding:18px}
        .kpage .card.impact{background:#FCFDFF}
        .kpage .chead{display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap}
        .kpage .chead .m{font-family:var(--k-mono);font-size:13.5px;font-weight:600;letter-spacing:-.01em;color:var(--k-ink);word-break:break-word}
        .kpage .chead .r{display:flex;gap:7px;align-items:center;margin-left:auto;flex-wrap:wrap}
        .kpage .prov{font-family:var(--k-mono);font-size:10px;letter-spacing:.03em;color:var(--k-t2);display:inline-flex;align-items:center;gap:4px;white-space:nowrap}
        .kpage .prov.obs{color:var(--k-good)}
        .kpage .cmeta{font-family:var(--k-mono);font-size:10.5px;letter-spacing:.02em;color:var(--k-ink-3);margin-top:7px;word-break:break-word}
        .kpage .cstmt{font-size:13.5px;color:var(--k-ink-2);margin:11px 0 0;max-width:var(--k-prose)}

        .kpage .srcrow{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-top:13px;padding-top:12px;border-top:1px solid var(--k-rule-soft)}
        .kpage .srclab{font-family:var(--k-mono);font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--k-ink-3)}
        .kpage .mchip{font-family:var(--k-mono);font-size:9.5px;font-weight:600;letter-spacing:.06em;padding:2px 6px;border-radius:4px;background:#E9F4F1;color:var(--k-t3)}
        .kpage .mchip.post{background:var(--k-t4-wash);color:var(--k-t4)}
        .kpage .srcurl{font-family:var(--k-mono);font-size:11.5px;color:var(--k-ink-2);text-decoration:none;word-break:break-all}
        .kpage a.srcurl{color:var(--k-fil-deep)}
        .kpage a.srcurl:hover{text-decoration:underline}
        .kpage .srcna{font-family:var(--k-mono);font-size:11px;color:var(--k-t2);display:inline-flex;align-items:center;gap:5px}

        .kpage details.dtoggle{margin-top:11px}
        .kpage details.dtoggle>summary{font-family:var(--k-mono);font-size:10.5px;letter-spacing:.05em;color:var(--k-fil-deep);cursor:pointer;list-style:none;display:inline-flex;align-items:center;gap:6px;padding:3px 0}
        .kpage details.dtoggle>summary::-webkit-details-marker{display:none}
        .kpage details.dtoggle>summary::marker{content:""}
        .kpage details.dtoggle>summary::before{content:"";width:0;height:0;border-left:5px solid currentColor;border-top:4px solid transparent;border-bottom:4px solid transparent;transition:transform .15s;display:inline-block;flex:none}
        .kpage details.dtoggle[open]>summary::before{transform:rotate(90deg)}
        .kpage details.dtoggle>summary:hover{text-decoration:underline}

        .kpage .derive{margin-top:10px;padding:14px 16px;background:var(--k-paper-2);border:1px solid var(--k-rule);border-radius:8px}
        .kpage .dk{font-family:var(--k-mono);font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--k-ink-3);margin-bottom:6px}
        .kpage .derive p{font-size:13px;color:var(--k-ink-2);margin:0 0 14px}
        .kpage .derive p:last-child{margin-bottom:0}
        .kpage .derive code{font-family:var(--k-mono);font-size:12px;background:var(--k-paper-3);padding:1px 5px;border-radius:4px}
        .kpage pre.req{font-family:var(--k-mono);font-size:11.5px;line-height:1.5;background:var(--k-ink);color:#DCE5F0;padding:12px 14px;border-radius:7px;overflow-x:auto;margin:0 0 14px;white-space:pre-wrap;word-break:break-word}

        .kpage .readout{display:flex;flex-wrap:wrap;gap:12px 34px;margin-top:14px;padding-top:13px;border-top:1px solid var(--k-rule-soft)}
        .kpage .readout .lab{font-family:var(--k-mono);font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--k-ink-3)}
        .kpage .readout .big{font-family:var(--k-mono);font-size:24px;font-weight:600;letter-spacing:-.03em;font-variant-numeric:tabular-nums;margin-top:5px;line-height:1}
        .kpage .readout .d{font-size:14px;margin-top:8px;color:var(--k-ink)}
        .kpage .readout .d.num{font-family:var(--k-mono);font-variant-numeric:tabular-nums}
        .kpage .readout .d.up{color:var(--k-good);font-weight:600;font-family:var(--k-mono)}
        .kpage .readout .d.dn{color:var(--k-bad);font-weight:600;font-family:var(--k-mono)}
        .kpage .inc{font-size:12.5px;color:var(--k-ink-2);margin-top:12px;padding:9px 12px;background:var(--k-paper-2);border-radius:7px}
        .kpage .inc b{color:var(--k-bad)}
        .kpage .plot{margin-top:14px}
        .kpage .plot svg{width:100%;height:auto;display:block;font-family:var(--k-body)}

        .kpage .dtable{margin-top:10px;max-height:300px;overflow:auto;border:1px solid var(--k-rule);border-radius:8px}
        .kpage .dtable table{width:100%;border-collapse:collapse;font-size:12px}
        .kpage .dtable th{position:sticky;top:0;background:var(--k-paper-2);font-family:var(--k-mono);font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--k-ink-3);text-align:left;padding:8px 12px;border-bottom:1px solid var(--k-rule);font-weight:500}
        .kpage .dtable td{padding:6px 12px;border-bottom:1px solid var(--k-rule-soft);color:var(--k-ink-2)}
        .kpage .dtable td.mono{font-family:var(--k-mono);font-size:11.5px}
        .kpage .dtable td.n{text-align:right;font-family:var(--k-mono);font-variant-numeric:tabular-nums;color:var(--k-ink)}
        .kpage .dtable tr:last-child td{border-bottom:0}

        .kpage .empty{font-size:13.5px;color:var(--k-ink-2);padding:14px 16px;background:var(--k-paper-2);border:1px solid var(--k-rule);border-radius:8px;margin-top:14px}
        .kpage .empty b{color:var(--k-ink)}
        .kpage .legend{display:flex;gap:16px;flex-wrap:wrap;font-family:var(--k-mono);font-size:10.5px;color:var(--k-ink-3);margin-top:18px}
        .kpage .legend span{display:inline-flex;align-items:center;gap:6px}
        .kpage .legend i{width:9px;height:9px;border-radius:2px;display:inline-block}

        @media(prefers-reduced-motion:reduce){.kpage *{animation:none!important;transition:none!important}}
        </style>
    """
    return (KERNEL_CSS,)


@app.cell(hide_code=True)
def collection_policy():
    # Two decisions about what the coverage denominator is allowed to charge a team for. Both
    # are OURS, both are stated on the page, and neither can hide a source that stopped
    # answering.
    #
    # COVERAGE_FROM -- coverage is judged from the day unattended collection became the record,
    # never from a metric's first ad-hoc probe. 41 commitments across 17 teams carry a single
    # live-review reading on 2026-07-15; anchoring a denominator on it charged each of them for
    # the month before the instrument existed, which reads as a team that stopped reporting
    # rather than as a monitor that had not been built. A metric first collected AFTER this date
    # still starts at its own first reading -- this is a floor, not an override.
    COVERAGE_FROM = "2026-08-22"

    # PLATFORM_OUTAGES -- days the OSO platform, not the source, failed. On 2026-08-22 OSO moved
    # ingestion runs into run groups and `run { id }` began returning 400; every fetch for all 12
    # teams returned nothing for two nights, and 2026-08-24 recovered on its own with no change
    # at any source. Those days leave the denominator entirely rather than counting as gaps
    # against a team. Dated explicitly because the public mart carries no error column -- only
    # `method` -- so there is nothing in the data to pattern-match, and a list you have to edit
    # by hand cannot quietly swallow a source that really did go dark.
    PLATFORM_OUTAGES = {"2026-08-22", "2026-08-23"}
    return COVERAGE_FROM, PLATFORM_OUTAGES


@app.cell(hide_code=True)
def public_engine(COVERAGE_FROM, PLATFORM_OUTAGES, datetime, math):
    # The formatting, axis, strip and line-chart helpers are lifted VERBATIM from
    # dashboards/propgf-kernel-mockup_v2.py so the two pages cannot drift apart
    # visually. What changes is the ROLL-UP: the mockup rolls readings into a
    # pass/fail SLA percentage, and no bar is in force here, so this page rolls
    # them into reading coverage instead -- the share of the periods a metric's
    # own cadence expects that actually carry a value. Same shape in the layout,
    # a claim the public tables can actually support.
    WIN = 90

    # ---------------------------------------------------------------- helpers

    def esc(s):
        if s is None:
            return ""
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


    def fmt(v):
        if v is None:
            return "—"
        a = abs(v)
        if a >= 1e12:
            return f"{v/1e12:.2f}T"
        if a >= 1e9:
            return f"{v/1e9:.2f}B"
        if a >= 1e6:
            return f"{v/1e6:.2f}M"
        if a >= 1e4:
            return f"{v/1e3:.1f}k"
        if a >= 100:
            return f"{round(v):,}"
        if a >= 1:
            return f"{round(v*100)/100:g}"
        return f"{round(v*1e4)/1e4:g}"


    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


    def as_date(iso):
        return datetime.date.fromisoformat(iso)


    def short(iso):
        d = as_date(iso)
        return f"{MONTHS[d.month-1]} {d.day}"


    def key_label(k):
        if len(k) == 7:
            y, m = k.split("-")
            return f"{MONTHS[int(m)-1]} {y[2:]}"
        return short(k)


    # ------------------------------------------------ series + coverage roll-up

    GRAIN = {"daily": 1, "weekly": 7, "monthly": 30}
    # A period is only as good as its worst reading: a day that produced no
    # defensible number outranks one that did.
    RANK = {"i": 2, "u": 1, "x": 0}


    def pts(e, today, win=WIN):
        """Readings inside the window as [(iso, value, outcome)], oldest first.

        outcome is 'u' (a value was read, and nothing scores it) or 'i' (the
        source was asked and gave no defensible number).
        """
        s = e.get("s")
        if not s:
            return []
        st = as_date(s["d0"])
        out = [((st + datetime.timedelta(days=off)).isoformat(), v, o)
               for off, v, o in zip(s["off"], s["v"], s["o"])]
        cut = (as_date(today) - datetime.timedelta(days=win - 1)).isoformat()
        f = [p for p in out if p[0] >= cut]
        return f if f else out[-win:]


    def bucket_key(iso, cad):
        if cad == "monthly":
            return iso[:7]
        if cad == "weekly":
            d = as_date(iso)
            return (d - datetime.timedelta(days=d.weekday())).isoformat()
        return iso


    def periods(cad, today, win=WIN):
        step = GRAIN.get(cad, 1)
        end = as_date(today)
        out = []
        for back in range(0, win, step):
            k = bucket_key((end - datetime.timedelta(days=back)).isoformat(), cad)
            if k not in out:
                out.append(k)
        out.reverse()
        return out


    def roll(e, today, win=WIN):
        """Coverage roll-up over the window, at the metric's own cadence grain.

        The denominator starts at the metric's FIRST reading, not at the window
        edge: a commitment first collected three weeks ago has not missed the
        sixty-nine days before that, and charging it for them would read as a
        failure to report rather than as an instrument that had not been built.
        COVERAGE_FROM floors that same argument at the programme level, and
        periods lost to a PLATFORM_OUTAGES day leave the denominator outright --
        both are our failures, not the team's, so neither is charged to it.
        """
        p = pts(e, today, win)
        by, val = {}, {}
        for iso, v, o_ in p:
            k = bucket_key(iso, e["cad"])
            # Inside one bucket a reading outranks an unmeasurable day, which outranks a
            # day we were the ones who were down.
            if v is not None:
                by[k], val[k] = "u", v
            elif o_ == "x":
                by.setdefault(k, "x")
            elif by.get(k) in (None, "x"):
                by[k] = "i"
        keys_all = periods(e["cad"], today, win)
        first = bucket_key(p[0][0], e["cad"]) if p else None
        floor = bucket_key(COVERAGE_FROM, e["cad"])
        start = max(k for k in (first, floor) if k)
        # A period drops out only when the outage cost us the WHOLE of it: a weekly or
        # monthly bucket still holds days the outage never touched, and is judged on those.
        keys = [k for k in keys_all
                if k >= start and by.get(k) != "x"
                and not (e["cad"] == "daily" and k in PLATFORM_OUTAGES)] or keys_all[-1:]
        read = sum(1 for k in keys if by.get(k) == "u")

        # A run of consecutive periods with no value. Ours to answer for, not
        # the team's, so it is called a gap and never coloured as a breach.
        runs, cur = [], None
        for k in keys:
            if by.get(k) == "u":
                cur = None
            elif cur:
                cur["n"] += 1
            else:
                cur = {"d": k, "n": 1}
                runs.append(cur)

        vals = [(iso, v) for iso, v, _o in p if v is not None]
        return {"by": by, "val": val, "keys": keys, "read": read,
                "expected": len(keys), "miss": len(keys) - read,
                "pct": (100.0 * read / len(keys)) if keys else None,
                "runs": runs, "last": p[-1] if p else None,
                "last_val": vals[-1] if vals else None,
                "n_read": len(vals), "n_att": len(p),
                # The date coverage is JUDGED from -- which is the floored, outage-trimmed
                # start, not p[0][0]. The card states this date, so they must not disagree.
                "from": keys[0] if keys else None}


    def grain_word(cad):
        return {"daily": "day", "weekly": "week", "monthly": "month"}.get(cad, "period")


    def agg(entries, today, win=WIN):
        """Aggregate coverage over a list of entry dicts."""
        if not entries:
            return {"state": "none", "pct": None, "gaps": 0, "read": 0, "expected": 0}
        read = exp = gaps = 0
        for e in entries:
            r = roll(e, today, win)
            read += r["read"]
            exp += r["expected"]
            gaps += len(r["runs"])
        return {"state": "none" if not exp else ("good" if read == exp else "warn"),
                "pct": (100.0 * read / exp) if exp else None,
                "gaps": gaps, "read": read, "expected": exp}


    def delta(e, today, win=WIN):
        p = [(i, v) for i, v, _o in pts(e, today, win) if v is not None]
        if len(p) < 2 or not p[0][1]:
            return {"cls": "flat", "txt": "—"}
        pc = ((p[-1][1] - p[0][1]) / abs(p[0][1])) * 100
        return {"cls": "up" if pc > 1.5 else ("dn" if pc < -1.5 else "flat"),
                "txt": ("+" if pc > 0 else "") + f"{pc:.1f}%"}


    # -------------------------------------------------------------- chrome

    ICON = {
        "good": '<svg width="9" height="9" viewBox="0 0 12 12" aria-hidden="true"><path d="M2 6.4 4.6 9 10 3.2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        "bad": '<svg width="9" height="9" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 3l6 6M9 3l-6 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
        "warn": '<svg width="9" height="9" viewBox="0 0 12 12" aria-hidden="true"><path d="M6 1.6 11 10.4H1z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>',
        "none": '<svg width="9" height="9" viewBox="0 0 12 12" aria-hidden="true"><circle cx="6" cy="6" r="4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-dasharray="2 2"/></svg>',
        "acc": '<svg width="9" height="9" viewBox="0 0 12 12" aria-hidden="true"><path d="M2 9 10 3M10 3H6.2M10 3v3.8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    }
    EXT_ICON = ('<svg width="9" height="9" viewBox="0 0 12 12" aria-hidden="true" '
            'style="vertical-align:baseline"><path d="M4 8 8.5 3.5M8.5 3.5H5.3M8.5 3.5v3.2" '
            'fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
            'stroke-linejoin="round"/></svg>')


    def chip(kind, txt):
        return f'<span class="chip c-{kind}">{ICON.get(kind, "")}{esc(txt)}</span>'


    # ---------------------------------------------------------- uptime strip

    def collapse_bars(keys, by, max_bars):
        if not max_bars or len(keys) <= max_bars:
            return [{"o": by.get(k) or "n", "lab": key_label(k), "span": 1} for k in keys]
        size = -(-len(keys) // max_bars)
        out = []
        for i in range(0, len(keys), size):
            grp = keys[i:i + size]
            o = "n"
            for k in grp:
                v = by.get(k)
                if v and (o == "n" or RANK[v] > RANK.get(o, 0)):
                    o = v
            lab = (key_label(grp[0]) + " – " + key_label(grp[-1])
                   if len(grp) > 1 else key_label(grp[0]))
            out.append({"o": o, "lab": lab, "span": len(grp)})
        return out


    STATE_TXT = {"u": "read", "i": "no defensible number",
                 "x": "OSO platform outage \u00b7 not counted"}
    MIN_BARS = 8


    def strip_bits(e, today, win=WIN):
        """What the coverage strip should draw.

        A monthly commitment fills only three cadence periods in a 90-day
        window, which reads as a broken graphic rather than a record. When the
        grain is that coarse the strip switches to one bar per reading -- and
        says so -- while the coverage percentage above it stays on the metric's
        own cadence either way.
        """
        r = roll(e, today, win)
        # The strip draws the WHOLE window, not just the periods since collection began: every
        # strip on the page then covers the same dates and can be read against its neighbours,
        # and the grey run in front of a young commitment is itself the fact worth seeing.
        keys_all = periods(e["cad"], today, win)
        if len(keys_all) >= MIN_BARS:
            return {"keys": keys_all, "by": r["by"],
                    "g": grain_word(e["cad"]), "dense": False}
        p = pts(e, today, win)
        return {"keys": [iso for iso, _v, _o in p],
                "by": {iso: ("u" if v is not None else "i") for iso, v, _o in p},
                "g": "reading", "dense": True}


    def strip_html(e, today, win=WIN, small=False, max_bars=None):
        b_ = strip_bits(e, today, win)
        g = b_["g"]
        bars = []
        for b in collapse_bars(b_["keys"], b_["by"], max_bars):
            state = STATE_TXT.get(b["o"], "no reading")
            many = f" (worst of {b['span']} {g}s)" if b["span"] > 1 else ""
            bars.append(f'<i data-o="{b["o"]}" title="{esc(b["lab"])} · {state}{many}"></i>')
        cls = "strip sm" if small else "strip"
        return (f'<div class="{cls}" role="img" aria-label="whether each {g} carries a '
                f'reading, last {win} days">{"".join(bars)}</div>')

    # ------------------------------------------------------------ line chart
    def nice_step(span, divisions=4):
        """A 1/2/2.5/5/10 step that splits `span` into roughly `divisions`."""
        raw = span / divisions
        if raw <= 0:
            return 1.0
        mag = 10.0 ** math.floor(math.log10(raw))
        for m in (1, 2, 2.5, 5, 10):
            if raw <= m * mag:
                return m * mag
        return 10 * mag


    def axis_ticks(lo, hi, divisions=4):
        """Round tick values inside the plotted range, so the axis never prints
        the padded minimum (0.9888, 10.41) that the data happens to land on."""
        step = nice_step(hi - lo, divisions)
        first = math.ceil(lo / step - 1e-9) * step
        out, v, guard = [], first, 0
        while v <= hi + 1e-9 and guard < 14:
            out.append(round(v, 10))
            v += step
            guard += 1
        return out, step


    def tick_label(v, step):
        if abs(v) >= 1e4 or (v and abs(v) < 1e-3):
            return fmt(v)
        dec, s = 0, step
        while s < 1 and dec < 6:
            s *= 10
            dec += 1
        return f"{v:,.{dec}f}"


    def line_svg(e, today, win=WIN, h=186, thr_tone="bad", thr_label=None, show_thr=True):
        p = pts(e, today, win)
        if len(p) < 2:
            return ""
        W, ml, mr, mt, mb = 760, 52, 22, 14, 26
        pw, ph = W - ml - mr, h - mt - mb
        vs = [x[1] for x in p]
        lo, hi = min(vs), max(vs)
        thr = float(e["thr"]) if (e.get("thr") is not None and show_thr) else None
        all_pos = lo >= 0 and (thr is None or thr >= 0)
        if thr is not None:
            lo, hi = min(lo, thr), max(hi, thr)
        if hi == lo:
            hi = lo + (abs(lo) or 1) * 0.12
        pad = (hi - lo) * 0.12
        lo, hi = lo - pad, hi + pad
        if all_pos and lo < 0:
            lo = 0

        def X(i):
            return ml + (i * pw / (len(p) - 1) if len(p) > 1 else pw / 2)

        def Y(v):
            return mt + (1 - (v - lo) / (hi - lo)) * ph

        thr_y = Y(thr) if thr is not None else None

        def keep(vals):
            # a gridline sitting under the dashed threshold rule reads as noise
            return [v for v in vals
                    if thr_y is None or abs(Y(v) - thr_y) >= 9]

        ticks, step = axis_ticks(lo, hi)
        # dropping a tick next to the threshold can leave the axis with a single
        # label; step down one level rather than ship a chart with no scale
        if len(keep(ticks)) < 2:
            fine, fine_step = axis_ticks(lo, hi, 8)
            if len(keep(fine)) > len(keep(ticks)):
                ticks, step = fine, fine_step

        g = []
        for yv in keep(ticks):
            y = Y(yv)
            g.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{W-mr}" y2="{y:.1f}" '
                     f'stroke="var(--k-grid)" stroke-width="1"/>'
                     f'<text x="{ml-8}" y="{y+3.5:.1f}" text-anchor="end" font-size="10" '
                     f'fill="var(--k-muted)" style="font-variant-numeric:tabular-nums">'
                     f'{esc(tick_label(yv, step))}</text>')
        d = " ".join(f'{"L" if i else "M"}{X(i):.1f},{Y(x[1]):.1f}' for i, x in enumerate(p))
        area = f'{d} L{X(len(p)-1):.1f},{mt+ph:.1f} L{X(0):.1f},{mt+ph:.1f} Z'
        t = ""
        if thr is not None:
            y = Y(thr)
            ly2 = y + 14 if y < mt + ph / 2 else y - 7
            lab = thr_label or (e["op"] + " " + fmt(float(e["thr"])))
            t = (f'<line x1="{ml}" y1="{y:.1f}" x2="{W-mr}" y2="{y:.1f}" '
                 f'stroke="var(--k-{thr_tone})" stroke-width="1.4" stroke-dasharray="5 4" opacity=".85"/>'
                 f'<text x="{ml+4}" y="{ly2:.1f}" font-size="9.5" fill="var(--k-{thr_tone})" '
                 f'font-family="var(--k-mono)" paint-order="stroke" stroke="#fff" stroke-width="3" '
                 f'stroke-linejoin="round">{esc(lab)}</text>')
        lx, ly = X(len(p) - 1), Y(p[-1][1])
        return (
            f'<div class="plot"><svg viewBox="0 0 {W} {h}" role="img" '
            f'aria-label="{esc(e["metric"])} over the last {win} days">'
            + "".join(g)
            + f'<path d="{area}" fill="var(--k-wash)"/>'
            f'<path d="{d}" fill="none" stroke="var(--k-accent)" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"><title>{esc(e["metric"])}</title></path>'
            + t
            + f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4.5" fill="var(--k-accent)" stroke="#fff" stroke-width="2"/>'
            f'<text x="{lx:.1f}" y="{ly-11:.1f}" text-anchor="end" font-size="11" font-weight="600" '
            f'fill="var(--k-ink)" paint-order="stroke" stroke="#fff" stroke-width="3.5" '
            f'stroke-linejoin="round">{esc(fmt(p[-1][1]))}</text>'
            f'<line x1="{ml}" y1="{mt+ph}" x2="{W-mr}" y2="{mt+ph}" stroke="var(--k-rule)" stroke-width="1"/>'
            f'<text x="{ml}" y="{h-7}" font-size="10" fill="var(--k-muted)" '
            f'font-family="var(--k-mono)">{esc(short(p[0][0]))}</text>'
            f'<text x="{W-mr}" y="{h-7}" text-anchor="end" font-size="10" fill="var(--k-muted)" '
            f'font-family="var(--k-mono)">{esc(short(p[-1][0]))}</text>'
            '</svg></div>')


    # --------------------------------------------------------------- cards

    def dense(e):
        """A copy of the entry carrying only the days that produced a value.

        `line_svg` is verbatim from the mockup and assumes every point is numeric, because the
        mockup's data has no gaps. Rather than edit the chart code -- and risk the two pages
        drifting apart -- the chart is handed a gap-free copy, and the card states the missing
        readings in words so the gap is never silently bridged.
        """
        s_ = e["s"]
        keep = [(o, v) for o, v in zip(s_["off"], s_["v"]) if v is not None]
        return {**e, "s": {"d0": s_["d0"], "off": [o for o, _ in keep],
                           "v": [v for _, v in keep], "o": ["u"] * len(keep)}}


    def dtable(e, today, win=WIN):
        """Date, value, and why a row is empty. Newest first.

        The mockup's third column is the SLA outcome; with no bar in force every cell in it
        would be a dash, so it carries the collection outcome instead -- which is the only
        judgement this page is entitled to make.
        """
        rows = "".join(
            f'<tr><td class="mono">{iso}</td><td class="n">{esc(fmt(v))}</td>'
            f'<td>{esc("" if o_ == "u" else STATE_TXT.get(o_, "no reading"))}</td></tr>'
            for iso, v, o_ in reversed(pts(e, today, win)))
        return (f'<div class="dtable"><table><thead><tr><th>date</th>'
                f'<th style="text-align:right">{esc(e["metric"])}</th>'
                f'<th>comment</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div>')


    def collection_row(e):
        """Where the reading came from, in place of the mockup's source block.

        The mockup names the endpoint and the SQL that reduces it to a scalar, because it reads
        the registry. The public mart carries neither -- only HOW each reading was taken -- so
        this row states that and links to the manifest, which is public and holds BOTH: the
        endpoint, the query sent to it, and the SQL that reduces the response to one number.
        Better than the bare host a mart column could carry, since most sources are JSON-RPC
        POST endpoints a browser cannot usefully open.
        """
        m = e["methods"]
        n = sum(m.values())
        live = m.get("nightly", 0)
        review = m.get("live-review", 0)
        hosts = sorted(h.split(":", 1)[1] for h in m if h.startswith("backfill:"))
        bits = []
        if live:
            bits.append(f'{live} unattended nightly run{"s" if live != 1 else ""}')
        if review:
            bits.append(f'{review} taken during a review')
        if hosts:
            bits.append("history backfilled from <b>" + "</b>, <b>".join(esc(h) for h in hosts)
                        + "</b>")
        src = f'{REGISTRY_BASE}/{e["team"]}.yaml'
        return (f'<div class="srcrow"><span class="srclab">collection</span>'
                f'<span class="mchip">{esc(e["cad"])}</span>'
                f'<span class="srcurl">{" · ".join(bits) or "no reading yet"}'
                f'<span style="color:var(--k-ink-3)"> · {n} row'
                f'{"s" if n != 1 else ""} in the public table</span></span></div>'
                f'<div class="srcrow"><span class="srclab">source</span>'
                f'<span class="srcurl"><a href="{esc(src)}" target="_blank" '
                f'rel="noopener noreferrer" style="color:var(--k-fil-deep)">'
                f'registry/{esc(e["team"])}.yaml {ARROW}</a>'
                f'<span style="color:var(--k-ink-3)"> — the endpoint we poll, the query we '
                f'send, and the SQL that turns the answer into this number</span>'
                f'</span></div>')


    def metric_card(e, today, win=WIN, show_team=True, qualify=False):
        """One commitment: coverage, the record, the readings, the numbers.

        The mockup's card in every respect except the roll-up: where it leads with a rolling SLA
        percentage and an interruption count -- both of which need an agreed threshold -- this
        leads with reading coverage and the gaps in collection, which is what the public tables
        can actually answer.
        """
        r = roll(e, today, win)
        d = dense(e)
        head = f'{e["team"]} · {e["fid"]}' if qualify else e["fid"]
        meta = " · ".join(x for x in [
            e["team"] if show_team else None, e["metric"], e["cad"],
            f'grant {e["grant"]}' if e["grant"] else "no grant pays for this",
        ] if x)
        state = (chip("acc", f'Monitored · {esc(e["cad"])}') if r["last_val"]
                 else chip("warn", "No reading yet"))

        g = grain_word(e["cad"])
        if r["runs"]:
            detail = " · ".join(
                key_label(x["d"]) + (f' ({x["n"]} {g}s)' if x["n"] > 1 else "")
                for x in r["runs"])
            inc = (f'<div class="inc"><b>{len(r["runs"])} gap'
                   f'{"s" if len(r["runs"]) > 1 else ""} in collection</b> · {esc(detail)}'
                   f' — days the source gave no defensible number, not days the metric '
                   f'was missed. Days our own platform was down are not counted here at '
                   f'all.</div>')
        else:
            inc = (f'<div class="inc">Every {g} since {esc(key_label(r["from"]))} carries a '
                   f'reading.</div>')

        latest = esc(fmt(r["last_val"][1])) if r["last_val"] else "—"
        sb = strip_bits(e, today, win)
        bar_caption = "one bar = one " + sb["g"]
        if sb["dense"]:
            bar_caption += " · coverage judged " + e["cad"]
        if not sb["keys"]:
            return (f'<article class="card" id="m-{e["id"]}">'
                    f'<div class="chead"><span class="m">{esc(head)}</span>'
                    f'<div class="r">{state}</div></div>'
                    f'<div class="cmeta">{esc(meta)}</div>'
                    f'<p class="cstmt">{esc(e["stmt"])}</p>'
                    f'<div class="empty">No reading has been collected for this metric '
                    f'yet.</div></article>')
        return (
            f'<article class="card" id="m-{e["id"]}">'
            f'<div class="chead"><span class="m">{esc(head)}</span>'
            f'<div class="r">{state}</div></div>'
            f'<div class="cmeta">{esc(meta)}</div>'
            f'<p class="cstmt">{esc(e["stmt"])}</p>'
            f'{collection_row(e)}'
            f'<div class="readout">'
            f'<div><div class="lab">coverage · {win}d</div>'
            f'<div class="big num">{pct_label(r["pct"])}</div></div>'
            f'<div><div class="lab">readings</div>'
            f'<div class="d flat num">{r["read"]} of {r["expected"]} {g}s</div></div>'
            f'<div><div class="lab">latest value</div>'
            f'<div class="d flat num">{latest}</div></div>'
            f'<div><div class="lab">change over {win}d</div>'
            f'<div class="d {delta(d, today, win)["cls"]}">'
            f'{esc(delta(d, today, win)["txt"])}</div></div></div>'
            f'{strip_html(e, today, win)}'
            f'<div class="axis"><span>{esc(key_label(sb["keys"][0]))}</span>'
            f'<span>{esc(bar_caption)}</span>'
            f'<span>{esc(key_label(sb["keys"][-1]))}</span></div>'
            f'{inc}'
            f'{line_svg(d, today, win, show_thr=False)}'
            f'<details class="dtoggle"><summary>show the numbers</summary>'
            f'{dtable(e, today, win)}</details></article>')


    # ====================================================================
    # PAGE ASSEMBLY
    # ====================================================================
    # --------------------------------------------------------------- copy deck
    # Tier framework, program copy and the FY cycle are carried from
    # dashboards/propgf-kernel-mockup_v2.py unchanged, except where a sentence
    # claimed something only the private registry can support.
    TIERS = [
        {"id": "irreplaceable", "name": "Irreplaceable", "v": "--k-t1",
         "label": "Only provider. Network halts without it. No substitute exists.",
         "def": "Ledger, resource, and programmability — what the blockchain and the physical-storage-backed ledger need in order to keep running at all.",
         "example": "Distributed randomness beacon — without it, block production stops.",
         "posture": "Must fund. Non-negotiable security requirements. Audits milestone-gated.",
         "short": "Must fund — non-negotiable"},
        {"id": "essential", "name": "Essential", "v": "--k-t2",
         "label": "Network-critical, but alternatives exist. We need at least one.",
         "def": "Core offerings — disk space from miners, storage primitives in smart contracts — that let participants engage with the irreplaceable components.",
         "example": "Testnets: the network continues without them, but at least one is needed to stage and rehearse upgrades.",
         "posture": "Fund for diversity that ensures uptime — maintain two or more implementations. Budget negotiable.",
         "short": "Fund for redundancy — 2+ implementations"},
        {"id": "important", "name": "Important", "v": "--k-t3",
         "label": "Load-bearing. Multiple dependents. Silent failure cascades.",
         "def": "Supports and improves access to the critical components, and speeds up development of revenue-generating work.",
         "example": "A testnet faucet: it makes test FIL easy to get, but the network runs without it.",
         "posture": "Fund maintenance, not features. Flag any repo with zero active developers.",
         "short": "Fund maintenance, not features"},
    ]

    TIMELINE = [
        {"date": "Jan 2026", "title": "FY26 term begins", "state": "done"},
        {"date": "Apr 2026", "title": "Mid-term audit", "state": "done"},
        {"date": "Aug 2026", "title": "Health reporting live", "state": "now"},
        {"date": "Oct 2026", "title": "Close-out audit", "state": ""},
        {"date": "Nov 2026", "title": "Applications close", "state": ""},
        {"date": "Dec 2026", "title": "Awards published", "state": ""},
        {"date": "Jan 2027", "title": "FY27 term begins", "state": ""},
    ]

    METHOD = [
        ("Two tables, both public",
         "<span class='mono'>filecoin.filpgf_public.kernel_timeseries_metrics_by_project</span> "
         "holds one row per team, function, metric and day. "
         "<span class='mono'>filecoin.filpgf_public.kernel_functions</span> holds the catalogue, "
         "including the functions nothing measures. Both refresh daily, and any OSO API key "
         "reproduces every number on this page."),
        ("Why nothing is scored",
         "Every threshold was withdrawn on <b>2026-08-20</b>. The numbers are stated in signed "
         "appendices, but the agreements carrying them are not executed, and a number nobody has "
         "countersigned is not a commitment. When contracts are signed the bars return unchanged "
         "and history re-judges itself, because the bar is recorded per day."),
        ("Coverage is about us, not them",
         "The percentage on every row is <b>reading coverage</b>: the share of the periods a "
         f"metric's own cadence expects that carry a value, counted from {COVERAGE_FROM} -- the "
         "day unattended nightly collection became the record -- or from the metric's first "
         "reading where that is later. Earlier one-off probes are shown but not scored against, "
         "because charging a team for the month before the monitor existed measures us, not "
         f"them. {' and '.join(sorted(PLATFORM_OUTAGES))} are excluded from every denominator on "
         "this page: our own platform, not any source, returned nothing for all twelve teams "
         "those nights. A gap "
         "means the source produced no defensible number that day — an endpoint down, a schema "
         "moved. That is our failure to measure, not the team's failure to deliver, so it is drawn "
         "as a break in the line rather than a drop to zero, and it never colours a row red."),
        ("What is missing here",
         "Adjudicated committee verdicts, draft metrics not yet adopted, the endpoint behind each "
         "reading and the SQL that reduces it to one number, and anything about what a grant is "
         "worth. The first three are in the internal dashboard; the last belongs on no public "
         "page."),
    ]

    GLOSSARY = [
        ("Kernel", "The funding program covering work the network cannot operate without. Funded as a <b>near-fixed cost</b> on an annual term with audits, not against milestones."),
        ("Function", "A capability the network needs, named by <b>what it does</b> rather than by which repo provides it. Functions outlive implementations — the function survives when the code that serves it is replaced."),
        ("Metric", "One number a funded team is measured on: an indicator with an agreed cadence and a public source, fetched by a pipeline the team does not control. It is the unit every card on this page draws."),
        ("Proposed", "A metric drafted against a function but not yet named in a signed agreement. Monitoring follows the agreements, so a proposed metric is not collected yet."),
        ("Coverage · 90d", "The share of the reading periods the window expects that actually carry a value, counted at each metric's own cadence so a weekly metric is not penalised for being coarse. Low coverage means the metric exists but is not being collected."),
        ("Unscored", "Measured, but not judged. A reading is unscored when no threshold is in force — which today is every reading, because SLA thresholds are still being negotiated."),
        ("Gap", "A period the source was asked and gave no defensible number. Not a zero, not a breach, and not the team's failure — it is a hole in the instrument."),
        ("Tier", "How replaceable a function is, from <b>Irreplaceable</b> to <b>Important</b>. Tier sets the funding posture and whether redundancy is required."),
        ("Single maintainer", "A function measured through exactly one team. Tolerable at lower tiers, a named risk at the top two, where the posture calls for two or more independent implementations."),
    ]

    # Every threshold was withdrawn on 2026-08-20 pending executed agreements. Without this
    # said plainly and above the fold, a viewer reads the coverage percentage as an SLA pass
    # rate, which is the exact misreading the withdrawal was meant to prevent.
    SLA_NOTICE = ('<div class="sla-notice"><span>&#9432;</span><span>'
                  '<b>SLA thresholds are still being negotiated.</b> This page reports what is '
                  'being measured, not whether a target was met. Monitoring follows the signed '
                  'agreements: a function is measured once an agreement names a metric for it.'
                  '</span></div>')

    # The manifests are public, so the page can show anyone exactly what is being observed
    # without the mart having to carry a source column.
    REGISTRY_BASE = "https://github.com/filecoin-project/pgf-monitor/blob/main/registry"

    YES = ('<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">'
           '<path d="M2 6.4 4.6 9 10 3.2" fill="none" stroke="currentColor" stroke-width="2" '
           'stroke-linecap="round" stroke-linejoin="round"/></svg>')
    NO = ('<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">'
          '<path d="M3 3l6 6M9 3l-6 6" fill="none" stroke="currentColor" stroke-width="2" '
          'stroke-linecap="round"/></svg>')
    ARROW = ('<svg width="11" height="11" viewBox="0 0 12 12" aria-hidden="true" '
             'style="vertical-align:-1px"><path d="M2 6h8M6.8 2.8 10 6l-3.2 3.2" fill="none" '
             'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
             'stroke-linejoin="round"/></svg>')
    CARET = ('<svg width="11" height="11" viewBox="0 0 12 12" aria-hidden="true">'
             '<path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" '
             'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>')


    def tier_by_id(tid):
        return next((t for t in TIERS if t["id"] == tid), None)


    def pct_label(v):
        return "—" if v is None else f"{v:.1f}%"


    def cov_pill(ag):
        if ag["pct"] is None:
            return '<span class="pill nm">not measured</span>'
        if ag["state"] == "good":
            return f'<span class="pill ok">{ICON["good"]} collecting</span>'
        return f'<span class="pill gap">{ICON["warn"]} gaps in collection</span>'


    def row_strip(ents, today):
        """The row's own strip: the commitment collected least completely.

        A row is only as well measured as its worst commitment, so that is the one drawn --
        the same rule the mockup uses for its worst-SLA metric.
        """
        if not ents:
            return '<div class="strip sm"></div>'
        worst = min(ents, key=lambda e: (roll(e, today)["pct"]
                                         if roll(e, today)["pct"] is not None else 101))
        row_bars = 46
        sbw = strip_bits(worst, today)
        if not sbw["keys"]:
            return '<div class="strip sm"></div>'
        span = 1 if len(sbw["keys"]) <= row_bars else -(-len(sbw["keys"]) // row_bars)
        cad = f'{span} {sbw["g"]}s' if span > 1 else f'1 {sbw["g"]}'
        return (strip_html(worst, today, small=True, max_bars=row_bars)
                + f'<div class="rowcad">1 bar = {cad}'
                + (f' · worst of {len(ents)}' if len(ents) > 1 else '') + '</div>')


    def build_public_page(reg):
        """reg = {'kfs':[...], 'entries':[...], 'projects':[...], 'today':'YYYY-MM-DD'}.

        The mockup's page, section for section, minus what the public tables cannot support:
        no committed amounts anywhere, no endpoint block on a card, and coverage wherever the
        mockup shows an SLA percentage.
        """
        E, KF, PR, today = reg["entries"], reg["kfs"], reg["projects"], reg["today"]
        ents = lambda f: [E[i] for i in f["e"]]
        teams_of = lambda f: list(dict.fromkeys(e["team"] for e in ents(f)))
        watched = [f for f in KF if f["e"]]
        n_rows = sum(len(e["s"]["v"]) for e in E)
        n_read = sum(e["n_real"] for e in E)
        teams = sorted({e["team"] for e in E})
        grants = sorted({e["grant"] for e in E if e["grant"]})

        # Collection status, derived rather than asserted. `run` is the trailing run of days on
        # which the unattended pipeline produced rows at all -- it is what makes a 23% coverage
        # figure legible, because most of the window predates the loop. `dry` is the trailing run
        # of days on which it produced rows and not one of them carried a value, which is the one
        # thing a reader must not mistake for every team failing at once.
        day = {}
        for e in E:
            _b = as_date(e["s"]["d0"])
            for _off, _v in zip(e["s"]["off"], e["s"]["v"]):
                _d = (_b + datetime.timedelta(days=_off)).isoformat()
                _r, _k = day.get(_d, (0, 0))
                day[_d] = (_r + 1, _k + (0 if _v is None else 1))
        run, cur = None, as_date(today)
        while cur.isoformat() in day:
            run = cur.isoformat()
            cur -= datetime.timedelta(days=1)
        dry, cur = 0, as_date(today)
        while cur.isoformat() in day and day[cur.isoformat()][1] == 0:
            dry += 1
            cur -= datetime.timedelta(days=1)
        status = ""
        if run:
            status = (f' The unattended pipeline has produced a reading every day since '
                      f'<b>{esc(short(run))}</b>; anything earlier was collected by hand during a '
                      f'review, which is why coverage over a {WIN}-day window reads low.')
        if dry:
            status += (f' Nothing has carried a value for <b>{dry} day'
                       f'{"s" if dry > 1 else ""}</b> — that is one gap in the instrument, not '
                       f'{len(E)} metrics failing at once.')

        out = []
        a = out.append

        # -------------------------------------------------------------- nav
        a('<nav class="nav"><div class="wrap nav-in">'
          '<a class="crumb" href="#k-top">fil<span class="fil">pgf</span>.io '
          '<span style="opacity:.4">/</span> <b>Kernel</b> '
          '<span style="opacity:.4">/</span> Monitoring</a>'
          '<div class="nav-links">'
          '<a href="#k-objective">Objective</a><a href="#k-timeline">Timeline</a>'
          '<a href="#k-categories">Categories</a><a href="#k-functions">Inventory</a>'
          '<a href="#k-metrics">Coverage</a><a href="#k-method">Method</a>'
          '<a href="#k-terms">Terms</a></div>'
          '<a class="nav-cta" href="#k-method">Query it yourself</a>'
          '</div></nav>')

        # ------------------------------------------------------------- hero
        a('<header class="hero" id="k-top"><div class="wrap">'
          '<p class="eyebrow">Kernel · Independent monitoring</p>'
          '<h1>What is being watched.</h1>'
          '<p class="lede">Every night, each metric below is fetched from the team\'s own '
          'infrastructure by a pipeline they do not control, and the reading is appended to a '
          'public record. Nothing here is scored: the numbers exist, the bars do not, because no '
          'agreement carrying one has been executed yet.</p>'
          '<div class="ladder"><div class="ladder-h">'
          '<span></span><span>Tier</span><span>Functions</span>'
          f'<span>Coverage · {WIN}d</span><span>Funding posture</span></div>')

        for t in TIERS:
            fns = [f for f in KF if f["tier"] == t["id"]]
            seen = [f for f in fns if f["e"]]
            ag = agg([e for f in fns for e in ents(f)], today)
            if not fns:
                count = ('<div class="rung-c" style="font-size:13px;color:var(--k-ink-3)">'
                         'Pending</div><div class="rung-cl">not inventoried</div>')
            else:
                count = (f'<div class="rung-c">{len(fns)}</div>'
                         f'<div class="rung-cl">in inventory</div>')
            note = (f'{len(seen)} of {len(fns)} reporting' if fns else "nothing to report")
            a(f'<a class="rung" href="#k-functions">'
              f'<span class="rung-bar" style="background:var({t["v"]})"></span>'
              f'<span><span class="rung-n">{esc(t["name"])}</span>'
              f'<span class="rung-s">{esc(t["label"])}</span></span>'
              f'<span>{count}</span>'
              f'<span><span class="rung-c">{pct_label(ag["pct"])}</span>'
              f'<span class="rung-cl">{esc(note)}</span></span>'
              f'<span class="rung-p">{esc(t["short"])}</span></a>')
        a('</div></div></header>')

        # ------------------------------------------------------- provenance
        a('<div class="prov-bar"><div class="wrap prov-in"><div>'
          f'Every figure on this page is read from two public tables in the OSO warehouse as of '
          f'<span class="mono">{esc(today)}</span> — '
          f'<span class="mono">kernel_timeseries_metrics_by_project</span> and '
          f'<span class="mono">kernel_functions</span>. No private source, no embedded snapshot '
          f'and no illustrative history: any OSO API key reproduces every one of the '
          f'<b>{n_rows}</b> daily rows, <b>{n_read}</b> of which carry a value.'
          f'{status}'
          '</div></div></div>')

        # -------------------------------------------------------- objective
        a('<section class="sec" id="k-objective"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Objective</p>'
          '<h2>Keep the floor from moving</h2></div>'
          '<div class="split"><div>'
          '<p>Most of what Filecoin runs on is maintained by small teams, and much of it has no '
          'second implementation. When one of those goes unfunded, nothing breaks on the day it '
          'happens — the repo just goes quiet, the maintainer moves on, and the network carries a '
          'dependency nobody is watching. Kernel exists to make that failure mode visible and to '
          'pay for it not to happen.</p>'
          '<p>The program starts from a map, not a wishlist. Every capability the network needs is '
          'written down as a <b>function</b>, independent of which repo currently provides it. Each '
          'function is placed in a tier according to how replaceable it is, and each tier carries a '
          'different funding posture — some are non-negotiable, some are funded for redundancy, some '
          'are funded only for maintenance.</p>'
          '<p>Funding follows an annual term with audits rather than milestones, because keeping '
          'something working is a continuous obligation and not a deliverable. This page is the '
          'audit trail: every metric on it names a reading cadence and a public source anyone '
          'can call. The thresholds those readings will be judged against are written down, and '
          'withdrawn until the agreements carrying them are executed — so what you are looking at '
          'is the instrument, working, before it is allowed to score anyone.</p>'
          '<a class="btn" href="#k-functions">See the inventory</a></div>'
          '<div class="panel"><div class="panel-t">Kernel funds</div><ul class="yn">'
          f'<li class="y"><i>{YES}</i><span>Maintenance of functions the network cannot operate without</span></li>'
          f'<li class="y"><i>{YES}</i><span>A second implementation where a single one is a systemic risk</span></li>'
          f'<li class="y"><i>{YES}</i><span>Monitoring, testnets, and incident response that keep the network observable</span></li>'
          f'<li class="y"><i>{YES}</i><span>Security and upgrade work required to stay production-safe</span></li>'
          '</ul><div class="panel-t">Kernel does not fund</div><ul class="yn">'
          f'<li class="n"><i>{NO}</i><span>New features or product expansion — that is Revenue Development</span></li>'
          f'<li class="n"><i>{NO}</i><span>Exploratory or unproven work — that is R&amp;D</span></li>'
          f'<li class="n"><i>{NO}</i><span>Functions with no maintainer willing to report health metrics</span></li>'
          '</ul></div></div></div></section>')

        # --------------------------------------------------------- timeline
        a('<section class="sec sec-alt" id="k-timeline"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Timeline</p><h2>One term, two audits</h2>'
          '<p class="lede">Kernel grants run on an annual term. Audits fall mid-term and at close, '
          'and each one checks the agreed resilience metrics rather than a feature list.</p></div>'
          '<div class="round"><div><div class="round-k">Next round opening</div>'
          '<div class="round-v">FY27 intake opens October 2026</div>'
          '<p>Applications close in November, awards are published in December, and the new term '
          'begins in January. Existing grantees re-apply on the same cycle.</p></div>'
          f'<a href="https://app.filpgf.io/" target="_blank" rel="noopener noreferrer">'
          f'Get notified {ARROW}</a></div><div class="tl">')
        for t in TIMELINE:
            a(f'<div class="tl-i {t["state"]}"><div class="tl-d">{esc(t["date"])}</div>'
              f'<div class="tl-t">{esc(t["title"])}</div></div>')
        a('</div></div></section>')

        # ------------------------------------------------------- tier cards
        a('<section class="sec" id="k-categories"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Categories</p>'
          '<h2>Four tiers, set by what happens without it</h2>'
          '<p class="lede">A function\'s tier is decided by substitutability, not by how much anyone '
          'likes it. That single judgement then drives how much scrutiny it gets, whether redundancy '
          'is required, and how negotiable the budget is.</p></div><div class="tiers">')
        for t in TIERS:
            fns = [f for f in KF if f["tier"] == t["id"]]
            band = f'{len(fns)} functions' if fns else "inventory pending"
            a(f'<article class="tier">'
              f'<div class="tier-band" style="background:var({t["v"]})">{esc(t["name"])}'
              f'<em>{esc(band)}</em></div>'
              f'<div class="tier-b"><div class="tier-lab">{esc(t["label"])}</div>'
              f'<p>{esc(t["def"])}</p><div class="tier-rows">'
              f'<div class="tier-row"><div class="tier-k">Example</div>'
              f'<div class="tier-v">{esc(t["example"])}</div></div>'
              f'<div class="tier-row"><div class="tier-k">Posture</div>'
              f'<div class="tier-v">{esc(t["posture"])}</div></div>'
              f'</div></div></article>')
        a('</div></div></section>')

        # -------------------------------------------------------- inventory
        a('<section class="sec sec-alt" id="k-functions"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Inventory</p><h2>The inventory</h2>'
          '<p class="lede">The same metrics, read two ways. <b>By project</b> asks what each '
          'reporting team is on the hook for; <b>by function</b> asks what the network needs '
          'and whether anyone is watching it. Open any row for the metrics behind it — what '
          'is collected, when, and every reading taken.</p>'
          '<div class="legend">'
          '<span><i style="background:var(--k-fil)"></i>reading collected</span>'
          '<span><i style="background:var(--k-warn)"></i>no defensible number</span>'
          '<span><i style="background:var(--k-skip)"></i>our platform was down</span>'
          '<span><i style="background:var(--k-none)"></i>no reading taken</span></div>'
          '</div></div>')

        # Radio + :checked rather than a script: the page is exported statically, so a
        # JS tab bar would come out dead. The panels must stay siblings of the inputs.
        a(f'<div class="wrap">{SLA_NOTICE}</div>'
          '<div class="kviews">'
          '<input type="radio" name="kview" id="kv-fn">'
          '<input type="radio" name="kview" id="kv-pr" checked>'
          '<div class="wrap"><div class="viewbar" role="tablist">'
          f'<label for="kv-pr">By project <b>{len(PR)}</b></label>'
          f'<label for="kv-fn">By function <b>{len(KF)}</b></label>'
          '</div></div>'
          '<div class="wrap vpanel v-fn">')

        for t in TIERS:
            fns = [f for f in KF if f["tier"] == t["id"]]
            seen = [f for f in fns if f["e"]]
            prop = [f for f in fns if not f["e"] and f["drafts"]]
            head = ((f'{len(seen)} of {len(fns)} monitored'
                     + (f' · {len(prop)} proposed' if prop else ""))
                    if fns else "inventory pending")
            a(f'<div class="fgroup"><div class="fg-h">'
              f'<span class="fg-n" style="color:var({t["v"]})">{esc(t["name"])}</span>'
              f'<span class="fg-c">{esc(head)}</span></div>')
            if not fns:
                a(f'<div class="note">Functions in this tier have not been inventoried yet. '
                  f'Posture is set — {esc(t["short"].lower())} — but nothing is being measured '
                  f'against it.</div></div>')
                continue
            for dom in dict.fromkeys(f["sub"] for f in fns):
                a(f'<div class="dom">{esc(dom)}</div>')
                for f in sorted([x for x in fns if x["sub"] == dom],
                                key=lambda x: (not x["e"], x["name"])):
                    a(function_row(f, t, today, ents(f), teams_of(f)))
            a('</div>')
        a('</div>')

        # ---------------------------------------------------- by project
        a('<div class="wrap vpanel v-pr">')
        covered = len({e["kernel_id"] for e in E if e["kernel_id"]})
        overall = agg(E, today)
        # Monitoring follows the signed agreements, so a function nobody has committed to is
        # WAITING, not failing. The three-way split says which: proposed but unsigned, or not
        # yet scoped at all. All 31 stay in the denominator -- coverage against only the covered
        # functions always reads 100%.
        drafted = [f for f in KF if not f["e"] and f["drafts"]]
        unscoped = [f for f in KF if not f["e"] and not f["drafts"]]
        a('<div class="mets two" style="margin-bottom:34px">'
          f'<div class="met"><div class="met-v">{len(watched)}'
          f'<span style="color:var(--k-ink-3)">/{len(KF)}</span></div>'
          f'<div class="met-k">Kernel functions monitored</div>'
          f'<div class="met-d">{len(drafted)} with metrics proposed, awaiting a signed '
          f'appendix · {len(unscoped)} not yet scoped</div></div>'
          f'<div class="met"><div class="met-v">{len(E)}</div>'
          f'<div class="met-k">Metrics collected</div>'
          f'<div class="met-d">{len(teams)} teams · {len(grants)} grants</div></div>'
          '</div>')
        with_grant = [p for p in PR if p["grants"]]
        without = [p for p in PR if not p["grants"]]
        for label, group, note in (
            ("Reporting under a grant", with_grant,
             "Each row is one Karma application and the metrics it pays for."),
            ("Reporting with no grant against it", without,
             "Metrics nobody is paid for — cross-checks we run at our own expense."),
        ):
            if not group:
                continue
            a(f'<div class="fgroup"><div class="fg-h">'
              f'<span class="fg-n">{esc(label)}</span>'
              f'<span class="fg-c">{len(group)} row{"s" if len(group) != 1 else ""}</span></div>'
              f'<div class="dom">{esc(note)}</div>')
            for p in group:
                a(project_row(p, today, E, KF))
            a('</div>')
        a('</div>')  # /v-pr
        a('</div></section>')  # /kviews /section

        # --------------------------------------------------- program metrics
        a('<section class="sec" id="k-metrics"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Coverage</p>'
          '<h2>How much of the Kernel is actually observed</h2>'
          '<p class="lede">Aggregate health matters less than coverage, and with no bar in force '
          'coverage is the only claim this page can make. A function with no reporter and no metric '
          'is invisible here, which is exactly what makes it dangerous.</p></div>'
          '<div class="mets">')
        for c in program_metrics(KF, E, PR, today, teams_of, overall):
            a(f'<div class="met"><div class="met-v">{esc(c["v"])}</div>'
              f'<div class="met-k">{esc(c["k"])}</div>'
              f'<div class="met-d {c["cls"]}">{esc(c["d"])}</div></div>')
        a('</div><p class="note" style="margin-top:22px">Every reading on this page is derived from '
          'the two public tables named below. Metrics for individual projects and repos live in the '
          f'<a href="https://app.filpgf.io/projects" target="_blank" rel="noopener noreferrer" '
          f'style="color:var(--k-fil-deep);white-space:nowrap">explorer {ARROW}</a>'
          '</p></div></section>')

        # ----------------------------------------------------------- method
        a('<section class="sec sec-alt" id="k-method"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Method</p>'
          '<h2>What this page can and cannot tell you</h2>'
          '<p class="lede">The page is built only from tables anyone can query. That constraint is '
          'the point, and it is also the limit.</p></div><dl class="terms">')
        for dt, dd in METHOD:
            a(f'<div class="term"><dt>{esc(dt)}</dt><dd>{dd}</dd></div>')
        a('</dl></div></section>')

        # --------------------------------------------------------- glossary
        a('<section class="sec" id="k-terms"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Terms</p>'
          '<h2>What these words mean here</h2>'
          '<p class="lede">Kernel uses a few words in a specific way. Getting them straight is most '
          'of understanding the program.</p></div><dl class="terms">')
        for dt, dd in GLOSSARY:
            a(f'<div class="term"><dt>{esc(dt)}</dt><dd>{dd}</dd></div>')
        a('</dl></div></section>')

        # ----------------------------------------------------------- footer
        a('<footer class="foot"><div class="wrap foot-in">'
          f'<span>Filecoin Kernel · independent monitoring · {esc(today)}</span>'
          '<span class="foot-links">'
          '<a href="https://github.com/filecoin-project/pgf-monitor">pipeline &amp; registry</a>'
          '<a href="#k-method">Method</a><a href="#k-top">Top</a></span>'
          '</div></footer>')

        return f'<div class="kpage" id="k-page">{"".join(out)}</div>'


    # ------------------------------------------------------------ components

    def function_row(f, t, today, es, teams):
        """One kernel function, with every commitment that evidences it.

        The mockup splits health metrics from growth counters; the public mart carries no such
        classification, so every commitment sits in one list and the row says nothing about
        which of them could report an outage.
        """
        ag = agg(es, today)
        seen = {}
        for e in es:
            seen[e["fid"]] = seen.get(e["fid"], 0) + 1
        dup_fids = {k for k, v in seen.items() if v > 1}
        n = len(teams)

        flags = []
        if n == 0:
            flags.append('<span class="flag bad">no maintainer reporting</span>')
        elif n == 1:
            flags.append('<span class="flag solo">single maintainer</span>')
        if es:
            flags.append(f'{len(es)} metric{"s" if len(es) > 1 else ""}')
        else:
            flags.append('<span class="none">nothing measured</span>')
        if f["drafts"]:
            flags.append(f'{f["drafts"]} proposed, not yet committed')
        meta = f'<div class="fn-m">{" · ".join(flags)}</div>'

        summary = (
            f'<summary>'
            f'<div><div class="fn-cat" style="color:var({t["v"]})">{esc(t["name"])} · '
            f'{esc(f["cat"])}</div>'
            f'<div class="fn-t">{esc(f["name"])}</div>{meta}</div>'
            f'<div class="fn-rowstrip">{row_strip(es, today)}</div>'
            f'<div class="fn-s"><div class="fn-p">{pct_label(ag["pct"])}</div>'
            f'<div class="fn-l">{"COVERAGE · %dD" % WIN if ag["pct"] is not None else "NO DATA"}'
            f'</div>{cov_pill(ag)}</div>'
            f'<span class="car">{CARET}</span></summary>')

        team_names = (", ".join(esc(x) for x in teams) if teams
                      else '<span class="dim">no team reporting yet</span>')
        grants = sorted({e["grant"] for e in es if e["grant"]})
        cells = [
            ("Teams reporting", team_names),
            ("Domain", f'<span class="dim">{esc(f["sub"])}</span>'),
            ("Metrics", f'<span class="num">{len(es)}</span>'),
            ("Proposed, not adopted", f'<span class="num">{f["drafts"]}</span>'),
            ("Grants", (" ".join(f'<span class="mono">{esc(g)}</span>' for g in grants)
                        if grants else '<span class="dim">none</span>')),
        ]
        grid = "".join(f'<div><div class="fm-k">{esc(k)}</div><div class="fm-v">{v}</div></div>'
                       for k, v in cells)

        body = [f'<div class="fn-d"><p class="fn-purpose">{esc(f["why"])}</p>'
                f'<div class="fn-grid">{grid}</div>']

        if es:
            body.append(f'<div class="metrics-head"><h4>Metrics</h4>'
                        f'<span>{len(es)} metric{"s" if len(es) > 1 else ""} · measured nightly, '
                        f'judged by nothing yet</span></div><div class="cards">'
                        + "".join(metric_card(e, today, qualify=e["fid"] in dup_fids)
                                  for e in es) + '</div>')
        else:
            extra = (f' {f["drafts"]} metric{"s" if f["drafts"] > 1 else ""} '
                     f'{"have" if f["drafts"] > 1 else "has"} been proposed against it, and '
                     f'{"are" if f["drafts"] > 1 else "is"} not yet adopted.'
                     if f["drafts"] else "")
            body.append('<div class="empty"><b>Nobody reports on this function.</b>'
                        f'{extra} Nothing on this page can tell you whether it is healthy, so an '
                        'interruption here would be invisible.</div>')
        body.append('</div>')
        return f'<details class="fn">{summary}{"".join(body)}</details>'


    def project_row(p, today, E, KF):
        """One grant, with every commitment it pays for.

        The mirror image of `function_row`, and the mockup's project row with the money taken
        out: no committed figure, and the bar that carried it now carries coverage instead.
        """
        es = [E[i] for i in p["e"]]
        ag = agg(es, today)
        kf_by_id = {f["kernel_id"]: f for f in KF}
        fns = [kf_by_id[k] for k in dict.fromkeys(e["kernel_id"] for e in es) if k in kf_by_id]
        tiers = [t for t in TIERS if any(f["tier"] == t["id"] for f in fns)]
        top_tier = tiers[0] if tiers else None

        # "1 Irreplaceable · 6 Essential" rather than a single tier name: a project that touches
        # one irreplaceable function and six essential ones is not an irreplaceable project.
        eyebrow = " · ".join(
            f'{sum(1 for f in fns if f["tier"] == t["id"])} {t["name"]}'
            for t in tiers) or "No kernel function mapped"
        colour = top_tier["v"] if top_tier else "--k-ink-3"

        bits = [f'{len(es)} metric{"s" if len(es) != 1 else ""}',
                f'{len(fns)} kernel function{"s" if len(fns) != 1 else ""}']
        bits.append(f'<span class="mono">{esc(p["grants"][0])}</span>' if p["grants"]
                    else '<span class="quiet">no grant against it</span>')
        meta = f'<div class="fn-m">{" · ".join(bits)}</div>'

        bar = ""
        if ag["pct"] is not None:
            bar = (f'<div class="ftrack"><span class="fbar" '
                   f'style="width:{max(2, round(ag["pct"]))}%"></span></div>')

        summary = (
            f'<summary>'
            f'<div><div class="fn-cat" style="color:var({colour})">{esc(eyebrow)}</div>'
            f'<div class="fn-t">{esc(p["name"])}</div>{meta}{bar}</div>'
            f'<div class="fn-rowstrip">{row_strip(es, today)}</div>'
            f'<div class="fn-s"><div class="fn-p">{pct_label(ag["pct"])}</div>'
            f'<div class="fn-l">{"COVERAGE · %dD" % WIN if ag["pct"] is not None else "NO DATA"}'
            f'</div>{cov_pill(ag)}</div>'
            f'<span class="car">{CARET}</span></summary>')

        cells = [
            ("Kernel functions", f'<span class="num">{len(fns)}</span>'),
            ("Metrics", f'<span class="num">{len(es)}</span>'),
            ("Grant", (" ".join(f'<span class="mono">{esc(g)}</span>' for g in p["grants"])
                       if p["grants"] else '<span class="dim">no grant pays for this</span>')),
            ("OSO project", (f'<span class="mono">{esc(p["slug"])}</span>' if p["slug"]
                             else '<span class="dim">not mapped</span>')),
        ]
        body = ['<div class="fn-d">',
                '<div class="fn-grid">' + "".join(
                    f'<div><div class="fm-k">{esc(k)}</div><div class="fm-v">{v}</div></div>'
                    for k, v in cells) + '</div>']

        if fns:
            chips = "".join(
                f'<span><i style="color:var({tier_by_id(f["tier"])["v"]})">'
                f'{esc(tier_by_id(f["tier"])["name"])}</i>{esc(f["name"])}</span>'
                for f in fns if tier_by_id(f["tier"]))
            body.append('<div class="pfns"><div class="dk">Kernel functions evidenced</div>'
                        f'<div class="chips">{chips}</div></div>')

        dup = {k for k, v in
               {e["fid"]: sum(1 for x in es if x["fid"] == e["fid"]) for e in es}.items() if v > 1}
        body.append(f'<div class="metrics-head"><h4>Metrics</h4>'
                    f'<span>{len(es)} metric{"s" if len(es) != 1 else ""} · '
                    f'{sum(x["n_real"] for x in es)} readings in the public table</span>'
                    f'</div><div class="cards">'
                    + "".join(metric_card(e, today, show_team=False, qualify=e["fid"] in dup)
                              for e in sorted(es, key=lambda x: x["fid"])) + '</div>')
        body.append('</div>')
        return f'<details class="fn">{summary}{"".join(body)}</details>'


    def program_metrics(KF, E, PR, today, teams_of, overall):
        listed = len(KF)
        watched = [f for f in KF if f["e"]]
        top_solo = sum(1 for f in KF
                       if f["tier"] in ("irreplaceable", "essential") and len(teams_of(f)) == 1)
        drafted = sum(1 for f in KF if not f["e"] and f["drafts"])
        unscoped = sum(1 for f in KF if not f["e"] and not f["drafts"])
        drafts = sum(f["drafts"] for f in KF)
        teams = len({e["team"] for e in E})
        cover = round(len(watched) / listed * 100) if listed else 0
        return [
            {"v": f"{cover}%", "k": "Kernel functions monitored",
             "d": f"{len(watched)} of {listed}, each under a signed agreement",
             "cls": ""},
            {"v": pct_label(overall["pct"]), "k": f"Reading coverage · rolling {WIN} days",
             "d": f'{overall["read"]} of {overall["expected"]} expected reading periods carry a '
                  f'value', "cls": "warn" if overall["state"] == "warn" else ""},
            {"v": str(len(E)), "k": "Metrics collected",
             "d": f"{teams} teams · {len(PR)} grant rows", "cls": ""},
            {"v": str(drafted), "k": "Functions with metrics proposed",
             "d": f"{drafts} metrics drafted, awaiting a signed appendix", "cls": ""},
            {"v": str(unscoped), "k": "Functions not yet scoped",
             "d": "No metric proposed against them yet", "cls": ""},
            {"v": str(top_solo), "k": "Top-tier functions measured through one team only",
             "d": "Posture calls for 2+ implementations", "cls": "bad" if top_solo else ""},
        ]

    return (build_public_page,)


@app.cell(hide_code=True)
def live_registry(build_registry, mo, pyoso_db_conn, to_rows):
    # The mockup carries its registry as a gzipped base64 blob. This one reads the same shape out
    # of the two public tables, so the page cannot describe a world the warehouse does not.
    _series = mo.sql(
        """
        SELECT sample_date, team, project_display_name, oso_project_slug, function_id,
               metric_name, grant_ref, kernel_id, kernel_function, tier, category, sub_category,
               amount, threshold_op, threshold_value, threshold_source, method, cadence,
               sla_statement
        FROM filecoin.filpgf_public.kernel_timeseries_metrics_by_project
        ORDER BY team, function_id, metric_name, sample_date
        """,
        output=False,
        engine=pyoso_db_conn,
    )
    # `draft_metrics` is why the catalogue is read at all: a function nothing measures has no row
    # in the series to ride on, and a coverage figure computed without it always reads 100%.
    _functions = mo.sql(
        """
        SELECT kernel_id, tier, category, sub_category, kernel_function, kernel_value,
               is_in_scope, adopted_metrics, draft_metrics, adopted_teams
        FROM filecoin.filpgf_public.kernel_functions
        ORDER BY tier, category, kernel_function
        """,
        output=False,
        engine=pyoso_db_conn,
    )
    REGISTRY = build_registry(to_rows(_series), to_rows(_functions))
    return (REGISTRY,)


@app.cell(hide_code=True)
def row_reader():
    def to_rows(result):
        """A query result as a list of row dicts, whichever frame mo.sql hands back.

        `list(df)` on a pandas DataFrame yields its COLUMN NAMES, not its rows -- which is how the
        first version of this cell fed build_registry a list of strings and died on
        `string indices must be integers`. Polars is asked first because mo.sql returns it here;
        pandas is the fallback, and anything else is an error rather than a guess.
        """
        if hasattr(result, "to_dicts"):          # polars
            return result.to_dicts()
        if hasattr(result, "to_dict"):           # pandas
            return result.to_dict("records")
        rows = list(result)
        if rows and not isinstance(rows[0], dict):
            raise TypeError(f"expected row dicts, got {type(rows[0]).__name__}")
        return rows

    return (to_rows,)


@app.cell(hide_code=True)
def registry_shape(PLATFORM_OUTAGES, datetime):
    def build_registry(rows, functions):
        """Rows -> the {kfs, entries, projects, today} shape the page renders.

        Readings are packed as day-offsets from the first one, exactly as the mockup packs them,
        so the chart and strip helpers can be reused unchanged.
        """
        def _txt(v):
            # polars hands back None, pandas hands back NaN for a missing varchar
            if v is None or v != v:
                return ""
            return str(v)

        def _iso(v):
            return v if isinstance(v, str) else v.isoformat()

        by_key = {}
        for r in rows:
            key = (r["team"], r["function_id"], r["metric_name"])
            by_key.setdefault(key, []).append(r)

        entries = []
        for (team, fid, metric), rs in sorted(by_key.items()):
            rs = sorted(rs, key=lambda x: _iso(x["sample_date"]))
            d0 = _iso(rs[0]["sample_date"])
            base = datetime.date.fromisoformat(d0)

            # An unmeasurable day is carried as a null value rather than dropped, so the line
            # breaks where the source failed instead of interpolating over it.
            def _num(v):
                # polars hands back None, pandas hands back NaN, and `NaN is None` is False --
                # which silently turned unmeasurable days into plottable garbage. v != v is the
                # NaN test that needs no numpy import.
                if v is None or v != v:
                    return None
                return float(v)

            offs, vals, outs, methods = [], [], [], {}
            for r in rs:
                offs.append((datetime.date.fromisoformat(_iso(r["sample_date"])) - base).days)
                _v = _num(r["amount"])
                vals.append(_v)
                # "x" -- read as no-reading everywhere, but never counted as a gap.
                outs.append("u" if _v is not None else
                            ("x" if _iso(r["sample_date"]) in PLATFORM_OUTAGES else "i"))
                _m = _txt(r.get("method")) or "unknown"
                methods[_m] = methods.get(_m, 0) + 1
            last = rs[-1]
            display = next((_txt(r.get("project_display_name")) for r in reversed(rs)
                            if _txt(r.get("project_display_name"))), "")
            entries.append({
                "id": len(entries),
                "team": team,
                "project": display or team,
                "slug": _txt(last.get("oso_project_slug")),
                "fid": fid,
                "metric": metric,
                "grant": _txt(last.get("grant_ref")),
                "kernel_id": _txt(last.get("kernel_id")),
                "kf": _txt(last.get("kernel_function")),
                "tier": _txt(last.get("tier")),
                "cat": _txt(last.get("category")),
                "sub": _txt(last.get("sub_category")),
                "cad": _txt(last.get("cadence")) or "daily",
                "stmt": _txt(last.get("sla_statement")),
                # No bar is in force, so the card draws no threshold line and claims no verdict.
                "op": last.get("threshold_op"),
                "thr": last.get("threshold_value"),
                "thr_src": _txt(last.get("threshold_source")),
                "methods": methods,
                "n_real": sum(1 for v in vals if v is not None),
                "s": {"d0": d0, "off": offs, "v": vals, "o": outs},
            })

        by_kernel = {}
        for e in entries:
            by_kernel.setdefault(e["kernel_id"], []).append(e["id"])

        kfs = [{
            "kernel_id": _txt(f["kernel_id"]),
            "name": _txt(f["kernel_function"]),
            "tier": _txt(f["tier"]),
            "cat": _txt(f["category"]),
            "sub": _txt(f["sub_category"]),
            "why": _txt(f.get("kernel_value")),
            "in_scope": bool(f.get("is_in_scope")),
            "drafts": int(f.get("draft_metrics") or 0),
            "e": by_kernel.get(_txt(f["kernel_id"]), []),
        } for f in functions]

        # A row of the "by project" view is one GRANT, not one team: a recipient can hold two
        # (ChainSafe holds Forest and Community Services), and `team` cannot tell them apart.
        # The one commitment no grant pays for gets its own row rather than being hidden.
        groups = {}
        for e in entries:
            key = e["grant"] or f'team:{e["team"]}'
            g = groups.setdefault(key, {"name": e["project"], "team": e["team"],
                                        "slug": e["slug"], "grants": [], "e": []})
            g["e"].append(e["id"])
            if e["grant"] and e["grant"] not in g["grants"]:
                g["grants"].append(e["grant"])
        projects = sorted(groups.values(), key=lambda p: (not p["grants"], p["name"].lower()))

        today = ""
        for e in entries:
            base = datetime.date.fromisoformat(e["s"]["d0"])
            last = (base + datetime.timedelta(days=e["s"]["off"][-1])).isoformat()
            today = max(today, last)
        return {"kfs": kfs, "entries": entries, "projects": projects, "today": today}

    return (build_registry,)


@app.cell(hide_code=True)
def _():
    import datetime
    import math

    return datetime, math


@app.cell(hide_code=True)
def setup_pyoso():
    # This code sets up pyoso to be used as a database provider for this notebook
    # This code is autogenerated. Modification could lead to unexpected results :)
    import pyoso
    import marimo as mo

    pyoso_db_conn = pyoso.Client().dbapi_connection()
    return mo, pyoso_db_conn


if __name__ == "__main__":
    app.run()
