class CostEstimator:
    def __init__(self):
        # Build Cost Assumptions (In-house OSS Stack)
        self.build_storage_cost_per_gb = 0.05  # $0.05 per GB/month (EBS/S3 mix)
        self.build_network_cost_per_gb = 0.02  # $0.02 per GB cross-AZ/Ingress
        self.build_compute_vm_cost = 150.0     # $150 per average VM
        self.build_metric_bytes_per_point = 2  # 2 bytes per metric point (TSDB compression)
        
        # Buy Cost Assumptions (Datadog SaaS - simplified)
        self.buy_apm_per_host = 40.0           # $40 per host/month (APM + Infra)
        self.buy_hosts_per_service = 3         # Average 3 hosts per service
        self.buy_log_cost_per_gb = 1.50        # $1.50 per GB ingested & retained (15 days)
        # Custom metrics pricing: $0.05 per 10 custom metrics. 
        # Assume 100K eps translates to ~1M active custom metrics. -> 100k eps = $5000/mo
        self.buy_metric_cost_per_100k_eps = 5000.0 

        # Ops Cost (FTE) - $10,000 per FTE/month
        self.fte_cost = 10000.0

    def estimate_build_cost(self, services, log_gb_day, metric_eps):
        # 1. Storage
        log_storage_gb = log_gb_day * 30
        metric_points_per_month = metric_eps * 86400 * 30
        metric_storage_gb = (metric_points_per_month * self.build_metric_bytes_per_point) / (1024**3)
        total_storage_gb = log_storage_gb + metric_storage_gb
        
        storage_cost = total_storage_gb * self.build_storage_cost_per_gb
        
        # 2. Compute (Estimate 1 VM per 20GB/day log + 1 VM per 50k eps)
        vms_needed = (log_gb_day / 20.0) + (metric_eps / 50000.0)
        compute_cost = vms_needed * self.build_compute_vm_cost
        
        # 3. Network
        network_cost = total_storage_gb * self.build_network_cost_per_gb
        
        # 4. Ops overhead
        if services <= 50:
            ops_fte = 0.5  # Part-time DevOps
        elif services <= 500:
            ops_fte = 1.5  # 1.5 Platform Engineers
        else:
            ops_fte = 4.0  # Dedicated observability team
        ops_cost = ops_fte * self.fte_cost

        total_cost = storage_cost + compute_cost + network_cost + ops_cost
        
        return {
            "Storage": storage_cost,
            "Compute": compute_cost,
            "Network": network_cost,
            "Ops": ops_cost,
            "Total": total_cost
        }

    def estimate_buy_cost(self, services, log_gb_day, metric_eps):
        # 1. APM / Hosts
        hosts = services * self.buy_hosts_per_service
        apm_cost = hosts * self.buy_apm_per_host
        
        # 2. Logs
        log_gb_month = log_gb_day * 30
        log_cost = log_gb_month * self.buy_log_cost_per_gb
        
        # 3. Metrics
        metric_cost = (metric_eps / 100000.0) * self.buy_metric_cost_per_100k_eps
        
        # Ops overhead for SaaS is much lower
        ops_fte = 0.1 if services <= 50 else (0.3 if services <= 500 else 0.5)
        ops_cost = ops_fte * self.fte_cost

        total_cost = apm_cost + log_cost + metric_cost + ops_cost
        
        return {
            "APM & Compute": apm_cost,
            "Logs": log_cost,
            "Metrics": metric_cost,
            "Ops": ops_cost,
            "Total": total_cost
        }


def print_tier_comparison(tier_name, specs, build_cost, buy_cost):
    print(f"{'='*60}")
    print(f"Tier: {tier_name} ({specs['services']} Services, {specs['log_gb_day']} GB Log/day, {specs['metric_eps']:,} EPS Metric)")
    print(f"{'-'*60}")
    
    print(f"{'Category':<20} | {'Build (In-house OSS)':<20} | {'Buy (Datadog SaaS)':<20}")
    print(f"{'-'*60}")
    
    categories = [("Compute / APM", "Compute", "APM & Compute"),
                  ("Storage / Logs", "Storage", "Logs"),
                  ("Network / Metrics", "Network", "Metrics"),
                  ("Ops Overhead", "Ops", "Ops")]
                  
    for label, build_key, buy_key in categories:
        build_val = f"${build_cost[build_key]:,.2f}"
        buy_val = f"${buy_cost[buy_key]:,.2f}"
        print(f"{label:<20} | {build_val:<20} | {buy_val:<20}")
        
    print(f"{'-'*60}")
    total_build = f"${build_cost['Total']:,.2f}"
    total_buy = f"${buy_cost['Total']:,.2f}"
    print(f"{'TOTAL MONTHLY COST':<20} | {total_build:<20} | {total_buy:<20}")
    
    # Conclusion
    savings = buy_cost['Total'] - build_cost['Total']
    multiplier = buy_cost['Total'] / build_cost['Total'] if build_cost['Total'] > 0 else 0
    print(f"\nConclusion: SaaS is {multiplier:.1f}x the cost of Build.")
    if savings > 0:
        print(f"Building in-house saves ${savings:,.2f} per month.")
    else:
        print(f"Buying SaaS saves ${-savings:,.2f} per month.")
    print(f"{'='*60}\n")


def main():
    tiers = {
        "Small": {"services": 10, "log_gb_day": 50, "metric_eps": 100_000},
        "Medium": {"services": 100, "log_gb_day": 500, "metric_eps": 1_000_000},
        "Large": {"services": 1000, "log_gb_day": 5000, "metric_eps": 10_000_000}
    }

    estimator = CostEstimator()

    for tier_name, specs in tiers.items():
        build_cost = estimator.estimate_build_cost(**specs)
        buy_cost = estimator.estimate_buy_cost(**specs)
        
        print_tier_comparison(tier_name, specs, build_cost, buy_cost)

if __name__ == "__main__":
    main()
