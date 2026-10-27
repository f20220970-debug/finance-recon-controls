# Finance Data Controls and Reconciliation Engine

A month-end reconciliation between a trading **sub-ledger** and the **general ledger (GL)** feed for a fictional
bank (5 desks, 4 legal entities, 5 currencies), with six automated data-quality controls, exception ageing and
prioritisation, and SQL for investigation. Known breaks are injected into synthetic data with a label, so the
controls can be **tested against the truth**, the way a control is validated before it is relied on.

## Key results
- Reconciled 20,000 sub-ledger trades against 19,890 GL lines.
- 939 breaks were injected; the six controls caught all 939 with 0 false alarms, while 582 one-cent rounding
  differences were correctly ignored by the tolerance rule.
- Exceptions by control: completeness 212, uniqueness 102, accuracy 244, FX validation 124, entity 108, timeliness 149.
- Net GL vs sub-ledger difference before fixes: USD −6.76m. Prioritising by size, 316 P1/P2 exceptions (34% of the
  count) hold 85% of the exception exposure, so the team can clear most of the value at risk first.

## The controls
| Control | Checks | Exception |
| --- | --- | --- |
| C1 completeness | every sub-ledger trade reaches the GL | missing_in_gl |
| C2 uniqueness | no trade is booked twice | duplicate_in_gl |
| C3 accuracy | USD amounts agree within max(USD 0.05, 0.01%) | amount_mismatch |
| C4 FX validation | GL FX rate within 0.5% of the reference rate | fx_rate_error |
| C5 entity | same legal entity in both systems (none in suspense) | wrong_entity |
| C6 timeliness | booked inside the reporting period | stale_booking |

Each exception gets its USD exposure, age and a priority (P1 over USD 1m, P2 over USD 100k, P3 otherwise).
`sql/exception_queries.sql` lists the P1 queue and the desk-entity pairs that create the most breaks.

## Limits
Synthetic data with known break types makes the controls easy to verify; real feeds have messier, unlabelled
breaks, many-to-many matches and timing differences, so a real build would add fuzzy matching, break ageing SLAs
and a root-cause log.

## Run it
```bash
pip install -r requirements.txt
pytest -q          # each control fires on a hand-made case; the tolerance rule ignores 1-cent noise
python run.py      # results/ and data/recon.duckdb
```
