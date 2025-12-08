import json

class MainAgent:
    def __init__(self, sales_agent, technical_agent, pricing_agent):
        self.sales_agent = sales_agent
        self.technical_agent = technical_agent
        self.pricing_agent = pricing_agent

    def run(self):
        print("\n==============================")
        print("STEP 1: SALES AGENT — Identify RFP")
        print("==============================")

        rfp_data = self.sales_agent.identify_rfp()
        print(f"Selected RFP: {rfp_data['title']}")
        print(f"Due Date: {rfp_data['due_date']}")
        print(f"Scope Count: {len(rfp_data['scope'])}")

        print("\n==============================")
        print("STEP 2: TECHNICAL AGENT — SKU Matching")
        print("==============================")

        technical_output = self.technical_agent.process_rfp(rfp_data)
        print("Top SKU Recommendations:")
        for item in technical_output["items"]:
            print(f" - Item: {item['rfp_item']}")
            print(f"   Best SKU: {item['best_sku']} ({item['best_match_percent']}% match)")

        print("\n==============================")
        print("STEP 3: PRICING AGENT — Material & Test Pricing")
        print("==============================")

        pricing_output = self.pricing_agent.calculate_price(technical_output)
        print("\nPricing Output:")
        for p in pricing_output["pricing_table"]:
            print(f"{p['rfp_item']} => Material: ₹{p['material_cost']} | Testing: ₹{p['test_cost']} | Total: ₹{p['total_cost']}")

        print("\n==============================")
        print("FINAL CONSOLIDATED RESPONSE")
        print("==============================")

        final_response = {
            "rfp_title": rfp_data["title"],
            "due_date": rfp_data["due_date"],
            "technical_match": technical_output,
            "pricing": pricing_output
        }

        # Save output to JSON
        with open("final_response.json", "w") as f:
            json.dump(final_response, f, indent=4)

        print("\nSaved: final_response.json")
        print("\n--- END OF PIPELINE ---")
        return final_response
