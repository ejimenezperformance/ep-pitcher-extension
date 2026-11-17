"""Build the EP Player Development case-study PDF from the results folder.

Run: python report/build_report.py  ->  report/EP_Pitcher_Extension_Report.pdf
"""
import json
from pathlib import Path

import pandas as pd
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", (ROOT / "figures").as_uri()
S = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
M = pd.read_csv(RES / "main_effects.csv").set_index("outcome")
SENS = pd.read_csv(RES / "sensitivity.csv")
LOO = pd.read_csv(RES / "loo_projection.csv").set_index("outcome")
TGT = pd.read_csv(RES / "offseason_targets_2027.csv")
B, P = S["baseline"], S["baseline"]["persistence"]
S2 = json.loads((RES / "summary_v2.json").read_text(encoding="utf-8"))
DEC = pd.read_csv(RES / "decomposition.csv").set_index("outcome")
SHP = pd.read_csv(RES / "shape_control.csv")
LOC = pd.read_csv(RES / "location.csv").set_index("outcome")
TH = json.loads((RES / "thresholds.json").read_text(encoding="utf-8"))
ABS = pd.read_csv(RES / "absence_by_change.csv")
RP = SENS[(SENS["sample"] == "relievers only") & (SENS["outcome"] == "csw_pct")].iloc[0]
SP = SENS[(SENS["sample"] == "starters only") & (SENS["outcome"] == "csw_pct")].iloc[0]

csw = M.loc["csw_pct"]
mph_equiv = csw["coef_per_ft"] * 0.3 / csw["velo_coef_per_mph"]
extra_strikes = csw["effect_per_0.3ft"] / 100 * S2["median_fastballs_per_season"]
called_share = DEC.loc["called_pct", "share_of_csw_effect"]


def f(x, d=2, sign=True):
    return f"{x:+.{d}f}" if sign else f"{x:.{d}f}"


def main_rows():
    names = {"csw_pct": ("CSW% (called + swinging strikes per pitch)", "pts", 2),
             "whiff_pct": ("Whiff% (whiffs per swing)", "pts", 2),
             "rv100": ("Run value per 100 fastballs", "runs", 2),
             "xwoba": ("xwOBA allowed on fastballs", "", 3)}
    out = ""
    for o in ["csw_pct", "whiff_pct", "rv100", "xwoba"]:
        r, (n, u, d) = M.loc[o], names[o]
        tag = "conf" if r["label"] == "CONFIRMED" else "nc"
        out += (f"<tr><td>{n}</td><td><b>{f(r['effect_per_0.3ft'], d)}</b> {u}</td>"
                f"<td>{f(r['boot_lo_0.3ft'], d)} to {f(r['boot_hi_0.3ft'], d)}</td>"
                f"<td>{r['q_bh']:.3f}</td><td><span class='tag {tag}'>{r['label']}</span></td></tr>")
    return out


def sens_rows():
    nice = {
        "all_pairs (no absence filter)": "All pairs, no absence filter",
        "primary minus role changes": "Without role changes (SP / RP)",
        "primary minus team changes": "Without team changes",
        "primary minus arm-angle change >=5 deg": "Without arm-angle changes of 5° or more",
        "primary + arm-angle control": "Arm-angle change added as a control",
        "primary minus 2022->2023 (league-wide shift)": "Without 2022→2023 (league-wide shift)",
        "relievers only": "Relievers only",
        "starters only": "Starters only",
    }
    s = SENS[SENS["outcome"] == "csw_pct"].set_index("sample")
    out = (f"<tr class='hl'><td>Primary sample</td><td>{int(csw['n_pairs'])}</td>"
           f"<td>{f(csw['effect_per_0.3ft'])}</td><td>{csw['p']:.3f}</td><td>Reference</td></tr>")
    for k, lab in nice.items():
        r = s.loc[k]
        verdict = "Holds" if r["p"] < 0.05 else "Same direction, not significant"
        pv = "&lt; 0.001" if r["p"] < 0.001 else f"{r['p']:.3f}"
        out += (f"<tr><td>{lab}</td><td>{int(r['n_pairs'])}</td><td>{f(r['effect_per_0.3ft'])}</td>"
                f"<td>{pv}</td><td>{verdict}</td></tr>")
    return out


def shape_rows():
    names = {"csw_pct": "CSW%", "called_pct": "Called strikes", "swstr_pct": "Swinging strikes",
             "whiff_pct": "Whiff% (per swing)", "xwoba": "xwOBA allowed"}
    out = ""
    for o, n in names.items():
        a = SHP[(SHP["outcome"] == o) & (SHP["model"] == "velocity only")].iloc[0]
        b = SHP[(SHP["outcome"] == o) & (SHP["model"] != "velocity only")].iloc[0]
        d = 3 if o == "xwoba" else 2
        pv = "&lt; 0.001" if b["p"] < 0.001 else f"{b['p']:.3f}"
        out += (f"<tr><td>{n}</td><td>{f(a['effect_per_0.3ft'], d)}</td>"
                f"<td><b>{f(b['effect_per_0.3ft'], d)}</b></td><td>{pv}</td></tr>")
    return out


def loc_rows():
    names = {"zone_pct": "Fastballs in the zone (Zone%)", "z_swing_pct": "Swings at zone fastballs (Z-Swing%)",
             "z_called_pct": "Called strikes on zone fastballs", "o_called_pct": "Called strikes outside the zone"}
    out = ""
    for o, n in names.items():
        r = LOC.loc[o]
        out += (f"<tr><td>{n}</td><td>{r['baseline_mean']:.1f}%</td><td><b>{f(r['effect_per_0.3ft'])}</b> pts</td>"
                f"<td>{f(r['boot_lo_0.3ft'])} to {f(r['boot_hi_0.3ft'])}</td><td>{r['p']:.3f}</td><td>{r['q_bh']:.3f}</td></tr>")
    return out


def target_rows():
    notes = {"Lynch IV, Daniel": "Elbow nerve IL Jul 2025; to rotation Aug 2026",
             "Ramírez, Yohan": "No IL found (paternity list only)",
             "Latz, Jacob": "No 2025–26 IL found; swingman",
             "Bachar, Lake": "No IL found; opener role",
             "Kerkering, Orion": "Hamstring strain, IL to open 2026",
             "Burke, Sean": "No 2026 IL found; bulk-relief usage",
             "Peralta, Freddy": "Traded twice; no 2026 IL found",
             "Taylor, Grant": "Groin strain Sep 2025; opener role",
             "Cavalli, Cade": "Calf contusion Aug 2026; arm-angle change",
             "Chapman, Aroldis": "Hamstring, lat tightness Sep 2026; velo down"}
    out = ""
    for _, r in TGT.iterrows():
        last, first = [x.strip() for x in r["name_y0"].split(",", 1)]
        out += (f"<tr><td>{first} {last}</td><td>{r['team_y1']}</td><td>{r['role_y1']}</td>"
                f"<td>{r['ext_y0']:.2f} → {r['ext_y1']:.2f}</td><td>{f(r['d_velo'])}</td>"
                f"<td>{f(r['d_arm_angle'], 1)}</td><td>{notes.get(r['name_y0'], '—')}</td></tr>")
    return out


_pairs = pd.read_csv(ROOT / "data/processed/pairs.csv")
TR = _pairs[(_pairs["name_y0"] == "Taylor, Grant") & (_pairs["pair"] == "2025->2026")].iloc[0]
_seas = pd.read_csv(ROOT / "data/processed/pitcher_seasons.csv")
_q26 = _seas[(_seas["n_fb"] >= 300) & (_seas["year"] == 2026)]
_ff = pd.concat([pd.read_csv(ROOT / f"data/raw/fastballs_{y}.csv", low_memory=False,
                             usecols=["player_name", "pitch_type", "release_extension", "game_date"]) for y in (2025, 2026)])
_ff = _ff[(_ff["player_name"] == "Taylor, Grant") & (_ff["pitch_type"] == "FF")]
_ff["d"] = pd.to_datetime(_ff["game_date"])
_m26 = _ff[_ff["d"].dt.year == 2026].groupby(_ff["d"].dt.month)["release_extension"].mean()
TC = {"ff_ext_25": _ff[_ff["d"].dt.year == 2025]["release_extension"].mean(),
      "ff_ext_26": _ff[_ff["d"].dt.year == 2026]["release_extension"].mean(),
      "pctl_26": 100 * (_q26["ext"] < TR["ext_y1"]).mean(),
      "m_peak": _m26.max(), "m_sep": _m26.loc[9]}

HEADER = "EMERSON PERFORMANCE | PITCHING DEVELOPMENT"
FOOTER = "PLAYER DEVELOPMENT CASE STUDY • FASTBALL EXTENSION"

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
@page {{ size: letter; margin: 0.75in 0.7in 0.7in 0.7in;
  @top-right {{ content: "{HEADER}"; font: 600 7.5pt Poppins; color: #0B1B33; letter-spacing: .5px; }}
  @bottom-center {{ content: "{FOOTER}  •  " counter(page); font: 7pt Poppins; color: #6B7280; }} }}
@page cover {{ margin: 0; @top-right {{ content: none; }} @bottom-center {{ content: none; }} }}
body {{ font-family: Poppins; font-size: 8.9pt; color: #1F2937; line-height: 1.4; }}
h1 {{ font: 700 20pt Poppins; color: #0B1B33; margin: 2px 0 4px; }}
h2 {{ font: 600 11.5pt Poppins; color: #0B1B33; margin: 18px 0 6px; border-left: 3px solid #D4A53A; padding-left: 7px; }}
.kicker {{ font: 600 7.5pt Poppins; color: #B8862A; letter-spacing: 1px; }}
.sub {{ font: italic 9.5pt Lora; color: #4B5563; margin: 0 0 10px; }}
p {{ margin: 4px 0 6px; }}
table {{ width: 100%; border-collapse: collapse; margin: 8px 0 12px; font-size: 8.3pt; }}
th {{ background: #0B1B33; color: #F5F3EC; text-align: left; padding: 4px 6px; font-weight: 600; }}
td {{ padding: 3.5px 6px; border-bottom: 1px solid #E5E1D6; vertical-align: top; }}
tr.hl td {{ background: #F5F3EC; font-weight: 600; }}
.box {{ background: #F5F3EC; border-left: 4px solid #D4A53A; padding: 7px 10px; margin: 8px 0; }}
.box.navy {{ border-left-color: #0B1B33; }}
.box b.lab {{ display: block; font: 600 7.5pt Poppins; letter-spacing: .8px; color: #0B1B33; margin-bottom: 2px; }}
.tag {{ font: 600 7pt Poppins; padding: 1px 5px; border-radius: 3px; }}
.conf {{ background: #0B1B33; color: #F5F3EC; }}
.nc {{ background: #E5E1D6; color: #374151; }}
.exp {{ background: #fff; color: #0B1B33; border: 1px solid #0B1B33; }}
.desc {{ background: #E9EEF5; color: #0B1B33; }}
.interp {{ font: 600 7pt Poppins; color: #B8862A; border: 1px solid #B8862A; padding: 0 4px; border-radius: 3px; }}
img.fig {{ width: 78%; display: block; margin: 14px auto 4px; }}
.cap {{ font: italic 7.8pt Lora; color: #6B7280; text-align: center; margin-bottom: 16px; }}
.kpis {{ display: flex; gap: 10px; margin: 10px 0; }}
.kpi {{ flex: 1; background: #F5F3EC; padding: 8px 10px; border-top: 3px solid #D4A53A; }}
.kpi .v {{ font: 700 20pt Poppins; color: #0B1B33; }}
.kpi .l {{ font-size: 7.8pt; color: #4B5563; line-height: 1.3; }}
ul {{ margin: 3px 0 6px 0; padding-left: 16px; }} li {{ margin-bottom: 3px; }}
.pb {{ break-before: page; }}
img.fig, .box, .two, .kpis, table {{ break-inside: avoid; }}

img.fig {{ break-after: avoid; }}
h1, h2, .kicker, .sub {{ break-after: avoid; }}
.cover {{ page: cover; height: 11in; width: 8.5in; background: #F5F3EC; text-align: center; padding: 1.3in 0.9in 0 0.9in; box-sizing: border-box; position: relative; border-top: 14px solid #0B1B33; }}
/* legacy */ .cover .mono {{ width: 92px; height: 92px; line-height: 92px; margin: 0 auto 14px; border-radius: 50%; background: #0B1B33; color: #D4A53A; font: 700 34pt Poppins; border: 4px solid #D4A53A; }}
.cover .logo {{ width: 190px; height: auto; display: block; margin: 0 auto 16px; }}
.cover .brand {{ font: 600 10pt Poppins; letter-spacing: 4px; color: #0B1B33; }}
.cover .rule {{ width: 80px; height: 3px; background: #D4A53A; margin: 26px auto 22px; }}
.cover h1 {{ font: 700 30pt Poppins; color: #0B1B33; line-height: 1.12; margin: 0 0 12px; }}
.cover .tag2 {{ font: 600 11pt Poppins; color: #B8862A; letter-spacing: 1.5px; margin-bottom: 20px; }}
.cover .sub {{ font: italic 12pt Lora; color: #374151; margin: 0 0.4in 34px; }}
.cover .focus {{ text-align: left; background: #fff; border-left: 4px solid #0B1B33; padding: 12px 16px; font-size: 9.5pt; line-height: 1.5; }}
.cover .focus b {{ font-size: 8pt; letter-spacing: 1px; color: #0B1B33; }}
.cover .case {{ margin-top: 60px; font: 600 10pt Poppins; letter-spacing: 2px; color: #0B1B33; }}
.cover .meta {{ position: absolute; bottom: 0.7in; left: 0.9in; right: 0.9in; font-size: 8.5pt; color: #4B5563; border-top: 1px solid #D4A53A; padding-top: 10px; }}
.cover .meta b {{ color: #0B1B33; }}
.two {{ display: flex; gap: 14px; }} .two > div {{ flex: 1; }}
.small {{ font-size: 7.8pt; color: #4B5563; }}
</style></head><body>

<section class="cover">
  <img class="logo" src="{(ROOT / "report" / "ep_logo.png").as_uri()}">
  <div class="brand">EMERSON PERFORMANCE</div>
  <div class="rule"></div>
  <h1>FASTBALL EXTENSION<br>DEVELOPMENT PROJECT</h1>
  <div class="tag2">PITCHING | LEAGUE-WIDE STATCAST STUDY</div>
  <div class="sub">A data-informed evaluation of fastball extension and an individualized offseason development proposal</div>
  <div class="focus"><b>PROJECT FOCUS</b><br>Determine whether gaining release extension — a product of stride length, hip mobility
  and lead-leg block — comes with better fastball outcomes beyond velocity, and how a club should train and monitor it.</div>
  <div class="case">2026 PLAYER DEVELOPMENT CASE STUDY</div>
  <div class="meta"><b>Prepared by Emerson Jimenez</b> · Emerson Performance · November 2026<br>
  Data: Baseball Savant (Statcast), regular season 2021–2026 · github.com/ejimenezperformance/ep-pitcher-extension</div>
</section>

<div class="kicker">01 | EXECUTIVE SUMMARY</div>
<h1>The decision question</h1>
<div class="sub">Is fastball extension worth training in the offseason, and what should a club expect if a pitcher gains it?
{S['n_pairs_primary']} year-over-year pairs, {S['n_pitchers_primary']} pitchers, Statcast 2021–2026.</div>

<div class="kpis">
  <div class="kpi"><div class="v">{f(csw['effect_per_0.3ft'])}</div><div class="l">CSW% points per +0.3 ft<br>95% CI {f(csw['boot_lo_0.3ft'])} to {f(csw['boot_hi_0.3ft'])}</div></div>
  <div class="kpi"><div class="v">≈ {mph_equiv:.1f} mph</div><div class="l">velocity gain with the<br>same CSW% effect</div></div>
  <div class="kpi"><div class="v">≈ {extra_strikes:.1f}</div><div class="l">extra strikes per season<br>({S2['median_fastballs_per_season']:.0f} fastballs, typical pitcher)</div></div>
</div>
<div class="box navy"><b class="lab">ANSWER</b>Yes, as a <b>strike-throwing</b> tool, with relievers first. Gaining extension came with more
fastball strikes — about {called_share*100:.0f}% of them <b>called</b> strikes — independent of velocity and pitch shape. It did not
come with weaker contact allowed, so it should not be sold as a run-prevention fix.</div>

<h2>Takeaways for a front office</h2>
<table><tr><th style="width:26%">Takeaway</th><th>Evidence</th><th style="width:12%">Label</th></tr>
<tr><td><b>Extension buys strikes</b></td><td>{f(csw['effect_per_0.3ft'])} CSW% pts per +0.3 ft (q = {csw['q_bh']:.3f}); held in every robustness check but starters alone.</td><td><span class="tag conf">CONFIRMED</span></td></tr>
<tr><td><b>Mostly called strikes</b></td><td>Called strikes {f(DEC.loc['called_pct','effect_per_0.3ft'])} pts per pitch (q = {DEC.loc['called_pct','q_bh']:.3f}); swinging strikes {f(DEC.loc['swstr_pct','effect_per_0.3ft'])} (not significant).</td><td><span class="tag exp">EXPLORATORY</span></td></tr>
<tr><td><b>Strongest in relievers</b></td><td>Relievers {f(RP['effect_per_0.3ft'])} (p = {RP['p']:.3f}); starters {f(SP['effect_per_0.3ft'])} (p = {SP['p']:.2f}, not significant).</td><td><span class="tag exp">EXPLORATORY</span></td></tr>
<tr><td><b>Not damage</b></td><td>xwOBA {f(M.loc['xwoba','effect_per_0.3ft'],3)}, run value {f(M.loc['rv100','effect_per_0.3ft'])} per 100 — both near zero.</td><td><span class="tag nc">NOT CONFIRMED</span></td></tr>
<tr><td><b>Separate from velocity</b></td><td>Year-over-year changes in extension and velocity barely move together (r = {B['corr_d_ext_d_velo']:.2f}).</td><td><span class="tag desc">DESCRIPTIVE</span></td></tr>
<tr><td><b>Gains are rare but hold</b></td><td>{B['pct_pairs_gain_ge_0.3']:.1f}% of pairs gained ≥ 0.3 ft; next-year change does not undo them (slope {P['slope_next_on_current']:+.2f}).</td><td><span class="tag desc">DESCRIPTIVE</span></td></tr>
<tr><td><b>A big drop is a health flag</b></td><td>All {S['big_losses_all']} pairs that lost ≥ 0.3 ft had a long absence (IL or option), vs {TH['absence_base_rate_pct']:.0f}% of all pairs. Smaller losses did not differ.</td><td><span class="interp">INTERPRETATION</span></td></tr>
</table>

<h2>Scope and interpretation</h2>
<p>All figures come from public Statcast data and are reproducible from the code repository. Labels:
<span class="tag conf">CONFIRMED</span> passed rules fixed before the real data was run;
<span class="tag exp">EXPLORATORY</span> is a follow-up test added afterward (significant, but not pre-registered);
<span class="tag desc">DESCRIPTIVE</span> describes the data without a hypothesis test;
<span class="interp">INTERPRETATION</span> is a biomechanical reading or hypothesis. The design is observational: a change
<i>came with</i> an outcome; it is never said to have <i>caused</i> it.</p>

<div class="pb"></div>
<div class="kicker">02 | STATISTICAL EVALUATION</div>
<h1>What came with a gain in extension</h1>
<div class="sub">Within-pitcher change model: Δoutcome ~ Δvelocity + Δextension + baseline level + season fixed effects.</div>
<table><tr><th>Outcome (per +0.3 ft, velocity constant)</th><th>Effect</th><th>95% CI (cluster bootstrap)</th><th>BH q</th><th>Label</th></tr>
{main_rows()}</table>
<p class="small">Rule fixed before running the real data: <b>CONFIRMED</b> = Benjamini–Hochberg q &lt; 0.05 across the four outcomes <b>and</b>
the +0.3 ft effect reaches a practical threshold (Whiff% ≥ +0.75, CSW% ≥ +0.50, RV/100 ≥ +0.20, xwOBA ≤ −0.005).</p>
<img class="fig" src="{FIG}/extension_effects_forest.png" style="width:100%">
<div class="cap">Dot = estimated effect of +0.3 ft. Bar = 95% CI. Dashed gold line = practical threshold set in advance.</div>

<h2>What the data does — and does not — tell us</h2>
<ul>
<li>Extension change <b>came with</b> more strikes; the design is observational, so it does not prove extension <b>caused</b> them.</li>
<li>Whiff% moved the same direction (+{M.loc['whiff_pct','effect_per_0.3ft']:.2f}) but the interval includes zero.</li>
<li>Out of sample, adding extension to a velocity-only model did not improve whiff projections (MAE change {LOO.loc['whiff_pct','mae_improvement']:+.4f}).
Use it as a development target, not as a projection input.</li>
</ul>
<h2>Projection test (leave one pitcher out)</h2>
<table><tr><th>Outcome change</th><th>MAE, velocity only</th><th>MAE, velocity + extension</th><th>Improvement (95% CI)</th></tr>
<tr><td>Whiff%</td><td>{LOO.loc['whiff_pct','mae_velo_only']:.3f}</td><td>{LOO.loc['whiff_pct','mae_velo_plus_ext']:.3f}</td><td>{LOO.loc['whiff_pct','mae_improvement']:+.4f} ({LOO.loc['whiff_pct','ci_lo']:+.3f} to {LOO.loc['whiff_pct','ci_hi']:+.3f})</td></tr>
<tr><td>xwOBA</td><td>{LOO.loc['xwoba','mae_velo_only']:.4f}</td><td>{LOO.loc['xwoba','mae_velo_plus_ext']:.4f}</td><td>{LOO.loc['xwoba','mae_improvement']:+.5f}</td></tr>
</table>
<div class="box"><b class="lab">ANALYTICAL STANDARD</b>Treat the CSW% result as the signal that justifies a development
plan. Do not treat it as a reason to add extension to projection models: out of sample, it did not reduce error.</div>

<div class="pb"></div>
<div class="kicker">03 | DOSE RESPONSE AND NATURAL BASELINE</div>
<h1>How much extension changes on its own</h1>
<div class="sub">Without a baseline, any change looks like success. These checks describe what happens without intervention.</div>
<img class="fig" src="{FIG}/extension_dose_response.png" style="width:74%">
<div class="cap">CSW% change after removing what velocity and the starting level explain. Error bars: 95% CI.</div>
<div class="two"><div>
<table><tr><th>Check</th><th>Result</th></tr>
<tr><td>Split-half reliability (odd vs even games)</td><td>r = {B['split_half_r']:.3f}</td></tr>
<tr><td>Smallest real season change (MDC95)</td><td>{B['mdc95_change_ft']:.2f} ft</td></tr>
<tr><td>SD of year-over-year change</td><td>{B['sd_delta_ext_ft']:.2f} ft</td></tr>
<tr><td>Pairs gaining ≥ 0.3 ft</td><td>{B['pct_pairs_gain_ge_0.3']:.1f}%</td></tr>
<tr><td>Next-year change on this-year change</td><td>slope {P['slope_next_on_current']:+.2f}</td></tr>
<tr><td>Gainers keeping ≥ half the gain</td><td>{round(P['gainers_pct_kept_half']*P['gainers_n']/100)} of {P['gainers_n']}</td></tr>
</table></div><div>
<div class="box"><b class="lab">READING THE BASELINE</b>Statcast measures season extension very precisely, so a change of
0.05 ft or more is real. But most pitchers move less than 0.12 ft a year, and big gains are rare. When they happen, they
do not regress the following season — which makes extension a durable, if slow, development target.</div>
</div></div>
<img class="fig" src="{FIG}/extension_change_distribution.png" style="width:72%">
<div class="cap">Distribution of year-over-year extension change in the primary sample.</div>

<div class="pb"></div>
<div class="kicker">04 | ALTERNATIVE EXPLANATIONS</div>
<h1>Does the result survive other explanations?</h1>
<div class="sub">CSW% effect per +0.3 ft under each filter or control.</div>
<table><tr><th>Sample / control</th><th>Pairs</th><th>CSW% per +0.3 ft</th><th>p</th><th>Verdict</th></tr>
{sens_rows()}</table>
<h2>Who were the big movers?</h2>
<p>Every pair that changed extension by 0.3 ft or more, before any filter, classified by the alternative explanations
the data can flag. A pair can carry more than one flag.</p>
<table><tr><th>Flag</th><th>Gained ≥ 0.3 ft (n = 20)</th><th>Lost ≥ 0.3 ft (n = 5)</th><th>What it could mean</th></tr>
<tr><td>Long absence (IL / option)</td><td>8</td><td>5</td><td>Injury or rehab changed the delivery</td></tr>
<tr><td>Arm-angle change ≥ 5°</td><td>6</td><td>2</td><td>A mechanical change moved release point</td></tr>
<tr><td>Team change</td><td>4</td><td>2</td><td>New coaching staff; different park tracking</td></tr>
<tr><td>Role change (SP / RP)</td><td>3</td><td>0</td><td>Different effort level and pitch mix</td></tr>
<tr class="hl"><td>No flagged alternative</td><td>7</td><td>0</td><td>Closest to a clean extension change</td></tr>
</table>
<div class="box"><b class="lab">WHY THIS MATTERS</b>Big extension changes rarely happen alone: 13 of 20 gains came with an absence,
a mechanical or team change, and every large loss came with an absence. That is why the main test removes absences and why
each of these explanations was tested as a control above.</div>

<h2>Injury and absence filter</h2>
<p><b>Automatic:</b> a gap of 30+ days between appearances or 21+ days missed at season end in either season removes the pair.
<b>Manual:</b> <i>data/injury_exclusions.csv</i> with public sources. Pete Fairbanks (2025→2026) was excluded for nerve irritation
and thoracic outlet syndrome surgery. League-average extension jumped about 0.08 ft in 2023 (pitch-clock year); season fixed
effects absorb it, and the result holds without that pair of seasons.</p>

<div class="pb"></div>
<div class="kicker">05 | WHERE THE GAIN COMES FROM</div>
<h1>Called strikes, not swings and misses</h1>
<div class="sub">CSW% is called strikes plus swinging strikes. Splitting it shows which part moved — and whether pitch shape explains it.
<span class="tag exp">EXPLORATORY</span></div>

<h2>Splitting CSW%</h2>
<table><tr><th>Component (per pitch)</th><th>Effect per +0.3 ft</th><th>95% CI (cluster bootstrap)</th><th>BH q</th><th>Share of CSW% gain</th></tr>
<tr class="hl"><td>CSW% (total)</td><td>{f(DEC.loc['csw_pct','effect_per_0.3ft'])} pts</td><td>{f(csw['boot_lo_0.3ft'])} to {f(csw['boot_hi_0.3ft'])}</td><td>—</td><td>100%</td></tr>
<tr><td>Called strikes</td><td><b>{f(DEC.loc['called_pct','effect_per_0.3ft'])} pts</b></td><td>{f(DEC.loc['called_pct','boot_lo_0.3ft'])} to {f(DEC.loc['called_pct','boot_hi_0.3ft'])}</td><td>{DEC.loc['called_pct','q_bh']:.3f}</td><td>{DEC.loc['called_pct','share_of_csw_effect']*100:.0f}%</td></tr>
<tr><td>Swinging strikes</td><td>{f(DEC.loc['swstr_pct','effect_per_0.3ft'])} pts</td><td>{f(DEC.loc['swstr_pct','boot_lo_0.3ft'])} to {f(DEC.loc['swstr_pct','boot_hi_0.3ft'])}</td><td>{DEC.loc['swstr_pct','q_bh']:.3f}</td><td>{DEC.loc['swstr_pct','share_of_csw_effect']*100:.0f}%</td></tr>
</table>
<p>Baseline rates: called strikes {S2['mean_called_pct']:.1f}% and swinging strikes {S2['mean_swstr_pct']:.1f}% of fastballs. In a typical season
({S2['median_fastballs_per_season']:.0f} fastballs), +0.3 ft came with about <b>{extra_strikes:.1f} more strikes</b>, roughly
{extra_strikes*called_share:.0f} of them called.</p>
<img class="fig" src="{FIG}/csw_decomposition.png" style="width:72%">
<div class="cap">Effect of +0.3 ft on each part of CSW%, velocity held constant.</div>

<h2>Controlling for pitch shape</h2>
<p>An extension change can come with a change in movement. The model was re-run adding the change in induced vertical
break, arm-side horizontal break and spin rate. Extension change was only weakly related to shape change
(r = {S2['corr_d_ext_with']['d_ivb']:+.2f} with IVB, {S2['corr_d_ext_with']['d_hb_arm']:+.2f} with horizontal break, {S2['corr_d_ext_with']['d_spin']:+.2f} with spin).</p>
<table><tr><th>Outcome (per +0.3 ft)</th><th>Velocity control only</th><th>Velocity + shape</th><th>p (with shape)</th></tr>
{shape_rows()}</table>

<div class="pb"></div>
<div class="kicker">05 | WHERE THE GAIN COMES FROM (CONTINUED)</div>
<h1>In the zone, or taken?</h1>
<div class="sub">More called strikes can mean two things: more fastballs thrown in the zone, or hitters swinging less at fastballs in the
zone. Statcast pitch location separates them. <span class="tag exp">EXPLORATORY</span></div>
<table><tr><th>Location metric (per +0.3 ft, velocity constant)</th><th>Baseline</th><th>Effect</th><th>95% CI (cluster bootstrap)</th><th>p</th><th>BH q</th></tr>
{loc_rows()}</table>
<img class="fig" src="{FIG}/location_effects.png" style="width:80%">
<div class="cap">Both command and hitter behavior moved in the direction of more called strikes; the umpire-related measure did not.</div>
<div class="box"><b class="lab">WHAT THIS MEANS</b>The strike gain did not come from better movement — it held with shape controlled —
and it did not come from umpires calling more balls strikes (out-of-zone called strikes: {f(LOC.loc['o_called_pct','effect_per_0.3ft'])}).
Pitchers who gained extension threw <b>more fastballs in the zone</b> ({f(LOC.loc['zone_pct','effect_per_0.3ft'])} pts) and hitters
<b>swung less at those zone fastballs</b> ({f(LOC.loc['z_swing_pct','effect_per_0.3ft'])} pts). Each was significant on its own
(p = {LOC.loc['zone_pct','p']:.2f} and {LOC.loc['z_swing_pct','p']:.2f}) but not after correcting for four tests (q = {LOC.loc['zone_pct','q_bh']:.2f}).
The most likely reading is that both play a part. <span class="interp">INTERPRETATION</span></div>
<div class="box navy"><b class="lab">WHY IT MATTERS FOR TRAINING</b>If part of the gain is command, a longer and more stable stride may
help a pitcher repeat his release, not just shorten the hitter's decision time. Both readings point to the same training
target: a lower half that can hold a longer stride for a full season.</div>

<div class="pb"></div>
<div class="kicker">06 | BIOMECHANICS AND TRAINING APPLICATION</div>
<h1>From finding to offseason plan</h1>
<div class="sub">Extension is where the ball leaves the hand, measured from the rubber. It is mostly stride length plus how far
the trunk travels over a firm lead leg. <span class="interp">INTERPRETATION</span></div>

<h2>What the literature supports</h2>
<ul>
<li>In professional pitchers, landing with a more open pelvis came with a longer stride, more lead-knee extension and higher
ball velocity, without more elbow varus torque (Dowling et al., 2022).</li>
<li>In elite youth pitchers, lead-knee angle at release — not stride length as a percent of height — was associated with ball
speed (van Trigt et al., 2018).</li>
<li>Changing stride length by ±25% changed lower-body joint loads and energy cost (Crotin &amp; Ramsey, 2015; Ramsey &amp; Crotin, 2022).
A longer stride has a physical cost that must be trained for.</li>
<li>Why strikes and not damage: each foot of extension adds about <b>{S['mechanism_mph_per_ft']:.1f} mph of perceived velocity</b>.
Less reaction time fits more late takes and misses; hitters who make contact still see the same pitch shape.</li>
</ul>

<h2>Training priorities</h2>
<table><tr><th style="width:20%">Priority</th><th>Why it matters for extension</th><th style="width:36%">Training emphasis</th></tr>
<tr><td>Hip mobility</td><td>A longer stride needs lead-hip internal rotation and trail-hip extension without the pelvis opening early.</td><td>90/90 progressions, loaded hip IR, half-kneeling hip-flexor work</td></tr>
<tr><td>Lead-leg block</td><td>The trunk can only travel forward over a front leg that stops and stays firm.</td><td>Split squats, single-leg RDL, isometric lunge holds, drop-to-stick landings</td></tr>
<tr><td>Adductor / groin capacity</td><td>Longer strides load the groin; capacity must come before length.</td><td>Copenhagen planks, lateral lunges, slide-board work</td></tr>
<tr><td>Lateral and rotational power</td><td>Drive down the mound sets stride length and tempo.</td><td>Lateral bounds, heidens, med-ball scoop throws from stride position</td></tr>
<tr><td>Delivery integration</td><td>Physical gains must show up in the delivery without costing command.</td><td>Stride-length targets in bullpens, increased in ~5% blocks, with velocity and strike% tracked</td></tr>
</table>

<h2>Progression</h2>
<table><tr><th style="width:16%">Phase</th><th style="width:20%">Weeks</th><th>Primary emphasis</th></tr>
<tr><td>1. Capacity</td><td>1–4</td><td>Mobility, adductor and single-leg strength; no delivery changes yet</td></tr>
<tr><td>2. Power</td><td>5–8</td><td>Lateral and rotational power; stride drills on flat ground</td></tr>
<tr><td>3. Transfer</td><td>9–12</td><td>Mound work with stride targets; extension measured each session</td></tr>
</table>

<div class="pb"></div>
<div class="kicker">07 | MEASUREMENT PLAN</div>
<h1>How improvement will be evaluated</h1>
<div class="sub">Use the same metric before, during and after the plan, against the pitcher's own baseline.</div>
<table><tr><th style="width:24%">Measure</th><th>How to evaluate</th><th style="width:34%">Threshold</th></tr>
<tr><td>Fastball extension</td><td>Statcast average by outing; rolling 5-outing mean vs prior-season baseline</td><td>Season: ±0.05 ft = real change. In season: 5-outing average −0.13 ft below own baseline = watch; −0.20 ft = alert</td></tr>
<tr><td>Fastball CSW%</td><td>Same windows, adjusted for velocity change</td><td>Expected ≈ +0.26 pts per +0.1 ft</td></tr>
<tr><td>Velocity</td><td>Track alongside to separate the two levers</td><td>No loss while extension rises</td></tr>
<tr><td>Health check</td><td>Alert-level in-season drop, or a season loss ≥ 0.3 ft</td><td>Medical review before any mechanical fix <span class="interp">INTERPRETATION</span></td></tr>
</table>

<div class="box"><b class="lab">HOW THE THRESHOLDS WERE SET</b>Across {TH['n_rolling_windows']:,} five-outing windows from healthy
pitcher-seasons, the 5-outing average stayed within ±{TH['p95_abs_5outing_dev_ft']:.2f} ft of the pitcher's own season average 95% of
the time; it fell 0.20 ft or more below only {TH['pct_below_minus_0.20']:.1f}% of the time. A season loss of 0.3 ft or more came with a
long absence in 5 of 5 pairs (base rate {TH['absence_base_rate_pct']:.0f}%); losses of 0.1–0.3 ft did not (55–58%).</div>

<h2>2027 watch list</h2>
<p class="small">No pitcher in the primary sample lost ≥ 0.3 ft from 2025 to 2026, so this post-hoc list uses losses of 0.15 ft or more
(≈ 3× the measurement threshold). It is a list for follow-up, not a test. Public injury records were checked for all ten (MLB.com, MiLB.com, RotoWire, CBS Sports).</p>
<table><tr><th>Pitcher</th><th>Team</th><th>Role</th><th>Ext 2025 → 2026 (ft)</th><th>Δ velo</th><th>Δ arm angle</th><th>Notes</th></tr>
{target_rows()}</table>

<h2>Reassessment process</h2>
<ul>
<li>Record each pitcher's prior-season extension, velocity and CSW% as the baseline before the plan starts.</li>
<li>Re-measure in spring bullpens and every regular-season outing; compare rolling means, not single outings.</li>
<li>Judge success on extension first (the trained quality), CSW% second (the expected outcome).</li>
<li>If extension rises but velocity or command drops, step back one progression block.</li>
</ul>

<div class="pb"></div>
<div class="kicker">08 | INDIVIDUAL CASE</div>
<h1>Grant Taylor, RHP, Chicago White Sox</h1>
<div class="sub">From the 2027 watch list: an elite-extension reliever who lost 0.24 ft from 2025 to 2026 and is slated to move toward a starting role.</div>

<div class="two"><div>
<table><tr><th>Fastballs</th><th>2025</th><th>2026</th><th>Change</th></tr>
<tr><td>Four-seam extension</td><td>{TC['ff_ext_25']:.2f} ft</td><td>{TC['ff_ext_26']:.2f} ft</td><td><b>{TC['ff_ext_26']-TC['ff_ext_25']:+.2f}</b></td></tr>
<tr><td>All-fastball extension</td><td>{TR['ext_y0']:.2f} ft</td><td>{TR['ext_y1']:.2f} ft</td><td>{TR['d_ext']:+.2f}</td></tr>
<tr><td>Velocity</td><td>{TR['velo_y0']:.1f}</td><td>{TR['velo_y1']:.1f}</td><td>{TR['d_velo']:+.1f}</td></tr>
<tr><td>CSW%</td><td>{TR['csw_pct_y0']:.1f}</td><td>{TR['csw_pct_y1']:.1f}</td><td>{TR['d_csw_pct']:+.1f}</td></tr>
<tr><td>Whiff% (per swing)</td><td>{TR['whiff_pct_y0']:.1f}</td><td>{TR['whiff_pct_y1']:.1f}</td><td>{TR['d_whiff_pct']:+.1f}</td></tr>
<tr><td>xwOBA allowed</td><td>{TR['xwoba_y0']:.3f}</td><td>{TR['xwoba_y1']:.3f}</td><td>{TR['d_xwoba']:+.3f}</td></tr>
<tr><td>Fastballs thrown</td><td>{int(TR['n_fb_y0'])}</td><td>{int(TR['n_fb_y1'])}</td><td>—</td></tr>
</table></div><div>
<div class="box navy"><b class="lab">CONTEXT</b>Even after the drop, his extension ranked near the top of MLB in 2026
({TC['pctl_26']:.0f}th percentile). History: Tommy John (2023), lat (2024), right groin strain on Sep 10, 2025. No 2026 IL stint found.
He worked as a multi-inning reliever in 2026 with a ~100-inning goal; the club plans a return to starting in 2027.
He also added a sinker in 2026, but the four-seam alone dropped too, so pitch mix does not explain the change.</div>
</div></div>

<img class="fig" src="{FIG}/case_taylor_extension.png" style="width:92%">
<div class="cap">Four-seam extension by outing. The drop started around the Sep 2025 groin strain and continued through the 2026 workload
(monthly average {TC['m_peak']:.2f} ft in May → {TC['m_sep']:.2f} ft in September).</div>

<div class="pb"></div>
<div class="kicker">08 | INDIVIDUAL CASE (CONTINUED)</div>
<h1>Plan for Grant Taylor</h1>
<div class="sub">Restore and hold extension through a full season, then measure whether the strikes come back.</div>
<h2>Development hypothesis <span class="interp">INTERPRETATION</span></h2>
<p>The loss looks like a <b>capacity</b> problem, not a mechanical choice: it began with a groin injury and deepened as the
workload grew. Groin and adductor capacity limit how long and how firmly a pitcher can stride. The goal is to <b>restore</b>
his 2025 extension and <b>hold it</b> through a season, not to add new length.</p>

<h2>Individual plan (12 weeks)</h2>
<table><tr><th style="width:15%">Phase</th><th>Prescription (example)</th><th style="width:28%">Physical marker</th></tr>
<tr><td>1. Capacity<br>Wk 1–4</td><td>Copenhagen plank progression 3×20–30 s/side, 3×/wk; adductor squeeze isometrics 5×5 s; split squat 3×6–8; daily lead-hip IR and trail-hip extension mobility</td><td>Groin squeeze force within 10% of the other side; lead-hip IR range back to his own baseline</td></tr>
<tr><td>2. Power<br>Wk 5–8</td><td>Lateral bounds to stick 4×5/side; single-leg RDL 3×6; med-ball scoop throws from stride position 4×5; slide-board work</td><td>Lateral jump distance and force-plate landing stability at or above baseline</td></tr>
<tr><td>3. Transfer<br>Wk 9–12</td><td>Bullpens with stride markers, +5% length blocks; extension measured every session (Rapsodo or TrackMan)</td><td>Bullpen four-seam extension ≥ 7.35 ft with velocity held</td></tr>
</table>

<h2>Targets and monitoring</h2>
<table><tr><th style="width:30%">Measure</th><th>Target</th><th style="width:36%">Expected outcome (model)</th></tr>
<tr><td>Four-seam extension (season)</td><td>≥ 7.35 ft (within measurement noise of 2025)</td><td rowspan="2">Regaining +0.2 ft came with ≈ +{csw['effect_per_0.3ft']*2/3:.1f} CSW% pts in the league model</td></tr>
<tr><td>Extension through the season</td><td>5-outing average never more than 0.13 ft below his own baseline (watch level)</td></tr>
<tr><td>Red flag</td><td colspan="2">5-outing average 0.20 ft or more below baseline (alert level, seen in 0.3% of healthy windows) → check groin and hip before any mechanical change</td></tr>
</table>
<h2>2027 season check-ins</h2>
<table><tr><th style="width:22%">When</th><th>Check</th><th style="width:34%">Decision</th></tr>
<tr><td>Spring training</td><td>Bullpen and live BP four-seam extension vs 7.35 ft target; groin squeeze test</td><td>Below target → extend Phase 3 before games</td></tr>
<tr><td>End of April</td><td>Season baseline set from first 5 outings</td><td>This becomes the in-season reference</td></tr>
<tr><td>Monthly</td><td>5-outing average vs April; CSW% and called-strike rate</td><td>Watch level (−0.13 ft) → reduce workload, add capacity work</td></tr>
<tr><td>End of season</td><td>Full-season extension and CSW% vs 2026</td><td>Judge the plan on extension first, strikes second</td></tr>
</table>
<p class="small">Caution: the league effect was clear in relievers but not significant in starters; if he moves to the rotation, the expected
CSW% gain is less certain. Injury history: RotoWire and MLB.com. Prescriptions are an example proposal, not a medical plan.</p>

<div class="pb"></div>
<div class="kicker">09 | METHOD, LIMITATIONS AND SOURCES</div>
<h1>How this was built</h1>
<h2>Project workflow</h2>
<table><tr><th style="width:16%">Step</th><th>Purpose</th><th style="width:30%">Output</th></tr>
<tr><td>1. Identify</td><td>Measure every pitcher's fastball extension, velocity and outcomes each season.</td><td>4,875 pitcher-season profiles</td></tr>
<tr><td>2. Test</td><td>Compare each pitcher to himself year over year, velocity held constant; rules fixed before the real data.</td><td>Effect sizes with 95% CIs</td></tr>
<tr><td>3. Develop</td><td>Translate the biomechanics of extension into trainable qualities.</td><td>Offseason training plan</td></tr>
<tr><td>4. Measure</td><td>Track extension outing by outing against the pitcher's own baseline.</td><td>Monitoring thresholds + watch list</td></tr>
</table>

<h2>Method</h2>
<ul>
<li><b>Data:</b> Baseball Savant pitch-level search, four-seamers and sinkers, regular season 2021–2026; minimum 300 fastballs per season.</li>
<li><b>Model:</b> within-pitcher change model with season fixed effects; errors clustered by pitcher; 2,000-resample cluster bootstrap.</li>
<li><b>Multiple testing:</b> Benjamini–Hochberg across four outcomes.</li>
<li><b>Projection test:</b> leave-one-pitcher-out cross-validation, velocity-only vs velocity + extension.</li>
<li><b>Follow-up tests (exploratory):</b> CSW% split into called and swinging strikes; pitch-shape controls (IVB, arm-side break, spin).</li>
<li><b>Known-answer test:</b> synthetic data with planted effects of +4, −4 and 0; all three recovered.</li>
</ul>
<h2>Limitations</h2>
<ul>
<li>Observational: "came with", not "caused".</li>
<li>Season averages; within-game fatigue is not modeled.</li>
<li>Pitch shape and location were tested (Section 05), but both location effects missed significance after correction; more zone pitches and fewer swings at zone pitches cannot yet be separated with confidence.</li>
<li>Height is not in Statcast; between-pitcher differences (+{S['cross_sectional_whiff_per_ft']:.1f} whiff pts per ft) partly reflect body size, which is why the decision test compares each pitcher to himself.</li>
<li>Only 12 pitchers gained ≥ 0.3 ft in the primary sample; the continuous model carries the result.</li>
</ul>
<h2>References</h2>
<p class="small">Crotin, R. L., &amp; Ramsey, D. K. (2015). Stride length: a reactive response to prolonged exertion potentially effecting ball velocity among baseball pitchers. <i>International Journal of Performance Analysis in Sport, 15</i>(1), 254–267.<br>
Dowling, B., Knapik, D. M., Luera, M. J., Garrigues, G. E., Nicholson, G. P., &amp; Verma, N. N. (2022). Influence of pelvic rotation on lower extremity kinematics, elbow varus torque, and ball velocity in professional baseball pitchers. <i>Orthopaedic Journal of Sports Medicine, 10</i>(11). doi:10.1177/23259671221130340<br>
Ramsey, D. K., &amp; Crotin, R. L. (2022). Stride length impacts on sagittal knee biomechanics in flat ground baseball pitching. <i>Applied Sciences, 12</i>(3), 995. doi:10.3390/app12030995<br>
van Trigt, B., Schallig, W., van der Graaff, E., Hoozemans, M. J. M., &amp; Veeger, D. (2018). Knee angle and stride length in association with ball speed in youth baseball pitchers. <i>Sports, 6</i>(2), 51. doi:10.3390/sports6020051<br>
MLB.com Glossary: Extension. mlb.com/glossary/statcast/extension<br>
<b>Code and data pipeline:</b> github.com/ejimenezperformance/ep-pitcher-extension · ejimenezperformance.github.io</p>

</body></html>"""

out = ROOT / "report" / "EP_Pitcher_Extension_Report.pdf"
HTML(string=html, base_url=str(ROOT)).write_pdf(out)
print(out)
