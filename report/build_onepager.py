"""One-page summary to send with the full report.

Run: python report/build_onepager.py -> report/EP_Pitcher_Extension_OnePager.pdf
"""
import json
from pathlib import Path

import pandas as pd
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", (ROOT / "figures").as_uri()
LOGO = (ROOT / "report" / "ep_logo.png").as_uri()
M = pd.read_csv(RES / "main_effects.csv").set_index("outcome")
DEC = pd.read_csv(RES / "decomposition.csv").set_index("outcome")
LOC = pd.read_csv(RES / "location.csv").set_index("outcome")
SENS = pd.read_csv(RES / "sensitivity.csv")
S = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
S2 = json.loads((RES / "summary_v2.json").read_text(encoding="utf-8"))
TH = json.loads((RES / "thresholds.json").read_text(encoding="utf-8"))
csw = M.loc["csw_pct"]
mph = csw["coef_per_ft"] * 0.3 / csw["velo_coef_per_mph"]
extra = csw["effect_per_0.3ft"] / 100 * S2["median_fastballs_per_season"]
rp = SENS[(SENS["sample"] == "relievers only") & (SENS["outcome"] == "csw_pct")].iloc[0]
sp = SENS[(SENS["sample"] == "starters only") & (SENS["outcome"] == "csw_pct")].iloc[0]

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page {{ size: letter; margin: 0.4in 0.5in; }}
body {{ font-family: Poppins; font-size: 8.3pt; color: #1F2937; line-height: 1.33; }}
.top {{ display: flex; align-items: center; gap: 14px; border-bottom: 3px solid #0B1B33; padding-bottom: 8px; }}
.top img {{ width: 78px; }}
.top .t {{ font: 700 15pt Poppins; color: #0B1B33; line-height: 1.1; }}
.top .s {{ font: italic 9pt Lora; color: #4B5563; }}
.top .r {{ margin-left: auto; text-align: right; font-size: 7.6pt; color: #4B5563; }}
.head {{ background: #F5F3EC; border-left: 4px solid #D4A53A; padding: 8px 12px; margin: 10px 0; font-size: 9.6pt; }}
.kpis {{ display: flex; gap: 8px; margin: 8px 0; }}
.kpi {{ flex: 1; border-top: 3px solid #D4A53A; background: #F5F3EC; padding: 6px 8px; }}
.kpi .v {{ font: 700 15pt Poppins; color: #0B1B33; }} .kpi .l {{ font-size: 7.3pt; color: #4B5563; line-height: 1.25; }}
h2 {{ font: 600 10pt Poppins; color: #0B1B33; border-left: 3px solid #D4A53A; padding-left: 6px; margin: 10px 0 4px; }}
ul {{ margin: 2px 0; padding-left: 15px; }} li {{ margin-bottom: 2px; }}
.two {{ display: flex; gap: 14px; }} .two > div {{ flex: 1; }}
img.fig {{ width: 100%; }}
.foot {{ position: fixed; bottom: 0; left: 0; right: 0; border-top: 1px solid #D4A53A; padding-top: 5px; font-size: 7.3pt; color: #4B5563; }}
.tag {{ font: 600 6.5pt Poppins; padding: 0 4px; border-radius: 3px; background: #0B1B33; color: #F5F3EC; }}
.tag.e {{ background: #fff; color: #0B1B33; border: 1px solid #0B1B33; }}
</style></head><body>
<div class="top"><img src="{LOGO}"><div><div class="t">Fastball Extension as a Development Lever</div>
<div class="s">League-wide Statcast study, 2021–2026 · one-page summary</div></div>
<div class="r"><b>Emerson Jimenez</b><br>Emerson Performance<br>November 2026</div></div>

<div class="head"><b>Bottom line.</b> When a pitcher gained <b>+0.3 ft</b> of fastball extension, his fastball came with
<b>{csw['effect_per_0.3ft']:+.2f} points of CSW%</b> (95% CI {csw['boot_lo_0.3ft']:+.2f} to {csw['boot_hi_0.3ft']:+.2f}) with velocity held
constant — about what <b>+{mph:.1f} mph</b> came with. It did not come with less damage. Extension is a strike-throwing tool to
train, starting with relievers.</div>

<div class="kpis">
<div class="kpi"><div class="v">{csw['effect_per_0.3ft']:+.2f}</div><div class="l">CSW% pts per +0.3 ft<br><span class="tag">CONFIRMED</span> q = {csw['q_bh']:.3f}</div></div>
<div class="kpi"><div class="v">≈ {mph:.1f} mph</div><div class="l">velocity gain with the<br>same strike effect</div></div>
<div class="kpi"><div class="v">≈ {extra:.1f}</div><div class="l">extra strikes per season<br>(typical pitcher)</div></div>
<div class="kpi"><div class="v">{S['n_pairs_primary']}</div><div class="l">pitcher pairs, {S['n_pitchers_primary']} pitchers<br>within-pitcher design</div></div>
</div>

<div class="two"><div>
<h2>What the data showed</h2>
<ul>
<li><b>Strikes, not damage.</b> xwOBA ({M.loc['xwoba','effect_per_0.3ft']:+.3f}) and run value ({M.loc['rv100','effect_per_0.3ft']:+.2f}/100) did not move.</li>
<li><b>Mostly called strikes</b> (~{DEC.loc['called_pct','share_of_csw_effect']*100:.0f}% of the gain). <span class="tag e">EXPLORATORY</span></li>
<li><b>More zone fastballs</b> ({LOC.loc['zone_pct','effect_per_0.3ft']:+.2f}) and <b>fewer swings at them</b> ({LOC.loc['z_swing_pct','effect_per_0.3ft']:+.2f}); no umpire effect. Neither survived multiple-test correction on its own. <span class="tag e">EXPLORATORY</span></li>
<li><b>Not movement.</b> The effect held with pitch shape controlled.</li>
<li><b>Relievers</b> {rp['effect_per_0.3ft']:+.2f} (p = {rp['p']:.3f}); starters {sp['effect_per_0.3ft']:+.2f} (n.s.).</li>
<li><b>Separate lever from velocity</b> (r = {S['baseline']['corr_d_ext_d_velo']:.2f}); big gains are rare but hold the next year.</li>
</ul>
</div><div>
<img class="fig" src="{FIG}/extension_dose_response.png">
</div></div>

<div class="two"><div>
<h2>What a club should do</h2>
<ul>
<li><b>Train it</b> through hip mobility, lead-leg block and adductor capacity, then stride work in bullpens.</li>
<li><b>Monitor it</b> outing by outing: a 5-outing average {TH['p95_abs_5outing_dev_ft']:.2f} ft below a pitcher's own baseline is outside 95% of normal variation.</li>
<li><b>Treat big drops as health checks first</b>: all 5 season losses of 0.3 ft or more came with a long absence.</li>
<li><b>Do not add it to projection models</b>: out of sample it did not reduce error.</li>
</ul>
<h2>How it was tested</h2>
<ul>
<li>Each pitcher compared to himself, year over year, regular-season four-seamers and sinkers, minimum 300 per season.</li>
<li>Rules for <span class="tag">CONFIRMED</span> fixed before the real data; Benjamini–Hochberg correction; cluster bootstrap CIs.</li>
<li>Absences filtered; 9 alternative explanations tested (role, team, arm angle, 2023 league shift, shape and more).</li>
<li>Known-answer test on synthetic data passed in both directions.</li>
</ul>
</div><div>
<h2>Applied case: Grant Taylor (CWS)</h2>
<p>Four-seam extension fell from 7.40 to 7.19 ft (2025 → 2026), starting near his Sep 2025 groin strain and continuing through a heavier
workload. The report includes a 12-week restore-and-hold plan, physical markers and in-season check-ins.</p>
<img class="fig" src="{FIG}/case_taylor_extension.png">
</div></div>

<div class="foot">Full report: EP_Pitcher_Extension_Report.pdf · Code and data pipeline: github.com/ejimenezperformance/ep-pitcher-extension ·
ejimenezperformance.github.io · Observational design: effects "came with" extension change; causation is not claimed.</div>
</body></html>"""

out = ROOT / "report" / "EP_Pitcher_Extension_OnePager.pdf"
HTML(string=html, base_url=str(ROOT)).write_pdf(out)
print(out)
