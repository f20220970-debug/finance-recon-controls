# Results summary

- Reconciled 20,000 sub-ledger trades against 19,890 GL lines across 4 entities and 5 desks.
- 939 breaks were injected; the 6 controls detected 939 (100.0%) with 0 false alarms, while 582 one-cent rounding differences were correctly ignored by the tolerance rule.
- Exceptions by control: C1 completeness 212, C2 uniqueness 102, C3 accuracy 244, C4 FX validation 124, C5 entity 108, C6 timeliness 149.
- Net GL vs sub-ledger difference before fixes: USD -6,757,675. Prioritising by size: 316 P1/P2 exceptions (34% of the count) hold 85% of exception exposure.
