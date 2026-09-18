# Basket

*Report link and screenshots to follow once the owner has built and published the .pbix — see [docs/BUILD.md](docs/BUILD.md).*

A Power BI model of Malaysia's Consumer Price Index — every month since 2010, every
state, and the full MCOICOP basket down to 101 classes — built for the question a
retail pricing team or a household-budget officer actually asks: **where is the cost
of living rising fastest, and in what?**

The interesting part is not the visuals. It is a proper star schema with a marked
date table and one grain, DAX measures that answer the question at whatever the
reader has selected, and a file of expected values computed independently so the
model can be checked while it is built.

## The question, and what the data already says

Using the figures the model must reproduce (`model/expected.json`, August 2026 —
the build script fetches the latest month, so these move each release):

- **Headline inflation is 1.93% year on year**, 0.29% month on month; the basket
  costs 12.4% more than in December 2019, the last pre-pandemic month.
- **The basket is not rising evenly.** Personal Care (+3.2%), Alcoholic Beverages &
  Tobacco (+2.8%) and Information & Communication (+2.6%) lead; Clothing & Footwear
  (+0.1%) and Furnishings (+0.4%) are flat. Food & Beverages sits on the headline at
  1.9%.
- **Location matters more than the national number suggests.** Negeri Sembilan is
  running at 2.6% and Sarawak at 0.5% — a fivefold spread inside one country. For
  food specifically, Johor is at 3.5% while Kelantan is at −0.1%.
- **Since December 2019 the biggest movers are not food.** Jewellery & watches
  +132% (gold), sewage collection +88% and water supply +42% (tariff resets),
  vehicle maintenance +41%. Mobile phones and electricity are 10% *cheaper* than
  before the pandemic.

A retailer reading this sets regional price reviews by state, not by a national
CPI print; a budget officer sees that the "cost of living" story is a handful of
administered prices and gold, not groceries.

## The model

```
            DimDate (6,087 days, marked as date table)
                │ DateKey
DimGeography ───┤ StateKey ──── FactCPI (76,456 rows: DateKey · StateKey · CategoryKey · Index)
(17: 16 states  │ CategoryKey
 + Malaysia)    │
            DimCategory (162: All items · 13 divisions · 47 groups · 101 classes, MCOICOP, EN + BM)
```

- **Grain:** one row per month × state × category, keyed to the first day of the
  month in a gap-free daily date table (Power BI will not mark a monthly table as a
  date table). The index is 2010 = 100 and is never summed; every measure evaluates
  at a single category and state.
- **Ragged hierarchy handled honestly.** State data exists at division level only;
  groups and classes exist nationally only. DimCategory carries a `Level` column and
  the parents' names on every row, so the report filters by level instead of
  pretending a drill hierarchy exists where the data does not.
- **Measures** (`model/measures.dax`): `CPI`, `CPI Latest`, `CPI YoY %`, `CPI MoM %`,
  `CPI 3m Annualised %`, `CPI Since Dec 2019 %`, `CPI YoY % National`,
  `CPI YoY vs National (pp)`, `CPI YoY % Headline`, `CPI YoY vs Headline (pp)`,
  `State Rank by YoY`, `Category Rank Since Dec 2019`, `Latest Month`,
  `Selection Title`. Time intelligence uses `DATEADD` over the date table; the
  pre-pandemic base is a flag on DimDate rather than a hard-coded date in every
  measure.
- **Expected values.** `prep/build.py` computes the headline, every division's
  YoY, every state's overall and food YoY and the top and bottom classes since
  Dec 2019 in pandas and writes them to `expected.json`. The build guide checks
  the model against them at each step; a relationship set the wrong way round
  shows up as a wrong number, not a plausible one.

## Pages

1. **Overview** — the four cards (index, YoY, MoM, since Dec 2019), the YoY line
   since 2011 against a 2% reference, divisions ranked by YoY for the latest month.
2. **By state** — bubble map and ranked table of states by YoY with the gap to the
   national rate in percentage points; defaults to Food & Beverages.
3. **What got expensive** — the ten classes that rose most and the ten that fell
   since December 2019; a matrix by division › group › class with YoY, the
   three-month annualised pace and the cumulative change.
4. **Explorer** — any category, any states side by side, index and YoY over time,
   with a searchable category slicer.

Theme: `theme/basket.json`, the New Genre reference translated for Power BI —
white canvas, `#f5f5f5` cards, no borders or shadows, Onyx and Slate Veil for
data, the steel blue for the single accent.

## Building it

`python prep/build.py` fetches the four DOSM datasets and the MCOICOP lookup and
writes `model/*.csv` and `model/expected.json`. Then follow
[docs/BUILD.md](docs/BUILD.md): load, model, paste the measures, apply the theme,
build the four pages, check against the expected values, publish.

The `.pbix` (and the text-based `.pbip` project) are committed once built, so the
model is in version control and not only the screenshots.

## Limitations

- **State detail stops at divisions.** DOSM publishes state CPI at the 13-division
  level only, so "which class is driving Johor's food inflation" cannot be answered
  from this data; the class view is national.
- **No weights, so no contributions.** The share of each division in the basket is
  not published with these series, so the model shows each division's own rate,
  not its contribution to the headline.
- **Index, not prices.** A 2010 = 100 index says how fast prices move, not what
  they are; Sarawak's low inflation does not mean Sarawak is cheap.
- **Publishing depends on a work or school account.** Power BI Service does not
  accept personal addresses; if the university tenant blocks it, the deliverable
  is the committed `.pbix` and screenshots.

## Data and licences

- *Consumer Price Index* by division, group, class and by state × division, and the
  MCOICOP lookup — Department of Statistics Malaysia via
  [data.gov.my](https://open.dosm.gov.my/data-catalogue/cpi_2d), CC BY 4.0.
  Monthly, base 2010 = 100, to August 2026 at the time of writing.
- State capital coordinates for the map are approximate and in `prep/build.py`.
- Design: the New Genre reference in `DESIGN.md`.
