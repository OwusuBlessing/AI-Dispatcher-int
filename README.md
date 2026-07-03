# AI Dispatcher

Freight matching for owner-operators: LLMs interpret language; Python enforces business rules.

## Pipeline flow

```
conversation.txt → Organizer (LLM) → Extractor (LLM) → Geocoder → Resolved Driver Profile
loads.xlsx       → Load Normalizer  → Rule Engine      → Distance & Rate → Top 3 + Audit → submission.md
```

## Profile extraction

Two LLM stages organize the transcript into evidence, then build a profile with confidence and quotes. Locations use `City, ST` + Nominatim geocoding (never LLM coordinates). Post-processing canonicalizes equipment and clears unstated fields.

## Incomplete rows

Config-driven Excel mapping (`configs/loads.yaml`). Blank rows are skipped; rows missing destination or price are still audited and rejected with a recorded reason.

## Assumptions

Trailer, weight, missing-data, and min-rate rules run in Python. Null `minimum_rate_per_mile` or `weight_capacity` skips that filter. Effective rate = price ÷ total trip miles (Haversine).

## Rejected high-paying load

**L05** (Waco → San Antonio, $640) has an effective rate of **$2.514/mi** — above the driver's $2/mi floor — but requires **flatbed**. This driver runs **hotshot/gooseneck** only, so it fails the equipment rule and is excluded before ranking.

## Run

```bash
pip install -e ".[dev,ai]"
cp .env.example .env
python scripts/create_submission.py
```

Agent models are configured in `configs/agent_llm_config.py`.
