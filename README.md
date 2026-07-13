# Facility Maintenance Dashboard (Prototype)
**Stack:** Python (Pandas) for data generation/cleaning/KPI calc → CSV → Power BI for visualization

---

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

---

## 1. Project Structure

```
facility-maintenance-dashboard/
├── scripts/
│   ├── 01_generate_data.py   # สร้าง synthetic dataset (dim + fact tables)
│   └── 02_etl_kpi.py         # clean data + คำนวณ KPI ทุกหน้า -> CSV
├── data/                      # output CSV ทั้งหมด (import เข้า Power BI ตรงนี้)
└── powerbi/                   # เก็บไฟล์ .pbix ที่คุณสร้างต่อใน Power BI Desktop
```

Dataset ที่สร้าง: **100 Assets, 500 Work Orders, 20 Vendors, 10 Technicians, 5 Buildings**
(ปรับ seed/จำนวนได้ที่ต้นสคริปต์ `01_generate_data.py`)

---

## 2. Data Model (Star Schema) สำหรับ Power BI

```
                dim_buildings ─┐
                                ├──< fact_workorders >──┐
dim_assets ────────────────────┘                        ├── dim_technicians
                                                          └── dim_vendors
dim_budget ── (BuildingID + Month) ── budget_vs_actual.csv (pre-joined)
```

**ขั้นตอนใน Power BI Desktop:**
1. `Get Data → Text/CSV` → import ทุกไฟล์ใน `data/`
2. ไปที่ **Model view** สร้างความสัมพันธ์ (relationships):
   - `dim_assets[AssetID]` 1 → * `fact_workorders[AssetID]`
   - `dim_buildings[BuildingID]` 1 → * `dim_assets[BuildingID]`
   - `dim_buildings[BuildingID]` 1 → * `fact_workorders[BuildingID]`
   - `dim_technicians[TechnicianID]` 1 → * `fact_workorders[TechnicianID]`
   - `dim_vendors[VendorID]` 1 → * `fact_workorders[VendorID]`
3. ตารางที่ผมคำนวณ KPI ไว้ล่วงหน้าแล้ว (เช่น `kpi_executive_summary.csv`, `technician_performance.csv`) **ไม่ต้อง join กับอะไร** — ใช้เป็น standalone table ลาก field ขึ้น card/chart ได้เลย เพื่อลดจำนวน DAX ที่ต้องเขียนเอง (ตามที่ขอไว้ว่า Python จัดการ KPI ให้เสร็จ)

---

## 3. Page-by-Page Design

### Page 1 — Executive Dashboard
Source: `kpi_executive_summary.csv` (single row) + `kpi_monthly_trend.csv`

| Visual | Field |
|---|---|
| 9x Card | Total Assets, Active WO, PM Completion %, CM %, Availability %, MTTR, MTBF, Cost Total, Overdue WO |
| Line chart | `kpi_monthly_trend`: Month (x) vs WorkOrderCount / TotalCost / PM_Completion_Pct |
| KPI conditional formatting | ตั้ง data bar/สีแดง-เขียวบน card ที่ Overdue WO และ Availability % |

Optional DAX (ถ้าอยากทำ dynamic filter ตามช่วงเวลาแทนค่าตายตัวจาก Python):
```DAX
MTTR (dynamic) = AVERAGEX(FILTER(fact_workorders, fact_workorders[Status]="Closed" && fact_workorders[WOType] IN {"CM","Emergency"}), fact_workorders[RepairTimeHours])
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

## 4. KPI Formulas (คำนวณไว้แล้วใน `02_etl_kpi.py`)

| KPI | สูตร |
|---|---|
| PM Completion % | closed PM WO ÷ total PM WO × 100 |
| CM % | CM WO count ÷ total WO count × 100 |
| MTTR | mean(RepairTimeHours) ของ WO ที่ Closed และเป็น CM/Emergency |
| MTBF | mean(operating hours ÷ จำนวน failure) ต่อ asset ที่เคย fail |
| Asset Availability % | 1 − (total downtime hours ÷ total possible operating hours ในช่วงวิเคราะห์) |
| Overdue WO | WO ที่ยังไม่ Closed และเลย DueDate |

---

## 5. Next Steps
1. เปิด Power BI Desktop → import ไฟล์ทั้งหมดใน `data/`
2. สร้างความสัมพันธ์ตาม data model ด้านบน
3. สร้าง 5 หน้าตาม mapping ข้างต้น → save เป็น `powerbi/Facility-Maintenance-Dashboard.pbix`
4. (ถ้าต้องการ refresh ข้อมูลใหม่) รัน `python3 01_generate_data.py && python3 02_etl_kpi.py` แล้วกด Refresh ใน Power BI

> ต้องการ dataset ที่สมจริงขึ้น (เช่น seasonal failure pattern, cost inflation ตามปี) หรืออยากให้ผมช่วยเขียน DAX measure เพิ่มเติม (time intelligence, YoY) บอกได้เลยครับ
