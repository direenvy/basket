# Building Basket in Power BI Desktop

About two hours the first time. Everything you need is in this repository:
the four CSVs in `model/`, the measures in `model/measures.dax`, the theme in
`theme/basket.json`, and `model/expected.json` — the numbers the finished model
must show, so you can check yourself as you go.

Power BI Desktop is free: Microsoft Store → "Power BI Desktop", or
https://powerbi.microsoft.com/desktop. Windows only.

## 1. Load the data (10 min)

1. Open Power BI Desktop → blank report → **Home › Get data › Text/CSV**.
2. Load `model/FactCPI.csv`. In the preview, click **Transform Data** and check the
   column types: `DateKey` **Whole number**, `StateKey` **Text**, `CategoryKey` **Text**
   (it must be text — codes like `01` lose their leading zero as a number), `Index`
   **Decimal number**. Then **Close & Apply**.
3. Repeat for `DimDate.csv` (`Date` → **Date**, `DateKey` → Whole number, `IsLatest`
   and `IsPrePandemicBase` → True/False), `DimCategory.csv` (every column Text except
   `LevelOrder` → Whole number), `DimGeography.csv` (`Latitude`/`Longitude` → Decimal,
   `IsNational` → True/False, `SortOrder` → Whole number).

Check: **Data** view → FactCPI has 76,070 rows, DimDate 199, DimCategory 162,
DimGeography 17 (`expected.json` → `rows`).

## 2. Model (15 min)

Go to **Model** view.

1. Relationships (drag the field from the fact to the dimension, or **Manage
   relationships › New**). Each is many-to-one, single direction, active:
   - `FactCPI[DateKey]` → `DimDate[DateKey]`
   - `FactCPI[StateKey]` → `DimGeography[StateKey]`
   - `FactCPI[CategoryKey]` → `DimCategory[CategoryKey]`
2. Mark the date table: select DimDate → **Table tools › Mark as date table** →
   column `Date`. (The YoY and MoM measures depend on this.)
3. Sort columns: select `DimDate[Month]` → **Column tools › Sort by column** →
   `MonthNumber`. Same for `DimDate[MonthYear]` → sort by `DateKey`, and
   `DimGeography[State]` → sort by `SortOrder`.
4. Hide the keys from report view (right-click → Hide): `FactCPI[DateKey]`,
   `FactCPI[StateKey]`, `FactCPI[CategoryKey]`, `DimDate[DateKey]`,
   `DimGeography[StateKey]`, `DimCategory[CategoryKey]`, and hide `FactCPI[Index]`
   too — the report should only ever use measures.
5. Optional: a display folder. Right-click DimCategory → **New hierarchy** is *not*
   useful here — the category table is ragged (a division row has no group or
   class), so the report uses the `Level` slicer instead of a drill hierarchy.

## 3. Measures (20 min)

**Home › Enter data** → name the table `Measures`, one column, OK. Select it,
then **New measure** and paste each block from `model/measures.dax` in turn
(everything after the `=` on the first line goes after the name). Set the format
noted in each comment: select the measure → **Measure tools › Format** (0.0,
Percentage with 1 decimal, or a custom format string in the Properties pane).
When all are in, delete the table's empty column so it shows as a measure table.

Check as you go — put a **Card** on the page with the measure and a slicer on
`DimCategory[Category]` = "All items" and `DimGeography[State]` = "Malaysia":

| Measure | Expected (`expected.json`) |
|---|---|
| CPI Latest | `headline_index` — 137.1 |
| CPI YoY % (with a slicer `DimDate[IsLatest]` = True) | `headline_yoy_pct` — 1.78% |
| CPI MoM % (same) | `headline_mom_pct` — 0.0% |
| CPI Since Dec 2019 % | `headline_since_dec2019_pct` — 12.1% |
| Latest Month | `latest_month` — Jul 2026 |

If YoY shows blank, the date table is not marked or `Date` is not a Date type.
If CPI Latest shows the wrong month, a date slicer is limiting the context.

## 4. Theme and canvas (5 min)

**View › Themes › Browse for themes** → `theme/basket.json`. Page size: **Format
page › Canvas settings** → 16:9. Keep the canvas white, visuals on `#f5f5f5`
cards, no borders, no shadows — the theme does this. Fonts are Segoe UI (Power BI
cannot embed DM Sans); that is fine.

## 5. Pages (60 min)

Every page carries the same two slicers top-left, single-select, as dropdowns:
`DimGeography[State]` (default Malaysia) and `DimCategory[Level]` +
`DimCategory[Category]` (default All items). Use **View › Sync slicers** so they
follow across pages.

### Page 1 — Overview

- Four **Cards** across the top: `CPI Latest` (title "Index, 2010 = 100"),
  `CPI YoY %` ("Inflation, year on year"), `CPI MoM %` ("Month on month"),
  `CPI Since Dec 2019 %` ("Since December 2019"). Each card carries a
  visual-level filter `DimDate[IsLatest]` = True.
- A **Line chart**: X = `DimDate[Date]` (continuous), Y = `CPI YoY %`, filter
  `DimDate[Year]` ≥ 2011. Add a constant line at 0.02 (Analytics pane › Constant
  line, label "2%"). Title from `Selection Title` (fx › field value).
- A **Clustered bar chart**: Y = `DimCategory[Category]`, X = `CPI YoY %`,
  visual-level filters `DimCategory[Level]` = Division and `DimDate[IsLatest]` =
  True, sorted descending. This is the "which divisions lead the basket" view; the
  expected order is in `expected.json › division_yoy_pct` (Information &
  Communication first, Clothing & Footwear last, in Jul 2026).
- A **Text box** bottom-left: "Source: DOSM Consumer Price Index via data.gov.my,
  CC BY 4.0. Data to {Latest Month}." (use a card for the month or type it).

### Page 2 — By state

- **Azure map** (or the default Map): Location = `DimGeography[State]`, Latitude /
  Longitude from the table, Bubble size = `CPI YoY %`, filter `DimGeography[IsNational]`
  = False and `DimDate[IsLatest]` = True. If the map visual is disabled, Options ›
  Global › Map and filled map visuals.
- A **Table**: `State`, `CPI YoY %`, `CPI YoY vs National (pp)`, `State Rank by YoY`,
  `CPI Since Dec 2019 %`; same two filters; sort by rank. Conditional formatting on
  the pp column: data bars, one colour (`#5a769f`).
- A **Clustered bar chart** of states by `CPI YoY %` (sorted), with the Category
  slicer set to Food & Beverages by default for this page — that is the view a
  retailer wants. Expected: `expected.json › state_food_yoy_pct` (Johor highest,
  Kelantan and Labuan at 0.0% in Jul 2026).

### Page 3 — What got expensive

- **Clustered bar chart**: Y = `DimCategory[Category]`, X = `CPI Since Dec 2019 %`,
  visual-level filters `DimCategory[Level]` = Class, `DimGeography[State]` = Malaysia,
  **Top N** = 10 by `CPI Since Dec 2019 %`. Title "Ten classes that rose most since
  Dec 2019". Expected: Jewellery & watches +127.5%, Sewage collection +88.4%, Water
  supply +42.5% …
- A second bar chart with **Bottom N** = 10: "…and ten that fell". Expected:
  Motorcycles −26.1%, Mobile telephone equipment −10.1%, Electricity −10.1% …
- A **Matrix**: rows `DimCategory[Division]` then `Group` then `Class` (this works as
  a matrix because each row filters to its own level via the `Level` field — put
  `DimCategory[Level]` = Class in the visual filter and use `Path` as the single row
  field if the nesting looks odd), values `CPI YoY %`, `CPI 3m Annualised %`,
  `CPI Since Dec 2019 %`, `Category Rank Since Dec 2019`.

### Page 4 — Explorer

- **Line chart**: X = `DimDate[Date]`, Y = `CPI` with legend `DimGeography[State]`;
  slicers on this page allow multi-select on State so a reader can put Johor against
  Sarawak against Malaysia for any category. Second line chart with `CPI YoY %`.
- A **Slicer** on `DimCategory[Category]` with search enabled (… › Search) so any of
  the 162 categories can be typed.

## 6. Check against expected.json (5 min)

With State = Malaysia, Category = All items and no date filter:
`CPI Latest` 137.1, `CPI Since Dec 2019 %` 12.1%. With `DimDate[IsLatest]` on the
page: `CPI YoY %` 1.78%. Switch State to Negeri Sembilan: `CPI YoY %` 2.48%
(`highest_state_overall_yoy`); Sarawak: 0.31%. If any differ, the culprit is
almost always the relationship direction or an unmarked date table.

## 7. Save and publish (10 min)

1. **File › Save as** → `basket.pbix` in this folder. Also **File › Options ›
   Preview features › Power BI Project (.pbip) save option**, restart, and **Save
   as** `basket.pbip`: that writes the model and report as text files that can be
   committed, so the model is in git as well as the binary.
2. Publish, one of:
   - **Power BI Service** (best): **Home › Publish** → My workspace. It needs a
     work or school account — try the APU address. Then in the service: open the
     report → **File › Embed report › Publish to web (public)** → copy the link. That
     link goes in the README and on the portfolio site.
   - If the APU tenant blocks Power BI or you have no school account: commit
     `basket.pbix`/`.pbip` here, take a screenshot of each page at 1920×1080
     (**View › Fit to page**, then Snipping Tool) into `docs/`, and the site links
     the repository. Optional: a 30-second screen recording of the slicers working.
3. Commit: `git add -A && git commit -m "Basket: the report" && git push`.

Then tell me the link (or that the screenshots are in), and I will write the
findings into the README, add the case study to the portfolio site, and update
the plan.
