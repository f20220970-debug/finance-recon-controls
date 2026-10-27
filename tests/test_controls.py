import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import controls as K  # noqa: E402
import make_data as D  # noqa: E402

FX = {"USD": 1.0, "EUR": 1.08}


def _frames():
    sub = pd.DataFrame({"trade_id": ["A", "B", "C", "D"], "desk": "Rates", "entity": "E1", "ccy": ["USD", "EUR", "USD", "USD"],
                        "amount_local": [100.0, 100.0, 50.0, 70.0], "booking_date": pd.Timestamp("2026-09-15")})
    sub["fx_rate"] = sub["ccy"].map(FX); sub["amount_usd"] = sub["amount_local"] * sub["fx_rate"]
    gl = sub.copy()
    gl = gl[gl.trade_id != "D"]                                          # missing
    gl.loc[gl.trade_id == "C", "amount_usd"] = 50.01                     # within tolerance
    gl.loc[gl.trade_id == "B", "fx_rate"] = 1.20                         # FX error
    gl = pd.concat([gl, gl[gl.trade_id == "A"]])                         # duplicate
    return sub, gl


def test_each_control_fires_and_tolerance_holds():
    sub, gl = _frames()
    ex = K.run_controls(sub, gl, FX)
    got = set(zip(ex.trade_id, ex.reason))
    assert ("D", "missing_in_gl") in got and ("A", "duplicate_in_gl") in got and ("B", "fx_rate_error") in got
    assert not any(t == "C" for t, _ in got)                             # 1-cent difference ignored


def test_full_run_detects_all_injected_breaks_without_false_alarms():
    sub, gl = D.make(n=5000)
    ev = K.evaluate(K.run_controls(sub, gl, D.CCY), gl, sub)
    assert ev["detection_rate"] > 0.98 and ev["false_alarms"] == 0
