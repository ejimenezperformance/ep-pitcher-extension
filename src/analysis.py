"""Does gaining fastball extension come with better fastball outcomes,
beyond what the velocity change explains?

Input : data/processed/pairs.csv, data/processed/pitcher_seasons.csv
Output: results/*.csv, results/summary.json

Criteria fixed BEFORE running on real data (see README "Pre-registered criteria"):
  CONFIRMED = Benjamini-Hochberg q < 0.05 across the 4 outcomes
              AND the effect of +0.3 ft reaches the practical threshold below.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
PROC, RES = ROOT / "data" / "processed", ROOT / "results"
RES.mkdir(exist_ok=True)

UNIT_FT = 0.3  # practical unit: a +0.3 ft change in average fastball extension
OUTCOMES = {  # outcome: (practical threshold per +0.3 ft, direction that is "better")
    "whiff_pct": (0.75, +1),   # percentage points of whiffs per swing
    "csw_pct": (0.50, +1),     # called + swinging strikes per pitch, points
    "rv100": (0.20, +1),       # run value per 100 fastballs, pitcher perspective
    "xwoba": (0.005, -1),      # expected wOBA allowed on fastballs
}
GAIN, STABLE = 0.3, 0.1
SEED = 2026
N_BOOT = 2000


# ---------------------------------------------------------------- models
def fit_delta_model(df: pd.DataFrame, outcome: str, extra: str = ""):
    """Within-pitcher model: change in outcome ~ change in velo + change in extension
    + baseline level (regression to the mean) + season-pair fixed effects.
    Standard errors clustered by pitcher (pitchers appear in several pairs)."""
    f = f"d_{outcome} ~ d_velo + d_ext + {outcome}_y0 + C(pair){extra}"
    fe = "C(pair)" if df["pair"].nunique() > 1 else None
    if fe is None:
        f = f.replace(" + C(pair)", "")
    return smf.ols(f, data=df).fit(cov_type="cluster",
                                   cov_kwds={"groups": df["pitcher"].astype(int)})


def effect_row(model, outcome: str, label: str, n: int) -> dict:
    b, se = model.params["d_ext"], model.bse["d_ext"]
    lo, hi = model.conf_int().loc["d_ext"]
    thr, sign = OUTCOMES[outcome]
    eff = b * UNIT_FT
    return {"sample": label, "outcome": outcome, "n_pairs": n,
            "coef_per_ft": b, "se": se, "p": model.pvalues["d_ext"],
            "effect_per_0.3ft": eff, "ci_lo_0.3ft": lo * UNIT_FT, "ci_hi_0.3ft": hi * UNIT_FT,
            "practical_threshold": thr * sign,
            "meets_practical": bool(sign * eff >= thr),
            "velo_coef_per_mph": model.params["d_velo"]}


def cluster_bootstrap_coef(df, outcome, n_boot=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    ids = df["pitcher"].unique()
    groups = {i: g for i, g in df.groupby("pitcher")}
    out = []
    for _ in range(n_boot):
        s = pd.concat([groups[i] for i in rng.choice(ids, len(ids))], ignore_index=True)
        try:
            out.append(smf.ols(f"d_{outcome} ~ d_velo + d_ext + {outcome}_y0 + C(pair)",
                               data=s).fit().params["d_ext"])
        except Exception:
            continue
    return np.percentile(out, [2.5, 97.5]) * UNIT_FT


def loo_projection(df, outcome="whiff_pct", n_boot=N_BOOT, seed=SEED):
    """Leave-one-pitcher-out: does adding d_ext improve out-of-sample prediction
    of the outcome change over a velocity-only model?"""
    base = f"d_{outcome} ~ d_velo + {outcome}_y0 + C(pair)"
    full = base + " + d_ext"
    err_b, err_f, pid = [], [], []
    for p, test in df.groupby("pitcher"):
        train = df[df["pitcher"] != p]
        test = test[test["pair"].isin(train["pair"].unique())]
        if test.empty:
            continue
        for f, store in ((base, err_b), (full, err_f)):
            pred = smf.ols(f, data=train).fit().predict(test)
            store.extend(np.abs(test[f"d_{outcome}"] - pred))
        pid.extend([p] * len(test))
    e = pd.DataFrame({"pitcher": pid, "base": err_b, "full": err_f})
    diff = (e["base"] - e["full"])  # > 0 means extension helps
    rng = np.random.default_rng(seed)
    ids = e["pitcher"].unique()
    per = e.assign(d=diff).groupby("pitcher")["d"].agg(["sum", "count"])
    boots = []
    for _ in range(n_boot):
        s = per.loc[rng.choice(ids, len(ids))]
        boots.append(s["sum"].sum() / s["count"].sum())
    return {"outcome": outcome, "mae_velo_only": e["base"].mean(),
            "mae_velo_plus_ext": e["full"].mean(), "mae_improvement": diff.mean(),
            "ci_lo": float(np.percentile(boots, 2.5)), "ci_hi": float(np.percentile(boots, 97.5)),
            "n": len(e)}


def cohens_d(a, b):
    a, b = np.asarray(a), np.asarray(b)
    s = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    return (a.mean() - b.mean()) / s


# ---------------------------------------------------------------- pipeline
def run(pairs: pd.DataFrame, seasons: pd.DataFrame) -> dict:
    summary = {}
    primary = pairs[~pairs["flag_absence"] & ~pairs["manual_exclude"]].dropna(
        subset=["d_ext", "d_velo", "d_whiff_pct", "d_xwoba"]).copy()
    summary["n_pairs_all"] = int(len(pairs))
    summary["n_pairs_primary"] = int(len(primary))
    summary["n_pitchers_primary"] = int(primary["pitcher"].nunique())

    # 1) natural baseline: measurement noise, year-to-year spread, persistence
    q = seasons[seasons["n_fb"] >= 300].dropna(subset=["ext_odd", "ext_even"])
    r_half = np.corrcoef(q["ext_odd"], q["ext_even"])[0, 1]
    se_season = (q["ext_odd"] - q["ext_even"]).std() / 2
    summary["baseline"] = {
        "split_half_r": r_half,
        "se_season_mean_ft": se_season,
        "mdc95_change_ft": 1.96 * np.sqrt(2) * se_season,
        "sd_delta_ext_ft": primary["d_ext"].std(),
        "pct_pairs_gain_ge_0.3": 100 * (primary["d_ext"] >= GAIN).mean(),
        "pct_pairs_loss_ge_0.3": 100 * (primary["d_ext"] <= -GAIN).mean(),
        "corr_d_ext_d_velo": primary[["d_ext", "d_velo"]].corr().iloc[0, 1],
    }
    nxt = primary.merge(
        pairs[["pitcher", "year_y0", "d_ext"]].rename(columns={"year_y0": "year_y1", "d_ext": "d_ext_next"}),
        on=["pitcher", "year_y1"])
    gainers, losers = nxt[nxt["d_ext"] >= GAIN], nxt[nxt["d_ext"] <= -GAIN]
    summary["baseline"]["persistence"] = {
        "slope_next_on_current": smf.ols("d_ext_next ~ d_ext", data=nxt).fit().params["d_ext"],
        "gainers_n": int(len(gainers)),
        "gainers_mean_gain": gainers["d_ext"].mean(),
        "gainers_mean_next_change": gainers["d_ext_next"].mean(),
        "gainers_pct_kept_half": 100 * ((gainers["d_ext"] + gainers["d_ext_next"]) >= gainers["d_ext"] / 2).mean(),
        "losers_n": int(len(losers)),
        "losers_mean_loss": losers["d_ext"].mean(),
        "losers_mean_next_change": losers["d_ext_next"].mean(),
        "losers_pct_recovered_half": 100 * (losers["d_ext_next"] >= -losers["d_ext"] / 2).mean(),
    }

    # 2) mechanism check (definitional): extension -> perceived velocity gain
    m = smf.ols("d_perceived_gain ~ d_ext", data=primary).fit()
    summary["mechanism_mph_per_ft"] = m.params["d_ext"]
    summary["mechanism_r2"] = m.rsquared

    # 3) main within-pitcher test, 4 outcomes, BH correction
    rows = [effect_row(fit_delta_model(primary, o), o, "primary", len(primary)) for o in OUTCOMES]
    main = pd.DataFrame(rows)
    main["q_bh"] = multipletests(main["p"], method="fdr_bh")[1]
    for o in OUTCOMES:
        lo, hi = cluster_bootstrap_coef(primary, o)
        main.loc[main["outcome"] == o, ["boot_lo_0.3ft", "boot_hi_0.3ft"]] = lo, hi
    main["label"] = np.where((main["q_bh"] < 0.05) & main["meets_practical"], "CONFIRMED",
                    np.where(main["q_bh"] < 0.05, "SIGNIFICANT, BELOW PRACTICAL THRESHOLD",
                             "NOT CONFIRMED"))
    main.to_csv(RES / "main_effects.csv", index=False)
    summary["main"] = main.to_dict(orient="records")

    # 4) sensitivity / alternative explanations
    sens_samples = {
        "all_pairs (no absence filter)": pairs.dropna(subset=["d_ext", "d_xwoba"]),
        "primary minus role changes": primary[~primary["flag_role_change"]],
        "primary minus team changes": primary[~primary["flag_team_change"]],
        "primary minus arm-angle change >=5 deg": primary[~primary["flag_arm_angle"]],
        "starters only": primary[(primary["role_y0"] == "SP") & (primary["role_y1"] == "SP")],
        "relievers only": primary[(primary["role_y0"] == "RP") & (primary["role_y1"] == "RP")],
        "primary minus 2022->2023 (league-wide shift)": primary[primary["pair"] != "2022->2023"],
    }
    sens = []
    for lab, s in sens_samples.items():
        for o in ["whiff_pct", "csw_pct", "xwoba"]:
            sens.append(effect_row(fit_delta_model(s, o), o, lab, len(s)))
    for o in ["whiff_pct", "csw_pct", "xwoba"]:
        mm = fit_delta_model(primary.dropna(subset=["d_arm_angle"]), o, " + d_arm_angle")
        sens.append(effect_row(mm, o, "primary + arm-angle control", int(mm.nobs)))
    pd.DataFrame(sens).to_csv(RES / "sensitivity.csv", index=False)

    # 5) out-of-sample projection test
    proj = [loo_projection(primary, o) for o in ["whiff_pct", "xwoba"]]
    pd.DataFrame(proj).to_csv(RES / "loo_projection.csv", index=False)
    summary["loo"] = proj

    # 6) groups: gainers / stable / losers on residualised whiff change
    res_model = smf.ols("d_whiff_pct ~ d_velo + whiff_pct_y0 + C(pair)", data=primary).fit()
    primary["resid_whiff"] = res_model.resid
    res_x = smf.ols("d_xwoba ~ d_velo + xwoba_y0 + C(pair)", data=primary).fit()
    primary["resid_xwoba"] = res_x.resid
    res_c = smf.ols("d_csw_pct ~ d_velo + csw_pct_y0 + C(pair)", data=primary).fit()
    primary["resid_csw"] = res_c.resid
    primary["group"] = np.select([primary["d_ext"] >= GAIN, primary["d_ext"] <= -GAIN,
                                  primary["d_ext"].abs() < STABLE],
                                 ["gained >=0.3 ft", "lost >=0.3 ft", "stable (<0.1 ft)"], "other")
    grp = []
    st = primary[primary["group"] == "stable (<0.1 ft)"]
    for g in ["gained >=0.3 ft", "lost >=0.3 ft"]:
        x = primary[primary["group"] == g]
        for col in ["resid_whiff", "resid_csw", "resid_xwoba"]:
            u = stats.mannwhitneyu(x[col], st[col])
            grp.append({"group": g, "metric": col, "n": len(x), "n_stable": len(st),
                        "mean_group": x[col].mean(), "mean_stable": st[col].mean(),
                        "cohens_d": cohens_d(x[col], st[col]), "mw_p": u.pvalue})
    grp = pd.DataFrame(grp)
    grp["q_bh"] = multipletests(grp["mw_p"], method="fdr_bh")[1]
    grp.to_csv(RES / "group_comparison.csv", index=False)
    summary["groups"] = grp.to_dict(orient="records")

    bins = pd.cut(primary["d_ext"], [-9, -0.3, -0.1, 0.1, 0.3, 9],
                  labels=["<= -0.3", "-0.3 to -0.1", "-0.1 to 0.1", "0.1 to 0.3", ">= 0.3"]).rename("bin")
    dose = primary.groupby(bins, observed=True).agg(
        n=("d_ext", "size"), d_ext=("d_ext", "mean"), d_velo=("d_velo", "mean"),
        raw_d_whiff=("d_whiff_pct", "mean"), resid_whiff=("resid_whiff", "mean"),
        resid_whiff_se=("resid_whiff", lambda s: s.std() / np.sqrt(len(s))),
        resid_xwoba=("resid_xwoba", "mean"), raw_d_csw=("d_csw_pct", "mean"),
        resid_csw=("resid_csw", "mean"),
        resid_csw_se=("resid_csw", lambda s: s.std() / np.sqrt(len(s)))).reset_index().rename(columns={"d_ext": "mean_d_ext"})
    dose.to_csv(RES / "dose_response.csv", index=False)

    # 7) between-pitcher (cross-sectional) association, for context only
    qs = seasons[seasons["n_fb"] >= 300]
    cs = smf.ols("whiff_pct ~ velo + ext + C(year)", data=qs).fit(
        cov_type="cluster", cov_kwds={"groups": qs["pitcher"].astype(int)})
    summary["cross_sectional_whiff_per_ft"] = cs.params["ext"]
    summary["cross_sectional_p"] = cs.pvalues["ext"]

    # 8) case table: biggest movers, with alternative explanations
    cols = ["name_y0", "pair", "role_y0", "role_y1", "team_y0", "team_y1", "ext_y0", "ext_y1",
            "d_ext", "d_velo", "d_arm_angle", "d_whiff_pct", "d_xwoba", "flag_absence",
            "flag_role_change", "flag_team_change", "flag_arm_angle", "manual_note"]
    movers = pd.concat([pairs.nlargest(15, "d_ext"), pairs.nsmallest(15, "d_ext")])[cols].copy()

    def why(r):
        tags = []
        if r.flag_absence: tags.append("absence/IL gap")
        if r.flag_role_change: tags.append(f"role {r.role_y0}->{r.role_y1}")
        if r.flag_team_change: tags.append(f"team {r.team_y0}->{r.team_y1}")
        if r.flag_arm_angle: tags.append(f"arm angle {r.d_arm_angle:+.1f} deg")
        if isinstance(r.manual_note, str) and r.manual_note: tags.append(r.manual_note)
        return "; ".join(tags) or "no flagged alternative"
    movers["alternative_explanations"] = movers.apply(why, axis=1)
    movers.to_csv(RES / "case_table.csv", index=False)

    # big losses and absences: how many >=0.3 ft losses came with an absence flag?
    big_loss = pairs[pairs["d_ext"] <= -GAIN]
    summary["big_losses_all"] = int(len(big_loss))
    summary["big_losses_with_absence"] = int(big_loss["flag_absence"].sum())
    summary["absence_rate_all_pairs"] = float(pairs["flag_absence"].mean())

    # 9) application (POST-HOC watch list, not a test): 2025->2026 losses beyond
    #    ~3x the measurement MDC (0.15 ft). No primary pair lost >= 0.3 ft.
    last = primary[primary["year_y1"] == primary["year_y1"].max()]
    targets = last[last["d_ext"] <= -0.15].sort_values("d_ext")[
        ["name_y0", "team_y1", "role_y1", "ext_y0", "ext_y1", "d_ext", "velo_y1", "d_velo",
         "d_arm_angle", "whiff_pct_y1", "d_whiff_pct", "xwoba_y1", "d_xwoba",
         "flag_role_change", "flag_team_change", "flag_arm_angle"]]
    targets.to_csv(RES / "offseason_targets_2027.csv", index=False)
    summary["n_targets_2027"] = int(len(targets))
    summary["recovery_rate_losers"] = summary["baseline"]["persistence"]["losers_pct_recovered_half"]

    primary.to_csv(PROC / "primary_sample.csv", index=False)
    (RES / "summary.json").write_text(json.dumps(summary, indent=2, default=float), encoding="utf-8")
    return summary


if __name__ == "__main__":
    s = run(pd.read_csv(PROC / "pairs.csv"), pd.read_csv(PROC / "pitcher_seasons.csv"))
    print(json.dumps({k: s[k] for k in ["n_pairs_primary", "mechanism_mph_per_ft"]}, indent=2, default=float))
    print(pd.read_csv(RES / "main_effects.csv")[["outcome", "effect_per_0.3ft", "ci_lo_0.3ft",
                                                  "ci_hi_0.3ft", "p", "q_bh", "label"]])
