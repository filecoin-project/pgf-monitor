import marimo

__generated_with = "unknown"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def kernel_page(KERNEL_CSS, PAGE_HTML, mo):
    mo.Html(KERNEL_CSS + PAGE_HTML)
    return


@app.cell(hide_code=True)
def compose_page(REGISTRY, build_kernel_page):
    # One composed page rather than one cell per section: the design is a
    # continuous document with alternating bands, which cell containers would
    # break up. It is plain HTML/CSS throughout — no iframe, no <script>, all
    # interactivity carried by <details> — so it survives static export whole.
    PAGE_HTML = build_kernel_page(REGISTRY)
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
def kernel_engine(datetime, json, math):
    # Readings roll up at each metric's own declared cadence and a period shows
    # its worst outcome — ported 1:1 from the Kernel monitoring reference
    # implementation and diffed against it (0 mismatches across 56 metrics).
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


    def usd(v):
        if v is None:
            return "—"
        if v >= 1e6:
            return f"${v/1e6:.2f}M"
        return f"${round(v/1e3):,}k"


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


    # ------------------------------------------------------- series + rollup

    GRAIN = {"daily": 1, "weekly": 7, "monthly": 30}
    RANK = {"f": 3, "i": 2, "p": 1}


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


    def roll(e, today, win=WIN):
        """Health roll-up over the window, at the metric's own cadence grain."""
        p = pts(e, today, win)
        by, val = {}, {}
        for iso, v, o in p:
            k = bucket_key(iso, e["cad"])
            if k not in by or RANK.get(o, 0) > RANK.get(by[k], 0) or by[k] == o:
                by[k], val[k] = o, v
        keys = periods(e["cad"], today, win)
        seen = [k for k in keys if by.get(k)]
        np_ = sum(1 for k in seen if by[k] == "p")
        nf = sum(1 for k in seen if by[k] == "f")
        runs, cur = [], None
        for k in keys:
            o = by.get(k)
            if o == "f":
                if cur:
                    cur["n"] += 1
                else:
                    cur = {"d": k, "n": 1}
                    runs.append(cur)
            elif o:
                cur = None
        return {"by": by, "val": val, "keys": keys, "np": np_, "nf": nf,
                "cover": len(seen), "expected": len(keys),
                "pct": (100.0 * np_ / (np_ + nf)) if (np_ + nf) else None,
                "runs": runs, "last": p[-1] if p else None}


    def grain_word(cad):
        return {"daily": "day", "weekly": "week", "monthly": "month"}.get(cad, "period")


    def agg(entries, today, win=WIN):
        """Aggregate health state over a list of entry dicts."""
        hs = [e for e in entries if e["cls"] == "health"]
        if not hs:
            return {"state": "none", "pct": None, "nf": 0}
        np_ = nf = 0
        any_fail = False
        for e in hs:
            r = roll(e, today, win)
            np_ += r["np"]
            nf += r["nf"]
            if r["last"] and r["last"][2] == "f":
                any_fail = True
        return {"state": "bad" if any_fail else ("good" if np_ else "warn"),
                "pct": (100.0 * np_ / (np_ + nf)) if (np_ + nf) else None, "nf": nf}


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


    # ------------------------------------------------------------- chrome

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


    # --------------------------------------------------------- uptime strip

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


    STATE_TXT = {"p": "meeting SLA", "f": "SLA not met", "i": "indeterminate"}
    READING_TXT = {"p": "within threshold", "f": "outside threshold",
                   "i": "indeterminate"}
    MIN_BARS = 8


    def strip_bits(e, today, win=WIN):
        """What the uptime strip should draw.

        A monthly commitment fills only three cadence periods in a 90-day
        window, which reads as a broken graphic rather than a record. When the
        cadence grain is that coarse the strip switches to one bar per reading
        — and says so — while the SLA percentage above it stays on the metric's
        own cadence either way. Bars are per reading rather than per calendar
        day so that a metric read every few days doesn't render as a mostly
        empty strip.
        """
        r = roll(e, today, win)
        if len(r["keys"]) >= MIN_BARS:
            return {"keys": r["keys"], "by": r["by"],
                    "g": grain_word(e["cad"]), "dense": False}
        p = pts(e, today, win)
        return {"keys": [iso for iso, _v, _o in p],
                "by": {iso: o for iso, _v, o in p},
                "g": "reading", "dense": True}


    def strip_html(e, today, win=WIN, small=False, max_bars=None):
        b_ = strip_bits(e, today, win)
        g = b_["g"]
        txt = READING_TXT if b_["dense"] else STATE_TXT
        bars = []
        for b in collapse_bars(b_["keys"], b_["by"], max_bars):
            state = txt.get(b["o"], "no reading")
            many = f" (worst of {b['span']} {g}s)" if b["span"] > 1 else ""
            bars.append(f'<i data-o="{b["o"]}" title="{esc(b["lab"])} · {state}{many}"></i>')
        cls = "strip sm" if small else "strip"
        label = ("outcome of each reading" if b_["dense"]
                 else f"SLA outcome per {g}")
        return (f'<div class="{cls}" role="img" aria-label="{label}, '
                f'last {win} days">{"".join(bars)}</div>')


    # ----------------------------------------------------------- line chart

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


    # ------------------------------------------------- the source being pinged

    def derive_sentence(ex):
        def c(s):
            return f"<code>{esc(s)}</code>"
        if ex.get("reduce") == "null_ratio":
            return f"The fraction of all returned rows where {c(ex.get('column'))} is null or absent."
        scalar = {
            "single": f"{c(ex.get('column'))} from the single row returned",
            "latest": f"{c(ex.get('column'))} from the most recent row, by {c(ex.get('timestamp_column') or 'timestamp')}",
            "avg": f"the mean of {c(ex.get('column'))} across every returned row",
            "min": f"the smallest {c(ex.get('column'))} across every returned row",
            "max": f"the largest {c(ex.get('column'))} across every returned row",
        }.get(ex.get("reduce"), f"{c(ex.get('column'))} from the returned rows")
        as_date = ", read as a timestamp" if ex.get("cast") == "date" else ""
        s = {
            "value": f"Report {scalar}{as_date}.",
            "diff": f"Take {scalar}{as_date} and subtract {c(ex.get('column2') or '?')} on that same row.",
            "age_seconds": f"Take {scalar}{as_date}, then report how many seconds have passed since.",
            "age_days": f"Take {scalar}{as_date}, then report how many days have passed since.",
        }.get(ex.get("derive"), f"Report {scalar}.")
        return s + (f" Unit: {c(ex['unit'])}." if ex.get("unit") else "")


    def src_detail(d):
        h = ['<div class="derive">']
        if d.get("kind") == "fixture":
            h.append(f'<div class="dk">how this is checked</div>'
                     f'<p>{esc(d.get("manual") or "")}</p>')
        else:
            body = ("\n\n" + json.dumps(d["body"], indent=2)) if d.get("body") else ""
            h.append(f'<div class="dk">request</div>'
                     f'<pre class="req">{esc(d.get("method"))} {esc(d.get("url"))}{esc(body)}</pre>')
            if d.get("sel"):
                h.append(f'<div class="dk">rows taken from</div><p><code>{esc(d["sel"])}</code></p>')
            h.append('<div class="dk">how the number is derived</div>')
            if d.get("sql"):
                h.append(f'<pre class="req">{esc(d["sql"])}</pre>')
            elif d.get("ex"):
                h.append(f'<p>{derive_sentence(d["ex"])}</p>')
            else:
                h.append('<p style="color:var(--k-muted)">not declared</p>')
        if d.get("auth"):
            h.append('<div class="dk">credential</div><p>a secret is attached; the endpoint is not '
                     'anonymously readable</p>')
        if d.get("note"):
            h.append(f'<div class="dk">note</div><p>{esc(d["note"])}</p>')
        h.append("</div>")
        return "".join(h)


    def src_block(e):
        d = e.get("sd")
        if not d:
            return ""
        if d.get("kind") == "fixture":
            head = f'<span class="srcna">{ICON["warn"]} reported by hand — no public endpoint</span>'
        else:
            bare = d["url"].split("://", 1)[-1]
            cut = bare.find("/")
            host = bare if cut < 0 else bare[:cut]
            path = "" if cut < 0 else bare[cut:]
            inner = f"<b>{esc(host)}</b>{esc(path)}"
            linkable = d.get("method") == "GET" and d["url"].startswith("https://")
            mchip = f'<span class="mchip{" post" if d.get("method") == "POST" else ""}">{esc(d.get("method"))}</span>'
            if linkable:
                head = (mchip + f'<a class="srcurl" href="{esc(d["url"])}" target="_blank" '
                        f'rel="noopener noreferrer">{inner} {EXT_ICON}</a>')
            else:
                head = mchip + f'<span class="srcurl">{inner}</span>'
        return (f'<div class="srcrow"><span class="srclab">source</span>{head}</div>'
                f'<details class="dtoggle"><summary>how this value is computed</summary>'
                f'{src_detail(d)}</details>')


    # ------------------------------------------------------- data table twin

    def dtable(e, today, win=WIN):
        p = list(reversed(pts(e, today, win)))
        sla = {"p": "met", "f": "not met", "i": "indeterminate"}
        rows = "".join(
            f'<tr><td class="mono">{iso}</td><td class="n">{esc(fmt(v))}</td>'
            f'<td>{sla.get(o, "no reading") if e["cls"] == "health" else "—"}</td></tr>'
            for iso, v, o in p)
        return (f'<div class="dtable"><table><thead><tr><th>date</th>'
                f'<th style="text-align:right">{esc(e["metric"])}</th>'
                f'<th>{"SLA" if e["cls"] == "health" else "—"}</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div>')


    # ----------------------------------------------------------- metric card

    def metric_card(e, today, win=WIN, show_team=True, qualify=False):
        if e["src"] == "observed":
            prov = (f'<span class="prov obs" title="{e["n_real"]} readings collected from the '
                    f'public source">observed · {e["n_real"]} pts</span>')
        else:
            prov = ""
        # The commitment id headlines the card, not the metric column: four of
        # Curio's cards measure `avg_days_between_releases`, so the column name
        # alone made distinct commitments read as the same card repeated.
        meta = " · ".join(x for x in [
            e["team"] if show_team else None, e["metric"], e["cad"],
            "impact metric" if e["shape"] == "level" else e["shape"],
            "proposed (draft)" if e["state"] == "draft" else None,
            "collected, not yet committed" if e["state"] == "observed" else None,
        ] if x)
        # two teams can commit the same id against one function (ankr and
        # chain.love both run `chain-sync-rpc-mainnet-head-lag` on their own
        # endpoint); the caller flags those so the headline stays unique
        head = f'{e["team"]} · {e["fid"]}' if qualify else e["fid"]
        tail = (f'<details class="dtoggle"><summary>show the numbers</summary>'
                f'{dtable(e, today, win)}</details>')

        if e["cls"] == "impact":
            p = pts(e, today, win)
            last = p[-1][1] if p else None
            dl = delta(e, today, win)
            floor = ""
            if e.get("thr") is not None:
                floor = (f'<div><div class="lab">floor committed</div>'
                         f'<div class="d flat num">{esc(e["op"])} {esc(fmt(float(e["thr"])))}</div></div>')
            thr_lab = ("floor " + fmt(float(e["thr"]))) if e.get("thr") is not None else None
            return (
                f'<article class="card impact" id="m-{e["id"]}">'
                f'<div class="chead"><span class="m">{esc(head)}</span>'
                f'<div class="r">{chip("acc", "impact · goal up")}{prov}</div></div>'
                f'<div class="cmeta">{esc(meta)}</div>'
                f'<p class="cstmt">{esc(e["stmt"])}</p>'
                f'{src_block(e)}'
                f'<div class="readout">'
                f'<div><div class="lab">latest</div><div class="big">{esc(fmt(last))}</div></div>'
                f'<div><div class="lab">change over {win}d</div>'
                f'<div class="d {dl["cls"]}">{esc(dl["txt"])}</div></div>{floor}</div>'
                f'{line_svg(e, today, win, thr_tone="muted", thr_label=thr_lab)}'
                f'{tail}</article>')

        r = roll(e, today, win)
        st = "none" if not r["last"] else ("bad" if r["last"][2] == "f"
                                           else ("good" if r["last"][2] == "p" else "warn"))
        g = grain_word(e["cad"])
        if r["runs"]:
            detail = " · ".join(
                key_label(x["d"]) + (f' ({x["n"]} {g}s)' if x["n"] > 1 else "") for x in r["runs"])
            inc = (f'<div class="inc"><b>{len(r["runs"])} interruption'
                   f'{"s" if len(r["runs"]) > 1 else ""}</b> · {esc(detail)}</div>')
        else:
            inc = '<div class="inc">No interruption in the window.</div>'
        pct = "—" if r["pct"] is None else f'{r["pct"]:.1f}%'
        sb = strip_bits(e, today, win)
        bar_caption = "one bar = one " + sb["g"]
        if sb["dense"]:
            bar_caption += " · SLA judged " + e["cad"]
        return (
            f'<article class="card" id="m-{e["id"]}">'
            f'<div class="chead"><span class="m">{esc(head)}</span>'
            f'<div class="r">{chip(st)}{prov}</div></div>'
            f'<div class="cmeta">{esc(meta)}</div>'
            f'<p class="cstmt">{esc(e["stmt"])}</p>'
            f'{src_block(e)}'
            f'<div class="readout">'
            f'<div><div class="lab">SLA met</div><div class="big num">{pct}</div></div>'
            f'<div><div class="lab">coverage</div>'
            f'<div class="d flat num">{r["cover"]} of {r["expected"]} {g}s read</div></div>'
            f'<div><div class="lab">latest</div><div class="d flat num">'
            f'{esc(fmt(r["last"][1]) if r["last"] else None)} '
            f'<span style="color:var(--k-muted);font-weight:400">vs {esc(e["op"])} '
            f'{esc(fmt(float(e["thr"])) if e.get("thr") is not None else None)}</span></div></div></div>'
            f'{strip_html(e, today, win)}'
            f'<div class="axis"><span>{esc(key_label(sb["keys"][0]))}</span>'
            f'<span>{esc(bar_caption)}</span>'
            f'<span>{esc(key_label(sb["keys"][-1]))}</span></div>'
            f'{inc}'
            f'{line_svg(e, today, win)}'
            f'{tail}</article>')


    # ====================================================================
    # PAGE ASSEMBLY
    # ====================================================================
    # --------------------------------------------------------------- copy deck
    # Tier framework, program copy and the FY cycle are carried from the
    # kernel-filecoin-pgf mockup. `declared` is the tier's full inventory size;
    # Important and Nice to have have not been inventoried, so they read as
    # pending rather than as zero.
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

    TIMELINE = [
        {"date": "Jan 2026", "title": "FY26 term begins", "state": "done"},
        {"date": "Apr 2026", "title": "Mid-term audit", "state": "done"},
        {"date": "Aug 2026", "title": "Health reporting live", "state": "now"},
        {"date": "Oct 2026", "title": "Close-out audit", "state": ""},
        {"date": "Nov 2026", "title": "Applications close", "state": ""},
        {"date": "Dec 2026", "title": "Awards published", "state": ""},
        {"date": "Jan 2027", "title": "FY27 term begins", "state": ""},
    ]

    GLOSSARY = [
        ("Kernel", "The funding program covering work the network cannot operate without. Funded as a <b>near-fixed cost</b> on an annual term with audits, not against milestones."),
        ("Function", "A capability the network needs, named by <b>what it does</b> rather than by which repo provides it. Functions outlive implementations — the function survives when the code that serves it is replaced."),
        ("Health metric", "A pass/fail commitment: a measurable indicator with an agreed threshold, cadence and public source, reported by the maintaining team. Functions without one cannot be assessed and are marked <b>not measured</b>."),
        ("Growth counter", "A metric tracked for direction rather than pass/fail. It can never report an outage, so it never colours a function's status."),
        ("Tier", "How replaceable a function is, from <b>Irreplaceable</b> to <b>Nice to have</b>. Tier sets the funding posture and whether redundancy is required."),
        ("SLA met · 90d", "The share of reading periods in the last 90 days that stayed within threshold. Periods are counted at each metric's own cadence, so a weekly metric is not penalised for being coarse."),
        ("Coverage", "How many of the reading periods the window expects actually carry a reading. Low coverage means the commitment exists but is not being collected."),
        ("Single maintainer", "A function maintained by exactly one team. Tolerable at lower tiers, a named risk at the top two, where the posture calls for two or more independent implementations."),
    ]


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
        return next(t for t in TIERS if t["id"] == tid)


    def pct_label(v):
        return "—" if v is None else f"{v:.1f}%"


    def build_kernel_page(reg):
        """reg = {'kfs':[...], 'entries':[...], 'projects':[...], 'today':'YYYY-MM-DD'}"""
        E, KF, PR, today = reg["entries"], reg["kfs"], reg["projects"], reg["today"]
        ents = lambda f: [E[i] for i in f["e"]]
        health = lambda f: [e for e in ents(f) if e["cls"] == "health"]
        impact = lambda f: [e for e in ents(f) if e["cls"] == "impact"]
        teams_of = lambda f: list(dict.fromkeys(e["team"] for e in ents(f)))
        pr_by_team = {p["team"]: p for p in PR}

        out = []
        a = out.append

        # -------------------------------------------------------------- nav
        a('<nav class="nav"><div class="wrap nav-in">'
          '<a class="crumb" href="#k-top">fil<span class="fil">pgf</span>.io '
          '<span style="opacity:.4">/</span> <b>Kernel</b></a>'
          '<div class="nav-links">'
          '<a href="#k-objective">Objective</a><a href="#k-timeline">Timeline</a>'
          '<a href="#k-categories">Categories</a><a href="#k-functions">Inventory</a>'
          '<a href="#k-metrics">Metrics</a><a href="#k-terms">Terms</a></div>'
          '<a class="nav-cta" href="#k-timeline">Apply · FY27</a>'
          '</div></nav>')

        # ------------------------------------------------------------- hero
        a('<header class="hero" id="k-top"><div class="wrap">'
          '<p class="eyebrow">Kernel · Program overview</p>'
          '<h1>What keeps the network running.</h1>'
          '<p class="lede">Kernel funds the functions Filecoin depends on to keep producing blocks, '
          'proving storage, and staying observable. It is treated as a near-fixed cost rather than a '
          'growth bet: the goal is not more features, it is that nothing essential quietly stops '
          'being maintained.</p>'
          '<div class="ladder"><div class="ladder-h">'
          '<span></span><span>Tier</span><span>Functions</span>'
          f'<span>SLA met · {WIN}d</span><span>Funding posture</span></div>')

        for t in TIERS:
            fns = [f for f in KF if f["tier"] == t["id"]]
            tier_ents = [e for f in fns for e in ents(f)]
            ag = agg(tier_ents, today)
            n_meas = sum(1 for f in fns if health(f))
            if t["declared"] is None:
                count = ('<div class="rung-c" style="font-size:13px;color:var(--k-ink-3)">Pending</div>'
                         '<div class="rung-cl">not inventoried</div>')
            else:
                listed = ("all listed" if len(fns) >= t["declared"]
                          else f"{len(fns)} listed")
                count = (f'<div class="rung-c">{t["declared"]}</div>'
                         f'<div class="rung-cl">{listed}</div>')
            sla_note = "no data" if ag["pct"] is None else f"{n_meas} measured"
            a(f'<a class="rung" href="#k-functions">'
              f'<span class="rung-bar" style="background:var({t["v"]})"></span>'
              f'<span><span class="rung-n">{esc(t["name"])}</span>'
              f'<span class="rung-s">{esc(t["label"])}</span></span>'
              f'<span>{count}</span>'
              f'<span><span class="rung-c">{pct_label(ag["pct"])}</span>'
              f'<span class="rung-cl">{sla_note}</span></span>'
              f'<span class="rung-p">{esc(t["short"])}</span></a>')
        a('</div></div></header>')

        # ------------------------------------------------------- provenance
        n_obs = sum(1 for e in E if e["src"] == "observed")
        a('<div class="prov-bar"><div class="wrap prov-in">'
          f'<div>Functions, teams, thresholds, source endpoints and committed amounts are read '
          f'from the Kernel registry as of <span class="mono">{esc(today)}</span>. Chart history '
          f'is illustrative, except on the {n_obs} metrics marked '
          f'<span class="prov obs">observed</span>.</div>'
          '</div></div>')

        # -------------------------------------------------------- objective
        a('<section class="sec" id="k-objective"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Objective</p>'
          '<h2>Keep the floor from moving</h2></div>'
          '<div class="split"><div>'
          '<p>Most of what Filecoin runs on is maintained by small teams, and much of it has no second '
          'implementation. When one of those goes unfunded, nothing breaks on the day it happens — the '
          'repo just goes quiet, the maintainer moves on, and the network carries a dependency nobody '
          'is watching. Kernel exists to make that failure mode visible and to pay for it not to '
          'happen.</p>'
          '<p>The program starts from a map, not a wishlist. Every capability the network needs is '
          'written down as a <b>function</b>, independent of which repo currently provides it. Each '
          'function is placed in a tier according to how replaceable it is, and each tier carries a '
          'different funding posture — some are non-negotiable, some are funded for redundancy, some '
          'are funded only for maintenance.</p>'
          '<p>Funding follows an annual term with audits rather than milestones, because keeping '
          'something working is a continuous obligation and not a deliverable. Every commitment on '
          'this page names a threshold, a reading cadence and a public endpoint anyone can call — so '
          'the audit is a lookup, not a conversation.</p>'
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
            band = ("inventory pending" if t["declared"] is None
                    else f'{t["declared"]} functions')
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
          '<p class="lede">The same commitments, read two ways. <b>By project</b> asks what each '
          'funded team is on the hook for; <b>by function</b> asks what the network needs and '
          'whether anyone is holding it up. The percentage is the share of reading periods in the '
          f'last {WIN} days that sat within threshold, counted at each metric\'s own cadence. Open '
          'any row for the commitments behind it in full — the uptime record, each interruption, '
          'the value against its threshold, and the public endpoint being read.</p>'
          '<div class="legend">'
          '<span><i style="background:var(--k-good)"></i>SLA met</span>'
          '<span><i style="background:var(--k-bad)"></i>not met</span>'
          '<span><i style="background:var(--k-warn)"></i>indeterminate</span>'
          '<span><i style="background:var(--k-none)"></i>no reading</span></div>'
          '</div></div>')

        # Radio + :checked rather than a script: the page is exported statically, so a
        # JS tab bar would come out dead. The panels must stay siblings of the inputs.
        a('<div class="kviews">'
          '<input type="radio" name="kview" id="kv-fn">'
          '<input type="radio" name="kview" id="kv-pr" checked>'
          '<div class="wrap"><div class="viewbar" role="tablist">'
          f'<label for="kv-pr">By project <b>{len(PR)}</b></label>'
          f'<label for="kv-fn">By function <b>{len(KF)}</b></label>'
          '</div></div>'
          '<div class="wrap vpanel v-fn">')

        for t in TIERS:
            fns = [f for f in KF if f["tier"] == t["id"]]
            head = ("inventory pending" if t["declared"] is None
                    else f'{t["declared"]} functions')
            a(f'<div class="fgroup"><div class="fg-h">'
              f'<span class="fg-n" style="color:var({t["v"]})">{esc(t["name"])}</span>'
              f'<span class="fg-c">{esc(head)}</span></div>')
            if not fns:
                a(f'<div class="note">Functions in this tier have not been inventoried yet. '
                  f'Posture is set — {esc(t["short"].lower())} — but nothing is being measured '
                  f'against it.</div></div>')
                continue
            for dom in dict.fromkeys(f["cat"] for f in fns):
                a(f'<div class="dom">{esc(dom)}</div>')
                for f in [x for x in fns if x["cat"] == dom]:
                    a(function_row(f, t, today, health(f), impact(f),
                                    teams_of(f), pr_by_team))
            if t["declared"] and len(fns) < t["declared"]:
                a(f'<div class="note">Showing {len(fns)} of {t["declared"]} functions in this tier. '
                  f'The remainder are in the full inventory.</div>')
            a('</div>')
        a('</div>')

        # ------------------------------------------------ by project / by team
        a('<div class="wrap vpanel v-pr">')
        funded = [p for p in PR if p.get("usd")]
        unfunded = [p for p in PR if not p.get("usd")]
        covered = len({n for p in PR for n in p["fns"]})
        a('<div class="mets" style="margin-bottom:34px">'
          f'<div class="met"><div class="met-v">{esc(usd(sum(p["usd"] for p in funded)))}</div>'
          f'<div class="met-k">Committed across the slate</div>'
          f'<div class="met-d">{len(funded)} funded of {len(PR)} reporting teams</div></div>'
          f'<div class="met"><div class="met-v">{covered}</div>'
          f'<div class="met-k">Kernel functions covered</div>'
          f'<div class="met-d">of {len(KF)} listed in the inventory</div></div>'
          f'<div class="met"><div class="met-v">{len(E)}</div>'
          f'<div class="met-k">Commitments reported</div>'
          f'<div class="met-d">{len([e for e in E if e["cls"] == "health"])} health · '
          f'{len([e for e in E if e["cls"] == "impact"])} growth</div></div>'
          '</div>')
        top = max((p.get("usd") or 0) for p in PR) or 1
        for label, group, note in (
            ("Funded this batch", funded,
             "Teams holding an award in the current batch."),
            ("Reporting without an award", unfunded,
             "Teams reporting commitments this batch without Kernel money against them."),
        ):
            a(f'<div class="fgroup"><div class="fg-h">'
              f'<span class="fg-n">{esc(label)}</span>'
              f'<span class="fg-c">{len(group)} team{"s" if len(group) != 1 else ""}</span></div>'
              f'<div class="dom">{esc(note)}</div>')
            for p in group:
                a(project_row(p, today, E, KF, top))
            a('</div>')
        a('</div>')  # /v-pr
        a('</div></section>')  # /kviews /section

        # --------------------------------------------------- program metrics
        a('<section class="sec" id="k-metrics"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Kernel metrics</p>'
          '<h2>How the program is doing</h2>'
          '<p class="lede">Aggregate health matters less than coverage. A function with no maintainer '
          'and no metric is invisible to this page, which is exactly what makes it dangerous.</p></div>'
          '<div class="mets">')
        for c in program_metrics(KF, E, PR, today, health, impact, teams_of):
            a(f'<div class="met"><div class="met-v">{esc(c["v"])}</div>'
              f'<div class="met-k">{esc(c["k"])}</div>'
              f'<div class="met-d {c["cls"]}">{esc(c["d"])}</div></div>')
        a('</div><p class="note" style="margin-top:22px">Every reading on this page is derived from '
          'the commitments in the Kernel registry. Metrics for '
          'individual projects and repos live in the '
          f'<a href="https://app.filpgf.io/projects" target="_blank" rel="noopener noreferrer" '
          f'style="color:var(--k-fil-deep);white-space:nowrap">explorer {ARROW}</a>'
          '</p></div></section>')

        # --------------------------------------------------------- glossary
        a('<section class="sec sec-alt" id="k-terms"><div class="wrap">'
          '<div class="sec-head"><p class="eyebrow">Terms</p>'
          '<h2>What these words mean here</h2>'
          '<p class="lede">Kernel uses a few words in a specific way. Getting them straight is most '
          'of understanding the program.</p></div><dl class="terms">')
        for dt, dd in GLOSSARY:
            a(f'<div class="term"><dt>{esc(dt)}</dt><dd>{dd}</dd></div>')
        a('</dl></div></section>')

        # ----------------------------------------------------------- footer
        a('<footer class="foot"><div class="wrap foot-in">'
          '<span>Filecoin Public Goods Funding · Kernel · administered by the Blueshift Foundation</span>'
          '<span class="foot-links"><a href="#k-top">Overview</a>'
          '<a href="#k-functions">Inventory</a><a href="#k-timeline">Apply</a></span>'
          '</div></footer>')

        return '<div class="kpage">' + "".join(out) + "</div>"


    # ------------------------------------------------------------ components

    def proposed_block(props, today, show_team=True, dup_fids=frozenset()):
        """Metrics a team has put forward but not yet committed to.

        Kept in their own section at the foot of a row so a proposal never sits
        beside the adopted commitment it resembles, and never implies a
        threshold anyone has agreed to.
        """
        if not props:
            return ""
        return (f'<div class="metrics-head"><h4>Proposed</h4>'
                f'<span>{len(props)} metric{"s" if len(props) > 1 else ""} · '
                f'put forward, not yet committed</span></div>'
                f'<div class="cards proposed">'
                + "".join(metric_card(e, today, show_team=show_team,
                                      qualify=e["fid"] in dup_fids) for e in props)
                + '</div>')


    def project_row(p, today, E, KF, top_usd):
        """One funded team, with every commitment it carries.

        The mirror image of `function_row`: same summary grid, same strip, same
        metric cards — read down the project rather than down the function.
        """
        # Proposed metrics are held out of the committed sections, the row counts
        # and the aggregate: a draft carries no agreed threshold, so it can be
        # neither met nor missed. Leaving them inline also put near-identical
        # cards side by side — Curio's adopted and proposed release cadences read
        # as one card duplicated.
        ents = [E[i] for i in p["e"]]
        props = [e for e in ents if e["state"] == "draft"]
        ents = [e for e in ents if e["state"] != "draft"]
        hs = [e for e in ents if e["cls"] == "health"]
        ims = [e for e in ents if e["cls"] == "impact"]
        ag = agg(ents, today)
        measured = ag["pct"] is not None

        kf_by_name = {f["name"]: f for f in KF}
        fns = [kf_by_name[n] for n in p["fns"] if n in kf_by_name]
        tiers = [t for t in TIERS if any(f["tier"] == t["id"] for f in fns)]
        top_tier = tiers[0] if tiers else None

        # "1 Irreplaceable · 6 Essential" rather than a single tier name: a project
        # that touches one irreplaceable function and six essential ones is not an
        # irreplaceable project, and the row should not imply it is.
        eyebrow = " · ".join(
            f'{sum(1 for f in fns if f["tier"] == t["id"])} {t["name"]}'
            for t in tiers) or "No function mapped"
        colour = top_tier["v"] if top_tier else "--k-ink-3"

        bits = [f'<span class="pmoney">{usd(p["usd"])}</span>' if p.get("usd")
                else '<span class="quiet">no award this batch</span>']
        bits.append(f'{len(hs)} health metric{"s" if len(hs) != 1 else ""}'
                    if hs else '<span class="none">no health metric</span>')
        if ims:
            bits.append(f'{len(ims)} growth counter{"s" if len(ims) > 1 else ""}')
        meta = f'<div class="fn-m">{" · ".join(bits)}</div>'

        bar = ""
        if p.get("usd"):
            pctw = max(2, round(100 * p["usd"] / top_usd))
            bar = f'<div class="ftrack"><span class="fbar" style="width:{pctw}%"></span></div>'

        worst = None
        if hs:
            worst = min(hs, key=lambda e: (roll(e, today)["pct"]
                                           if roll(e, today)["pct"] is not None else 101))
        if worst is not None:
            row_bars = 46
            sbw = strip_bits(worst, today)
            span = 1 if len(sbw["keys"]) <= row_bars else -(-len(sbw["keys"]) // row_bars)
            cad = f'{span} {sbw["g"]}s' if span > 1 else f'1 {sbw["g"]}'
            strip = (strip_html(worst, today, small=True, max_bars=row_bars)
                     + f'<div class="rowcad">1 bar = {cad}'
                     + (f' · worst of {len(hs)}' if len(hs) > 1 else '') + '</div>')
        else:
            strip = '<div class="strip sm"></div>'

        if measured:
            pill = (f'<span class="pill bad">{ICON["bad"]} interrupted</span>'
                    if ag["state"] == "bad"
                    else f'<span class="pill ok">{ICON["good"]} meeting</span>')
        else:
            pill = '<span class="pill nm">not measured</span>'

        summary = (
            f'<summary>'
            f'<div><div class="fn-cat" style="color:var({colour})">{esc(eyebrow)}</div>'
            f'<div class="fn-t">{esc(p["name"])}</div>{meta}{bar}</div>'
            f'<div class="fn-rowstrip">{strip}</div>'
            f'<div class="fn-s"><div class="fn-p">{pct_label(ag["pct"])}</div>'
            f'<div class="fn-l">{"SLA MET · %dD" % WIN if measured else "NO DATA"}</div>{pill}</div>'
            f'<span class="car">{CARET}</span></summary>')

        body = ['<div class="fn-d">']
        if p.get("scope"):
            body.append(f'<p class="fn-purpose">{esc(p["scope"])}</p>')
        cells = [
            ("Committed this batch",
             (usd(p["usd"]) if p.get("usd") else '<span class="dim">no active grant</span>')),
            ("Kernel functions", f'<span class="num">{len(fns)}</span>'),
            ("Health commitments", f'<span class="num">{len(hs)}</span>'),
            ("Growth counters", f'<span class="num">{len(ims)}</span>'),
        ]
        body.append('<div class="fn-grid">' + "".join(
            f'<div><div class="fm-k">{esc(k)}</div><div class="fm-v">{v}</div></div>'
            for k, v in cells) + '</div>')

        if fns:
            chips = "".join(
                f'<span><i style="color:var({tier_by_id(f["tier"])["v"]})">'
                f'{esc(tier_by_id(f["tier"])["name"])}</i>{esc(f["name"])}</span>' for f in fns)
            body.append('<div class="pfns"><div class="dk">Kernel functions funded</div>'
                        f'<div class="chips">{chips}</div></div>')

        if hs:
            body.append(f'<div class="metrics-head"><h4>Health commitments</h4>'
                        f'<span>{len(hs)} metric{"s" if len(hs) > 1 else ""} · a threshold, met or missed</span></div>'
                        f'<div class="cards">'
                        + "".join(metric_card(e, today, show_team=False) for e in hs) + '</div>')
        else:
            pending = ("" if not props else
                       f' The {len(props)} below {"is" if len(props) == 1 else "are"} proposed, '
                       'not yet agreed.')
            body.append('<div class="empty"><b>No health metric is committed by this team.</b> '
                        'Nothing here can be held to a threshold, so an interruption in its work '
                        f'would be invisible to this page.{pending}</div>')

        if ims:
            body.append(f'<div class="metrics-head"><h4>Growth counters</h4>'
                        f'<span>tracked for direction · never colours the row</span></div>'
                        f'<div class="cards">'
                        + "".join(metric_card(e, today, show_team=False) for e in ims) + '</div>')

        body.append(proposed_block(props, today, show_team=False))

        # What the team asked to be judged on that no public source can answer
        # yet. Named in the same slug vocabulary the cards use, so a reader can
        # tell a gap in the instrument from a gap in the team's commitments.
        if p.get("asks"):
            chips = "".join(f'<span class="mono">{esc(a.replace("_", "-"))}</span>'
                            for a in p["asks"])
            body.append('<div class="pfns asks"><div class="dk">Requested · no public '
                        f'signal yet</div><div class="chips">{chips}</div></div>')

        body.append('</div>')
        return f'<details class="fn">{summary}{"".join(body)}</details>'


    def function_row(f, t, today, hs, ims, teams, pr_by_team):
        # see project_row: proposals sit in their own section, out of the counts
        # and out of the aggregate
        props = [e for e in hs + ims if e["state"] == "draft"]
        hs = [e for e in hs if e["state"] != "draft"]
        ims = [e for e in ims if e["state"] != "draft"]
        ag = agg(hs + ims, today)
        seen = {}
        for e in hs + ims + props:
            seen[e["fid"]] = seen.get(e["fid"], 0) + 1
        dup_fids = {k for k, v in seen.items() if v > 1}
        n = len(teams)
        measured = ag["pct"] is not None

        flags = []
        if n == 0:
            flags.append('<span class="flag bad">no maintainer reporting</span>')
        elif n == 1:
            flags.append('<span class="flag solo">single maintainer</span>')
        if not hs:
            flags.append('<span class="none">no health metric</span>')
        else:
            flags.append(f'{len(hs)} health metric{"s" if len(hs) > 1 else ""}')
        if ims:
            flags.append(f'{len(ims)} growth counter{"s" if len(ims) > 1 else ""}')
        meta = f'<div class="fn-m">{" · ".join(flags)}</div>'

        # the weakest health metric drives the row strip — a function is only as
        # healthy as its worst commitment
        worst = None
        if hs:
            worst = min(hs, key=lambda e: (roll(e, today)["pct"]
                                           if roll(e, today)["pct"] is not None else 101))
        if worst is not None:
            # 90 bars inside a 190px column renders as 1px hairlines; pairing
            # them up keeps the row strip legible at a glance
            row_bars = 46
            sbw = strip_bits(worst, today)
            g = sbw["g"]
            span = 1 if len(sbw["keys"]) <= row_bars else -(-len(sbw["keys"]) // row_bars)
            cad = f"{span} {g}s" if span > 1 else f"1 {g}"
            strip = (strip_html(worst, today, small=True, max_bars=row_bars)
                     + f'<div class="rowcad">1 bar = {cad}'
                     + (f' · worst of {len(hs)}' if len(hs) > 1 else '') + '</div>')
        else:
            strip = '<div class="strip sm"></div>'

        if measured:
            pill = (f'<span class="pill bad">{ICON["bad"]} interrupted</span>'
                    if ag["state"] == "bad"
                    else f'<span class="pill ok">{ICON["good"]} meeting</span>')
        else:
            pill = '<span class="pill nm">not measured</span>'

        summary = (
            f'<summary>'
            f'<div><div class="fn-cat" style="color:var({t["v"]})">{esc(t["name"])} · {esc(f["sub"])}</div>'
            f'<div class="fn-t">{esc(f["name"])}</div>{meta}</div>'
            f'<div class="fn-rowstrip">{strip}</div>'
            f'<div class="fn-s"><div class="fn-p">{pct_label(ag["pct"])}</div>'
            f'<div class="fn-l">{"SLA MET · %dD" % WIN if measured else "NO DATA"}</div>{pill}</div>'
            f'<span class="car">{CARET}</span></summary>')

        # ---- expanded panel
        if teams:
            team_names = ", ".join(
                esc(pr_by_team[x]["name"]) if x in pr_by_team else esc(x) for x in teams)
        else:
            team_names = '<span class="dim">no team reporting yet</span>'
        funded = [pr_by_team[x] for x in teams
                  if x in pr_by_team and pr_by_team[x].get("usd")]
        money = (usd(sum(p["usd"] for p in funded)) + f' <span style="color:var(--k-ink-3);'
                 f'font-family:var(--k-mono);font-size:12px">across {len(funded)} '
                 f'grant{"s" if len(funded) > 1 else ""}</span>') if funded else \
            '<span class="dim">no active grant</span>'

        cells = [
            ("Teams reporting", team_names),
            ("Domain", f'<span class="dim">{esc(f["cat"])}</span>'),
            ("Health commitments", f'<span class="num">{len(hs)}</span>'),
            ("Growth counters", f'<span class="num">{len(ims)}</span>'),
            ("Committed through Dec", money),
        ]
        grid = "".join(f'<div><div class="fm-k">{esc(k)}</div><div class="fm-v">{v}</div></div>'
                       for k, v in cells)

        body = [f'<div class="fn-d"><p class="fn-purpose">{esc(f["why"])}</p>'
                f'<div class="fn-grid">{grid}</div>']

        if hs:
            body.append(f'<div class="metrics-head"><h4>Health commitments</h4>'
                        f'<span>{len(hs)} metric{"s" if len(hs) > 1 else ""} · a threshold, met or missed</span></div>'
                        f'<div class="cards">'
                        + "".join(metric_card(e, today, qualify=e["fid"] in dup_fids)
                                  for e in hs) + '</div>')
        else:
            extra = ""
            if ims:
                names = ", ".join(f'<span class="mono">{esc(e["metric"])}</span>' for e in ims)
                extra = (f' Its only monitoring is {len(ims)} growth counter'
                         f'{"s" if len(ims) > 1 else ""} ({names}), which can never report an outage.')
            body.append('<div class="empty"><b>No health metric is committed against this '
                        f'function.</b>{extra} Until one is, an interruption here would be invisible '
                        'to this page.</div>')

        if ims:
            body.append(f'<div class="metrics-head"><h4>Growth counters</h4>'
                        f'<span>tracked for direction · never colours the row</span></div>'
                        f'<div class="cards">'
                        + "".join(metric_card(e, today, qualify=e["fid"] in dup_fids)
                                  for e in ims) + '</div>')

        body.append(proposed_block(props, today, dup_fids=dup_fids))
        body.append('</div>')
        return f'<details class="fn">{summary}{"".join(body)}</details>'


    def program_metrics(KF, E, PR, today, health, impact, teams_of):
        listed = len(KF)
        declared = sum(t["declared"] or 0 for t in TIERS)
        all_h = [e for e in E if e["cls"] == "health"]
        all_i = [e for e in E if e["cls"] == "impact"]
        ag = agg(all_h, today)
        measured_fns = [f for f in KF if health(f)]
        unmeasured = listed - len(measured_fns)
        top_solo = sum(1 for f in KF
                       if f["tier"] in ("irreplaceable", "essential") and len(teams_of(f)) == 1)
        unowned = sum(1 for f in KF if not teams_of(f))
        teams = len({e["team"] for e in E})
        money = sum(p.get("usd") or 0 for p in PR)
        n_funded = sum(1 for p in PR if p.get("usd"))
        cover = round(len(measured_fns) / listed * 100)

        return [
            {"v": usd(money), "k": "Committed across funded teams",
             "d": f"{n_funded} of {len(PR)} reporting teams · batch ends Dec", "cls": ""},
            {"v": pct_label(ag["pct"]), "k": "SLA met across all health commitments",
             "d": f"Rolling {WIN} days · {len(all_h)} commitments, "
                  f"{len(all_i)} growth counters", "cls": ""},
            {"v": f"{cover}%", "k": "Measurement coverage",
             "d": f"{unmeasured} of {listed} functions report no health metric",
             "cls": "warn" if unmeasured else ""},
            {"v": str(top_solo), "k": "Top-tier functions with a single maintaining team",
             "d": "Posture calls for 2+ implementations", "cls": "bad" if top_solo else ""},
            {"v": str(unowned), "k": "Functions with no team reporting",
             "d": "Invisible to this page until one signs up",
             "cls": "bad" if unowned else ""},
            {"v": str(teams), "k": "Teams reporting",
             "d": f"Across {declared} declared functions", "cls": ""},
        ]

    return (build_kernel_page,)


@app.cell(hide_code=True)
def registry(base64, gzip, json):
    # The Kernel registry, gzipped + base64 on one line. A triple-quoted
    # blob with content at column 0 is the classic Pyodide publish failure,
    # and packing it this way sidesteps it entirely.
    _PAYLOAD = "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"
    REGISTRY = json.loads(gzip.decompress(base64.b64decode(_PAYLOAD)).decode("utf-8"))
    return (REGISTRY,)


@app.cell(hide_code=True)
def _():
    import base64
    import datetime
    import gzip
    import json
    import math

    return base64, datetime, gzip, json, math


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
