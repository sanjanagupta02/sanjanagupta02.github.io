"""
Merges supernovae_osc.json into supernovae.json (TNS).

Rules:
  - TNS-only entry      --> kept as-is, source set to "TNS"
  - OSC-only entry      --> added as-is, source stays "OSC"
  - In both (by name)   --> TNS wins on every non-null field;
                            OSC fills in fields that are null in TNS;
                            source set to "TNS+OSC"

Output overwrites supernovae_database/supernovae.json.

Usage:
    python scripts/merge_osc.py
Run from the portfolio/ root directory.
"""

import json

TNS_JSON  = "supernovae_database/supernovae.json"
OSC_JSON  = "supernovae_database/supernovae_osc.json"
OUT_JSON  = "supernovae_database/supernovae.json"

# Fields that can be filled from OSC when TNS has null
FILLABLE = ['type', 'discovery_date', 'redshift', 'reporting_group']


def name_key(name):
    """Lowercase, strip whitespace -- used for matching across sources."""
    return name.strip().lower() if name else ''


# ------------------------------------------------------------------ #
# Load both files
# ------------------------------------------------------------------ #
with open(TNS_JSON) as f:
    tns_records = json.load(f)

with open(OSC_JSON) as f:
    osc_records = json.load(f)

print(f'TNS entries : {len(tns_records)}')
print(f'OSC entries : {len(osc_records)}')

# ------------------------------------------------------------------ #
# Index OSC by normalised name for fast lookup
# ------------------------------------------------------------------ #
osc_by_name = {}
for rec in osc_records:
    key = name_key(rec['name'])
    osc_by_name[key] = rec

# ------------------------------------------------------------------ #
# Pass 1 -- process every TNS entry
# ------------------------------------------------------------------ #
merged    = []
tns_only  = 0
tns_osc   = 0

for tns_rec in tns_records:
    key     = name_key(tns_rec['name'])
    osc_rec = osc_by_name.get(key)

    if osc_rec is None:
        # TNS only -- just tag the source
        out = dict(tns_rec)
        out['source'] = 'TNS'
        tns_only += 1
    else:
        # In both -- TNS wins; fill nulls from OSC
        out = dict(tns_rec)
        for field in FILLABLE:
            if out.get(field) is None and osc_rec.get(field) is not None:
                out[field] = osc_rec[field]
        out['source'] = 'TNS+OSC'
        tns_osc += 1

    merged.append(out)

# ------------------------------------------------------------------ #
# Pass 2 -- add OSC-only entries (not found in TNS at all)
# ------------------------------------------------------------------ #
tns_keys = {name_key(r['name']) for r in tns_records}
osc_only = 0

for osc_rec in osc_records:
    if name_key(osc_rec['name']) not in tns_keys:
        merged.append(osc_rec)   # source is already "OSC"
        osc_only += 1

# ------------------------------------------------------------------ #
# Report
# ------------------------------------------------------------------ #
print(f'\nMerge results:')
print(f'  TNS only              : {tns_only}')
print(f'  TNS + OSC (merged)    : {tns_osc}')
print(f'  OSC only (new)        : {osc_only}')
print(f'  Total in master file  : {len(merged)}')

# ------------------------------------------------------------------ #
# Write
# ------------------------------------------------------------------ #
with open(OUT_JSON, 'w') as f:
    json.dump(merged, f, separators=(',', ':'))

print(f'\nSaved --> {OUT_JSON}')
