# AI Dispatcher Take-Home — System Design & Implementation Plan

This is the architecture I would confidently build as a senior AI engineer. The key design principle is:

> **Separate language understanding from business logic.**

The LLM is responsible for **understanding messy human language**. Python is responsible for **deterministic business decisions**.

This makes the system explainable, testable, modular, and easy to extend.

---

# High Level Architecture

```text
                           Driver Conversation
                                   │
                                   ▼
                 ┌──────────────────────────────────┐
                 │ Conversation Organizer Agent     │
                 │ (LLM)                            │
                 └──────────────────────────────────┘
                                   │
                                   ▼
                      Structured Conversation Evidence
                                   │
                                   ▼
                 ┌──────────────────────────────────┐
                 │ Driver Profile Extraction Agent   │
                 │ (LLM)                            │
                 └──────────────────────────────────┘
                                   │
                                   ▼
                      Structured Driver Profile
                                   │
                  ┌────────────────┴─────────────────┐
                  ▼                                  ▼
         Location Resolution                Equipment Resolution
       (Geocoder + Cache)         (Deterministic → LLM Fallback)
                  │                                  │
                  └────────────────┬─────────────────┘
                                   ▼
                      Fully Resolved Driver Profile
                                   │
                                   ▼
                     Load Dataset Normalization
                                   │
                                   ▼
                    Eligibility / Business Rules
                                   │
                                   ▼
                           Load Audit Trail
                                   │
                                   ▼
                         Distance Calculator
                                   │
                                   ▼
                    Effective Rate Calculator
                                   │
                                   ▼
                           Ranking Engine
                                   │
                                   ▼
         Part A Output │ Top 3 Loads │ README │ Audit Report
```

---

# Philosophy

Every stage has **exactly one responsibility**.

| Stage                  | Responsibility                  |
| ---------------------- | ------------------------------- |
| Conversation Organizer | Organize messy conversation     |
| Profile Extractor      | Infer structured driver profile |
| Location Resolver      | Resolve city → coordinates      |
| Equipment Resolver     | Resolve equipment compatibility |
| Rule Engine            | Apply deterministic constraints |
| Ranking Engine         | Compute effective rate          |
| README Generator       | Produce submission artifacts    |

No stage does multiple jobs.

---

# Stage 1 — Conversation Organizer Agent

## Goal

Do **not** extract the final profile.

Instead, transform an unstructured phone conversation into organized semantic evidence.

Input

```
Raw conversation transcript
```

Output

```json
{
    "locations": [],
    "equipment": [],
    "constraints": [],
    "preferences": [],
    "financial": [],
    "operations": [],
    "availability": [],
    "other": []
}
```

Every extracted item contains

* speaker
* raw quote
* category
* explicit / implicit
* confidence

Example

```json
{
    "category":"Location",
    "speaker":"Driver",
    "quote":"I'm usually in that area but I'm in Dallas.",
    "classification":"Explicit"
}
```

No interpretation.

Only organization.

---

# Stage 2 — Driver Profile Extraction Agent

Input

```
Conversation Evidence
```

Output

```json
{
    "required_fields":{},
    "preferences":{},
    "constraints":{},
    "metadata":{},
    "confidence":{},
    "evidence":{}
}
```

---

## Required Assignment Fields

These directly populate Part A.

* Current Location
* Current Latitude
* Current Longitude
* Home Base
* Home Latitude
* Home Longitude
* Minimum Rate Per Mile
* Equipment Types
* Weight Capacity

---

## Additional Internal Fields

These improve downstream reasoning.

### Operational

* Preferred regions
* Avoided regions
* Preferred cities
* Avoided cities
* Preferred lanes

### Business

* Requires factorable brokers
* Negotiates rates
* Hard constraints
* Soft preferences

### Equipment

* Raw description
* Canonical equipment

### Work

* Days per week
* Availability
* Schedule flexibility

### Metadata

Every field stores

* confidence
* evidence quote
* reasoning notes

Example

```json
{
    "minimum_rate_per_mile":{
        "value":2.0,
        "confidence":0.98,
        "evidence":"As long as it's above $2/mile..."
    }
}
```

---

# Stage 3 — Location Resolution

The LLM never generates coordinates.

It only extracts structured locations.

Example

```json
{
    "city":"Dallas",
    "state":"Texas",
    "country":"USA"
}
```

Pipeline

```
Normalize

↓

Local Cache

↓

Found?

↓

Yes

↓

Return Coordinates

↓

No

↓

Geocoder API

↓

Cache

↓

Return
```

Output

```json
{
    "city":"Dallas",
    "lat":32.7767,
    "lon":-96.7970
}
```

---

# Stage 4 — Equipment Resolution

Purpose

Resolve semantic compatibility between

Driver equipment

and

Load requirement.

Pipeline

```
Normalize

↓

Exact Match

↓

Synonym Dictionary

↓

Match?

↓

YES

↓

PASS

↓

NO

↓

LLM Compatibility Resolver

↓

PASS / FAIL

↓

Cache Decision
```

The LLM is only a fallback.

---

# Stage 5 — Load Dataset Normalization

Read Excel.

Normalize

* trailer
* price
* weight
* city names
* missing values

No LLM.

---

# Stage 6 — Business Rule Engine

Pure Python.

Every load passes through identical deterministic rules.

Rules

## Missing Data

Reject

if

* missing destination
* missing price

---

## Equipment

Compatible?

---

## Weight

Within driver's capacity?

---

## Minimum Rate

Effective rate

≥ driver's minimum

---

Future rules become trivial

Example

* broker approval
* hazmat
* region preference

---

# Stage 7 — Audit Trail

Every load receives a decision.

Example

| Load | Trailer | Weight | Missing | Eligible | Reason           |
| ---- | ------- | ------ | ------- | -------- | ---------------- |
| L01  | FAIL    | PASS   | PASS    | Reject   | Trailer mismatch |
| L02  | PASS    | PASS   | PASS    | Accept   | —                |
| L06  | PASS    | PASS   | FAIL    | Reject   | Missing price    |

Nothing is hidden.

Everything is explainable.

---

# Stage 8 — Distance Calculator

Only eligible loads.

Compute

```
Current Truck Location

↓

Origin

↓

Destination

↓

Home Base
```

Formula

```
Deadhead To Origin

+

Loaded Miles

+

Deadhead Home
```

---

# Stage 9 — Effective Rate

```
price

/

(
deadhead_to_origin
+
loaded_miles
+
deadhead_home
)
```

Store

```
effective_rate
```

inside audit trail.

---

# Stage 10 — Ranking

```
Eligible Loads

↓

Sort DESC

↓

Top 3
```

---

# Stage 11 — Deliverables

Automatically generate

* Part A Answer
* Ranked Top 3
* README
* Audit Table

README generated from pipeline outputs.

Not manually written.

---

# Testing Strategy

Besides the assignment conversation,

create

```
tests/data/conversations/
```

with around 10 conversations.

Examples

* Missing location
* Conflicting location
* Multiple equipment
* Implicit preferences
* Missing rate
* No constraints
* Weight mentioned
* Weight omitted
* Equipment synonyms
* Noisy dispatcher conversation

Each test contains

```
conversation.txt

expected_profile.json

expected_ranking.json
```

Pipeline runs end-to-end.

Compare outputs.

Regression testing becomes automatic.

---

# Repository Structure

```text
ai_dispatcher/
│
├── README.md
├── pyproject.toml
├── requirements.txt
├── .env.example
│
├── data/
│   ├── raw/
│   │   ├── conversation.txt
│   │   └── loads.xlsx
│   ├── processed/
│   └── cache/
│       ├── geocode_cache.json
│       └── equipment_cache.json
│
├── configs/
│   ├── settings.py
│   ├── prompts.yaml
│   └── rules.yaml
│
├── prompts/
│   ├── conversation_organizer.md
│   ├── profile_extractor.md
│   ├── equipment_matcher.md
│   └── readme_generator.md
│
├── src/
│   ├── main.py
│   │
│   ├── domain/
│   │   ├── models.py
│   │   ├── enums.py
│   │   └── schemas.py
│   │
│   ├── agents/
│   │   ├── conversation_organizer.py
│   │   ├── profile_extractor.py
│   │   ├── equipment_matcher.py
│   │   └── readme_generator.py
│   │
│   ├── services/
│   │   ├── geocoder.py
│   │   ├── load_reader.py
│   │   ├── load_normalizer.py
│   │   ├── distance_service.py
│   │   ├── rate_calculator.py
│   │   ├── ranking_service.py
│   │   └── audit_service.py
│   │
│   ├── rules/
│   │   ├── base_rule.py
│   │   ├── trailer_rule.py
│   │   ├── weight_rule.py
│   │   ├── missing_data_rule.py
│   │   ├── rate_rule.py
│   │   └── engine.py
│   │
│   ├── providers/
│   │   ├── llm/
│   │   │   ├── base.py
│   │   │   ├── openai_provider.py
│   │   │   ├── anthropic_provider.py
│   │   │   └── factory.py
│   │   │
│   │   └── geocoding/
│   │       ├── base.py
│   │       ├── nominatim_provider.py
│   │       └── factory.py
│   │
│   ├── pipelines/
│   │   ├── extraction_pipeline.py
│   │   ├── matching_pipeline.py
│   │   └── submission_pipeline.py
│   │
│   ├── utils/
│   │   ├── json_utils.py
│   │   ├── logging.py
│   │   ├── cache.py
│   │   └── validation.py
│   │
│   └── outputs/
│       ├── profile.json
│       ├── audit.csv
│       ├── ranking.csv
│       ├── README.md
│       └── part_a_answer.xlsx
│
├── tests/
│   ├── unit/
│   │   ├── test_rules.py
│   │   ├── test_geocoder.py
│   │   ├── test_distance.py
│   │   └── test_equipment.py
│   │
│   ├── integration/
│   │   ├── test_extraction_pipeline.py
│   │   ├── test_matching_pipeline.py
│   │   └── test_submission_pipeline.py
│   │
│   └── data/
│       ├── conversations/
│       │   ├── case_01/
│       │   │   ├── conversation.txt
│       │   │   ├── expected_profile.json
│       │   │   └── expected_top3.json
│       │   ├── case_02/
│       │   ├── case_03/
│       │   ├── case_04/
│       │   ├── case_05/
│       │   ├── case_06/
│       │   ├── case_07/
│       │   ├── case_08/
│       │   ├── case_09/
│       │   └── case_10/
│       │
│       └── loads/
│           └── sample_loads.xlsx
│
└── scripts/
    ├── run_pipeline.py
    ├── run_tests.py
    └── generate_submission.py
```

# Engineering Principles

* **Single Responsibility Principle:** Each component has one clear purpose.
* **Provider Abstraction:** LLMs and geocoders are accessed through interfaces, making it easy to swap providers.
* **Deterministic First:** Use rules and normalization before invoking an LLM.
* **LLM for Semantics:** Reserve LLMs for understanding language and resolving ambiguity, not for arithmetic or business rules.
* **Evidence Preservation:** Keep the original quote, normalized value, confidence, and reasoning for every extracted field.
* **Auditability:** Every accepted or rejected load has a recorded explanation.
* **Testability:** End-to-end regression cases plus unit and integration tests ensure changes don't silently break behavior.
* **Extensibility:** New rules, providers, or extraction fields can be added with minimal changes to the existing pipeline.

This structure mirrors how I'd build a maintainable AI service in production: modular, provider-agnostic, observable, and designed so each layer can evolve independently.
