"""
01_generate_data.py
--------------------
Generate synthetic facility-maintenance data:
  - 5 Buildings
  - 20 Vendors
  - 10 Technicians
  - 100 Assets  (AHU, Pump, Chiller, Lighting, Generator, Fire Pump, UPS)
  - 500 Work Orders (PM / CM / Emergency)

Output: CSV files in ../data/  (ready to be loaded into Power BI)
"""

import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

np.random.seed(42)
random.seed(42)

TODAY = datetime(2026, 7, 12)          # "as of" date used for age / overdue calcs
OUT_DIR = "../data"

# =========================================================
# 1) DIM: Buildings
# =========================================================
buildings = pd.DataFrame({
    "BuildingID": [f"BLD-{i:02d}" for i in range(1, 6)],
    "BuildingName": ["Head Office", "Plant A", "Plant B", "Warehouse", "Data Center"],
    "Location": ["Bangkok", "Rayong", "Chonburi", "Samut Prakan", "Bangkok"],
})

# =========================================================
# 2) DIM: Vendors
# =========================================================
vendor_types = ["HVAC", "Electrical", "Fire Safety", "Power/UPS", "Mechanical", "General"]
vendor_prefix = ["Siam", "Thai", "Asia", "Central", "National", "Union", "Premier", "Best", "Metro", "Delta"]

vendors = pd.DataFrame({
    "VendorID": [f"VEN-{i:02d}" for i in range(1, 21)],
})
vendors["ServiceType"] = [random.choice(vendor_types) for _ in range(20)]
vendors["VendorName"] = [f"{random.choice(vendor_prefix)} {t} Services" for t in vendors["ServiceType"]]
vendors["Rating"] = np.round(np.random.uniform(3.0, 5.0, 20), 1)
vendors["ContractStartDate"] = [
    (datetime(2022, 1, 1) + timedelta(days=random.randint(0, 700))).date() for _ in range(20)
]

# =========================================================
# 3) DIM: Technicians
# =========================================================
tech_names = ["Somchai", "Suda", "Anan", "Kanya", "Prasert",
              "Malee", "Wichai", "Nid", "Somsak", "Aree"]
specialties = ["HVAC", "Electrical", "Mechanical", "Fire Safety", "Power/UPS"]

technicians = pd.DataFrame({
    "TechnicianID": [f"TECH-{i:02d}" for i in range(1, 11)],
    "TechnicianName": tech_names,
    "Specialty": [random.choice(specialties) for _ in range(10)],
    "HireDate": [(datetime(2018, 1, 1) + timedelta(days=random.randint(0, 2500))).date() for _ in range(10)],
})

# =========================================================
# 4) DIM: Assets
# =========================================================
asset_types = ["AHU", "Pump", "Chiller", "Lighting", "Generator", "Fire Pump", "UPS"]
life_years_map = {"AHU": 15, "Pump": 12, "Chiller": 20, "Lighting": 8,
                   "Generator": 25, "Fire Pump": 20, "UPS": 10}
cost_range_map = {"AHU": (150000, 400000), "Pump": (50000, 150000), "Chiller": (800000, 2500000),
                   "Lighting": (5000, 20000), "Generator": (500000, 1500000),
                   "Fire Pump": (300000, 700000), "UPS": (200000, 600000)}

asset_rows = []
for i in range(1, 101):
    atype = random.choice(asset_types)
    life = life_years_map[atype]
    install_date = TODAY - timedelta(days=random.randint(180, int(life * 365 * 1.1)))
    age_years = (TODAY - install_date).days / 365
    remaining_life = max(life - age_years, 0)
    ratio = remaining_life / life

    if ratio > 0.6:
        condition, risk = "Good", "Low"
    elif ratio > 0.35:
        condition, risk = "Fair", "Medium"
    elif ratio > 0.15:
        condition, risk = "Poor", "High"
    else:
        condition, risk = "Critical", "Critical"

    planned_replacement = install_date + timedelta(days=int(life * 365))
    cost = random.randint(*cost_range_map[atype])

    asset_rows.append({
        "AssetID": f"AST-{i:03d}",
        "AssetType": atype,
        "BuildingID": random.choice(buildings["BuildingID"]),
        "InstallationDate": install_date.date(),
        "ExpectedLifeYears": life,
        "AgeYears": round(age_years, 1),
        "RemainingLifeYears": round(remaining_life, 1),
        "CurrentCondition": condition,
        "RiskLevel": risk,
        "PlannedReplacementDate": planned_replacement.date(),
        "PurchaseCost": cost,
    })

assets = pd.DataFrame(asset_rows)

# =========================================================
# 5) FACT: Work Orders
# =========================================================
wo_types = ["PM", "CM", "Emergency"]
wo_type_weights = [0.55, 0.30, 0.15]
statuses = ["Open", "In Progress", "Closed"]
status_weights = [0.10, 0.15, 0.75]

analysis_start = datetime(2025, 1, 1)
analysis_days = (TODAY - analysis_start).days

# --- Seasonal pattern config -----------------------------------------
# Thailand hot season (Mar-May) drives higher chiller/AHU cooling-load
# failures. Weight = relative likelihood a CM/Emergency WO for that
# asset type lands in a given calendar month (1.0 = baseline).
SEASONAL_MONTH_WEIGHT = {
    "Chiller":  {1: 0.6, 2: 0.8, 3: 2.4, 4: 2.8, 5: 2.2, 6: 1.2,
                 7: 0.9, 8: 0.8, 9: 0.7, 10: 0.6, 11: 0.5, 12: 0.5},
    "AHU":      {1: 0.7, 2: 0.9, 3: 1.8, 4: 2.1, 5: 1.7, 6: 1.1,
                 7: 1.0, 8: 0.9, 9: 0.8, 10: 0.7, 11: 0.6, 12: 0.6},
}


def seasonal_created_date(asset_type, wtype):
    """Sample a CreatedDate; CM/Emergency on Chiller & AHU are skewed
    toward the hot season (Mar-May). All other WOs stay uniform."""
    weights_map = SEASONAL_MONTH_WEIGHT.get(asset_type)
    if wtype == "PM" or weights_map is None:
        return analysis_start + timedelta(days=random.randint(0, analysis_days))

    months = pd.period_range(analysis_start, TODAY, freq="M")
    w = [weights_map[m.month] for m in months]
    chosen_month = random.choices(months, weights=w)[0]
    month_start = chosen_month.to_timestamp()
    month_end = min(chosen_month.to_timestamp(how="end"), TODAY)
    day_offset = random.randint(0, max((month_end - month_start).days, 0))
    return month_start + timedelta(days=day_offset)


wo_rows = []
for i in range(1, 501):
    asset = assets.sample(1).iloc[0]
    wtype = random.choices(wo_types, wo_type_weights)[0]
    created = seasonal_created_date(asset["AssetType"], wtype)

    response_hours = round(np.random.exponential(4) + (0.5 if wtype == "Emergency" else 2), 1)
    if wtype == "Emergency":
        repair_hours = round(np.random.exponential(6) + 2, 1)
    elif wtype == "CM":
        repair_hours = round(np.random.exponential(10) + 4, 1)
    else:
        repair_hours = round(np.random.exponential(3) + 1, 1)

    status = random.choices(statuses, status_weights)[0]
    if (TODAY - created).days < 3:
        status = random.choice(["Open", "In Progress"])

    completed = None
    if status == "Closed":
        completed = created + timedelta(hours=response_hours + repair_hours)

    priority = "High" if wtype == "Emergency" else random.choice(["Medium", "Low", "Medium"])
    downtime_hours = repair_hours if wtype in ["CM", "Emergency"] else 0
    cost = round(random.uniform(1500, 8000) if wtype == "PM" else random.uniform(5000, 60000), 0)

    due_days = 3 if wtype == "Emergency" else (14 if wtype == "CM" else 30)
    due_date = created + timedelta(days=due_days)
    overdue = (status != "Closed") and (TODAY > due_date)

    wo_rows.append({
        "WorkOrderID": f"WO-{i:04d}",
        "AssetID": asset["AssetID"],
        "AssetType": asset["AssetType"],
        "BuildingID": asset["BuildingID"],
        "WOType": wtype,
        "Status": status,
        "Priority": priority,
        "CreatedDate": created.date(),
        "DueDate": due_date.date(),
        "ResponseTimeHours": response_hours,
        "RepairTimeHours": repair_hours,
        "CompletedDate": completed.date() if completed else None,
        "DowntimeHours": downtime_hours,
        "Cost": cost,
        "TechnicianID": random.choice(technicians["TechnicianID"]),
        "VendorID": random.choice(vendors["VendorID"]),
        "Overdue": overdue,
    })

work_orders = pd.DataFrame(wo_rows)

# =========================================================
# 6) DIM: Monthly Budget (for Budget vs Actual page)
# =========================================================
months = pd.date_range("2025-01-01", "2026-06-01", freq="MS")
budget_rows = []
for b in buildings["BuildingID"]:
    base_budget = random.randint(80000, 200000)
    for m in months:
        budget_rows.append({
            "BuildingID": b,
            "Month": m.strftime("%Y-%m"),
            "BudgetAmount": round(base_budget * random.uniform(0.9, 1.15), 0),
        })
budget = pd.DataFrame(budget_rows)

# =========================================================
# Save all raw tables
# =========================================================
buildings.to_csv(f"{OUT_DIR}/dim_buildings.csv", index=False)
vendors.to_csv(f"{OUT_DIR}/dim_vendors.csv", index=False)
technicians.to_csv(f"{OUT_DIR}/dim_technicians.csv", index=False)
assets.to_csv(f"{OUT_DIR}/dim_assets.csv", index=False)
work_orders.to_csv(f"{OUT_DIR}/fact_workorders.csv", index=False)
budget.to_csv(f"{OUT_DIR}/dim_budget.csv", index=False)

print("Generated:")
print(f"  Buildings   : {len(buildings)}")
print(f"  Vendors     : {len(vendors)}")
print(f"  Technicians : {len(technicians)}")
print(f"  Assets      : {len(assets)}")
print(f"  Work Orders : {len(work_orders)}")
print(f"  Budget rows : {len(budget)}")
