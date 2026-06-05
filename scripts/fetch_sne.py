"""
TNS supernova fetcher -- downloads the full TNS catalog and smartly
updates the master supernovae_database/supernovae.json.

Merge rules (applied per entry, matched by name):
  - New in TNS (not in master)           --> added, source = "TNS"
  - In master as "TNS" or "TNS+OSC"      --> TNS non-null fields overwrite;
                                              null TNS fields never blank out
                                              existing data (preserves OSC fills)
  - In master as "OSC", now also in TNS  --> source becomes "TNS+OSC";
                                              same field-level merge applies
  - In master as "OSC", still not in TNS --> untouched

This means reclassifications in TNS always propagate, but OSC-filled
fields (e.g. redshift that TNS is missing) are never wiped out.

Usage:
    python scripts/fetch_sne.py
Run from the portfolio/ root directory.
Requires env vars: TNS_BOT_ID, TNS_BOT_NAME
"""

import io
import json
import math
import os
import shutil
import sys
import zipfile

import pandas as pd
import requests

MASTER_JSON = "supernovae_database/supernovae.json"

# Fields we update from fresh TNS data (when TNS value is non-null)
UPDATABLE = ['ra', 'dec', 'type', 'discovery_date', 'redshift', 'reporting_group']

# ------------------------------------------------------------------ #
# Credentials
# ------------------------------------------------------------------ #
TNS_ID   = os.environ.get("TNS_BOT_ID", "")
TNS_NAME = os.environ.get("TNS_BOT_NAME", "")

if not TNS_ID or not TNS_NAME:
    print("Error: TNS_BOT_ID and TNS_BOT_NAME environment variables must be set.")
    sys.exit(1)

headers = {
    "user-agent": f'tns_marker{{"tns_id": {TNS_ID}, "type": "user", "name": "{TNS_NAME}"}}'
}

# ------------------------------------------------------------------ #
# Download
# ------------------------------------------------------------------ #
url = "https://www.wis-tns.org/system/files/tns_public_objects/tns_public_objects.csv.zip"
print("Downloading full TNS catalog (this may take a few minutes)...")

r = requests.get(url, headers=headers, timeout=300)
r.raise_for_status()
print(f"Downloaded {len(r.content) / 1024:.0f} KB")

with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    with z.open(z.namelist()[0]) as f:
        df = pd.read_csv(f, skiprows=1, low_memory=False)

# ------------------------------------------------------------------ #
# Parse and clean
# ------------------------------------------------------------------ #
df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
print(f"Columns: {list(df.columns)}")
print(f"Total rows in download: {len(df)}")

if 'type' not in df.columns:
    print("Error: 'type' column not found in CSV.")
    sys.exit(1)

sne = df[df['type'].str.startswith('SN', na=False)].copy()
print(f"Supernovae rows: {len(sne)}")

# Column name mapping (TNS CSV column names vary slightly over time)
col_map = {
    'objname':             'name',
    'name':                'name',
    'ra':                  'ra',
    'declination':         'dec',
    'dec':                 'dec',
    'type':                'type',
    'discoverydate':       'discovery_date',
    'discovery_date_(ut)': 'discovery_date',
    'redshift':            'redshift',
    'reporting_group':     'reporting_group',
    'reporting_group/s':   'reporting_group',
}
rename = {k: v for k, v in col_map.items() if k in sne.columns}
sne = sne.rename(columns=rename)

# Build full name (prefix + name) if both columns exist
if 'name_prefix' in sne.columns and 'name' in sne.columns:
    sne['name'] = sne.apply(
        lambda row: f"{row['name_prefix']} {row['name']}"
        if pd.notna(row.get('name_prefix')) and str(row.get('name_prefix')).strip()
        else str(row['name']),
        axis=1
    )

# Keep only schema columns that exist
keep = ['name', 'ra', 'dec', 'type', 'discovery_date', 'redshift', 'reporting_group']
keep = [c for c in keep if c in sne.columns]
sne  = sne[keep].copy()

# Coerce numeric columns
for col in ['ra', 'dec', 'redshift']:
    if col in sne.columns:
        sne[col] = pd.to_numeric(sne[col], errors='coerce')

# Drop rows missing coordinates
sne = sne.dropna(subset=['ra', 'dec'])

# Convert to list of dicts; replace float NaN with None (NaN is invalid JSON)
fresh_records = sne.to_dict(orient='records')
for rec in fresh_records:
    for k in rec:
        if isinstance(rec[k], float) and math.isnan(rec[k]):
            rec[k] = None

print(f"Fresh TNS records after cleaning: {len(fresh_records)}")

# ------------------------------------------------------------------ #
# Load current master
# ------------------------------------------------------------------ #
try:
    with open(MASTER_JSON) as f:
        master_records = json.load(f)
    print(f"Current master entries: {len(master_records)}")
except FileNotFoundError:
    print("No existing master file found -- will create a fresh one.")
    master_records = []

# ------------------------------------------------------------------ #
# Helper: normalised name key for matching
# ------------------------------------------------------------------ #
def name_key(name):
    return name.strip().lower() if name else ''

# Index master by normalised name for fast lookup
master_index = {}
for rec in master_records:
    master_index[name_key(rec['name'])] = rec

# ------------------------------------------------------------------ #
# Delta merge
# ------------------------------------------------------------------ #
n_added   = 0   # new to TNS, not seen before
n_updated = 0   # existing entry had at least one field changed
n_unchanged = 0 # existing entry, nothing changed
n_osc_promoted = 0  # was OSC-only, now also in TNS

fresh_keys = set()

for fresh in fresh_records:
    key = name_key(fresh['name'])
    fresh_keys.add(key)
    existing = master_index.get(key)

    if existing is None:
        # Brand new entry from TNS
        new_entry = dict(fresh)
        new_entry['source'] = 'TNS'
        master_index[key] = new_entry
        n_added += 1

    else:
        prev_source = existing.get('source', 'TNS')
        changed = False

        for field in UPDATABLE:
            fresh_val = fresh.get(field)
            if fresh_val is not None:
                if existing.get(field) != fresh_val:
                    existing[field] = fresh_val
                    changed = True
            # if fresh_val is None, we leave whatever is in existing untouched

        # Update source label
        if prev_source == 'OSC':
            existing['source'] = 'TNS+OSC'
            n_osc_promoted += 1
            changed = True
        # "TNS" stays "TNS", "TNS+OSC" stays "TNS+OSC"

        if changed:
            n_updated += 1
        else:
            n_unchanged += 1

# ------------------------------------------------------------------ #
# Safety check -- the master should never shrink significantly
# ------------------------------------------------------------------ #
new_total = len(master_index)
old_total = len(master_records)

if new_total < old_total * 0.95:
    print(
        f"\nSAFETY ABORT: master would shrink from {old_total} to {new_total} entries "
        f"({old_total - new_total} lost). This looks wrong -- not writing anything."
    )
    sys.exit(1)

# ------------------------------------------------------------------ #
# Write -- safely via temp file, with backup of previous version
# ------------------------------------------------------------------ #
output   = list(master_index.values())
tmp_json = MASTER_JSON + ".tmp"
bak_json = MASTER_JSON + ".bak"

# Step 1: write to temp file (original untouched if this fails)
with open(tmp_json, 'w') as f:
    json.dump(output, f, separators=(',', ':'))

# Step 2: keep a copy of the previous master as .bak
if os.path.exists(MASTER_JSON):
    shutil.copy2(MASTER_JSON, bak_json)

# Step 3: atomically replace the master with the temp file
os.replace(tmp_json, MASTER_JSON)

# ------------------------------------------------------------------ #
# Summary
# ------------------------------------------------------------------ #
print(f"\nUpdate complete:")
print(f"  New entries added        : {n_added}")
print(f"  Existing entries updated : {n_updated}  (reclassifications, new fields)")
print(f"  OSC entries now in TNS   : {n_osc_promoted}")
print(f"  Unchanged                : {n_unchanged}")
print(f"  Master total             : {len(output)}  (was {old_total})")
print(f"\nSaved    --> {MASTER_JSON}")
print(f"Backup   --> {bak_json}")
