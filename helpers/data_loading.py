"""Site definitions and raster loading for the change-backcalculation notebook."""

import yaml
import numpy as np
from osgeo import gdal

from .raster_utils import load_array, match_to_grid


def load_sites(path='data/site_definition.yaml'):
    """Load the site definitions (extent, resolution, CRS, ...) used by the notebook."""
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def load_site_layers(site_name, cfg, years, pairs):
    """Load and align the IMD status and IMDC change rasters for one site.

    Historical status layers that don't match the 2024 baseline grid are
    resampled onto it (bilinear) — this happens for the 2006-2015 epochs,
    which are only available natively at 20 m.

    Returns a dict with 'status' ({year: (array, ds)}), 'change'
    ({pair: (array, ds)}), the baseline dataset 'ref_ds', and 'cross_res'
    (True when the change layer is coarser than the status layer).
    """
    status_res, change_res = cfg['status_res'], cfg['change_res']

    def imd_path(year):
        return f'data/IMD_{year}_{site_name}_{status_res}m.tif'

    def imdc_path(pair):
        return f'data/IMDC_{pair}_{site_name}_{change_res}m.tif'

    status = {}
    for year in years:
        arr, ds = load_array(imd_path(year))
        arr[arr == 255] = np.nan  # 255 is the IMD nodata value
        status[year] = (arr, ds)

    ref_shape, ref_ds = status[years[0]][0].shape, status[years[0]][1]
    for year in years[1:]:
        arr, ds = status[year]
        if arr.shape != ref_shape:
            status[year] = (match_to_grid(arr, ds, ref_ds, alg=gdal.GRA_Bilinear), ref_ds)

    change = {pair: load_array(imdc_path(pair)) for pair in pairs}

    cross_res = status_res != change_res
    print(f'Loaded {len(status)} status layers and {len(change)} change layers for {site_name}.')
    if cross_res:
        print(f'  Cross-resolution site: {change_res} m IMDC-derived change mask will be resampled '
              f'to the {status_res} m status grid.')

    return {'status': status, 'change': change, 'ref_ds': ref_ds, 'cross_res': cross_res}
