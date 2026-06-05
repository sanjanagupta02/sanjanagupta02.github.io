"""
OSC converter -- reads OpenSNCat.csv and writes supernovae_osc.json.

Usage:
    python scripts/convert_osc.py

Run from the portfolio/ root directory.
"""

import csv
import json
import re
import sys

INPUT_CSV   = "supernovae_database/OpenSNCat.csv"
OUTPUT_JSON = "supernovae_database/supernovae_osc.json"

# ------------------------------------------------------------------ #
# Types that are clearly not supernovae -- skip these entries entirely
# ------------------------------------------------------------------ #
EXCLUDE_TYPES = {
    'Candidate',   # unconfirmed transient
    'LGRB',        # long gamma-ray burst (not a SN)
    'removed',     # de-listed from OSC
    'Galaxy',      # misidentified galaxy nucleus
    'AGN',         # active galactic nucleus
    'CV',          # cataclysmic variable
    'LPV',         # long period variable (stellar pulsation)
}

# ------------------------------------------------------------------ #
# Type normalization: OSC format --> our "SN xxx" format
# Covers every OSC type that differs from simply prepending "SN "
# ------------------------------------------------------------------ #
TYPE_MAP = {
    # space --> dash
    'Ic BL':          'SN Ic-BL',
    'Ia CSM':         'SN Ia-CSM',
    # OSC Pec suffix --> lowercase to match TNS style
    'Ia Pec':         'SN Ia-pec',
    'Ib Pec':         'SN Ib-pec',
    'Ic Pec':         'SN Ic-pec',
    'II Pec':         'SN II-pec',
    'IIn Pec':        'SN IIn-pec',
    # OSC suffix variants --> TNS-style names
    'Ia-91T':         'SN Ia-91T-like',
    'Ia-91bg':        'SN Ia-91bg-like',
    'Ia-02cx':        'SN Iax[02cx-like]',
    'Iax[02cx-like]': 'SN Iax[02cx-like]',
    # OSC space variants for II subtypes
    'II P':           'SN IIP',
    'II L':           'SN IIL',
    # ambiguous classifications -- keep as-is with SN prefix
    'Ib/c':           'SN Ib/c',
    'Ib/c?':          'SN Ib/c?',
    'IIb/Ib/Ic':      'SN IIb/Ib/Ic',
    'Ia/c':           'SN Ia/c',
    'Ia/Ic':          'SN Ia/Ic',
}


def normalize_type(raw):
    """Return normalized type string, None (no type), or 'EXCLUDE'."""
    t = raw.strip()
    if not t:
        return None                     # no type -- include, type will be null
    if t in EXCLUDE_TYPES:
        return 'EXCLUDE'
    if t in TYPE_MAP:
        return TYPE_MAP[t]
    if t.startswith('SN '):
        return t                        # already correct format
    return f'SN {t}'                    # prepend SN to everything else


def normalize_name(raw):
    """
    Add a space after the SN/AT/SNLS prefix when it is directly followed
    by a digit: SN1987A --> SN 1987A, AT2018kwm --> AT 2018kwm.
    Survey designations (CSS..., PS1-..., Gaia...) are left untouched.
    """
    name = raw.strip()
    m = re.match(r'^(SN|AT|SNLS)(\d)', name)
    if m:
        prefix = m.group(1)
        return f'{prefix} {name[len(prefix):]}'
    return name


def hms_to_deg(hms):
    """HH:MM:SS.ss --> decimal degrees (RA)."""
    hms = hms.strip()
    if not hms:
        return None
    parts = hms.split(':')
    if len(parts) != 3:
        return None
    try:
        h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
        return (h + m / 60.0 + s / 3600.0) * 15.0
    except ValueError:
        return None


def dms_to_deg(dms):
    """+-DD:MM:SS.ss --> decimal degrees (Dec)."""
    dms = dms.strip()
    if not dms:
        return None
    sign = -1 if dms.startswith('-') else 1
    dms = dms.lstrip('+-')
    parts = dms.split(':')
    if len(parts) != 3:
        return None
    try:
        d, m, s = float(parts[0]), float(parts[1]), float(parts[2])
        return sign * (d + m / 60.0 + s / 3600.0)
    except ValueError:
        return None


def first_value(field):
    """OSC stores multiple measurements comma-separated; take the first."""
    if not field:
        return None
    return field.split(',')[0].strip() or None


def parse_redshift(z_str):
    """Return float redshift, or None if missing/implausible."""
    if not z_str:
        return None
    try:
        z = float(z_str)
        # redshift must be positive and physically reasonable
        if 0.0 < z < 10.0:
            return z
    except ValueError:
        pass
    return None


def normalize_date(date_str):
    """YYYY/MM/DD --> YYYY-MM-DD; partial dates (YYYY/MM) also converted."""
    if not date_str:
        return None
    return date_str.strip().replace('/', '-')


# ------------------------------------------------------------------ #
# Main conversion
# ------------------------------------------------------------------ #
records        = []
skipped_excl   = 0
skipped_coords = 0

with open(INPUT_CSV, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        raw_type = row.get('Type', '').strip()
        norm_type = normalize_type(raw_type)

        if norm_type == 'EXCLUDE':
            skipped_excl += 1
            continue

        ra_str  = first_value(row.get('R.A.', ''))
        dec_str = first_value(row.get('Dec.', ''))
        ra  = hms_to_deg(ra_str)  if ra_str  else None
        dec = dms_to_deg(dec_str) if dec_str else None

        if ra is None or dec is None:
            skipped_coords += 1
            continue

        z_str = first_value(row.get('z', ''))
        z     = parse_redshift(z_str)

        disc_raw  = first_value(row.get('Disc. Date', ''))
        disc_date = normalize_date(disc_raw)

        records.append({
            'name':            normalize_name(row.get('Name', '').strip()),
            'ra':              round(ra,  6),
            'dec':             round(dec, 6),
            'type':            norm_type,        # None if no type in OSC
            'discovery_date':  disc_date,
            'redshift':        z,
            'reporting_group': None,
            'source':          'OSC',
        })

# ------------------------------------------------------------------ #
# Deduplicate -- keep the entry with the most non-null fields
# ------------------------------------------------------------------ #
seen = {}
for rec in records:
    key = rec['name'].strip().lower()
    if key not in seen:
        seen[key] = rec
    else:
        existing_score = sum(1 for v in seen[key].values() if v is not None)
        new_score      = sum(1 for v in rec.values()       if v is not None)
        if new_score > existing_score:
            seen[key] = rec

deduped    = list(seen.values())
n_dupes    = len(records) - len(deduped)

# ------------------------------------------------------------------ #
# Report
# ------------------------------------------------------------------ #
total_rows = skipped_excl + skipped_coords + len(records)
print(f'Total OSC rows read  : {total_rows}')
print(f'Excluded (non-SN)    : {skipped_excl}  (Candidate / LGRB / removed / Galaxy / AGN / CV / LPV)')
print(f'Skipped (no coords)  : {skipped_coords}')
print(f'Duplicates removed   : {n_dupes}')
print(f'Written to JSON      : {len(deduped)}')

typed   = sum(1 for r in deduped if r['type'])
untyped = len(deduped) - typed
print(f'  with type          : {typed}')
print(f'  without type       : {untyped}')

with open(OUTPUT_JSON, 'w') as f:
    json.dump(deduped, f, separators=(',', ':'))

print(f'\nSaved --> {OUTPUT_JSON}')
