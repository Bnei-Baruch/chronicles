import argparse
import csv
import json
import os
import requests

from datetime import datetime
from requests.exceptions import JSONDecodeError

parser = argparse.ArgumentParser(description="Scan chronicles")

parser.add_argument("-c", "--cache", type=str, help="Cache csv file.")
parser.add_argument("-u", "--unique", type=str, help="Comma-separated list of fields to distinct by. Adds COUNT, max_id, and max_created_at if created_at is present.")
parser.add_argument("-f", "--fields", type=str, help="Comma-separated list of fields to fetch from API.")
parser.add_argument("--start-id", type=str, help="Starting entry ID for scanning. Examples: '2r' (Jan 2025), '2rd' (mid-Jan 2025), '2r0I' (end 2024), '2aKV' (end 2023), '35' (Nov 4th)")
parser.add_argument("--end-id", type=str, help="Ending entry ID for scanning (optional, scans until no more entries if not specified)")
parser.add_argument("-e", "--event-types", type=str, help="Comma-separated list of event types to filter. If not specified, all event types are included")
# parser.add_argument("-o", "--output", type=str, help="Translated docx")

args = parser.parse_args()

# FIELDS = ["id", "namespace", "created_at", "user_id", "ip_addr"]
# FIELDS = ["id", "namespace", "created_at", "user_id", "ip_addr", "user_agent", "client_event_id", "client_event_type", "client_flow_id", "client_flow_type", "client_session_id", "data"]
FIELDS = [f.strip() for f in args.fields.split(',')] if args.fields else ["id", "namespace", "created_at", "user_id", "ip_addr"]
EVENT_TYPES = [e.strip() for e in args.event_types.split(',')] if args.event_types else []
LIMIT = 50000

def scan(id, retries):
    try:
        response = requests.post("https://chronicles.kli.one/scan",
                data=json.dumps({"id": id, "fields": FIELDS, "limit": LIMIT, "event_types": EVENT_TYPES}),
                headers={"Content-Type": "application/json"},
        )
        #print(f"{response}")
        json_response = response.json()
        #print(f"{json_response}")
        entries = json_response["entries"]
        return entries
    except JSONDecodeError as e:
        if retries > 0:
            print('Error decoding json, retrying... ', e)
            return scan(id, retries-1)
        else:
            raise e

def read_headers(filename):
    entries = []
    with open(filename, 'r') as infile:
        csv_reader = csv.reader(infile)
        return next(csv_reader)

def read_csv(filename):
    with open(filename, 'r') as infile:
        csv_reader = csv.reader(infile)
        headers = next(csv_reader)
        for row in csv_reader:
            entry = {}
            for idx, col in enumerate(headers):
                entry[col] = row[idx]
            yield entry

def create_unique_key(entry, distinct_fields):
    """Create a unique key from distinct field values."""
    key_parts = []
    for field in distinct_fields:
        key_parts.append(str(entry.get(field, '')))
    return '|||'.join(key_parts)

def process_unique_entry(entry, unique_dict, distinct_fields, has_created_at):
    """Process an entry in unique mode by aggregating based on distinct fields."""
    # Create a key from distinct field values
    key = create_unique_key(entry, distinct_fields)

    # Initialize or update aggregation
    if key not in unique_dict:
        # Store all fields from the first entry with this key
        unique_dict[key] = {
            'fields': {},
            'count': 0,
            'max_id': entry.get('id', ''),
            'max_created_at': entry.get('created_at', '') if has_created_at else None
        }
        # Store all field values from first entry
        for field in FIELDS:
            unique_dict[key]['fields'][field] = entry.get(field, '')

    unique_dict[key]['count'] += 1

    # Update max_id
    if 'id' in entry:
        current_max_id = unique_dict[key]['max_id']
        new_id = entry['id']
        if not current_max_id or new_id > current_max_id:
            unique_dict[key]['max_id'] = new_id

    # Update max_created_at if applicable
    if has_created_at and 'created_at' in entry:
        current_max = unique_dict[key]['max_created_at']
        new_created_at = entry['created_at']
        if not current_max or new_created_at > current_max:
            unique_dict[key]['max_created_at'] = new_created_at

def aggregate_unique_entries(unique_dict, distinct_fields, has_created_at):
    """Convert aggregated unique entries dict to list format for flushing."""
    entries = []
    for key, agg_data in unique_dict.items():
        entry = {}
        # Add all field values
        for field in FIELDS:
            entry[field] = agg_data['fields'].get(field, '')
        # Add aggregation fields
        entry['COUNT'] = str(agg_data['count'])
        entry['max_id'] = agg_data['max_id']
        if has_created_at:
            entry['max_created_at'] = agg_data['max_created_at']
        entries.append(entry)
    return entries

def flush_entries(filename, entries, unique_mode=False, distinct_fields=None, has_created_at=False):
    if unique_mode and distinct_fields:
        # In unique mode, headers are all FIELDS + COUNT + max_id + max_created_at (if applicable)
        headers = list(FIELDS) + ['COUNT', 'max_id']
        if has_created_at:
            headers.append('max_created_at')
    else:
        headers = FIELDS

    rows = []
    if os.path.exists(filename):
        headers = read_headers(filename)
    else:
        rows.append(headers)

    for entry in entries:
        row = []
        for header in headers:
            row.append(entry.get(header, ''))
        rows.append(row)
    with open(filename, 'a', newline='') as outfile:
        csv_writer = csv.writer(outfile)
        csv_writer.writerows(rows)

def perform_flush(unique_mode, unique_dict, distinct_fields, has_created_at, append_entries, is_final=False):
    """Flush data to cache file and print summary."""
    if not args.cache:
        return

    if unique_mode:
        # Flush all unique entries
        aggregated = aggregate_unique_entries(unique_dict, distinct_fields, has_created_at)
        if os.path.exists(args.cache):
            os.remove(args.cache)
        flush_entries(args.cache, aggregated, unique_mode, distinct_fields, has_created_at)

        # Print created_at range if available
        if has_created_at and aggregated:
            created_ats = [e.get('created_at', '') for e in aggregated if e.get('created_at')]
            if created_ats:
                min_created = min(created_ats)
                max_created = max(created_ats)
                label = "Final" if is_final else "Flushed"
                print(f"{label}: {len(unique_dict)} unique entries to cache. Created_at range: {min_created} to {max_created}")
            else:
                print(f"{'Final' if is_final else 'Flushed'}: {len(unique_dict)} unique entries to cache")
        else:
            print(f"{'Final' if is_final else 'Flushed'}: {len(unique_dict)} unique entries to cache")
    elif append_entries:
        # Flush entries in normal mode
        flush_entries(args.cache, append_entries)
        if 'created_at' in FIELDS:
            created_ats = [e.get('created_at', '') for e in append_entries if e.get('created_at')]
            if created_ats:
                min_created = min(created_ats)
                max_created = max(created_ats)
                label = "Final" if is_final else "Flushed"
                print(f"{label} chunk created_at range: {min_created} to {max_created}")

def process_entry(entry, visits):
    namespace = entry["namespace"]
    if namespace not in visits:
        visits[namespace] = {}

    created_at = entry["created_at"]
    date = ''
    try:
        date = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError as ve:
        print('Error parsing time:', ve)
        print('Entry: ', entry)
        try:
            date = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
        except:
            print('Error second parsing time:', ve)
            print('Entry: ', entry)

        
    year_time_key = f"{date.year}"
    month_time_key = f"{date.year}-{date.month}"
    day_time_key = f"{date.year}-{date.month}-{date.day}"
    date_keys = [year_time_key, month_time_key, day_time_key]

    for time_key in [year_time_key, month_time_key, day_time_key]:
        if time_key not in visits[namespace]:
            visits[namespace][time_key] = {}

        user_id = entry["user_id"]
        visits[namespace][time_key][user_id] = True

    # For next bulk
    return entry["id"]


def main():
    # Validate that 'id' is in FIELDS
    if 'id' not in FIELDS:
        print("Error: 'id' field is mandatory and must be in FIELDS")
        return

    entries = []
    visits = {}

    # Entry ID examples:
    # "2r"       - Start of Jan 2025
    # "2rd"      - 14th Jan 25 (9M entries up to 22nd Jan)
    # "2r0I"     - End of 2024 (19M entries)
    # "2aKV"     - End of 2023 (445M entries)
    # "35db1t"   - Nov 18th
    # "35"       - Nov 4th

    # Set starting entry ID
    if args.start_id:
        entry_id = args.start_id
        print(f"Starting from entry ID: {entry_id}")
    else:
        entry_id = "2r"  # Default: start of Jan 2025
        print(f"Using default start ID: {entry_id}")

    # Set ending entry ID (optional)
    end_id = args.end_id
    if end_id:
        print(f"Will stop at entry ID: {end_id}")

    # Parse unique mode settings
    unique_mode = args.unique is not None
    distinct_fields = []
    has_created_at = 'created_at' in FIELDS  # Check if created_at is in the fields we fetch
    max_id_global = entry_id  # Track max_id globally for unique mode pagination
    if unique_mode:
        distinct_fields = [f.strip() for f in args.unique.split(',')]
        # Validate all distinct_fields exist in FIELDS
        for field in distinct_fields:
            if field not in FIELDS:
                print(f"Error: distinct field '{field}' is not in FIELDS: {FIELDS}")
                return
        print(f"Unique mode enabled. Distinct by: {distinct_fields}")
        print(f"Fetching fields: {FIELDS}")
        output_fields = list(FIELDS) + ['COUNT', 'max_id']
        if has_created_at:
            output_fields.append('max_created_at')
        print(f"Output fields: {output_fields}")

    # Data structures for unique mode
    unique_dict = {}

    # Restore from cache
    read_count = 0
    total_count_from_cache = 0
    if args.cache and os.path.exists(args.cache):
        max_id_global = ""
        for entry in read_csv(args.cache):
            if unique_mode:
                # In unique mode, cache already has aggregated data
                # Validate max_id exists for pagination
                if 'max_id' not in entry or not entry['max_id']:
                    print("Error: max_id field is missing in cache file. Cannot resume in unique mode without max_id for pagination.")
                    return
                # We need to restore the unique_dict from it
                key = create_unique_key(entry, distinct_fields)
                unique_dict[key] = {
                    'fields': {},
                    'count': int(entry.get('COUNT', 1)),
                    'max_id': entry['max_id'],
                    'max_created_at': entry.get('max_created_at', '') if has_created_at else None
                }
                # Accumulate the actual count of original entries
                total_count_from_cache += int(entry.get('COUNT', 1))
                # Restore all field values
                for field in FIELDS:
                    unique_dict[key]['fields'][field] = entry.get(field, '')
                # Track the maximum max_id for pagination
                if not max_id_global or entry['max_id'] > max_id_global:
                    max_id_global = entry['max_id']
            else:
                entry_id = process_entry(entry, visits)
            read_count += 1
            if read_count % 1000000 == 0:
                print(f"Read {read_count/1000000}M entries from cache.")

    if unique_mode:
        entry_id = max_id_global
        print(f"Loaded {len(unique_dict)} unique entries from cache (representing {total_count_from_cache} total entries). Max id [{entry_id}]")
    else:
        print(f"Read {len(entries)/1000}K from cache, last id [{entry_id}].")

    count = len(entries) if not unique_mode else total_count_from_cache
    print_count = count
    scan_count = count
    append_entries = []
    while True:
        entries = scan(entry_id, 3)
        print(f"Read {len(entries)} entries")
        if len(entries) == 0:
            break
        entries_processed = 0
        for entry in entries:
            # Check if we've reached the end_id
            if end_id and 'id' in entry and entry['id'] >= end_id:
                print(f"Reached end ID: {entry['id']} (>= {end_id}), stopping scan")
                break

            if unique_mode:
                process_unique_entry(entry, unique_dict, distinct_fields, has_created_at)
            else:
                append_entries.append(entry)
                entry_id = process_entry(entry, visits)
            # Always update entry_id for pagination
            if 'id' in entry:
                entry_id = entry['id']

            entries_processed += 1

        count += entries_processed

        # If we stopped early due to end_id, break out of main loop
        if entries_processed < len(entries):
            break

        if count - print_count >= 20000:
            print(f"{count/1000}K entries processed")
            if unique_mode:
                print(f"  {len(unique_dict)} unique entries so far")
            print_count = count
            current_time = datetime.now()
            formatted_time = current_time.strftime("%H:%M:%S")
            print("Current Time:", formatted_time)
        if count - scan_count >= 2000000:
            perform_flush(unique_mode, unique_dict, distinct_fields, has_created_at, append_entries)
            append_entries = []
            scan_count = count

    # Final flush: ensure any remaining data is written (handles early exit due to end_id or < 2M entries)
    perform_flush(unique_mode, unique_dict, distinct_fields, has_created_at, append_entries, is_final=True)

    # Print summary for unique mode
    if unique_mode:
        print(f"\nTotal entries read: {count}")
        print(f"Unique entries after deduplication: {len(unique_dict)}")

    for (namespace, app_visits) in visits.items():
        print(f"{namespace} - {len(app_visits)}")
        for (date_key, users) in app_visits.items():
            count = sum(1 for user_id in users if user_id.startswith("client:local:"))
            print(f"\t{date_key} - {len(users)} - incognito({count}) - logged in({len(users)-count})")


if __name__ == "__main__":
    main()
