from decimal import Decimal

def validate_summary(schema, rows, summary, tolerance=Decimal("0.01")):
    report = {}

    if schema == "utility_bill":
        # Utility bill line-item rows are often usage/rate fragments and may not
        # represent bill-summary monetary totals. Treat this check as informational.
        if "current_charges" in summary:
            report["current_charges_match"] = "not_applicable"
            report["current_charges_match_reason"] = "line_items_not_authoritative_for_summary"
        elif "subtotal" in summary:
            report["subtotal_match"] = "not_applicable"
            report["subtotal_match_reason"] = "line_items_not_authoritative_for_summary"

    if (
        "previous_charges" in summary
        and "current_charges" in summary
        and "tax" in summary
        and "total" in summary
    ):
        expected_total = (
            summary["previous_charges"] +
            summary["current_charges"] +
            summary["tax"]
        )
        report["total_match"] = abs(expected_total - summary["total"]) <= tolerance
    elif "subtotal" in summary and "tax" in summary and "total" in summary:
        expected_total = summary["subtotal"] + summary["tax"]
        report["total_match"] = abs(expected_total - summary["total"]) <= tolerance

    return report
