import argparse
import csv
import json
import os
import requests

from datetime import datetime
from requests.exceptions import JSONDecodeError

parser = argparse.ArgumentParser(description="Scan chronicles")

parser.add_argument("-c", "--cache", type=str, help="Cache csv file.")
# parser.add_argument("-o", "--output", type=str, help="Translated docx")

args = parser.parse_args()

# FIELDS = ["id", "namespace", "created_at", "user_id"]
FIELDS = ["id", "namespace", "created_at", "user_id", "ip_addr", "user_agent", "client_event_id", "client_event_type", "client_flow_id", "client_flow_type", "client_session_id", "data"]
LIMIT = 500000

def scan(id, retries):
    try:
        response = requests.post("https://chronicles.kli.one/scan",
                data=json.dumps({"id": id, "fields": FIELDS, "limit": LIMIT}),
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

def flush_entries(filename, entries):
    headers = FIELDS
    rows = []
    if os.path.exists(args.cache):
        headers = read_headers(filename)
    else:
        rows.append(headers)

    for entry in entries:
        row = []
        for header in headers:
            row.append(entry[header])
        rows.append(row)
    with open(filename, 'a', newline='') as outfile:
        csv_writer = csv.writer(outfile)
        csv_writer.writerows(rows)

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
    entries = []
    visits = {}
    entry_id = "2rd"  # 14th Jan 25. (9M entries up to 22nd Jan)
    # entry_id = "2r0I"  # end of 24 (19M entries)
    # entry_id = "2aKV"  # end of 23 (445M entries)

    # Restore from cache
    read_count = 0
    if args.cache and os.path.exists(args.cache):
        for entry in read_csv(args.cache):
            entry_id = process_entry(entry, visits)
            read_count += 1
            if read_count % 1000000 == 0:
                print(f"Read {read_count/1000000}M entries from cache.")

    print(f"Read {len(entries)/1000}K from cache, last id [{entry_id}].")

    count = len(entries)
    print_count = count
    scan_count = count
    append_entries = []
    while True:
        entries = scan(entry_id, 3)
        if len(entries) == 0:
            break
        for entry in entries:
            append_entries.append(entry)
            entry_id = process_entry(entry, visits)

        count += len(entries)
        if count - print_count >= 20000:
            print(f"{count/1000}K entries read")
            print_count = count
            current_time = datetime.now()
            formatted_time = current_time.strftime("%H:%M:%S")
            print("Current Time:", formatted_time)
        if len(entries) == 0 or count - scan_count >= 50000:
            flush_entries(args.cache, append_entries)
            append_entries = []
    for (namespace, app_visits) in visits.items():
        print(f"{namespace} - {len(app_visits)}")
        for (date_key, users) in app_visits.items():
            count = sum(1 for user_id in users if user_id.startswith("client:local:"))
            print(f"\t{date_key} - {len(users)} - incognito({count}) - logged in({len(users)-count})")


if __name__ == "__main__":
    main()
