#!/usr/bin/env python3
"""Cost model for evaluating AIOps platform business value and break-even point.

Usage:
    python cost_model.py
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Load default values from environment variables
ENV_AIOPS_COST = float(os.getenv("AIOPS_MONTHLY_COST", "15000"))
ENV_MTTR_REDUCTION = float(os.getenv("EXPECTED_MTTR_REDUCTION_PCT", "0.4"))
ENV_DOWNTIME_COST = float(os.getenv("DOWNTIME_COST_PER_HOUR", "0.0"))

def is_worth_it(
    num_services: int,
    incidents_per_month: int,
    avg_incident_duration_hours: float,
    downtime_cost_per_hour: float = ENV_DOWNTIME_COST,
    expected_mttr_reduction_pct: float = ENV_MTTR_REDUCTION,
    aiops_monthly_cost: float = ENV_AIOPS_COST,
) -> dict:
    """Calculates ROI, monthly value, payback period, and returns a business verdict.
    
    Verdict rules:
        roi > 1.5 -> "worth_it"
        1.0 < roi <= 1.5 -> "marginal"
        roi <= 1.0 -> "not_worth_it"
    """
    monthly_downtime_hours = incidents_per_month * avg_incident_duration_hours
    monthly_value = (
        monthly_downtime_hours
        * expected_mttr_reduction_pct
        * downtime_cost_per_hour
    )
    
    monthly_cost = float(aiops_monthly_cost)
    
    if monthly_cost > 0:
        roi = monthly_value / monthly_cost
    else:
        roi = float('inf')
        
    if monthly_value > 0:
        payback_months = monthly_cost / monthly_value
    else:
        payback_months = float('inf')
        
    if roi > 1.5:
        verdict = "worth_it"
    elif roi > 1.0:
        verdict = "marginal"
    else:
        verdict = "not_worth_it"
        
    return {
        "monthly_value": float(monthly_value),
        "monthly_cost": monthly_cost,
        "roi": float(roi),
        "payback_months": payback_months,
        "verdict": verdict
    }

if __name__ == "__main__":
    # Scenario 1 (Small SaaS/Internal Stack)
    print("Scenario 1 (20 services - Overridden parameters):")
    res1 = is_worth_it(
        num_services=20,
        incidents_per_month=2,
        avg_incident_duration_hours=1.0,
        downtime_cost_per_hour=10_000,
        aiops_monthly_cost=15_000
    )
    print(res1)
    print()

    # Scenario 2 (Medium scale enterprise)
    print("Scenario 2 (100 services - Overridden parameters):")
    res2 = is_worth_it(
        num_services=100,
        incidents_per_month=5,
        avg_incident_duration_hours=2.0,
        downtime_cost_per_hour=20_000,
        aiops_monthly_cost=25_000
    )
    print(res2)
    print()

    # Scenario 3: Medium-large E-Commerce Platform (Custom Scenario loaded from .env)
    # -------------------------------------------------------------------------------
    # Industry: Medium-large E-commerce (approx. $400M annual revenue)
    # Downtime cost defense:
    # 1. Direct sales loss: $400M / 365 / 24 = ~$45,600 revenue per hour.
    # 2. Marketing waste: paid search/ads continue driving traffic to a broken website, costing ~$2,000/hr.
    # 3. Customer support overhead: call centers flooded with checkout failure tickets, costing ~$1,500/hr.
    # 4. Indirect brand damage: cart abandonment, users leaving for competitors, costing ~$1,000/hr.
    # Total Downtime Cost = ~$50,000/hour (defined as DOWNTIME_COST_PER_HOUR in .env).
    print("Scenario 3 (Custom E-Commerce Platform - 150 services loaded from .env):")
    res3 = is_worth_it(
        num_services=150,
        incidents_per_month=6,
        avg_incident_duration_hours=1.5
        # downtime_cost_per_hour, expected_mttr_reduction_pct, and aiops_monthly_cost are loaded from .env
    )
    print(res3)
