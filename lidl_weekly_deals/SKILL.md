---
name: lidl_weekly_deals
description: Fetch Lidl Belgium's weekly promotions and identify healthy items with recipe suggestions for a couple.
metadata:
  openclaw:
    requires:
      bins:
        - python3
---

When the user asks about Lidl promotions, weekly deals, or wants healthy meal ideas based on current Lidl offers, do the following:

1. Run the scraper to fetch this week's promotions:
   ```
   python lidl_promotions.py
   ```
   The script prints a JSON array to stdout. Each product has: `name`, `brand`, `category`, `regular_price` (EUR), `discounted_price` (EUR), `quantity`, and `special_conditions`.

2. Review all products and select the ones best suited for a health-conscious couple. Prioritise:
   - Fresh fruit and vegetables
   - Lean proteins: fish, poultry, legumes, eggs, tofu
   - Whole grains and complex carbohydrates
   - Healthy dairy: plain yoghurt, cottage cheese, kefir
   - Nuts, seeds, olive oil, and other healthy fats

   Skip or deprioritise: heavily processed foods, sugary snacks, alcohol, confectionery, and ready-meals.

3. List the healthy shortlist clearly — name, discounted price, quantity, and any special conditions (e.g. Lidl Plus required).

4. Suggest 3–5 recipes the couple can cook this week using those ingredients. Common pantry staples (olive oil, garlic, onion, canned tomatoes, pasta, rice, spices, stock) may be added freely. For each recipe include:
   - Name and one-sentence description
   - Which promoted ingredients it uses
   - Step-by-step preparation (4–8 steps)
   - Approximate prep and cook time
