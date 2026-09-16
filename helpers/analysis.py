"""Small numeric summaries used to compare the two reconstruction methods."""

import numpy as np


def summarize_invalid(results, years):
    """Count physically-impossible (< 0 or > 100 %) pixels per reconstructed year.

    Returns {year: (n_invalid, n_valid_total, pct_invalid)}.
    """
    summary = {}
    for year in years:
        arr = results[year]
        n_inv = int(np.nansum((arr < 0) | (arr > 100)))
        n_total = int(np.sum(~np.isnan(arr)))
        summary[year] = (n_inv, n_total, 100 * n_inv / n_total if n_total else 0)
    return summary


def print_invalid_summary(summary, years):
    for year in years:
        n_inv, _, pct = summary[year]
        print(f'  20{year}: {n_inv:6,} invalid pixels  ({pct:.2f} % of total)')
