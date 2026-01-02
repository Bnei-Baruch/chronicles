# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains two Python tools for Chronicles API data analysis:

1. **scan.py** - Fetches and optionally deduplicates event data from Chronicles API endpoint (https://chronicles.kli.one/scan)
2. **analyze.py** - Analyzes deduplicated data to calculate unique user statistics per namespace and month

The tools process large volumes of event logs (hundreds of millions of entries), with deduplication reducing data to millions of unique entries.

## Commands

### Scanning Data (scan.py)

```bash
# Normal mode - fetch and store all entries
python scan.py -c cache.csv -f "id,namespace,created_at,user_id,ip_addr"

# Unique mode - deduplicate by namespace and user_id
python scan.py -c unique_cache.csv -u "namespace,user_id" -f "id,namespace,created_at,user_id,ip_addr"

# The unique mode outputs: all FIELDS + COUNT + max_id + max_created_at
```

### Analyzing Data (analyze.py)

```bash
# Analyze deduplicated data and print to console (defaults to 2025-01-01 to 2026-01-01)
python analyze.py -i unique_cache.csv

# Save results to CSV
python analyze.py -i unique_cache.csv -o results.csv

# Analyze specific date range
python analyze.py -i unique_cache.csv --from 2024-01-01 --to 2024-12-31

# Analyze from a specific date to default end
python analyze.py -i unique_cache.csv --from 2024-06-01
```

### Dependencies

The script uses standard Python libraries:
- `requests` for API calls
- `csv` for data persistence
- `json` for request/response handling
- `datetime` for timestamp parsing
- `argparse` for CLI arguments

Install dependencies with: `pip install requests`

## Architecture

### scan.py - Data Collection & Deduplication

#### Core Components

1. **API Scanning (`scan` function)**
   - Makes POST requests to Chronicles API with pagination
   - Fetches up to 50,000 entries per request (configurable via LIMIT)
   - Filters for specific event types: "player-play" and "download"
   - Includes retry logic (3 attempts) for failed JSON decoding
   - Uses entry ID for pagination cursor

2. **Normal Mode**
   - `process_entry()` - Tracks visit statistics by namespace/date
   - `flush_entries()` - Appends entries to CSV incrementally
   - Flushes every 2M entries (configurable)
   - Progress reporting every 20K entries

3. **Unique Mode** (enabled with `-u` flag)
   - `create_unique_key()` - Creates composite key from distinct fields
   - `process_unique_entry()` - Aggregates entries by unique key, tracking COUNT, max_id, max_created_at
   - `aggregate_unique_entries()` - Converts aggregated dictionary to CSV format
   - `flush_entries()` - Overwrites entire file with aggregated state every 2M entries
   - Validates that 'id' is in FIELDS (mandatory for pagination)
   - Validates that all distinct fields exist in FIELDS
   - Uses global max_id across all unique entries for pagination

4. **Key Configuration**
   - **FIELDS** - Columns to fetch from API (specified via `-f` flag, defaults to: id, namespace, created_at, user_id, ip_addr)
   - **LIMIT** - Entries per API request (50,000)
   - **Starting entry_id** - Multiple historical checkpoints available in code
   - **Event types** - Filters for "player-play" and "download"
   - **Flush frequency** - Every 2M entries

### analyze.py - User Statistics Analysis

#### Core Components

1. **Data Loading (`read_dedup_csv` function)**
   - Reads deduplicated CSV from scan.py unique mode
   - Expects fields: id, namespace, created_at, user_id, ip_addr, COUNT, max_id, max_created_at

2. **Date Range Handling**
   - Uses span from `created_at` to `max_created_at` for each entry
   - User is counted in ALL months/weeks within their activity range
   - Date filtering with `--from` and `--to` flags (defaults: 2025-01-01 to 2026-01-01)
   - Clips entry date ranges to filter bounds
   - Skips entries completely outside the filter range
   - `get_all_months_in_range()` - Generates all year-month periods
   - `get_all_weeks_in_range()` - Generates all ISO week periods

3. **User Categorization**
   - **Logged in users** - Tracked by unique user_id
   - **Anonymous users** - user_id starts with "client:local:", counted TWO ways:
     - **By IP** (anon_by_ip) - Merged by IP address (multiple sessions from same IP = 1 user)
     - **By ID** (anon_by_id) - Each unique client:local:* ID counted separately (shows total sessions)

4. **Statistical Aggregation**
   - Tracks unique users per namespace (plus special "all" namespace)
   - Calculates both monthly and weekly timespans
   - Overall totals per namespace across all time
   - Prints warnings for skipped entries (missing namespace, user_id, or timestamps)

5. **Output Formats**
   - Console: Formatted tables showing overall, monthly, and weekly breakdowns per namespace
   - CSV (optional): namespace, timespan_type, timespan, total_users, logged_users, anon_by_ip, anon_by_id
   - **Total calculation**: logged_users + anon_by_ip (using merged IP count for more accurate unique user estimate)

### Data Flow

**Collection (scan.py):**
1. Load cache if provided (`-c` flag), resume from last max_id
2. Fetch entries from API in batches
3. In unique mode: aggregate by distinct fields, update COUNT/max_id/max_created_at
4. Flush to cache every 2M entries (rewrite in unique mode, append in normal mode)
5. Print created_at range for each flush to track progress

**Analysis (analyze.py):**
1. Read deduplicated CSV with aggregated entries
2. Apply date filtering (--from and --to flags)
3. Parse created_at and max_created_at to get activity date range, clip to filter bounds
4. Generate all months and weeks within the clipped range
5. Categorize users: logged (by user_id) and anonymous (counted both by IP and by ID)
6. Update stats for each timespan in range for both specific namespace and "all" namespace
7. Calculate overall, monthly, and weekly unique user counts
8. Output statistics to console (with "all" namespace first) and optionally to CSV
