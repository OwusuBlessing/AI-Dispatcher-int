# AI Dispatcher — Submission

## Driver Profile (Part A)

| Field | Value | Confidence |
| --- | --- | --- |
| Current Location | Dallas, TX | 1.00 |
| Current Latitude | 32.7763 | 1.00 |
| Current Longitude | -96.7969 | 1.00 |
| Home Base | San Antonio, TX | 0.97 |
| Home Latitude | 29.4246 | 0.97 |
| Home Longitude | -98.4951 | 0.97 |
| Minimum Rate ($/mi) | 2 | 1.00 |
| Equipment Types | hotshot, gooseneck | 1.00 |
| Weight Capacity (lbs) | — | — |
| Canonical Equipment | hotshot, gooseneck | — |

## Load Audit

| Load | Trailer | Location | Weight | Missing | Rate | Eligible | $/mi | Miles | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L01 | FAIL | PASS | PASS | PASS | — | Reject | $0.97 | 640 | Not recommended — Equipment mismatch: this driver runs gooseneck, hotshot, which cannot haul a van load. |
| L02 | PASS | PASS | PASS | PASS | PASS | Accept | $2.42 | 662 | Recommended — this load passes equipment, data quality, location policy, and pay checks. |
| L03 | PASS | PASS | PASS | PASS | PASS | Accept | $3.10 | 484 | Recommended — this load passes equipment, data quality, location policy, and pay checks. |
| L04 | FAIL | PASS | PASS | PASS | — | Reject | $1.42 | 1058 | Not recommended — Equipment mismatch: this driver runs gooseneck, hotshot, which cannot haul a van load. |
| L05 | FAIL | PASS | PASS | PASS | — | Reject | $2.51 | 255 | Not recommended — Equipment mismatch: this driver runs gooseneck, hotshot, which cannot haul a flatbed load. |
| L06 | FAIL | PASS | PASS | FAIL | — | Reject | — | — | Not recommended — Load data is incomplete (missing required load data: price), so it cannot be ranked fairly. Equipment mismatch: this driver runs gooseneck, hotshot, which cannot haul a van load. |
| L07 | PASS | PASS | PASS | FAIL | — | Reject | — | — | Not recommended — Load data is incomplete (missing required load data: destination), so it cannot be ranked fairly. |
| L08 | PASS | PASS | PASS | PASS | PASS | Accept | $2.48 | 685 | Recommended — this load passes equipment, data quality, location policy, and pay checks. |

## Top 3 Recommended Loads

| Rank | Load | Route | Price | $/mi | Total mi |
| --- | --- | --- | --- | --- | --- |
| 1 | L03 | Austin → Corpus Christi | $1,500 | $3.10 | 484 |
| 2 | L08 | Dallas → Mcallen | $1,700 | $2.48 | 685 |
| 3 | L02 | Houston → Laredo | $1,600 | $2.42 | 662 |