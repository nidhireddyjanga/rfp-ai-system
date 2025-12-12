import json
import csv
import os
from typing import Dict, Any, List
MARGIN_PERCENT = 12      # 12% profit margin
GST_PERCENT = 18         # 18% GST
FIXED_OVERHEAD = 500     # optional fixed charge per item

TEST_NAME_TO_CODE = {
    "Insulation Resistance Test": "IR_TEST",
    "High Voltage Test": "HV_TEST",
    "Conductor Resistance Test": "CR_TEST",
    "Flame Retardant Test": "FR_TEST",
}

def add_warning(warnings_list, wtype, item_id, detail, suggestion):
    warnings_list.append({
        "type": wtype,
        "item_id": item_id,
        "detail": detail,
        "suggestion": suggestion
    })


def load_price_table(path: str) -> dict:
    prices = {}

    if not os.path.exists(path):
        print(f"[WARNING] Pricing file not found: {path}")
        return prices

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            code = (
                row.get("code")
                or row.get("sku")
                or row.get("test_code")
                or row.get("name")
                or ""
            ).strip()

            try:
                price_val = float(row.get("unit_price", 0))
            except:
                price_val = 0.0

            if code:
                prices[code] = price_val

    return prices


TECHNICAL_RECO_PATHS = [
    "technical_reco.json",
    "data/technical_reco.json",
    "agents/technical_reco.json",
    "agents/output/technical_reco.json",
    "output/technical_reco.json",
]


def find_technical_reco() -> Dict[str, Any]:
    for p in TECHNICAL_RECO_PATHS:
        if os.path.exists(p):
            print(f"[INFO] Loaded technical reco from: {p}")
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)

    raise FileNotFoundError(
        f"technical_reco.json not found in: {TECHNICAL_RECO_PATHS}"
    )


def calculate_pricing_from_reco(
    reco: Dict[str, Any],
    product_prices: Dict[str, float],
    test_prices: Dict[str, float],
    output_dir: str = ".",
) -> Dict[str, Any]:

    all_results = {"rfps": [], "warnings": []}

    for rfp in reco.get("rfps", []):
        rfp_id = rfp.get("rfp_id")
        item_outputs = []
        warnings = []
        grand_total = 0.0

        raw_tests = rfp.get("tests", [])
        normalized_tests = []

        for t in raw_tests:
            if isinstance(t, str):
                normalized_tests.append(TEST_NAME_TO_CODE.get(t, t))
            elif isinstance(t, dict):
                tc = t.get("test_code") or t.get("name")
                normalized_tests.append(TEST_NAME_TO_CODE.get(tc, tc))

        # Processing each item
        for item in rfp.get("items", []):
            item_id = item.get("item_id")
            sku = item.get("top_sku")
            quantity = 1.0  # default

            warnings.append(
                {
                    "type": "quantity_missing",
                    "item_id": item_id,
                    "sku": sku,
                    "message": "Quantity not provided; defaulting to 1.",
                }
            )

           
            unit_material_price = product_prices.get(sku, 0.0)

            if unit_material_price == 0:
                add_warning(
                        warnings,
                        wtype="quantity_missing",
                        item_id=item_id,
                        detail=f"Quantity not found for item {item_id}, using default qty=1.",
                        suggestion="Add 'quantity' field in RFP scope or technical agent output."
                    )

            material_cost = round(unit_material_price * quantity, 2)

            
            test_breakdown = []
            test_cost = 0.0

            for tcode in normalized_tests:
                unit_test_price = test_prices.get(tcode, 0.0)

                if unit_test_price == 0:
                    warnings.append(
                        {
                            "type": "test_not_found",
                            "item_id": item_id,
                            "test_code": tcode,
                            "message": "Test missing in test_pricing.csv",
                        }
                    )

                subtotal = round(unit_test_price * 1, 2)
                test_cost += subtotal

                test_breakdown.append(
                    {
                        "test_code": tcode,
                        "unit_price": unit_test_price,
                        "quantity": 1,
                        "total": subtotal,
                    }
                )

            total_cost = round(material_cost + test_cost, 2)
            margin_amount = round(total_cost * (MARGIN_PERCENT / 100), 2)
            cost_after_margin = round(total_cost + margin_amount, 2)
            gst_amount = round(cost_after_margin * (GST_PERCENT / 100), 2)
            final_cost = round(cost_after_margin + gst_amount + FIXED_OVERHEAD, 2)

            grand_total += final_cost

            item_outputs.append(
            {
                "item_id": item_id,
                "sku": sku,
                "description": item.get("description", ""),
                "quantity": quantity,
                "unit_material_price": unit_material_price,
                "material_cost": material_cost,

                "tests": test_breakdown,
                "test_cost": test_cost,
                "base_total_cost": total_cost,
                "margin_percent": MARGIN_PERCENT,
                "margin_amount": margin_amount,
                "gst_percent": GST_PERCENT,
                "gst_amount": gst_amount,
                "fixed_overhead": FIXED_OVERHEAD,

                "final_cost": final_cost,
                "spec_match": item.get("spec_match"),
            }
        )


        # Final RFP pricing object
        pricing_output = {
            "rfp_id": rfp_id,
            "title": rfp.get("title"),
            "currency": "INR",
            "items": item_outputs,
            "grand_total": round(grand_total, 2),
            "warnings": warnings,
        }

        # Write per-RFP output file
        out_path = os.path.join(output_dir, f"pricing_output_{rfp_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(pricing_output, f, indent=2)

        all_results["rfps"].append(pricing_output)
        all_results["warnings"].extend(warnings)

    # Combined output for all RFPs
    with open("pricing_output_combined.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    return all_results


if __name__ == "__main__":
    reco = find_technical_reco()

    product_prices = load_price_table("data/product_pricing.csv")
    test_prices = load_price_table("data/test_pricing.csv")

    result = calculate_pricing_from_reco(
        reco,
        product_prices,
        test_prices,
        output_dir="."
    )

    print(json.dumps(result, indent=2))
