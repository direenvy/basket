"""Build the star schema Power BI loads.

Source: DOSM's Consumer Price Index on data.gov.my (cpi_2d, cpi_3d, cpi_4d,
cpi_2d_state) and the MCOICOP lookup, all CC BY 4.0. Output: four CSVs in
model/ — one fact, three dimensions — plus expected.json, the figures the
DAX measures must reproduce once the model is built.

    python prep/build.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "model"
SRC = "https://storage.dosm.gov.my"
BASE_YEAR = "2010"  # index base 2010 = 100
PRE_PANDEMIC = "2019-12-01"

# Regions as DOSM groups them; the coordinates are state capitals, for the map.
STATES = {
    "Malaysia": ("National", 4.2105, 101.9758),
    "Johor": ("Southern", 1.4854, 103.7618),
    "Kedah": ("Northern", 6.1184, 100.3685),
    "Kelantan": ("East Coast", 6.1254, 102.2381),
    "Melaka": ("Southern", 2.1896, 102.2501),
    "Negeri Sembilan": ("Southern", 2.7258, 101.9424),
    "Pahang": ("East Coast", 3.8077, 103.3260),
    "Perak": ("Northern", 4.5975, 101.0901),
    "Perlis": ("Northern", 6.4414, 100.1986),
    "Pulau Pinang": ("Northern", 5.4141, 100.3288),
    "Sabah": ("East Malaysia", 5.9804, 116.0735),
    "Sarawak": ("East Malaysia", 1.5533, 110.3592),
    "Selangor": ("Central", 3.0738, 101.5183),
    "Terengganu": ("East Coast", 5.3117, 103.1324),
    "W.P. Kuala Lumpur": ("Central", 3.1390, 101.6869),
    "W.P. Labuan": ("East Malaysia", 5.2831, 115.2308),
    "W.P. Putrajaya": ("Central", 2.9264, 101.6964),
}


def load() -> dict[str, pd.DataFrame]:
    out = {name: pd.read_parquet(f"{SRC}/cpi/{name}.parquet") for name in ["cpi_2d", "cpi_3d", "cpi_4d", "cpi_2d_state"]}
    out["lookup"] = pd.read_parquet(f"{SRC}/dictionaries/mcoicop.parquet")
    for k in ["cpi_2d", "cpi_3d", "cpi_4d", "cpi_2d_state"]:
        out[k]["date"] = pd.to_datetime(out[k]["date"])
    return out


def dim_category(lookup: pd.DataFrame) -> pd.DataFrame:
    """One row per code at division, group and class level, each carrying its
    parents' names so a hierarchy can be built in the model without a bridge."""
    div = lookup[lookup.digits.isin([1, 2])].set_index("division").desc_en.to_dict()
    grp = lookup[lookup.digits == 3].set_index("group").desc_en.to_dict()
    rows = []
    for r in lookup[lookup.digits.isin([1, 2, 3, 4])].rename(columns={"class": "cls"}).itertuples():
        level = {1: "All items", 2: "Division", 3: "Group", 4: "Class"}[r.digits]
        code = {1: "overall", 2: r.division, 3: r.group, 4: r.cls}[r.digits]
        rows.append(
            {
                "CategoryKey": code,
                "Level": level,
                "LevelOrder": r.digits,
                "Category": r.desc_en,
                "CategoryBM": r.desc_bm,
                "DivisionCode": "overall" if r.digits == 1 else r.division,
                "Division": "All items" if r.digits == 1 else div.get(r.division, r.division),
                "GroupCode": r.group if r.digits >= 3 else "",
                "Group": grp.get(r.group, "") if r.digits >= 3 else "",
                "ClassCode": code if r.digits == 4 else "",
                "Class": r.desc_en if r.digits == 4 else "",
            }
        )
    df = pd.DataFrame(rows).drop_duplicates("CategoryKey")
    # The overall row and each division sit on their own path; a class shows Division › Group › Class.
    df["Path"] = df.apply(lambda x: " › ".join([p for p in [x["Division"] if x["LevelOrder"] > 1 else "", x["Group"], x["Class"]] if p]), axis=1)
    return df.sort_values(["LevelOrder", "CategoryKey"]).reset_index(drop=True)


def dim_geography() -> pd.DataFrame:
    rows = [{"StateKey": k, "State": k, "Region": v[0], "Latitude": v[1], "Longitude": v[2], "IsNational": k == "Malaysia", "SortOrder": i} for i, (k, v) in enumerate(STATES.items())]
    return pd.DataFrame(rows)


def dim_date(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Daily, with no gaps: Power BI refuses to mark a table with gaps as a date
    table and DATEADD needs contiguous days. The facts sit on the first of each
    month; the other days carry no facts and never appear in a visual."""
    idx = pd.date_range(start, end + pd.offsets.MonthEnd(0), freq="D")
    df = pd.DataFrame({"Date": idx})
    df["DateKey"] = df.Date.dt.strftime("%Y%m%d").astype(int)
    df["IsMonthStart"] = df.Date.dt.day == 1
    df["Year"] = df.Date.dt.year
    df["Quarter"] = "Q" + df.Date.dt.quarter.astype(str)
    df["YearQuarter"] = df.Year.astype(str) + " " + df.Quarter
    df["MonthNumber"] = df.Date.dt.month
    df["Month"] = df.Date.dt.strftime("%b")
    df["YearMonth"] = df.Date.dt.strftime("%Y-%m")
    df["MonthYear"] = df.Date.dt.strftime("%b %Y")
    df["YearMonthNumber"] = df.Date.dt.strftime("%Y%m").astype(int)  # one value per month: what MonthYear sorts by
    df["IsLatest"] = df.Date == end  # the first of the latest month, where the latest facts sit
    df["IsPrePandemicBase"] = df.Date == pd.Timestamp(PRE_PANDEMIC)
    return df


def fact(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    parts = []
    for name, key in [("cpi_2d", "division"), ("cpi_3d", "group"), ("cpi_4d", "class")]:
        d = data[name].rename(columns={key: "CategoryKey"})
        d["StateKey"] = "Malaysia"
        parts.append(d[["date", "StateKey", "CategoryKey", "index"]])
    s = data["cpi_2d_state"].rename(columns={"division": "CategoryKey", "state": "StateKey"})
    parts.append(s[["date", "StateKey", "CategoryKey", "index"]])
    f = pd.concat(parts, ignore_index=True)
    f = f[f.date >= pd.Timestamp(f"{BASE_YEAR}-01-01")]  # the state series start in 2010; keep one base for all
    f["DateKey"] = f.date.dt.strftime("%Y%m%d").astype(int)
    f = f.rename(columns={"index": "Index"})[["DateKey", "StateKey", "CategoryKey", "Index"]]
    f = f.dropna(subset=["Index"]).drop_duplicates(["DateKey", "StateKey", "CategoryKey"])
    return f.sort_values(["StateKey", "CategoryKey", "DateKey"]).reset_index(drop=True)


def expected(f: pd.DataFrame, cat: pd.DataFrame, dates: pd.DataFrame) -> dict:
    """The figures the DAX measures must reproduce, computed here in pandas so the
    owner can check the model as they build it."""
    latest_key = int(dates.loc[dates.IsLatest, "DateKey"].iloc[0])
    latest = pd.to_datetime(str(latest_key))
    year_ago = int((latest - pd.DateOffset(years=1)).strftime("%Y%m%d"))
    month_ago = int((latest - pd.DateOffset(months=1)).strftime("%Y%m%d"))
    pre = int(pd.Timestamp(PRE_PANDEMIC).strftime("%Y%m%d"))
    piv = f.pivot_table(index="DateKey", columns=["StateKey", "CategoryKey"], values="Index")

    def val(state, code, key):
        try:
            v = float(piv.loc[key, (state, code)])
        except KeyError:
            return None
        return None if v != v else v  # a NaN would silently break the ranking below

    def pct(a, b):
        return None if a is None or b is None or b == 0 else round((a / b - 1) * 100, 2)

    names = cat.set_index("CategoryKey").Category.to_dict()
    divisions = cat[cat.Level == "Division"].CategoryKey.tolist()
    states = [s for s in piv.columns.get_level_values(0).unique() if s != "Malaysia"]
    out = {
        "latest_month": latest.strftime("%Y-%m"),
        "headline_index": val("Malaysia", "overall", latest_key),
        "headline_yoy_pct": pct(val("Malaysia", "overall", latest_key), val("Malaysia", "overall", year_ago)),
        "headline_mom_pct": pct(val("Malaysia", "overall", latest_key), val("Malaysia", "overall", month_ago)),
        "headline_since_dec2019_pct": pct(val("Malaysia", "overall", latest_key), val("Malaysia", "overall", pre)),
        "division_yoy_pct": {names[c]: pct(val("Malaysia", c, latest_key), val("Malaysia", c, year_ago)) for c in divisions},
        "state_overall_yoy_pct": {s: pct(val(s, "overall", latest_key), val(s, "overall", year_ago)) for s in states},
        "state_food_yoy_pct": {s: pct(val(s, "01", latest_key), val(s, "01", year_ago)) for s in states},
    }
    classes = cat[cat.Level == "Class"].CategoryKey.tolist()
    since = {names[c]: pct(val("Malaysia", c, latest_key), val("Malaysia", c, pre)) for c in classes}
    since = {k: v for k, v in since.items() if v is not None}
    ranked = sorted(since.items(), key=lambda kv: kv[1], reverse=True)
    out["class_since_dec2019_top5"] = dict(ranked[:5])
    out["class_since_dec2019_bottom5"] = dict(ranked[-5:][::-1])
    out["highest_state_overall_yoy"] = max(out["state_overall_yoy_pct"].items(), key=lambda kv: kv[1] or -99)
    out["lowest_state_overall_yoy"] = min(out["state_overall_yoy_pct"].items(), key=lambda kv: kv[1] if kv[1] is not None else 99)
    out["rows"] = {"FactCPI": int(len(f)), "DimDate": int(len(dates)), "DimCategory": int(len(cat)), "DimGeography": len(STATES)}
    return out


def main() -> None:
    data = load()
    cat = dim_category(data["lookup"])
    geo = dim_geography()
    f = fact(data)
    dates = dim_date(pd.to_datetime(str(f.DateKey.min())), pd.to_datetime(str(f.DateKey.max())))
    f = f[f.CategoryKey.isin(cat.CategoryKey)]
    MODEL.mkdir(parents=True, exist_ok=True)
    f.to_csv(MODEL / "FactCPI.csv", index=False, lineterminator="\n")
    cat.to_csv(MODEL / "DimCategory.csv", index=False, lineterminator="\n")
    geo.to_csv(MODEL / "DimGeography.csv", index=False, lineterminator="\n")
    dates.assign(Date=dates.Date.dt.strftime("%Y-%m-%d")).to_csv(MODEL / "DimDate.csv", index=False, lineterminator="\n")
    # One workbook, four sheets: a single Get Data step in Power BI Desktop. Dates as
    # ISO text so the Excel connector types them as dates rather than serial numbers.
    with pd.ExcelWriter(MODEL / "basket.xlsx", engine="openpyxl") as xw:
        f.to_excel(xw, sheet_name="FactCPI", index=False)
        dates.assign(Date=dates.Date.dt.strftime("%Y-%m-%d")).to_excel(xw, sheet_name="DimDate", index=False)
        cat.to_excel(xw, sheet_name="DimCategory", index=False)
        geo.to_excel(xw, sheet_name="DimGeography", index=False)
    exp = expected(f, cat, dates)
    (MODEL / "expected.json").write_text(json.dumps(exp, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"FactCPI {len(f):,} rows · DimDate {len(dates)} · DimCategory {len(cat)} · DimGeography {len(geo)}")
    print(f"latest {exp['latest_month']}: headline {exp['headline_index']} · YoY {exp['headline_yoy_pct']}% · MoM {exp['headline_mom_pct']}% · since Dec 2019 {exp['headline_since_dec2019_pct']}%")


if __name__ == "__main__":
    main()
