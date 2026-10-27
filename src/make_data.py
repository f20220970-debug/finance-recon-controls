"""Synthetic month-end data for a bank's finance reporting: a sub-ledger of trades/positions and the
general ledger (GL) feed that should agree with it. Known breaks are injected on purpose, with a
label, so the controls can be tested against the truth. Everything is fictional."""
import numpy as np
import pandas as pd

SEED = 42
DESKS = ["Rates", "Credit", "FX", "Equities", "Treasury"]
ENTITIES = ["UBS AG London", "UBS AG Zurich", "UBS Europe SE", "UBS India"]
CCY = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "CHF": 1.12, "INR": 0.012}
BREAKS = {"missing_in_gl": 0.010, "amount_mismatch": 0.012, "fx_rate_error": 0.006, "duplicate_in_gl": 0.005,
          "wrong_entity": 0.006, "stale_booking": 0.008}


def make(n=20000, seed=SEED):
    rng = np.random.default_rng(seed)
    sub = pd.DataFrame({
        "trade_id": [f"T{100000 + i}" for i in range(n)],
        "desk": rng.choice(DESKS, n), "entity": rng.choice(ENTITIES, n, p=[.35, .3, .25, .1]),
        "ccy": rng.choice(list(CCY), n, p=[.45, .2, .12, .13, .10]),
        "amount_local": np.round(rng.lognormal(11, 1.3, n) * rng.choice([1, -1], n, p=[.6, .4]), 2),
        "booking_date": pd.Timestamp("2026-09-30") - pd.to_timedelta(rng.integers(0, 30, n), unit="D"),
    })
    sub["fx_rate"] = sub["ccy"].map(CCY)
    sub["amount_usd"] = (sub["amount_local"] * sub["fx_rate"]).round(2)
    gl = sub[["trade_id", "desk", "entity", "ccy", "amount_local", "fx_rate", "amount_usd", "booking_date"]].copy()
    gl["break_truth"] = "none"
    r = rng.random(n); edges = np.cumsum(list(BREAKS.values()))
    kind = np.select([r < edges[0]] + [(r >= a) & (r < b) for a, b in zip(edges[:-1], edges[1:])], list(BREAKS), "none")
    gl["break_truth"] = kind
    m = kind == "amount_mismatch"; gl.loc[m, "amount_usd"] = (gl.loc[m, "amount_usd"] * rng.uniform(1.02, 1.3, m.sum())).round(2)
    m = kind == "fx_rate_error"; gl.loc[m, "fx_rate"] = gl.loc[m, "fx_rate"] * 1.05; gl.loc[m, "amount_usd"] = (gl.loc[m, "amount_local"] * gl.loc[m, "fx_rate"]).round(2)
    m = kind == "wrong_entity"; gl.loc[m, "entity"] = rng.choice(ENTITIES, m.sum())
    gl.loc[m & (gl["entity"] == sub["entity"]), "entity"] = "UBS Suspense"
    m = kind == "stale_booking"; gl.loc[m, "booking_date"] = gl.loc[m, "booking_date"] + pd.Timedelta(days=35)
    dups = gl[kind == "duplicate_in_gl"].copy()
    gl = pd.concat([gl[kind != "missing_in_gl"], dups], ignore_index=True)
    # tiny rounding noise on some clean rows: should NOT be raised as breaks (tolerance check)
    noise = (gl["break_truth"] == "none") & (rng.random(len(gl)) < 0.03)
    gl.loc[noise, "amount_usd"] = gl.loc[noise, "amount_usd"] + rng.choice([-0.01, 0.01], noise.sum())
    return sub, gl
