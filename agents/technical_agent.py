import json
import csv
import os
from dataclasses import dataclass, asdict
from typing import Dict, List, Any


RFP_DIR = os.getenv("RFP_DIR", r"C:\\Users\\tanma\\Downloads\\RFPs")
DATA_DIR = os.getenv("DATA_DIR", r"C:\\Users\\tanma\\Downloads\\Data")
OUTPUT_PATH = os.getenv("TECHNICAL_RECO_PATH", r"C:\\Users\\tanma\\Downloads\\technical_reco.json")


@dataclass
class Product:
    sku: str
    name: str
    voltage: str
    conductor: str
    insulation_thickness_mm: float
    std: str


def load_products(data_dir: str) -> List[Product]:
    products: List[Product] = []
    products_path = os.path.join(data_dir, "products.csv")
    with open(products_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append(
                Product(
                    sku=row["sku"],
                    name=row.get("name", ""),
                    voltage=row["voltage"],
                    conductor=row["conductor"],
                    insulation_thickness_mm=float(row["insulation_thickness_mm"]),
                    std=row.get("std", ""),
                )
            )
    return products


def load_rfps(rfp_dir: str) -> List[Dict[str, Any]]:
    rfps: List[Dict[str, Any]] = []
    for fn in sorted(os.listdir(rfp_dir)):
        if not fn.lower().endswith(".json"):
            continue
        path = os.path.join(rfp_dir, fn)
        with open(path, "r", encoding="utf-8") as f:
            rfps.append(json.load(f))
    return rfps


def _score_insulation(rfp_value: float, product_value: float, tolerance_ratio: float = 0.2) -> int:
    """Return 1 if product thickness is within ±(tolerance_ratio) of RFP value, else 0."""

    tolerance = rfp_value * tolerance_ratio
    return 1 if abs(product_value - rfp_value) <= tolerance else 0


def match_item(item: Dict[str, Any], products: List[Product]) -> Dict[str, Any]:
    """Match a single RFP scope item against all products.

    Scoring logic (all-or-nothing, each attribute weight = 1/3):
      - voltage: exact string match
      - conductor: exact string match
      - insulation_thickness_mm: within ±20% tolerance

    spec_match% = (score_total / 3) * 100
    """

    specs = item["specs"]
    rfp_voltage = specs["voltage"]
    rfp_conductor = specs["conductor"]
    rfp_ins_thk = float(specs["insulation_thickness_mm"])

    candidate_rows: List[Dict[str, Any]] = []

    for p in products:
        voltage_score = 1 if p.voltage == rfp_voltage else 0
        conductor_score = 1 if p.conductor == rfp_conductor else 0
        insulation_score = _score_insulation(rfp_ins_thk, p.insulation_thickness_mm)

        total_score = voltage_score + conductor_score + insulation_score
        spec_match_pct = int(round((total_score / 3.0) * 100))

        candidate_rows.append(
            {
                "sku": p.sku,
                "name": p.name,
                "product_specs": {
                    "voltage": p.voltage,
                    "conductor": p.conductor,
                    "insulation_thickness_mm": p.insulation_thickness_mm,
                    "std": p.std,
                },
                "scores": {
                    "voltage": voltage_score,
                    "conductor": conductor_score,
                    "insulation_thickness_mm": insulation_score,
                    "total": total_score,
                },
                "spec_match": spec_match_pct,
            }
        )

    # Sort by spec_match desc, then by absolute insulation difference (closer is better), then by SKU
    candidate_rows.sort(
        key=lambda row: (
            -row["spec_match"],
            abs(row["product_specs"]["insulation_thickness_mm"] - rfp_ins_thk),
            row["sku"],
        )
    )

    top_candidates = candidate_rows[:3]
    top = top_candidates[0]

    result = {
        "item_id": item["item_id"],
        "description": item.get("description", ""),
        "top_sku": top["sku"],
        "spec_match": top["spec_match"],
        "comparison": {
            "rfp_specs": {
                "voltage": rfp_voltage,
                "conductor": rfp_conductor,
                "insulation_thickness_mm": rfp_ins_thk,
            },
            "candidates": top_candidates,
        },
    }
    return result


def build_technical_reco(rfp_dir: str, data_dir: str) -> Dict[str, Any]:
    products = load_products(data_dir)
    rfps = load_rfps(rfp_dir)

    reco = {
        "source_rfps_dir": os.path.abspath(rfp_dir),
        "source_data_dir": os.path.abspath(data_dir),
        "rfps": [],
    }

    for rfp in rfps:
        rfp_entry = {
            "rfp_id": rfp.get("id"),
            "title": rfp.get("title"),
            "due_date": rfp.get("due_date"),
            "tests": rfp.get("tests", []),
            "items": [],
        }
        for item in rfp.get("scope", []):
            rfp_entry["items"].append(match_item(item, products))
        reco["rfps"].append(rfp_entry)

    return reco


def main() -> None:
    reco = build_technical_reco(RFP_DIR, DATA_DIR)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(reco, f, indent=2)
    print(f"technical_reco.json written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

