## Project Overview

### What is this project?
A prototype **asset maintenance analytics dashboard** for a multi-building
facility portfolio. It covers the full data pipeline a real Facilities
Management (FM) team would need: raw maintenance records → cleaned data →
calculated KPIs → an interactive Power BI dashboard across five pages
(Executive Summary, Asset Lifecycle, Work Orders, Maintenance Cost, and
Risk). The dataset is synthetic (100 assets, 500 work orders, 20 vendors,
10 technicians, 5 buildings) but modeled on realistic facility-operations
patterns — including a seasonal spike in chiller/AHU failures during
Thailand's hot season (March–May).

### Why I built it
Facility and asset management roles increasingly expect engineers to be
comfortable working with maintenance data, not just physical equipment.
Most facility teams still run on spreadsheets or basic CMMS reports with
no real KPI visibility (MTTR, MTBF, PM compliance, budget variance). I
built this to demonstrate that I can:
- Translate operational maintenance activity into the KPIs that facility
  and asset managers actually get measured on.
- Design a **star-schema data model** (dimension + fact tables) the way
  a BI tool or CMMS database would structure it, rather than a single
  flat spreadsheet.
- Build the reporting layer end-to-end — from data generation and
  cleaning in Python to a multi-page executive dashboard — the same
  workflow used to report on Work Orders, contractor performance, and
  budget vs. actual spend in a real FM/property-services environment
  (e.g., the kind of reporting expected in an MSA-based facilities
  contract).

### Who this is useful for / use cases
- **Facilities / Building Engineers & Managers** — track PM compliance,
  overdue work orders, and asset condition across a building portfolio
  at a glance.
- **Asset Managers** — see remaining useful life, risk level, and planned
  replacement timing per asset type, to plan capex ahead of failures
  instead of reacting to them.
- **Client-facing FM teams (e.g., outsourced facility service providers)**
  — the Work Order and Vendor Performance pages mirror what's reported
  in monthly client review meetings under a Management Services
  Agreement (MSA): SLA adherence, response/resolution time, vendor cost.
- **Portfolio piece** — demonstrates practical data + reporting skills
  (Python/Pandas, KPI design, Power BI, DAX time intelligence) applied
  to a real facilities-management problem rather than a generic dataset.

### What I learned / practiced
- **Reliability KPI calculation**: implementing MTTR and MTBF correctly
  from raw timestamped event data (not just looking the formulas up —
  actually deriving operating-hours-per-failure logic per asset).
- **Star-schema data modeling**: structuring dimension tables (assets,
  buildings, vendors, technicians) and one fact table (work orders) so
  Power BI relationships and DAX measures work correctly, instead of
  building everything into one wide table.
- **Synthetic data design with realistic structure**: generating data
  that isn't just random noise — building in believable seasonality
  (chiller/AHU failures spiking in hot season), realistic status/type
  distributions, and overdue-work-order logic based on due dates.
- **Power BI time intelligence (DAX)**: writing YoY/MoM measures using
  `SAMEPERIODLASTYEAR`, `DATEADD`, and `DATESYTD` against a proper date
  table — a core BI skill for any KPI reporting role.
- **KPI-first thinking over chart-first thinking**: designing each
  dashboard page around *the decision it needs to support* (e.g., the
  Risk page exists to flag which assets need capex attention now) rather
  than picking visuals first and fitting data to them.

## How the Synthetic Dataset Was Generated

No real building data was available, so this project uses **Python**
(`pandas`, `numpy`, `random`) to generate a synthetic-but-realistic
facility maintenance dataset.

1. **Define target volume** — the scale was fixed upfront: 5 Buildings,
   20 Vendors, 10 Technicians, 100 Assets (7 types), 500 Work Orders
   (PM / CM / Emergency) — enough volume to make KPIs and charts
   meaningful without being unrealistically large.

2. **Build dimension tables first** — Buildings, Vendors, Technicians,
   and Assets are generated as independent tables, each with realistic
   attributes (e.g., expected lifespan per asset type, vendor service
   type, technician specialty).

3. **Generate the Work Order fact table** — each of the 500 Work Orders
   is created by randomly linking to an Asset, Technician, and Vendor,
   then assigning type, status, cost, and timestamps using **weighted**
   random distributions instead of pure uniform randomness. For example,
   55% of work orders are Preventive Maintenance (PM) to reflect
   realistic maintenance practice, and repair times follow an
   **exponential distribution** to mimic the real-world pattern of "most
   repairs are fast, a few take much longer."

4. **Add realistic constraints** — rules keep the data logically
   consistent: a Work Order can't be "Closed" before enough time has
   passed, overdue status is derived from due dates based on urgency
   (Emergency = 3 days, CM = 14 days, PM = 30 days), and Chiller/AHU
   failures are weighted toward Thailand's hot season (Mar–May).

5. **Export to CSV** — all tables are exported to `/data` as a **star
   schema** (dimension + fact tables), ready to import into Power BI and
   relate via `AssetID`, `BuildingID`, `VendorID`, and `TechnicianID`.

A fixed random seed (`42`) makes the dataset reproducible — re-running
`scripts/01_generate_data.py` produces the same data every time.

---

## 1. Project Structure

```
facility-maintenance-dashboard/
├── scripts/
│   ├── 01_generate_data.py   # create synthetic dataset (dim + fact tables)
│   └── 02_etl_kpi.py         # clean data + calculate KPI all pages -> CSV
├── data/                     # all output CSV (import to Power BI)
└── powerbi/                  
```

Dataset: **100 Assets, 500 Work Orders, 20 Vendors, 10 Technicians, 5 Buildings**

---

## 2. Data Model (Star Schema)

<img width="774" height="604" alt="DataModel" src="https://github.com/user-attachments/assets/1f81e827-7e34-4a9e-bede-37450bae89d4"/>


## 3. Page-by-Page Design

### Page 1 — Executive Dashboard
Source: `kpi_executive_summary.csv` (single row) + `kpi_monthly_trend.csv`

| Visual | Field |
|---|---|
| 9x Card | Total Assets, Active WO, PM Completion %, CM %, Availability %, MTTR, MTBF, Cost Total, Overdue WO |
| Line chart | `kpi_monthly_trend`: Month (x) vs WorkOrderCount / TotalCost / PM_Completion_Pct |
| KPI conditional formatting | ตั้ง data bar/สีแดง-เขียวบน card ที่ Overdue WO และ Availability % |

```

### Page 2 — Asset Lifecycle
Source: `asset_lifecycle.csv`

| Visual | Field |
|---|---|
| Slicer (buttons) | AssetType = AHU / Pump / Chiller / Lighting / Generator / Fire Pump / UPS |
| Table/Matrix | AssetID, InstallationDate, RemainingLifeYears, CurrentCondition, RiskLevel, PlannedReplacementDate |
| Gauge or bar | RemainingLifeYears vs ExpectedLifeYears ต่อ Asset |
| Scatter | AgeYears (x) vs RemainingLifeYears (y), สีตาม RiskLevel |

### Page 3 — Work Order Dashboard
Source: `workorder_status_summary.csv`, `technician_performance.csv`, `vendor_performance.csv`

| Visual | Field |
|---|---|
| Donut/Stacked bar | Status: Open / In Progress / Closed |
| Stacked bar | WOType: PM / CM / Emergency |
| Card | Avg(ResponseTimeHours), Avg(RepairTimeHours) จาก `fact_workorders` |
| Table | `technician_performance`: WorkOrdersHandled, AvgResponseTimeHours, AvgResolutionTimeHours |
| Table + bar | `vendor_performance`: WorkOrdersHandled, AvgCost, Rating |

### Page 4 — Maintenance Cost
Source: `cost_by_building.csv`, `cost_by_asset_type.csv`, `cost_by_vendor.csv`, `budget_vs_actual.csv`

| Visual | Field |
|---|---|
| Bar chart | Cost by BuildingName |
| Bar/Treemap | Cost by AssetType |
| Bar chart | Cost by VendorName |
| Combo chart (clustered column + line) | `budget_vs_actual`: Month (x), BudgetAmount (column), ActualCost (line), แยกตาม BuildingName |

### Page 5 — Risk Dashboard
Source: `risk_dashboard.csv`, `risk_heatmap.csv`

| Visual | Field |
|---|---|
| Card | Count of RiskLevel = "Critical" |
| Table | Overdue PM: filter `IsOverduePM = TRUE` |
| Table | High Risk Equipment: filter `RiskLevel IN {High, Critical}` |
| Table | Repeated Failures: filter `RepeatedFailureFlag = TRUE`, แสดง FailureCount |
| Matrix + conditional formatting (heatmap) | `risk_heatmap.csv`: rows=BuildingName, columns=AssetType, values=AvgRiskScore → ใช้ background color scale (เขียว→แดง) |

---

## 4. KPI Formulas 

| KPI | สูตร |
|---|---|
| PM Completion % | closed PM WO ÷ total PM WO × 100 |
| CM % | CM WO count ÷ total WO count × 100 |
| MTTR | mean(RepairTimeHours) ของ WO ที่ Closed และเป็น CM/Emergency |
| MTBF | mean(operating hours ÷ จำนวน failure) ต่อ asset ที่เคย fail |
| Asset Availability % | 1 − (total downtime hours ÷ total possible operating hours ในช่วงวิเคราะห์) |
| Overdue WO | WO ที่ยังไม่ Closed และเลย DueDate |

---
