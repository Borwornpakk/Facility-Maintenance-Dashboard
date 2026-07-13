"""
02_etl_kpi.py
-------------
Load the raw dimension/fact tables, clean them, and calculate every KPI
needed for the 5 Power BI pages. Each output CSV maps to one visual group
so Power BI just needs to import + relate + drag fields (minimal DAX).

Outputs (in ../data/):
  kpi_executive_summary.csv     -> Page 1 (single-row KPI card values)
  kpi_monthly_trend.csv         -> Page 1 (trend line: cost / WO count / PM%)
  asset_lifecycle.csv           -> Page 2 (per-asset lifecycle detail)
  workorder_status_summary.csv  -> Page 3 (status/type counts)
  technician_performance.csv    -> Page 3
  vendor_performance.csv        -> Page 3
  cost_by_building.csv          -> Page 4
  cost_by_asset_type.csv        -> Page 4
  cost_by_vendor.csv            -> Page 4
  budget_vs_actual.csv          -> Page 4
  risk_dashboard.csv            -> Page 5 (critical/high-risk/overdue lists)
  risk_heatmap.csv              -> Page 5 (Building x AssetType matrix)
"""

import pandas as pd
import numpy as np

DATA = "../data"
TODAY = pd.Timestamp("2026-07-12")

# =========================================================
# LOAD + CLEAN
# =========================================================
buildings = pd.read_csv(f"{DATA}/dim_buildings.csv")
vendors = pd.read_csv(f"{DATA}/dim_vendors.csv")
technicians = pd.read_csv(f"{DATA}/dim_technicians.csv")
assets = pd.read_csv(f"{DATA}/dim_assets.csv", parse_dates=["InstallationDate", "PlannedReplacementDate"])
wo = pd.read_csv(f"{DATA}/fact_workorders.csv", parse_dates=["CreatedDate", "DueDate", "CompletedDate"])
budget = pd.read_csv(f"{DATA}/dim_budget.csv")

# basic cleaning: trim strings, drop dup WO ids, fill NA numeric with 0
for col in ["WOType", "Status", "Priority", "AssetType", "BuildingID"]:
    wo[col] = wo[col].astype(str).str.strip()
wo = wo.drop_duplicates(subset="WorkOrderID")
wo["Cost"] = wo["Cost"].fillna(0)
wo["Overdue"] = wo["Overdue"].astype(bool)

closed = wo[wo["Status"] == "Closed"].copy()
failures = wo[wo["WOType"].isin(["CM", "Emergency"])].copy()
closed_failures = closed[closed["WOType"].isin(["CM", "Emergency"])].copy()

# =========================================================
# PAGE 1: Executive Dashboard
# =========================================================
total_assets = len(assets)
active_wo = wo[wo["Status"].isin(["Open", "In Progress"])].shape[0]

pm_total = wo[wo["WOType"] == "PM"].shape[0]
pm_closed = closed[closed["WOType"] == "PM"].shape[0]
pm_completion_pct = round(pm_closed / pm_total * 100, 1) if pm_total else 0

cm_pct = round(wo[wo["WOType"] == "CM"].shape[0] / len(wo) * 100, 1)

mttr_hours = round(closed_failures["RepairTimeHours"].mean(), 1)

# MTBF: operating hours per asset / number of failures on that asset
asset_age_hours = (TODAY - assets["InstallationDate"]).dt.days * 24
fail_count_per_asset = failures.groupby("AssetID").size()
mtbf_df = pd.DataFrame({
    "AssetID": assets["AssetID"],
    "OperatingHours": asset_age_hours,
    "Failures": assets["AssetID"].map(fail_count_per_asset).fillna(0),
})
mtbf_df = mtbf_df[mtbf_df["Failures"] > 0]
mtbf_hours = round((mtbf_df["OperatingHours"] / mtbf_df["Failures"]).mean(), 0)

# Asset availability over analysis period (2025-01-01 to today)
period_hours = (TODAY - pd.Timestamp("2025-01-01")).days * 24 * total_assets
total_downtime = wo["DowntimeHours"].sum()
availability_pct = round((1 - total_downtime / period_hours) * 100, 2)

maintenance_cost_total = round(wo["Cost"].sum(), 0)
overdue_wo = int(wo["Overdue"].sum())

exec_summary = pd.DataFrame([{
    "TotalAssets": total_assets,
    "ActiveWorkOrders": active_wo,
    "PM_Completion_Pct": pm_completion_pct,
    "CM_Pct": cm_pct,
    "AssetAvailability_Pct": availability_pct,
    "MTTR_Hours": mttr_hours,
    "MTBF_Hours": mtbf_hours,
    "MaintenanceCostTotal": maintenance_cost_total,
    "OverdueWorkOrders": overdue_wo,
}])
exec_summary.to_csv(f"{DATA}/kpi_executive_summary.csv", index=False)

# monthly trend (cost, WO count, PM completion %) for the KPI trend chart
wo["Month"] = wo["CreatedDate"].dt.to_period("M").astype(str)
monthly = wo.groupby("Month").agg(
    WorkOrderCount=("WorkOrderID", "count"),
    TotalCost=("Cost", "sum"),
).reset_index()
monthly_pm = wo[wo["WOType"] == "PM"].groupby("Month").apply(
    lambda d: round((d["Status"] == "Closed").mean() * 100, 1)
).reset_index(name="PM_Completion_Pct")
monthly_trend = monthly.merge(monthly_pm, on="Month", how="left").sort_values("Month")
monthly_trend.to_csv(f"{DATA}/kpi_monthly_trend.csv", index=False)

# =========================================================
# PAGE 2: Asset Lifecycle
# =========================================================
asset_lifecycle = assets.merge(buildings, on="BuildingID", how="left")
asset_lifecycle = asset_lifecycle[[
    "AssetID", "AssetType", "BuildingName", "InstallationDate", "ExpectedLifeYears",
    "AgeYears", "RemainingLifeYears", "CurrentCondition", "RiskLevel", "PlannedReplacementDate",
    "PurchaseCost",
]]
asset_lifecycle.to_csv(f"{DATA}/asset_lifecycle.csv", index=False)

# =========================================================
# PAGE 3: Work Order Dashboard
# =========================================================
status_summary = wo.groupby(["WOType", "Status"]).size().reset_index(name="Count")
status_summary.to_csv(f"{DATA}/workorder_status_summary.csv", index=False)

tech_perf = wo.merge(technicians, on="TechnicianID", how="left").groupby(
    ["TechnicianID", "TechnicianName", "Specialty"]
).agg(
    WorkOrdersHandled=("WorkOrderID", "count"),
    AvgResponseTimeHours=("ResponseTimeHours", "mean"),
    AvgResolutionTimeHours=("RepairTimeHours", "mean"),
).reset_index()
tech_perf[["AvgResponseTimeHours", "AvgResolutionTimeHours"]] = tech_perf[
    ["AvgResponseTimeHours", "AvgResolutionTimeHours"]
].round(1)
tech_perf.to_csv(f"{DATA}/technician_performance.csv", index=False)

vendor_perf = wo.merge(vendors, on="VendorID", how="left").groupby(
    ["VendorID", "VendorName", "ServiceType", "Rating"]
).agg(
    WorkOrdersHandled=("WorkOrderID", "count"),
    AvgCost=("Cost", "mean"),
    AvgResolutionTimeHours=("RepairTimeHours", "mean"),
).reset_index()
vendor_perf[["AvgCost", "AvgResolutionTimeHours"]] = vendor_perf[
    ["AvgCost", "AvgResolutionTimeHours"]
].round(1)
vendor_perf.to_csv(f"{DATA}/vendor_performance.csv", index=False)

# =========================================================
# PAGE 4: Maintenance Cost
# =========================================================
cost_by_building = wo.merge(buildings, on="BuildingID").groupby("BuildingName")["Cost"].sum().round(0).reset_index()
cost_by_building.to_csv(f"{DATA}/cost_by_building.csv", index=False)

cost_by_asset_type = wo.groupby("AssetType")["Cost"].sum().round(0).reset_index()
cost_by_asset_type.to_csv(f"{DATA}/cost_by_asset_type.csv", index=False)

cost_by_vendor = wo.merge(vendors, on="VendorID").groupby("VendorName")["Cost"].sum().round(0).reset_index()
cost_by_vendor.to_csv(f"{DATA}/cost_by_vendor.csv", index=False)

actual_by_month_building = wo.merge(buildings, on="BuildingID").groupby(
    ["BuildingID", "Month"]
)["Cost"].sum().reset_index().rename(columns={"Cost": "ActualCost"})
budget_vs_actual = budget.merge(actual_by_month_building, on=["BuildingID", "Month"], how="left")
budget_vs_actual["ActualCost"] = budget_vs_actual["ActualCost"].fillna(0).round(0)
budget_vs_actual = budget_vs_actual.merge(buildings, on="BuildingID")
budget_vs_actual["Variance"] = budget_vs_actual["BudgetAmount"] - budget_vs_actual["ActualCost"]
budget_vs_actual.to_csv(f"{DATA}/budget_vs_actual.csv", index=False)

# =========================================================
# PAGE 5: Risk Dashboard
# =========================================================
critical_assets = asset_lifecycle[asset_lifecycle["RiskLevel"] == "Critical"]
high_risk_assets = asset_lifecycle[asset_lifecycle["RiskLevel"].isin(["High", "Critical"])]

overdue_pm = wo[(wo["WOType"] == "PM") & (wo["Overdue"])]

repeat_failure_counts = failures.groupby("AssetID").size().reset_index(name="FailureCount")
repeated_failures = repeat_failure_counts[repeat_failure_counts["FailureCount"] >= 3].merge(
    asset_lifecycle[["AssetID", "AssetType", "BuildingName", "RiskLevel"]], on="AssetID", how="left"
)

risk_dashboard = asset_lifecycle.copy()
risk_dashboard["IsOverduePM"] = risk_dashboard["AssetID"].isin(overdue_pm["AssetID"])
risk_dashboard["FailureCount"] = risk_dashboard["AssetID"].map(
    repeat_failure_counts.set_index("AssetID")["FailureCount"]
).fillna(0).astype(int)
risk_dashboard["RepeatedFailureFlag"] = risk_dashboard["FailureCount"] >= 3
risk_dashboard.to_csv(f"{DATA}/risk_dashboard.csv", index=False)

# heatmap matrix: Building x AssetType -> avg risk score + WO cost (for Power BI matrix/heatmap visual)
risk_score_map = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
risk_dashboard["RiskScore"] = risk_dashboard["RiskLevel"].map(risk_score_map)
heatmap = risk_dashboard.groupby(["BuildingName", "AssetType"]).agg(
    AssetCount=("AssetID", "count"),
    AvgRiskScore=("RiskScore", "mean"),
).reset_index()
heatmap["AvgRiskScore"] = heatmap["AvgRiskScore"].round(2)
heatmap.to_csv(f"{DATA}/risk_heatmap.csv", index=False)

# =========================================================
# BONUS: Seasonal failure pattern (Chiller/AHU hot-season spike)
# =========================================================
failures["MonthNum"] = failures["CreatedDate"].dt.month
seasonal_pattern = failures.groupby(["AssetType", "MonthNum"]).size().reset_index(name="FailureCount")
month_names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
               7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
seasonal_pattern["MonthName"] = seasonal_pattern["MonthNum"].map(month_names)
seasonal_pattern = seasonal_pattern.sort_values(["AssetType", "MonthNum"])
seasonal_pattern.to_csv(f"{DATA}/seasonal_failure_pattern.csv", index=False)

print("KPI / summary tables written to ../data/")
print(exec_summary.to_string(index=False))
