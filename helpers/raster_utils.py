"""Raster I/O and image helper functions used by the change-backcalculation notebook."""

import io
import base64
import warnings

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgba
from osgeo import gdal, osr
from PIL import Image

gdal.UseExceptions()
warnings.filterwarnings('ignore', category=FutureWarning)


def load_array(path):
    """Open a single-band GeoTIFF and return (array as float64, GDAL dataset)."""
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f'Cannot open: {path}')
    return ds.GetRasterBand(1).ReadAsArray().astype(float), ds


def normalize_change(arr):
    """Convert raw IMDC byte values to change amounts in [-100, +100]. 0 = no change."""
    a = arr.copy()
    a[a >= 201] = 100  # 201 = no-change class, 255 = nodata -> treat as no change
    a -= 100
    return a


def match_to_grid(src_arr, src_ds, tgt_ds, alg=None):
    """Resample src_arr (georeferenced by src_ds) to match the tgt_ds pixel grid.

    Both datasets must share the same CRS. No reprojection is performed.
    """
    if alg is None:
        alg = gdal.GRA_NearestNeighbour
    mem = gdal.GetDriverByName('MEM')
    src = mem.Create('', src_ds.RasterXSize, src_ds.RasterYSize, 1, gdal.GDT_Float32)
    src.SetGeoTransform(src_ds.GetGeoTransform())
    src.SetProjection(src_ds.GetProjection())
    src.GetRasterBand(1).WriteArray(src_arr.astype(np.float32))
    dst = mem.Create('', tgt_ds.RasterXSize, tgt_ds.RasterYSize, 1, gdal.GDT_Float32)
    dst.SetGeoTransform(tgt_ds.GetGeoTransform())
    dst.SetProjection(tgt_ds.GetProjection())
    gdal.ReprojectImage(src, dst, None, None, alg)
    return dst.GetRasterBand(1).ReadAsArray()


def array_to_img(arr, cmap_name='YlOrRd', vmin=0, vmax=100, max_px=1024, clr_below_vmin = None, clr_above_vmax = None):    
    """Convert a 2-D numpy array to a base64 PNG data URI for folium ImageOverlay."""
    a = arr.copy().astype(float)
    nodata = np.isnan(a)
    below = ~nodata & (a < vmin)
    above = ~nodata & (a > vmax)
    a_norm = np.clip((a - vmin) / (vmax - vmin), 0, 1)
    a_norm[nodata] = 0
    rgba = plt.get_cmap(cmap_name)(a_norm)
    rgba[nodata] = 0.0  # transparent nodata
    if clr_below_vmin is not None:
        rgba[below] = to_rgba(clr_below_vmin)
    if clr_above_vmax is not None:
        rgba[above] = to_rgba(clr_above_vmax)
    img = Image.fromarray((rgba * 255).astype(np.uint8))
    if max(img.size) > max_px:
        scale = max_px / max(img.size)
        img = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def bbox_to_4326(xmin, ymin, xmax, ymax, source_epsg):
    """Convert a projected bounding box to EPSG:4326 center and folium bounds.

    Returns (clat, clon, bounds) where bounds = [[south, west], [north, east]].
    """
    src = osr.SpatialReference()
    src.ImportFromEPSG(source_epsg)
    src.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    dst = osr.SpatialReference()
    dst.ImportFromEPSG(4326)
    dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    t = osr.CoordinateTransformation(src, dst)

    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    clon, clat, _ = t.TransformPoint(cx, cy)
    sw_lon, sw_lat, _ = t.TransformPoint(xmin, ymin)
    ne_lon, ne_lat, _ = t.TransformPoint(xmax, ymax)
    return clat, clon, [[sw_lat, sw_lon], [ne_lat, ne_lon]]
