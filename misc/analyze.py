import argparse
import csv
from datetime import datetime, timedelta
from collections import defaultdict

class UnionFind:
    """Union-Find data structure for grouping user IDs connected by shared IPs."""
    def __init__(self):
        self.parent = {}

    def find(self, x):
        """Find the root representative of x's set with path compression."""
        if x not in self.parent:
            self.parent[x] = x
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # Path compression
        return self.parent[x]

    def union(self, x, y):
        """Merge the sets containing x and y, using lexicographic order."""
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x != root_y:
            # Merge by lexicographic order - smaller becomes parent
            if root_x < root_y:
                self.parent[root_y] = root_x
            else:
                self.parent[root_x] = root_y

    def get_canonical(self, x):
        """Get the canonical (lexicographically first) representative for x."""
        return self.find(x)

parser = argparse.ArgumentParser(description="Analyze deduplicated scan data")
parser.add_argument("-i", "--input", type=str, required=True, help="Input CSV file with deduplicated data")
parser.add_argument("-o", "--output", type=str, help="Output CSV file for results (optional)")
parser.add_argument("--from", dest="date_from", type=str, default="2025-01-01", help="Start date (YYYY-MM-DD). Default: 2025-01-01")
parser.add_argument("--to", dest="date_to", type=str, default="2026-01-01", help="End date (YYYY-MM-DD). Default: 2026-01-01")

args = parser.parse_args()

def parse_date_arg(date_str):
    """Parse date argument in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        print(f"Error: Invalid date format '{date_str}'. Expected YYYY-MM-DD")
        exit(1)

def parse_timestamp(ts_str):
    """Parse timestamp string to datetime object."""
    if not ts_str:
        return None
    try:
        return datetime.strptime(ts_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        try:
            return datetime.strptime(ts_str, '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            return None

def get_year_month(dt):
    """Get year-month string from datetime."""
    return f"{dt.year}-{dt.month:02d}"

def get_iso_week(dt):
    """Get ISO year-week string from datetime."""
    iso_cal = dt.isocalendar()
    return f"{iso_cal[0]}-W{iso_cal[1]:02d}"

def get_all_months_in_range(start_dt, end_dt):
    """Get all year-month strings between start and end dates."""
    if not start_dt or not end_dt:
        return []

    months = set()
    current = start_dt.replace(day=1)
    end_month = end_dt.replace(day=1)

    while current <= end_month:
        months.add(get_year_month(current))
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    return list(months)

def get_all_weeks_in_range(start_dt, end_dt):
    """Get all ISO year-week strings between start and end dates."""
    if not start_dt or not end_dt:
        return []

    weeks = set()
    current = start_dt

    while current <= end_dt:
        weeks.add(get_iso_week(current))
        current += timedelta(days=7)

    # Make sure we capture the end week
    weeks.add(get_iso_week(end_dt))

    return list(weeks)

def read_dedup_csv(filename):
    """Read the deduplicated CSV file."""
    with open(filename, 'r') as infile:
        csv_reader = csv.DictReader(infile)
        for row in csv_reader:
            yield row

def main():
    # Parse date filter arguments
    filter_start = parse_date_arg(args.date_from)
    filter_end = parse_date_arg(args.date_to)

    print(f"Date filter: {filter_start.strftime('%Y-%m-%d')} to {filter_end.strftime('%Y-%m-%d')}")

    # FIRST PASS: Build Union-Find structure for anonymous users
    print(f"\nFirst pass: Building IP-based user grouping from {args.input}...")

    uf = UnionFind()
    ip_to_users = defaultdict(set)  # Map IP -> set of user_ids that used this IP

    entry_count = 0
    for entry in read_dedup_csv(args.input):
        entry_count += 1
        if entry_count % 100000 == 0:
            print(f"  Processed {entry_count/1000}K entries...")

        user_id = entry.get('user_id', '')
        ip_addr = entry.get('ip_addr', '')

        # Only process anonymous users with valid IPs
        if user_id and user_id.startswith('client:local:') and ip_addr:
            ip_to_users[ip_addr].add(user_id)

    print(f"  Found {len(ip_to_users)} unique IPs used by anonymous users")

    # Build Union-Find by connecting all users that share an IP
    print(f"  Building transitive connections...")
    for ip, users in ip_to_users.items():
        users_list = list(users)
        # Connect all users on this IP
        for i in range(len(users_list) - 1):
            uf.union(users_list[i], users_list[i + 1])

    # Count unique groups
    unique_groups = len(set(uf.get_canonical(user) for user in uf.parent.keys()))
    print(f"  Grouped {len(uf.parent)} anonymous user IDs into {unique_groups} unique users (via transitive IP connections)")

    # SECOND PASS: Count statistics with canonical user IDs
    print(f"\nSecond pass: Analyzing statistics with canonical user IDs...")

    # Data structures for monthly and weekly stats
    # namespace -> month/week -> {"logged": set(), "anon_by_ip": set(), "anon_by_id": set()}
    # - logged: logged-in user_ids
    # - anon_by_ip: canonical user_ids (merged via transitive IP connections)
    # - anon_by_id: original unmerged user_ids (each session counted separately)
    monthly_stats = defaultdict(lambda: defaultdict(lambda: {"logged": set(), "anon_by_ip": set(), "anon_by_id": set()}))
    weekly_stats = defaultdict(lambda: defaultdict(lambda: {"logged": set(), "anon_by_ip": set(), "anon_by_id": set()}))

    # Overall namespace stats (across all time)
    namespace_stats = defaultdict(lambda: {"logged": set(), "anon_by_ip": set(), "anon_by_id": set()})

    entry_count = 0
    skipped_no_namespace = 0
    skipped_no_user = 0
    skipped_no_timestamp = 0
    skipped_outside_range = 0

    for entry in read_dedup_csv(args.input):
        entry_count += 1
        if entry_count % 100000 == 0:
            print(f"  Processed {entry_count/1000}K entries...")

        namespace = entry.get('namespace', '')
        user_id = entry.get('user_id', '')
        ip_addr = entry.get('ip_addr', '')
        created_at_str = entry.get('created_at', '')
        max_created_at_str = entry.get('max_created_at', '')

        if not namespace:
            skipped_no_namespace += 1
            continue

        if not user_id:
            skipped_no_user += 1
            continue

        # Parse timestamps to get date range
        start_dt = parse_timestamp(created_at_str)
        end_dt = parse_timestamp(max_created_at_str) if max_created_at_str else start_dt

        if not start_dt:
            skipped_no_timestamp += 1
            continue

        # If no end date, use start date
        if not end_dt:
            end_dt = start_dt

        # Check if entry is completely outside the filter range
        if end_dt < filter_start or start_dt > filter_end:
            skipped_outside_range += 1
            continue

        # Clip the date range to the filter bounds
        clipped_start = max(start_dt, filter_start)
        clipped_end = min(end_dt, filter_end)

        # Get all months and weeks in the clipped range
        months = get_all_months_in_range(clipped_start, clipped_end)
        weeks = get_all_weeks_in_range(clipped_start, clipped_end)

        # Determine if user is anonymous or logged in
        is_anonymous = user_id.startswith('client:local:')

        # Update stats for both specific namespace and "all" namespace
        namespaces_to_update = [namespace, "all"]

        for ns in namespaces_to_update:
            # Update monthly stats for all months in range
            for month in months:
                if is_anonymous:
                    # For anon_by_ip: use canonical (merged) user_id
                    canonical_user = uf.get_canonical(user_id)
                    monthly_stats[ns][month]["anon_by_ip"].add(canonical_user)
                    # For anon_by_id: use original user_id (unmerged count)
                    monthly_stats[ns][month]["anon_by_id"].add(user_id)
                else:
                    monthly_stats[ns][month]["logged"].add(user_id)

            # Update weekly stats for all weeks in range
            for week in weeks:
                if is_anonymous:
                    # For anon_by_ip: use canonical (merged) user_id
                    canonical_user = uf.get_canonical(user_id)
                    weekly_stats[ns][week]["anon_by_ip"].add(canonical_user)
                    # For anon_by_id: use original user_id (unmerged count)
                    weekly_stats[ns][week]["anon_by_id"].add(user_id)
                else:
                    weekly_stats[ns][week]["logged"].add(user_id)

            # Update overall namespace stats
            if is_anonymous:
                # For anon_by_ip: use canonical (merged) user_id
                canonical_user = uf.get_canonical(user_id)
                namespace_stats[ns]["anon_by_ip"].add(canonical_user)
                # For anon_by_id: use original user_id (unmerged count)
                namespace_stats[ns]["anon_by_id"].add(user_id)
            else:
                namespace_stats[ns]["logged"].add(user_id)

    print(f"\nProcessed {entry_count} total entries")
    if skipped_no_namespace > 0:
        print(f"Warning: Skipped {skipped_no_namespace} entries with missing namespace")
    if skipped_no_user > 0:
        print(f"Warning: Skipped {skipped_no_user} entries with missing user_id")
    if skipped_no_timestamp > 0:
        print(f"Warning: Skipped {skipped_no_timestamp} entries with missing/invalid created_at")
    if skipped_outside_range > 0:
        print(f"Info: Skipped {skipped_outside_range} entries outside date filter range")
    print()

    # Prepare results for CSV output
    results = []

    # Print and collect results - sort namespaces with "all" first
    all_namespaces = sorted(monthly_stats.keys())
    if "all" in all_namespaces:
        all_namespaces.remove("all")
        all_namespaces = ["all"] + all_namespaces

    for namespace in all_namespaces:
        print(f"\n{'='*80}")
        print(f"Namespace: {namespace}")
        print(f"{'='*80}")

        # Overall namespace stats
        logged_total = len(namespace_stats[namespace]["logged"])
        anon_by_ip_total = len(namespace_stats[namespace]["anon_by_ip"])
        anon_by_id_total = len(namespace_stats[namespace]["anon_by_id"])
        # Two total calculations
        total_by_ip = logged_total + anon_by_ip_total  # Using transitive IP merging
        total_by_id = logged_total + anon_by_id_total  # Using unmerged session IDs

        print(f"\nOverall Stats:")
        print(f"  Total unique users (by transitive IP): {total_by_ip}")
        print(f"  Total unique users (by ID): {total_by_id}")
        print(f"  - Logged in users: {logged_total}")
        print(f"  - Anonymous users (by IP, merged via transitive connections): {anon_by_ip_total}")
        print(f"  - Anonymous users (by ID, unmerged sessions): {anon_by_id_total}")

        results.append({
            "namespace": namespace,
            "timespan_type": "total_by_ip",
            "timespan": "TOTAL",
            "total_by_ip": total_by_ip,
            "total_by_id": total_by_id,
            "logged_users": logged_total,
            "anon_by_ip": anon_by_ip_total,
            "anon_by_id": anon_by_id_total
        })

        results.append({
            "namespace": namespace,
            "timespan_type": "total_by_id",
            "timespan": "TOTAL",
            "total_by_ip": total_by_ip,
            "total_by_id": total_by_id,
            "logged_users": logged_total,
            "anon_by_ip": anon_by_ip_total,
            "anon_by_id": anon_by_id_total
        })

        # Monthly breakdown
        print(f"\nMonthly Breakdown:")
        print(f"  {'Month':<12} {'Tot(IP)':>10} {'Tot(ID)':>10} {'Logged':>10} {'Anon(IP)':>11} {'Anon(ID)':>11}")
        print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*11} {'-'*11}")

        for month in sorted(monthly_stats[namespace].keys()):
            logged_count = len(monthly_stats[namespace][month]["logged"])
            anon_by_ip_count = len(monthly_stats[namespace][month]["anon_by_ip"])
            anon_by_id_count = len(monthly_stats[namespace][month]["anon_by_id"])
            total_by_ip_count = logged_count + anon_by_ip_count
            total_by_id_count = logged_count + anon_by_id_count

            print(f"  {month:<12} {total_by_ip_count:>10} {total_by_id_count:>10} {logged_count:>10} {anon_by_ip_count:>11} {anon_by_id_count:>11}")

            results.append({
                "namespace": namespace,
                "timespan_type": "month",
                "timespan": month,
                "total_by_ip": total_by_ip_count,
                "total_by_id": total_by_id_count,
                "logged_users": logged_count,
                "anon_by_ip": anon_by_ip_count,
                "anon_by_id": anon_by_id_count
            })

        # Weekly breakdown
        print(f"\nWeekly Breakdown:")
        print(f"  {'Week':<12} {'Tot(IP)':>10} {'Tot(ID)':>10} {'Logged':>10} {'Anon(IP)':>11} {'Anon(ID)':>11}")
        print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*11} {'-'*11}")

        for week in sorted(weekly_stats[namespace].keys()):
            logged_count = len(weekly_stats[namespace][week]["logged"])
            anon_by_ip_count = len(weekly_stats[namespace][week]["anon_by_ip"])
            anon_by_id_count = len(weekly_stats[namespace][week]["anon_by_id"])
            total_by_ip_count = logged_count + anon_by_ip_count
            total_by_id_count = logged_count + anon_by_id_count

            print(f"  {week:<12} {total_by_ip_count:>10} {total_by_id_count:>10} {logged_count:>10} {anon_by_ip_count:>11} {anon_by_id_count:>11}")

            results.append({
                "namespace": namespace,
                "timespan_type": "week",
                "timespan": week,
                "total_by_ip": total_by_ip_count,
                "total_by_id": total_by_id_count,
                "logged_users": logged_count,
                "anon_by_ip": anon_by_ip_count,
                "anon_by_id": anon_by_id_count
            })

    # Write to output file if specified
    if args.output:
        with open(args.output, 'w', newline='') as outfile:
            fieldnames = ['namespace', 'timespan_type', 'timespan', 'total_by_ip', 'total_by_id', 'logged_users', 'anon_by_ip', 'anon_by_id']
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        print(f"\nResults written to {args.output}")

if __name__ == "__main__":
    main()
