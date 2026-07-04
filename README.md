# AI Dispatcher

Freight matching for owner-operators: LLMs interpret language; Python enforces business rules.

## Pipeline flow

```
conversation.txt → Organizer (LLM) → Extractor (LLM) → Geocoder → Resolved Driver Profile
loads.xlsx       → Load Normalizer  → Rule Engine      → Distance & Rate → Top 3 + Audit → submission.md
```

## Profile extraction

Two LLM stages build a profile with confidence and quotes. Locations use `City, ST` + Nominatim (never LLM coordinates). Post-processing canonicalizes equipment and clears unstated fields.

## Incomplete rows

Incomplete loads (missing price or destination) stay in the audit trail but are marked ineligible and excluded from the top 3, because effective $/mi cannot be computed. The pipeline never fails on incomplete rows. Audit table, Part A profile, and top 3: [src/outputs/submission.md](src/outputs/submission.md).

## Assumptions

Trailer, weight, missing-data, and min-rate rules run in Python. Null min rate or weight capacity skips that filter. Effective rate = price ÷ total trip miles (Haversine).

## Rejected high-paying load

**L04** (Plano → Memphis, $1,500) is the highest-priced rejected load but requires **van**. Driver runs **hotshot/gooseneck** only, so equipment fails before ranking.

## Run

```bash
pip install -e ".[dev,ai]"
cp .env.example .env
python scripts/create_submission.py
```

Agent models: `configs/agent_llm_config.py`.
