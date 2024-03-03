# -*- coding: utf-8 -*-
"""
Created on Sun Mar  3 14:08:37 2024

@author: zachs
"""

import gdal


def hdf_to_geotiff(input_hdf_path, output_geotiff_path):
    # Open the HDF file
    hdf_dataset = gdal.Open(input_hdf_path)

    if hdf_dataset is None:
        raise FileNotFoundError("HDF file not found or cannot be opened.")

    # Get the subdataset name from the HDF file
    subdataset_name = hdf_dataset.GetSubDatasets()[0][0]

    # Open the subdataset
    subdataset = gdal.Open(subdataset_name)

    # Get metadata and projection information
    metadata = subdataset.GetMetadata()
    projection = subdataset.GetProjection()

    # Create output GeoTIFF
    driver = gdal.GetDriverByName("GTiff")
    geotiff_dataset = driver.Create(
        output_geotiff_path,
        subdataset.RasterXSize,
        subdataset.RasterYSize,
        1,
        gdal.GDT_Float32,
    )

    if geotiff_dataset is None:
        raise RuntimeError("Failed to create GeoTIFF file.")

    # Write data to GeoTIFF
    geotiff_dataset.GetRasterBand(1).WriteArray(subdataset.ReadAsArray())

    # Set metadata and projection
    geotiff_dataset.SetMetadata(metadata)
    geotiff_dataset.SetProjection(projection)

    # Close datasets
    hdf_dataset = None
    subdataset = None
    geotiff_dataset = None

    print("Conversion successful.")


# Example usage:
input_hdf_path = (
    r"C:\Users\zachs\Desktop\tmp\MOD09.A2024056.1435.061.2024058042139.hdf"
)
output_geotiff_path = r"C:\Users\zachs\Desktop\tmp\MODIS_True_Color.tif"
hdf_to_geotiff(input_hdf_path, output_geotiff_path)
