"""
TNS supernova fetcher — always downloads the full catalog.
Usage: python scripts/fetch_sne.py

Requires env vars: TNS_BOT_ID, TNS_BOT_NAME
"""

import requests
import zipfile
import io
import pandas as pd
import json
import os
import sys
from datetime import datetime

TNS_ID   = os.environ.get("TNS_BOT_ID", "")
TNS_NAME = os.environ.get("TNS_BOT_NAME", "")

if not TNS_ID or not TNS_NAME:
    print("Error: TNS_BOT_ID and TNS_BOT_NAME environment variables must be set.")
    sys.exit(1)

headers = {
    "user-agent": f'tns_marker{{"tns_id": {TNS_ID}, "type": "user", "name": "{TNS_NAME}"}}'
}

url = "https://www.wis-tns.org/system/files/tns_public_objects/tns_public_objects.csv.zip"
print("Downloading full TNS catalog (this may take a few minutes)...")

r = requests.get(url, headers=headers, timeout=300)
r.raise_for_status()
print(f"Downloaded {len(r.content) / 1024:.0f} KB")

with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    with z.open(z.namelist()[0]) as f:
        df = pd.read_csv(f, skiprows=1, low_memory=False)

# Normalize column names
df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
print(f"Columns: {list(df.columns)}")
print(f"Total rows in download: {len(df)}")

# Filter for supernovae only
if 'type' not in df.columns:
    print("Error: 'type' column not found in CSV.")
    sys.exit(1)

sne = df[df['type'].str.startswith('SN', na=False)].copy()
print(f"Supernovae rows: {len(sne)}")

# Column name mapping (TNS CSV column names vary slightly over time)
col_map = {
    'objname':              'name',
    'name':                 'name',
    'ra':                   'ra',
    'declination':          'dec',
    'dec':                  'dec',
    'type':                 'type',
    'discoverydate':        'discovery_date',
    'discovery_date_(ut)':  'discovery_date',
    'redshift':             'redshift',
    'reporting_group':      'reporting_group',
    'reporting_group/s':    'reporting_group',
}
rename = {k: v for k, v in col_map.items() if k in sne.columns}
sne = sne.rename(columns=rename)

# Build full name (prefix + name) if both columns exist
if 'name_prefix' in sne.columns and 'name' in sne.columns:
    sne['name'] = sne.apply(
        lambda r: f"{r['name_prefix']} {r['name']}"
        if pd.notna(r.get('name_prefix')) and str(r.get('name_prefix')).strip()
        else str(r['name']),
        axis=1
    )

# Keep only schema columns that exist
keep = ['name', 'ra', 'dec', 'type', 'discovery_date', 'redshift', 'reporting_group']
keep = [c for c in keep if c in sne.columns]
sne = sne[keep].copy()

# Coerce numeric columns
for col in ['ra', 'dec', 'redshift']:
    if col in sne.columns:
        sne[col] = pd.to_numeric(sne[col], errors='coerce')

# Drop rows missing coordinates
sne = sne.dropna(subset=['ra', 'dec'])

# Full catalog replaces existing data
json_path = "supernovae_database/supernovae.json"
combined = sne

records = combined.to_dict(orient='records')

# Replace float NaN with None so json.dump writes null not NaN (NaN is invalid JSON)
import math
for rec in records:
    for k in rec:
        if isinstance(rec[k], float) and math.isnan(rec[k]):
            rec[k] = None

with open(json_path, 'w') as f:
    json.dump(records, f, separators=(',', ':'))

print(f"Done. {len(records)} supernovae saved to {json_path}.")
