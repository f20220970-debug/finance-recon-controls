"""Month-end reconciliation run: generate data, run controls, measure them against the truth,
write exception reports and a summary, and load everything into DuckDB for SQL."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

import controls as K  # noqa: E402
import make_data as D  # noqa: E402


def main():
    sub, gl = D.make()
    ex = K.run_controls(sub, gl, D.CCY)
    ev = K.evaluate(ex, gl, sub)
    (ROOT / "results").mkdir(exist_ok=True); (ROOT / "data").mkdir(exist_ok=True)
    by_ctrl = ex.groupby("control").agg(exceptions=("trade_id", "size"), exposure_usd=("exposure_usd", "sum")).reset_index()
    by_desk = (ex.merge(sub[["trade_id", "desk", "entity"]], on="trade_id")
                 .groupby(["desk", "control"]).size().unstack(fill_value=0))
    ex.to_csv(ROOT / "results/exceptions.csv", index=False)
    by_ctrl.round(0).to_csv(ROOT / "results/exceptions_by_control.csv", index=False)
    by_desk.to_csv(ROOT / "results/exceptions_by_desk.csv")
    con = duckdb.connect(str(ROOT / "data/recon.duckdb"))
    for name, df in {"subledger": sub, "gl": gl, "exceptions": ex}.items():
        df = df.copy()
        for c in df.columns:
            if df[c].dtype.kind not in "biufM":
                df[c] = df[c].astype(object)          # plain Python strings for DuckDB
        con.register("tmp_df", df)
        con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM tmp_df")
        con.unregister("tmp_df")
    total_gl = gl.drop_duplicates("trade_id")["amount_usd"].sum(); total_sub = sub["amount_usd"].sum()
    p1 = ex[ex["priority"] == "P1"]; p12 = ex[ex["priority"].isin(["P1", "P2"])]
    clean = gl[gl["break_truth"] == "none"].drop_duplicates("trade_id").merge(sub[["trade_id", "amount_usd"]], on="trade_id", suffixes=("", "_sub"))
    rounding = int(((clean["amount_usd"] - clean["amount_usd_sub"]).abs() > 0).sum())
    lines = ["# Results summary", "",
             f"- Reconciled {len(sub):,} sub-ledger trades against {len(gl):,} GL lines across {sub['entity'].nunique()} entities and {sub['desk'].nunique()} desks.",
             f"- {ev['injected_breaks']:,} breaks were injected; the 6 controls detected {ev['detected']:,} ({100 * ev['detection_rate']:.1f}%) "
             f"with {ev['false_alarms']} false alarms, while {rounding:,} one-cent rounding differences were correctly ignored by the tolerance rule.",
             "- Exceptions by control: " + ", ".join(f"{r.control} {r.exceptions}" for r in by_ctrl.itertuples()) + ".",
             f"- Net GL vs sub-ledger difference before fixes: USD {total_gl - total_sub:,.0f}. Prioritising by size: {len(p12)} P1/P2 exceptions "
             f"({100 * len(p12) / len(ex):.0f}% of the count) hold {100 * p12['exposure_usd'].sum() / ex['exposure_usd'].sum():.0f}% of exception exposure.",
             ]
    (ROOT / "results/summary.md").write_text("\n".join(lines) + "\n"); print("\n".join(lines))


if __name__ == "__main__":
    main()
