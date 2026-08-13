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
