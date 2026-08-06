"""
Developer Strategy (Long-Term Picks) - fully rule-based, no ML involved.

Qualification rules:
  1. Promoter Holding > 60%
  2. FII Holding > 1.5%
  3. Retail Holding:
       Case 1: current quarter retail holding <= 30%  -> ACCEPT (ignore history)
       Case 2: current quarter retail holding  > 30%  -> check previous 3 quarters;
               accept only if ALL 3 previous quarters were < 30%, else REJECT
  4. DII holding has no restriction (informational only)
"""


def evaluate_long_term_pick(ownership: dict) -> dict:
    reasons = []
    qualified = True

    promoter = ownership["promoter_holding"]
    fii = ownership["fii_holding"]
    dii = ownership["dii_holding"]
    retail = ownership["retail_holding"]
    q1, q2, q3 = ownership["retail_q1"], ownership["retail_q2"], ownership["retail_q3"]

    # Rule 1: Promoter holding
    if promoter > 60:
        reasons.append(f"Promoter holding {promoter:.1f}% > 60% (pass)")
    else:
        qualified = False
        reasons.append(f"Promoter holding {promoter:.1f}% <= 60% (fail)")

    # Rule 2: FII holding
    if fii > 1.5:
        reasons.append(f"FII holding {fii:.2f}% > 1.5% (pass)")
    else:
        qualified = False
        reasons.append(f"FII holding {fii:.2f}% <= 1.5% (fail)")

    # Rule 3: Retail holding case logic
    if retail <= 30:
        reasons.append(f"Retail holding {retail:.1f}% <= 30% - accepted immediately, prior quarters ignored (pass)")
    else:
        prev_quarters = [q1, q2, q3]
        if all(q < 30 for q in prev_quarters):
            reasons.append(
                f"Retail holding {retail:.1f}% > 30%, but all previous 3 quarters "
                f"({q1:.1f}%, {q2:.1f}%, {q3:.1f}%) were below 30% (pass)"
            )
        else:
            qualified = False
            reasons.append(
                f"Retail holding {retail:.1f}% > 30%, and not all previous 3 quarters "
                f"({q1:.1f}%, {q2:.1f}%, {q3:.1f}%) were below 30% (fail)"
            )

    # DII - informational only
    reasons.append(f"DII holding {dii:.1f}% (no restriction, informational)")

    trend = "Improving" if retail < q1 else ("Stable" if abs(retail - q1) < 1 else "Weakening")

    return {
        "symbol": ownership["symbol"],
        "qualified": qualified,
        "promoter_holding": promoter,
        "fii_holding": fii,
        "dii_holding": dii,
        "retail_holding": retail,
        "retail_q1": q1,
        "retail_q2": q2,
        "retail_q3": q3,
        "ownership_trend": trend,
        "reason": " | ".join(reasons),
    }


def evaluate_all(ownership_rows: list) -> list:
    return [evaluate_long_term_pick(row) for row in ownership_rows]
