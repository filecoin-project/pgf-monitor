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
          --k-go:#1A7F4B; --k-wait:#C98A00;

          --k-display:'Archivo',system-ui,sans-serif;
          --k-body:'Inter',system-ui,sans-serif;
          --k-mono:'IBM Plex Mono',ui-monospace,monospace;
          --k-wrap:1180px; --k-gutter:28px;

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
        .kpage .lede{color:var(--k-ink-2);font-size:16.5px;max-width:64ch;margin:16px 0 0}
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
        .kpage .hero .lede{font-size:18px;max-width:60ch}

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
        .kpage .sec-head{max-width:66ch;margin-bottom:42px}

        /* provenance banner */
        .kpage .prov-bar{background:var(--k-paper-2);border-bottom:1px solid var(--k-rule)}
        .kpage .prov-in{display:flex;gap:14px;align-items:flex-start;padding:15px 0}
        .kpage .prov-in svg{flex:none;margin-top:2px;color:var(--k-t2)}
        .kpage .prov-in div{font-size:13px;color:var(--k-ink-3);max-width:96ch}
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
        .kpage .car{color:var(--k-ink-3);transition:transform .18s;justify-self:end;display:flex;align-items:center}
        .kpage details.fn[open] .car{transform:rotate(180deg);color:var(--k-ink)}
        .kpage .flag{font-family:var(--k-mono);font-size:10.5px;letter-spacing:.02em}
        .kpage .flag.solo{color:var(--k-t2)}
        .kpage .flag.bad{color:var(--k-t1)}
        .kpage .fn-rowstrip{min-width:0}
        .kpage .rowcad{font-family:var(--k-mono);font-size:9px;letter-spacing:.04em;line-height:1.4;color:var(--k-ink-3);margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

        /* expanded detail panel */
        .kpage .fn-d{padding:18px}
        .kpage .fn-purpose{font-size:14.5px;color:var(--k-ink-2);margin:0;max-width:82ch}
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
        .kpage .cstmt{font-size:13.5px;color:var(--k-ink-2);margin:11px 0 0;max-width:88ch}

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
def public_engine(datetime, math):
    # The formatting, axis and line-chart helpers are lifted VERBATIM from
    # dashboards/propgf-kernel-mockup_v2.py so the two pages cannot drift apart visually. What is
    # authored here is the page composition, because the mockup's own builder renders program
    # sections this page must not have: committed amounts per team, source endpoints, and an SLA
    # verdict vocabulary (p/f/i) that has no member meaning "measured, but no bar was agreed" --
    # which is the state of every metric on this page.
    WIN = 90

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


    GRAIN = {"daily": 1, "weekly": 7, "monthly": 30}
    def pts(e, today, win=WIN):
        """Readings inside the window as [(iso, value, outcome)], oldest first."""
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


    def grain_word(cad):
        return {"daily": "day", "weekly": "week", "monthly": "month"}.get(cad, "period")


    def delta(e, today, win=WIN):
        p = pts(e, today, win)
        if len(p) < 2:
            return {"cls": "flat", "txt": "—"}
        f, l = p[0][1], p[-1][1]
        if not f:
            return {"cls": "flat", "txt": "—"}
        pc = ((l - f) / abs(f)) * 100
        return {"cls": "up" if pc > 1.5 else ("dn" if pc < -1.5 else "flat"),
                "txt": ("+" if pc > 0 else "") + f"{pc:.1f}%"}


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
    LABEL = {"good": "meeting", "bad": "interrupted",
             "warn": "indeterminate", "none": "not measured"}


    def chip(kind, txt=None):
        return (f'<span class="chip c-{kind}">{ICON.get(kind, "")}'
                f'{esc(txt or LABEL.get(kind, kind))}</span>')


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


    TIERS = [
        {"id": "irreplaceable", "name": "Irreplaceable", "declared": 5, "v": "--k-t1",
         "label": "Only provider. Network halts without it. No substitute exists.",
         "def": "Ledger, resource, and programmability — what the blockchain and the physical-storage-backed ledger need in order to keep running at all.",
         "example": "Distributed randomness beacon — without it, block production stops.",
         "posture": "Must fund. Non-negotiable security requirements. Audits milestone-gated.",
         "short": "Must fund — non-negotiable"},
        {"id": "essential", "name": "Essential", "declared": 24, "v": "--k-t2",
         "label": "Network-critical, but alternatives exist. We need at least one.",
         "def": "Core offerings — disk space from miners, storage primitives in smart contracts — that let participants engage with the irreplaceable components.",
         "example": "Testnets: the network continues without them, but at least one is needed to stage and rehearse upgrades.",
         "posture": "Fund for diversity that ensures uptime — maintain two or more implementations. Budget negotiable.",
         "short": "Fund for redundancy — 2+ implementations"},
        {"id": "important", "name": "Important", "declared": None, "v": "--k-t3",
         "label": "Load-bearing. Multiple dependents. Silent failure cascades.",
         "def": "Supports and improves access to the critical components, and speeds up development of revenue-generating work.",
         "example": "A testnet faucet: it makes test FIL easy to get, but the network runs without it.",
         "posture": "Fund maintenance, not features. Flag any repo with zero active developers.",
         "short": "Fund maintenance, not features"},
        {"id": "nice", "name": "Nice to have", "declared": None, "v": "--k-t4",
         "label": "Enriches the ecosystem. Network survives without it.",
         "def": "Initiatives that encourage additional growth, where having even one instance may matter for basic ecosystem support.",
         "example": "F3: the network exists without it, but it improves UX considerably and encourages growth.",
         "posture": "Discretionary. Fund only where aligned with the sustainability strategy.",
         "short": "Discretionary"},
    ]

    def tier_by_id(tid):
        return next(t for t in TIERS if t["id"] == tid)


    def pct_label(v):
        return "—" if v is None else f"{v:.1f}%"



    # --------------------------------------------------------------- cards

    def dense(e):
        """A copy of the entry carrying only the days that produced a value.

        `line_svg` is verbatim from the mockup and assumes every point is numeric, because the
        mockup's data has no gaps. Rather than edit the chart code -- and risk the two pages
        drifting apart -- the chart is handed a gap-free copy, and the card states the number of
        unmeasurable days in words so the gap is never silently bridged.
        """
        s_ = e["s"]
        keep = [(o, v) for o, v in zip(s_["off"], s_["v"]) if v is not None]
        return {**e, "s": {"d0": s_["d0"], "off": [o for o, _ in keep],
                           "v": [v for _, v in keep], "o": ["u"] * len(keep)}}

    def public_dtable(e, today, win=WIN):
        """Date and value, newest first. Two columns, not three.

        The mockup's dtable carries an SLA column; with no bar in force every cell in it would be
        a dash, so the column is dropped rather than rendered empty.
        """
        rows = "".join(
            f'<tr><td class="mono">{iso}</td><td class="n">{esc(fmt(v))}</td></tr>'
            for iso, v, _o in reversed(pts(e, today, win)))
        return (f'<div class="dtable"><table><thead><tr><th>date</th>'
                f'<th style="text-align:right">{esc(e["metric"])}</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div>')


    def public_card(e, today, win=WIN, show_team=True, qualify=False):
        """One commitment: its latest reading, its movement, and its history.

        Deliberately NOT the mockup's metric_card. That card leads with a rolling SLA percentage
        and an interruption count, both of which require an agreed threshold; with none in force
        they would render as a reassuring "No interruption in the window" on a metric nobody has
        promised anything about. This shows the number and the trend, and says so.
        """
        # Both of these read values arithmetically, so they take the gap-free copy too; `p` keeps
        # the nulls because the numbers table should still show an unmeasurable day as a row.
        d = dense(e)
        p = pts(e, today, win)
        real = pts(d, today, win)
        last = real[-1][1] if real else None
        dl = delta(d, today, win)
        head = f'{e["team"]} · {e["fid"]}' if qualify else e["fid"]
        meta = " · ".join(x for x in [
            e["team"] if show_team else None, e["metric"], e["cad"], e["shape"],
        ] if x)
        prov = (f'<span class="prov obs" title="{e["n_real"]} readings fetched from the '
                f'source">observed · {e["n_real"]} pts</span>')
        _gaps = sum(1 for v in e["s"]["v"] if v is None)
        gap_note = (f'<div class="lab" style="color:var(--k-warn)">{_gaps} day'
                    f'{"s" if _gaps > 1 else ""} unmeasurable</div>') if _gaps else ""
        return (
            f'<article class="card" id="m-{e["id"]}">'
            f'<div class="chead"><span class="m">{esc(head)}</span>'
            f'<div class="r">{chip("warn", "no agreed bar")}{prov}</div></div>'
            f'<div class="cmeta">{esc(meta)}</div>'
            f'<p class="cstmt">{esc(e["stmt"])}</p>'
            f'<div class="readout">'
            f'<div><div class="lab">latest</div><div class="big">{esc(fmt(last))}</div></div>'
            f'<div><div class="lab">change over {win}d</div>'
            f'<div class="d {dl["cls"]}">{esc(dl["txt"])}</div></div>'
            f'<div><div class="lab">readings</div>'
            f'<div class="d flat num">{e["n_real"]}</div>{gap_note}</div></div>'
            f'{line_svg(d, today, win, show_thr=False)}'
            f'<details class="dtoggle"><summary>show the numbers</summary>'
            f'{public_dtable(e, today, win)}</details></article>')

    # ---------------------------------------------------------------- page

    def build_public_page(reg):
        """reg = {'kfs':[...], 'entries':[...], 'today':'YYYY-MM-DD'} -- no projects, no money."""
        E, KF, today = reg["entries"], reg["kfs"], reg["today"]
        ents = lambda f: [E[i] for i in f["e"]]
        watched = [f for f in KF if f["e"]]
        # Two different counts, and the page must not conflate them: every daily row in the table,
        # and the subset that carries a value. 6 rows are days a source gave no defensible number.
        n_rows = sum(len(e["s"]["v"]) for e in E)
        n_read = sum(e["n_real"] for e in E)
        teams = sorted({e["team"] for e in E})
        grants = sorted({e["grant"] for e in E if e.get("grant")})

        out = []
        a = out.append

        a('<nav class="nav"><div class="wrap nav-in">'
          '<a class="crumb" href="#p-top">fil<span class="fil">pgf</span>.io '
          '<span style="opacity:.4">/</span> <b>Kernel</b> '
          '<span style="opacity:.4">/</span> Monitoring</a>'
          '<div class="nav-links">'
          '<a href="#p-coverage">Coverage</a><a href="#p-metrics">Metrics</a>'
          '<a href="#p-method">Method</a></div>'
          '<a class="nav-cta" href="#p-method">Query it yourself</a>'
          '</div></nav>')

        # ------------------------------------------------------------- hero
        a('<header class="hero" id="p-top"><div class="wrap">'
          '<p class="eyebrow">Kernel · Independent monitoring</p>'
          '<h1>What is being watched.</h1>'
          '<p class="lede">Every night, each metric below is fetched from the team\'s own '
          'infrastructure by a pipeline they do not control, and the reading is appended to a '
          'public record. Nothing here is scored: the numbers exist, the bars do not, because no '
          'agreement carrying one has been executed yet.</p>'
          '<div class="ladder"><div class="ladder-h">'
          '<span></span><span>Tier</span><span>Functions</span>'
          f'<span>Watched</span><span>What the tier means</span></div>')

        for t in TIERS:
            fns = [f for f in KF if f["tier"] == t["id"]]
            seen = [f for f in fns if f["e"]]
            tone = "good" if fns and len(seen) == len(fns) else ("warn" if seen else "none")
            a(f'<div class="rung">'
              f'<span class="rung-bar" style="background:var({t["v"]})"></span>'
              f'<span><span class="rung-n">{esc(t["name"])}</span>'
              f'<span class="rung-s">{esc(t["label"])}</span></span>'
              f'<span><span class="rung-c">{len(fns)}</span>'
              f'<span class="rung-cl">in inventory</span></span>'
              f'<span><span class="rung-c" style="color:var(--k-{tone})">{len(seen)}</span>'
              f'<span class="rung-cl">reporting</span></span>'
              f'<span class="rung-p">{esc(t["def"])}</span></div>')
        a('</div></div></header>')

        # ------------------------------------------------------- provenance
        a('<div class="prov-bar"><div class="wrap prov-in"><div>'
          f'Every figure on this page is read from two public tables in the OSO warehouse as of '
          f'<span class="mono">{esc(today)}</span> — '
          f'<span class="mono">kernel_timeseries_metrics_by_project</span> and '
          f'<span class="mono">kernel_functions</span>. No private source, no embedded snapshot: '
          f'any OSO API key reproduces every one of the {n_rows} daily rows, '
          f'{n_read} of which carry a value.'
          '</div></div></div>')

        # -------------------------------------------------------- headlines
        a('<section class="sec" id="p-coverage"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Coverage</p>'
          '<h2>Half the inventory reports nothing</h2>'
          '<p class="lede">A coverage figure computed over the functions we already measure would '
          'always read 100%. This one is computed over the whole catalogue, so the gap is '
          'visible.</p></div>'
          '<div class="mets" style="margin-bottom:34px">'
          f'<div class="met"><div class="met-v">{len(E)}</div>'
          f'<div class="met-k">Commitments measured</div>'
          f'<div class="met-d">{len(teams)} teams · {len(grants)} grants</div></div>'
          f'<div class="met"><div class="met-v">{len(watched)}<span style="color:var(--k-ink-3)">'
          f'/{len(KF)}</span></div>'
          f'<div class="met-k">Kernel functions with a reporter</div>'
          f'<div class="met-d bad">{len(KF) - len(watched)} report nothing at all</div></div>'
          f'<div class="met"><div class="met-v">0</div>'
          f'<div class="met-k">Readings judged</div>'
          f'<div class="met-d warn">No bar is in force until a contract is executed</div></div>'
          '</div>')

        for t in TIERS:
            fns = [f for f in KF if f["tier"] == t["id"]]
            if not fns:
                continue
            seen = [f for f in fns if f["e"]]
            a(f'<div class="fgroup"><div class="fg-h">'
              f'<span class="fg-n" style="color:var({t["v"]})">{esc(t["name"])}</span>'
              f'<span class="fg-c">{len(seen)} of {len(fns)} reporting</span></div>')
            for f in sorted(fns, key=lambda x: (not x["e"], x["name"])):
                es = ents(f)
                if es:
                    who = ", ".join(sorted({e["team"] for e in es}))
                    a(f'<div class="rung" style="grid-template-columns:8px minmax(0,2fr) 120px '
                      f'minmax(0,1fr)">'
                      f'<span class="rung-bar" style="background:var(--k-good)"></span>'
                      f'<span><span class="rung-n" style="font-size:15px">{esc(f["name"])}</span>'
                      f'<span class="rung-s">{esc(f["sub"])}</span></span>'
                      f'<span><span class="rung-c">{len(es)}</span>'
                      f'<span class="rung-cl">metrics</span></span>'
                      f'<span class="rung-p">{esc(who)}</span></div>')
                else:
                    a(f'<div class="rung" style="grid-template-columns:8px minmax(0,2fr) 120px '
                      f'minmax(0,1fr)">'
                      f'<span class="rung-bar" style="background:var(--k-none)"></span>'
                      f'<span><span class="rung-n" style="font-size:15px;color:var(--k-ink-3)">'
                      f'{esc(f["name"])}</span>'
                      f'<span class="rung-s">{esc(f["sub"])}</span></span>'
                      f'<span><span class="rung-c" style="color:var(--k-ink-3)">—</span>'
                      f'<span class="rung-cl">no metric</span></span>'
                      f'<span class="rung-p" style="color:var(--k-ink-3)">Nobody reports on this '
                      f'function, so nothing on this page can tell you whether it is healthy.'
                      f'</span></div>')
            a('</div>')
        a('</div></section>')

        # ----------------------------------------------------------- metrics
        a('<section class="sec sec-alt" id="p-metrics"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Metrics</p>'
          '<h2>The readings themselves</h2>'
          '<p class="lede">One card per commitment, newest reading first. The line is the metric '
          'in its own units over the last 90 days; a gap is a day the source gave no defensible '
          'number, which is not a zero and not a failure.</p></div>')

        dup = {f for f in {e["fid"] for e in E}
               if len({e["team"] for e in E if e["fid"] == f}) > 1}
        for team in teams:
            mine = [e for e in E if e["team"] == team]
            a(f'<div class="fgroup"><div class="fg-h">'
              f'<span class="fg-n">{esc(team)}</span>'
              f'<span class="fg-c">{len(mine)} commitment'
              f'{"s" if len(mine) > 1 else ""}</span></div>'
              f'<div class="cards">')
            for e in sorted(mine, key=lambda x: x["fid"]):
                a(public_card(e, today, show_team=False, qualify=e["fid"] in dup))
            a('</div></div>')
        a('</div></section>')

        # ------------------------------------------------------------ method
        a('<section class="sec" id="p-method"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Method</p>'
          '<h2>What this page can and cannot tell you</h2></div>'
          '<div class="terms">'
          '<div class="term"><h3>Two tables, both public</h3>'
          '<p><span class="mono">filecoin.filpgf_public.kernel_timeseries_metrics_by_project</span> '
          'holds one row per team, function, metric and day. '
          '<span class="mono">filecoin.filpgf_public.kernel_functions</span> holds the catalogue, '
          'including the functions nothing measures. Both refresh daily.</p></div>'
          '<div class="term"><h3>Why nothing is scored</h3>'
          '<p>Every threshold was withdrawn on 2026-08-20. The numbers are stated in signed '
          'appendices, but the agreements carrying them are not executed, and a number nobody has '
          'countersigned is not a commitment. When contracts are signed the bars return unchanged '
          'and history re-judges itself, because the bar is recorded per day.</p></div>'
          '<div class="term"><h3>A gap is not a zero</h3>'
          '<p>A missing reading means the source produced no defensible number that day — an '
          'endpoint down, a schema moved. That is our failure to measure, not the team\'s failure '
          'to deliver, and it is drawn as a break in the line rather than a drop to zero.</p></div>'
          '<div class="term"><h3>What is missing here</h3>'
          '<p>Adjudicated committee verdicts, draft metrics not yet adopted, the source endpoint '
          'behind each reading, and anything about what a grant is worth. The first three are in '
          'the internal dashboard; the last belongs on no public page.</p></div>'
          '</div></div></section>')

        a('<footer class="foot"><div class="wrap foot-in">'
          f'<span>Filecoin Kernel · independent monitoring · {esc(today)}</span>'
          '<span class="foot-links">'
          '<a href="https://github.com/filecoin-project/pgf-monitor">pipeline &amp; registry</a>'
          '</span></div></footer>')

        return f'<div class="kpage" id="k-top">{"".join(out)}</div>'

    return (build_public_page,)


@app.cell(hide_code=True)
def live_registry(build_registry, mo, pyoso_db_conn, to_rows):
    # The mockup carries its registry as a gzipped base64 blob. This one reads the same shape out
    # of the two public tables, so the page cannot describe a world the warehouse does not.
    _series = mo.sql(
        """
        SELECT sample_date, team, function_id, metric_name, grant_ref, kernel_id, kernel_function,
               tier, category, sub_category, amount, threshold_op, threshold_value, cadence,
               sla_statement
        FROM filecoin.filpgf_public.kernel_timeseries_metrics_by_project
        ORDER BY team, function_id, metric_name, sample_date
        """,
        output=False,
        engine=pyoso_db_conn,
    )
    _functions = mo.sql(
        """
        SELECT kernel_id, tier, category, sub_category, kernel_function, kernel_value
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
def registry_shape(datetime):
    def build_registry(rows, functions):
        """Rows -> the {kfs, entries, today} shape the page renders.

        Readings are packed as day-offsets from the first one, exactly as the mockup packs them,
        so the chart helpers can be reused unchanged.
        """
        by_key = {}
        for r in rows:
            key = (r["team"], r["function_id"], r["metric_name"])
            by_key.setdefault(key, []).append(r)

        entries = []
        for (team, fid, metric), rs in sorted(by_key.items()):
            rs = sorted(rs, key=lambda x: x["sample_date"])
            first = rs[0]["sample_date"]
            d0 = first if isinstance(first, str) else first.isoformat()
            base = datetime.date.fromisoformat(d0)

            def _iso(v):
                return v if isinstance(v, str) else v.isoformat()

            # An unmeasurable day is carried as a null value rather than dropped, so the line
            # breaks where the source failed instead of interpolating over it.
            def _num(v):
                # polars hands back None, pandas hands back NaN, and `NaN is None` is False --
                # which silently turned 6 unmeasurable days into plottable garbage. v != v is the
                # NaN test that needs no numpy import.
                if v is None or v != v:
                    return None
                return float(v)

            offs, vals, outs = [], [], []
            for r in rs:
                offs.append((datetime.date.fromisoformat(_iso(r["sample_date"])) - base).days)
                _v = _num(r["amount"])
                vals.append(_v)
                outs.append("i" if _v is None else "u")
            last = rs[-1]
            entries.append({
                "id": len(entries),
                "team": team,
                "fid": fid,
                "metric": metric,
                "grant": last.get("grant_ref") or "",
                "kernel_id": last.get("kernel_id") or "",
                "kf": last.get("kernel_function") or "",
                "tier": last.get("tier") or "",
                "cat": last.get("category") or "",
                "sub": last.get("sub_category") or "",
                "cad": last.get("cadence") or "daily",
                "stmt": last.get("sla_statement") or "",
                "shape": "reading",
                # No bar is in force, so the card draws no threshold line and claims no verdict.
                "op": last.get("threshold_op"),
                "thr": last.get("threshold_value"),
                "src": "observed",
                "n_real": sum(1 for v in vals if v is not None),
                "s": {"d0": d0, "off": offs, "v": vals, "o": outs},
            })

        by_kernel = {}
        for e in entries:
            by_kernel.setdefault(e["kernel_id"], []).append(e["id"])

        kfs = [{
            "name": f["kernel_function"],
            "tier": f["tier"],
            "cat": f["category"],
            "sub": f["sub_category"],
            "why": f.get("kernel_value") or "",
            "e": by_kernel.get(f["kernel_id"], []),
        } for f in functions]

        today = max((e["s"]["d0"] for e in entries), default="")
        for e in entries:
            base = datetime.date.fromisoformat(e["s"]["d0"])
            last = (base + datetime.timedelta(days=e["s"]["off"][-1])).isoformat()
            today = max(today, last)
        return {"kfs": kfs, "entries": entries, "today": today}

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
