# Actual vs. Expected Medical Expense — Process Flow

The diagram below shows how the six steps relate to each other across the three phases. Steps 1, 2, and 3 can be worked in parallel; Step 4 depends on Step 2; Step 5 converges Steps 3 and 4; and Step 6 is the final join of Steps 1 and 5.

```mermaid
flowchart TD
    subgraph P1["📥 Phase 1: Data Ingestion & Summarization"]
        S1["**Step 1** — Get Actual HCTA Data\nOwner: Jacob / Jonathan\nData thru: Apr-26\nAlt: Summarize from Tre"]
        S2["**Step 2** — Get Forecast HCTA Data\nOwner: Jacob / Jonathan\nData thru: Dec-25"]
        S3["**Step 3** — Read Jordan Forecast\nOwner: Jordan\nActuals thru Dec-25 · Forecast Jan-26+"]
    end

    subgraph P2["⚙️ Phase 2: Data Processing & Modeling"]
        S4["**Step 4** — Create Forecast HCTA Allocations\nOwner: Andrew\nDerived from Step 2"]
        S5["**Step 5** — Apply Allocations to Jordan Forecast\nOwner: Andrew\nFull-year 2026 expected view"]
    end

    subgraph P3["📊 Phase 3: Executive Dashboard"]
        S6["**Step 6** — Create Actual vs. Expected Display\nOwner: Andrew\nInputs: Steps 1 & 5"]
    end

    S2 --> S4
    S4 --> S5
    S3 --> S5
    S1 --> S6
    S5 --> S6
```
