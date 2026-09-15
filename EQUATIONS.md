# SAMCO CTO Hub — Controlled Equations

These formulas represent the deterministic corporate calculation layer. Machine-learning outputs may propose or forecast values, but they do not replace these formulas without an approved rule change.

## 1. Productivity / duration

```text
Duration (working days)
= Quantity ÷ (Daily Productivity × Number of Crews)
```

```text
Crew Hours per Unit
= Crew Hours per Day ÷ Daily Production
```

```text
Equipment Hours per Unit
= (Number of Machines × Working Hours per Day) ÷ Daily Production
```

## 2. Material allowance

```text
Material Cost / Unit
= Material Unit Price × (1 + Wastage %)
```

## 3. Direct unit rate

```text
Direct Unit Rate
= Material Cost / Unit
+ Labor Cost / Unit
+ Equipment Cost / Unit
+ Subcontractor Rate / Unit
```

## 4. BOQ amount

```text
Amount
= Quantity × Direct Unit Rate
```

## 5. Concrete mix cost

For each concrete grade:

```text
Cement Cost / m3
= Cement kg/m3 ÷ 1000 × Cement EGP/ton

Sand Cost / m3
= Sand m3/m3 × Sand EGP/m3

Gravel Cost / m3
= Gravel m3/m3 × Gravel EGP/m3

Concrete Total Cost / m3
= Cement Cost
+ Sand Cost
+ Gravel Cost
+ Admixture Allowance
+ Batching / Mixing / Pumping Allowance
```

The workbook states that mix ratios are planning values and must be confirmed against approved project trial mixes.

## 6. Equipment ownership-rate model

```text
Depreciation / Month
= (Purchase Cost - Salvage Cost) ÷ Depreciation Life Cycle

Depreciation / Day
= Depreciation / Month ÷ Working Days per Month

Depreciation / Hour
= Depreciation / Day ÷ Working Hours per Day
```

Fuel, operator, oil/lubricants, maintenance and tyre costs are added to calculate machine cost per hour.

## 7. Tender commercial build-up

```text
Site Overhead Amount
= Direct Cost × Site Overhead %

Head Office Overhead Amount
= Direct Cost × Head Office Overhead %

Subtotal after Overheads
= Direct Cost + Site Overhead + Head Office Overhead

Contingency Amount
= Subtotal after Overheads × Risk Contingency %

Escalation Amount
= applicable cost base × Price Escalation %

Subtotal before Profit
= Subtotal after Overheads + Contingency + Escalation

Profit Amount
= Subtotal before Profit × Profit Margin %

Net Bid Price before Bonds / Insurance / VAT
= Subtotal before Profit + Profit

Bonds & Insurance Amount
= Net Bid Price × Bonds/Insurance %

Financing Cost
= applicable cost base × Financing Cost %

Price before VAT
= Net Bid Price + Bonds/Insurance + Financing

VAT Amount
= Price before VAT × VAT %

Grand Total Bid Price
= Price before VAT + VAT
```

## 8. Example default assumptions present in the supplied pricing workbook

These are imported dynamically and remain editable by Admin; they are not hardcoded into application code.

- Site overhead: 10%
- Head-office overhead: 6%
- Risk contingency matrix: Low 3%, Medium 6%, High 10%, Very High 15%
- Annual escalation assumption: 15%
- VAT: 14%
- Financing cost allowance: approximately 3.6164%

The app must read the current generated JSON value rather than rely on this documentation text.
