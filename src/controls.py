"""Reconciliation and data-quality controls between the sub-ledger and the GL feed.

Controls (each produces exceptions with a reason code):
  C1 completeness   - trade in sub-ledger but missing from GL
  C2 uniqueness     - trade booked more than once in GL
  C3 accuracy       - USD amount differs beyond tolerance (0.05 USD or 0.01%, whichever is larger)
  C4 FX validation  - GL FX rate differs from the reference rate by more than 0.5%
  C5 entity         - legal entity differs between systems (or sits in suspense)
  C6 timeliness     - booked in GL after the month-end close (outside the reporting period)
Each exception is aged and sized so the largest/oldest are fixed first.
"""
import numpy as np
import pandas as pd

TOL_ABS, TOL_REL, FX_TOL = 0.05, 0.0001, 0.005
PERIOD_END = pd.Timestamp("2026-09-30")


def run_controls(sub: pd.DataFrame, gl: pd.DataFrame, ref_fx: dict) -> pd.DataFrame:
    ex = []
    dup_ids = gl["trade_id"][gl["trade_id"].duplicated()].unique()
    for t in dup_ids:
        ex.append({"trade_id": t, "control": "C2 uniqueness", "reason": "duplicate_in_gl"})
    g1 = gl.drop_duplicates("trade_id")
    m = sub.merge(g1, on="trade_id", how="left", suffixes=("_sub", "_gl"), indicator=True)
    for t in m.loc[m["_merge"] == "left_only", "trade_id"]:
        ex.append({"trade_id": t, "control": "C1 completeness", "reason": "missing_in_gl"})
    both = m[m["_merge"] == "both"].copy()
    fx_bad = (both["fx_rate_gl"] / both["ccy_gl"].map(ref_fx) - 1).abs() > FX_TOL
    tol = np.maximum(TOL_ABS, TOL_REL * both["amount_usd_sub"].abs())
    amt_bad = (both["amount_usd_gl"] - both["amount_usd_sub"]).abs() > tol
    for t in both.loc[fx_bad, "trade_id"]:
        ex.append({"trade_id": t, "control": "C4 FX validation", "reason": "fx_rate_error"})
    for t in both.loc[amt_bad & ~fx_bad, "trade_id"]:
        ex.append({"trade_id": t, "control": "C3 accuracy", "reason": "amount_mismatch"})
    for t in both.loc[both["entity_gl"] != both["entity_sub"], "trade_id"]:
        ex.append({"trade_id": t, "control": "C5 entity", "reason": "wrong_entity"})
    for t in both.loc[both["booking_date_gl"] > PERIOD_END, "trade_id"]:
        ex.append({"trade_id": t, "control": "C6 timeliness", "reason": "stale_booking"})
    out = pd.DataFrame(ex)
    if out.empty:
        return out
    size = sub.set_index("trade_id")["amount_usd"].abs()
    out["exposure_usd"] = out["trade_id"].map(size).fillna(0)
    out["age_days"] = (PERIOD_END - out["trade_id"].map(sub.set_index("trade_id")["booking_date"])).dt.days
    out["priority"] = np.where(out["exposure_usd"] > 1e6, "P1", np.where(out["exposure_usd"] > 1e5, "P2", "P3"))
    return out


def evaluate(exceptions: pd.DataFrame, gl: pd.DataFrame, sub: pd.DataFrame) -> dict:
    """Compare raised exceptions with the injected truth: detection rate and false alarms."""
    truth = gl.loc[gl["break_truth"] != "none", ["trade_id", "break_truth"]].drop_duplicates()
    missing = set(sub["trade_id"]) - set(gl["trade_id"])
    truth = pd.concat([truth, pd.DataFrame({"trade_id": list(missing), "break_truth": "missing_in_gl"})]).drop_duplicates()
    raised = set(zip(exceptions["trade_id"], exceptions["reason"]))
    true_pairs = set(zip(truth["trade_id"], truth["break_truth"]))
    detected = len(raised & true_pairs)
    false_alarms = len(raised - true_pairs)
    return {"injected_breaks": len(true_pairs), "detected": detected, "detection_rate": detected / len(true_pairs),
            "false_alarms": false_alarms, "exceptions_raised": len(raised)}
