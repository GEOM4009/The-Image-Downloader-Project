# -*- coding: utf-8 -*-
"""
Created on Fri Mar 12 11:42:00 2024

@author: Philip, Shea, Collin and Zacharie
"""

# import dependencies

import os
import subprocess
from datetime import datetime
import re
import glob
import rasterio
from rasterio.enums import ColorInterp
import numpy as np
from osgeo import gdal
import argparse
from configparser import RawConfigParser
import sys
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
import fiona


# New API download from LANCE NRT with token access (Zacharie)
def download_HDF_file(url, auth_token, download_HDF_dir):
    """
    Download an HDF file using wget command.

    Parameters:
    - url (str): URL of the HDF file to download.
    - auth_token (str): Authorization token for the request.
    - download_dir (str): Directory where the HDF file will be saved.
    """
    command = [
        "wget",
        url,
        "--header",
        f"Authorization: Bearer {auth_token}",
        "-P",
        download_HDF_dir,
    ]

    try:
        # Execute the wget command
        subprocess.run(command, shell=True)
        print("HDF file downloaded successfully.")
    except subprocess.CalledProcessError as e:
        # Handle error if the command fails
        print("Error downloading HDF file:", e)


def download_txt_file(url, auth_token, download_txt_dir):
    """
    Download an txt file using wget command.

    Parameters:
    - url (str): URL of the HDF file to download.
    - auth_token (str): Authorization token for the request.
    - download_dir (str): Directory where the HDF file will be saved.
    """
    command = [
        "wget",
        url,
        "--header",
        f"Authorization: Bearer {auth_token}",
        "-O",
        download_txt_dir,
    ]

    try:
        # Execute the wget command
        subprocess.run(command, shell=True)
        print("HDF file downloaded successfully.")
    except subprocess.CalledProcessError as e:
        # Handle error if the command fails
        print("Error downloading HDF file:", e)


# Text file processing function--------- (Collin)
def extract_granule_id(txt_file, kml_path):
    """
    This function takes the input text file and bounding polygon KML file.
    It loads in each GranuleID and corresponding attributes and uses the GRingLatitude and GRingLongitude values as geometry
    There is an optional step that is commented that enables the users to export the selected geometry as a GPKG for troubleshooting/accuracy verification.
    The geodataframe is sorted by the inputted area of interest and the most recent entry is selected and returned.
    The function uses an example bounding of Cambridge Bay (and the surrounding Airport and Canadian High Arctic Research Centre)

    My inspiration for this code came from Derek's workshop #6 which uses the fiona supported drivers and opens a kml as a pdf.
    The rest of the code used geopandas general methods as well as the coordinate format from the HEG tool


    Parameters:
        txt_file (str): The path to the txt file directory.
        kml_path (str): The path to the KML file containing bounding polygon.
    Returns:
        selected_granuleID (str): A string containing the GranuleID for the hdf download request.
        selected_granuleID (str): The selected granuleID.
        upper_left (str): Coordinates of the upper left corner in the HEG tool format.
        lower_right (str): Coordinates of the lower right corner in the HEG tool format.
    """
    # Read the text file into a DataFrame skipping the first two rows as they are info
    df_txt = pd.read_csv(txt_file, skiprows=2)

    # Import KML driver for reading the KML file
    fiona.supported_drivers["KML"] = "rw"

    # Read the kml file and extract the aoi polygon
    poly_aoi = gpd.read_file(kml_path, driver="KML", crs="EPSG:4326")

    # Extract geometry of the AOI
    aoi_geometry = poly_aoi.geometry.iloc[0]

    # Extract upper left and lower right coordinates and put it into the HEG readable format
    xmin, ymin, xmax, ymax = (
        aoi_geometry.bounds
    )  # .bounds gets the minumum bounding box (so the xmin, ymax, xmax, ymin) coordinates

    upper_left = "( " + str(xmin) + " " + str(ymax) + " )"
    lower_right = "( " + str(xmax) + " " + str(ymin) + " )"

    # Convert bounding coordinates to Polygon geometries to display where the imagery is
    geometry = [
        Polygon(
            [
                (row["GRingLongitude1"], row["GRingLatitude1"]),
                (row["GRingLongitude2"], row["GRingLatitude2"]),
                (row["GRingLongitude3"], row["GRingLatitude3"]),
                (row["GRingLongitude4"], row["GRingLatitude4"]),
            ]
        )
        for index, row in df_txt.iterrows()
    ]

    # Create a GeoDataFrame to house the entries
    gdf = gpd.GeoDataFrame(df_txt, geometry=geometry, crs="EPSG:4326")

    # Filter based on AOI polygon kml
    selected_granules = gdf[gdf.intersects(aoi_geometry)]

    selected_granule = selected_granules.iloc[-1]

    # Export the selected granule to a GPKG for viewing in QGIS or another format to ensure accuracy
    # Uncomment for use:
    # export_geom.to_file(
    # "Insert your file path .gpkg",
    # driver="GPKG",
    #  )

    return str(selected_granule["# GranuleID"]), upper_left, lower_right


# Place Code Here for HDF to GeoTIFF conversion (Zacharie)--------------------------------------


# This section of the code was taken from and AI generated script to search the
# hdf file for the time
def extract_date_from_filename(filename):
    """
    This function reads in an HDF file name and returns tha date from that file.

    Parameters
    ----------
    filename : TYPE
        DESCRIPTION: Entire file path and name of the HDF file

    Returns
    -------
    hdf_date : TYPE
        DESCRIPTION.

    """
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if match:
        year = match.group(1)
        day_of_year = match.group(2)
        hdf_date = datetime.strptime(year + day_of_year, "%Y%j")
        return hdf_date
    else:
        return None


# Only changing the output file sequentially was taken from AI,and
# https://www.geeksforgeeks.org/python-program-to-replace-specific-line-in-file/
# I used this site to get started on how to modify lines of text
def modify_parameter_file(
    parameter_file_path,
    input_filename,
    output_filenames,
    ul_corner_coordinates,
    lr_corner_coordinates,
):
    """
    This function goes in and modifies the inputted parameter file to change
    the input_filename, output_filenames, the ul_corner_coordinates and the
    lr_corner_coordinates. This is to adjust the HEGTool parameters to take in the
    proper files and bounding boxes.

    Parameters
    ----------
    parameter_file_path : TYPE
        DESCRIPTION: This is the entire file path and name to the necessary txt parameter file for the HEGTool
    input_filename : TYPE
        DESCRIPTION: This is the entire file path and name to the necessary HDF file for the HEGTool
    output_filenames : TYPE
        DESCRIPTION: This is the entire file path and name for the three necessary HDF output files for the HEGTool
    ul_corner_coordinates : TYPE
        DESCRIPTION: The upper left coordinates in the proper format for the HEGTool
    lr_corner_coordinates : TYPE
        DESCRIPTION: The lower right coordinates in the proper format for the HEGTool

    Returns
    -------
    None.

    """
    with open(parameter_file_path, "r", newline="") as file:
        lines = file.readlines()

    modified_lines = []
    for line in lines:
        if line.strip().startswith("INPUT_FILENAME"):
            modified_lines.append(f"INPUT_FILENAME = {input_filename}\n")
        elif line.strip().startswith("OUTPUT_FILENAME"):
            modified_lines.append(
                f"OUTPUT_FILENAME = {output_filenames.pop(0)}\n"
            )
        elif line.strip().startswith("SPATIAL_SUBSET_UL_CORNER"):
            modified_lines.append(
                f"SPATIAL_SUBSET_UL_CORNER = {ul_corner_coordinates}\n"
            )
        elif line.strip().startswith("SPATIAL_SUBSET_LR_CORNER"):
            modified_lines.append(
                f"SPATIAL_SUBSET_LR_CORNER = {lr_corner_coordinates}\n"
            )
        else:
            modified_lines.append(line)

    with open(parameter_file_path, "w", newline="") as file:
        file.writelines(modified_lines)
        print("The parameter file has been modified")


# I found out that the file was in Windows CR LF not in Unix LF
# https://stackoverflow.com/questions/36422107/how-to-convert-crlf-to-lf-on-a-windows-machine-in-python
def convert_windows_to_unix_line_endings(file_path):
    """
    This function takes the entire parameter file txt and converts it into
    the proper Unix (LF) that it need to be in

    Parameters
    ----------
    file_path : TYPE
        DESCRIPTION: The entire file path and name of the parameter file

    Returns
    -------
    None.

    """
    WINDOWS_LINE_ENDING = b"\r\n"
    UNIX_LINE_ENDING = b"\n"

    try:
        with open(file_path, "rb") as open_file:
            content = open_file.read()

        content = content.replace(WINDOWS_LINE_ENDING, UNIX_LINE_ENDING)

        with open(file_path, "wb") as open_file:
            open_file.write(content)

        print(
            f"Line endings converted from Windows (CRLF) to Unix (LF) in {file_path}"
        )
    except IOError:
        print(f"Error: Unable to open or modify file {file_path}")


def get_newest_hdf_file(hdf_directory):
    """
    Find the newest HDF file in the specified directory.

    Parameters:
    - hdf_directory (str): Path to the directory containing HDF files.

    Returns:
    - input_hdf_filename (str): Filename of the newest HDF file, or None if no HDF files are found.
    """
    # Use glob to find all HDF files in the directory
    hdf_files = glob.glob(os.path.join(hdf_directory, "*.hdf"))

    # Sort the HDF files by modification time (newest first)
    hdf_files.sort(key=os.path.getmtime, reverse=True)

    # Grab the newest HDF file if it exists
    if hdf_files:
        newest_hdf_file = hdf_files[0]
        print("Newest HDF file:", newest_hdf_file)
        return newest_hdf_file
    else:
        print("No HDF files found in the directory.")
        return None


def add_datetime_to_filenames(
    directory_path, base_filenames, formatted_datetime
):
    """
    This function takes in the path where you want the output HDF files to be in
    and add the date taken from the HDF and add the base_filename in that order.

    Parameters
    ----------
    directory_path : TYPE
        DESCRIPTION.
    base_filenames : TYPE
        DESCRIPTION.
    formatted_datetime : TYPE
        DESCRIPTION.

    Returns
    -------
    new_filenames : TYPE
        DESCRIPTION.

    """
    new_filenames = []
    for filename in base_filenames:
        # Split the file name and extension
        base_name, extension = os.path.splitext(filename)
        # Create the new filename with datetime and the original extension
        new_filename = os.path.join(
            directory_path,
            f"{formatted_datetime}_MODIS_SWATH_TYPE_L2_{base_name}{extension}",
        )
        new_filenames.append(new_filename)

    return new_filenames


# Place Code here for GeoTIFF merge (Philip) -------------------------------------------
# Resources used: Code snippet provided by Derek, AI and https://rasterio.readthedocs.io/en/stable/topics/color.html
def merge_raster(band1_path, band2_path, band3_path, output_path):
    """
    Create an RGB image from three grayscale GeoTIFF bands.

    Parameters:
        band1_path (str): Path to the first grayscale GeoTIFF file.
        band2_path (str): Path to the second grayscale GeoTIFF file.
        band3_path (str): Path to the third grayscale GeoTIFF file.
        output_path (str): Path to the output RGB GeoTIFF file.
    """
    # Open grayscale GeoTIFF files
    with rasterio.open(band1_path) as src1, rasterio.open(
        band2_path
    ) as src2, rasterio.open(band3_path) as src3:
        b1 = src1.read(1)  # Read band 1
        b2 = src2.read(1)  # Read band 2
        b3 = src3.read(1)  # Read band 3

    # Stack bands into an array
    b123 = np.stack([b1, b2, b3], axis=-1)

    # Get metadata from one of the input files
    with rasterio.open(band1_path) as src:
        meta = src.meta.copy()
        meta.update(count=3)  # Update the band count to 3 for RGB
        meta.update(
            dtype="uint8"
        )  # Update the data type to ensure RGB interpretation
        meta.update(nodata=None)  # Remove nodata value

    # Write stacked RGB image to output file
    with rasterio.open(output_path, "w", **meta) as dst:
        for i in range(3):  # Loop through each band
            dst.write(
                b123[:, :, i], i + 1
            )  # Write each band with the correct index (starting from 1)

    # Update color interpretation of bands
    with rasterio.open(output_path, "r+") as src:
        src.colorinterp = [
            ColorInterp.red,
            ColorInterp.green,
            ColorInterp.blue,
        ]

    print("RGB image saved as '{}'".format(output_path))


# Place Code here for Georeferencing------------------------------------------


def getgt_proj(input_image):
    """
    Fetches the geotransform and projection of a given input image.

    Parameters:
    - input_image: Path to the input image file.

    Returns:
    A tuple containing (geotransform, projection).
    """
    # Open the image
    ds = gdal.Open(input_image)

    # Initialize return values
    geotransform, projection = None, None

    # Fetch geotransformation
    geotransform = ds.GetGeoTransform()
    if geotransform:
        print("Geotransform:", geotransform)

    # Fetch projection
    projection = ds.GetProjection()
    if projection:
        print("Projection:", projection)

    # Close the dataset
    ds = None

    # Return the geotransform and projection
    return geotransform, projection


def georeference_image(input_image, output_image, geotransform, projection):
    """
    Georeferences an image using GDAL.Together these steps open an existing image file, create a georeferenced copy of it by setting its geotransformation and projection, and save it as a new GeoTIFF.

    Parameters:
    - input_image: Path to the input image.
    - output_image: Path to the output georeferenced image.
    - geotransform: Geotransform tuple for the image.
    - projection: Projection as a WKT string.
    """
    # Open the input image
    src = gdal.Open(
        input_image, gdal.GA_ReadOnly
    )  # The input image file is opened in read-only mode so it cannot be modified
    driver = gdal.GetDriverByName("GTiff")  # I assume our image is a GeoTiff ?

    # Create the output image that is a copy of the source image
    dst = driver.CreateCopy(
        output_image, src, 0
    )  # Creates a copy (dst) of the source dataset (src). The '0' argument indicates no additional options are passed to CreatCopy

    # Set the geotransformation and projection
    dst.SetGeoTransform(
        geotransform
    )  # 'geotransform' specifies how pixels in the raster geographically coordinate. It contains 6 coefficients which define the transformation
    dst.SetProjection(
        projection
    )  # The projection is specified as Well-Known Text (WKT)

    # Close the datasets
    dst = None
    src = None
    print("Georeferencing complete.")


# Place Code here for GeoTIFF to KML conversion (Shea) ------------------------------
def convert_to_kmz(input_tiff, output_kmz):
    """
    Converts a GeoTIFF image to KMZ format using GDAL.

    Parameters:
    - input_tiff: Path to the input GeoTIFF image.
    - output_kmz: Path to the output KMZ file.
    """
    # 'gdal_translate' is a GDAL utility used to convert raster data between different formats, '-of' 'KMLSUPEROVERLAY' specify the output format
    command = [
        "gdal_translate",
        "-of",
        "KMLSUPEROVERLAY",
        input_tiff,
        output_kmz,
    ]
    subprocess.run(command)
    print("Conversion to KMZ complete.")


# Place Code to Read from config file (Zacharie) -------------------------------------------------


def getargs():
    """
    Get command line arguments.

    Returns
    -------
    cfg_path : str
        path to config file

    """

    parser = argparse.ArgumentParser(description="Process a file path.")

    # add an argument for configfile
    parser.add_argument(
        "configfile",
        type=str,
        help="enter the full path and name of your config file",
    )
    # now make a list of all the arguments
    args = parser.parse_args()
    cfg_path = args.configfile
    return cfg_path


def getconfig(cfg_path):
    """
    This function takes in the configuration file path and returns all the
    variables found within

    Parameters
    ----------
    cfg_path : TYPE
        DESCRIPTION.

    Returns
    -------
    parameter_file_path : TYPE
        DESCRIPTION.
    directory_path : TYPE
        DESCRIPTION.
    hdf_directory : TYPE
        DESCRIPTION.
    base_filenames : TYPE
        DESCRIPTION.
    working_directory : TYPE
        DESCRIPTION.
    MRTBINDIR : TYPE
        DESCRIPTION.
    PGSHOME : TYPE
        DESCRIPTION.
    MRTDATADIR : TYPE
        DESCRIPTION.
    auth_token : TYPE
        DESCRIPTION.
    download_HDF_directory : TYPE
        DESCRIPTION.
    download_txt_directory : TYPE
        DESCRIPTION.
    base_txt_url : TYPE
        DESCRIPTION.
    base_HDF_url : TYPE
        DESCRIPTION.
    kml_path : TYPE
        DESCRIPTION.

    """

    cfg = os.path.expanduser(cfg_path)
    config = RawConfigParser()  # run the parser

    try:
        config.read(cfg)  # read file
        # now get the variables stored in the config file
        # there are 3 categories - names, logging, and settings

        parameter_file_path = config.get("Paths", "parameter_file_path")
        directory_path = config.get("Paths", "directory_path")
        hdf_directory = config.get("Paths", "hdf_directory")

        base_filenames = config.get("Names", "base_filenames")
        working_directory = config.get("HegTool", "working_directory")
        MRTBINDIR = config.get("HegTool", "MRTBINDIR")
        PGSHOME = config.get("HegTool", "PGSHOME")
        MRTDATADIR = config.get("HegTool", "MRTDATADIR")
        auth_token = config.get("LANCE", "auth_token")
        download_HDF_directory = config.get("LANCE", "download_HDF_directory")
        download_txt_directory = config.get("LANCE", "download_txt_directory")
        base_txt_url = config.get("LANCE", "base_txt_url")
        base_HDF_url = config.get("LANCE", "base_HDF_url")
        kml_path = config.get("BoundingBox", "kml_path")

    except:
        print(
            "Trouble reading config file, please check the file and path are valid\n"
        )
        sys.exit(1)

    return (
        parameter_file_path,
        directory_path,
        hdf_directory,
        base_filenames,
        working_directory,
        MRTBINDIR,
        PGSHOME,
        MRTDATADIR,
        auth_token,
        download_HDF_directory,
        download_txt_directory,
        base_txt_url,
        base_HDF_url,
        kml_path,
    )


def main():
    """Run script - main function."""

    # get the config file name
    configfile = getargs()
    # read in the config info
    (
        parameter_file_path,
        directory_path,
        hdf_directory,
        base_filenames,
        working_directory,
        MRTBINDIR,
        PGSHOME,
        MRTDATADIR,
        auth_token,
        download_HDF_directory,
        download_txt_directory,
        base_txt_url,
        base_HDF_url,
        kml_path,
    ) = getconfig(configfile)

    # Split the string using a space delimiter (you can change this based on the actual delimiter)
    try:
        # need to parse out the names of the contestants
        # first put each line in a list and remove spaces
        base_filenames = [x.strip() for x in base_filenames.splitlines()]
        # then remove empty rows
        base_filenames = [
            base_filenames
            for base_filenames in base_filenames
            if base_filenames
        ]

        print(base_filenames)
    except:
        print("There was an error in splitting the base file names")

    # Get the date from today in UTC time to build the correct url for txt download
    # Get the current UTC date and time
    t = datetime.utcnow()

    # Format the date string for the text file name
    txt_file_name = datetime.strftime(t, "MYD03_%Y-%m-%d.txt")

    # Construct the full URL for the text file download
    txt_url_full = (
        '"' + base_txt_url + datetime.strftime(t, "%Y/") + txt_file_name + '"'
    )

    # Download the txt file for that day
    #   download_txt_file(txt_url_full, auth_token, download_txt_directory)

    print("--------------------------")

    hdf_year = datetime.strftime(t, "%Y/0")
    day_of_year = str(t.timetuple().tm_yday)

    granule_id, upper_left, lower_right = extract_granule_id(
        download_txt_directory, kml_path
    )
    print("--------------------------")
    print(granule_id)
    print("--------------------------")

    # This part read the txt file and places all the HDF ID's in lists with their info and bounding coordinates
    hdf_url_full = (
        '"' + base_HDF_url + hdf_year + day_of_year + "/" + granule_id + '"'
    )
    print(hdf_url_full)
    # This line downloads the hdf file with the full url with new hdf file name
    # download_HDF_file(hdf_url_full, auth_token, download_HDF_directory)

    # This line takes the newest file in the hdf directory
    input_hdf_filename = get_newest_hdf_file(hdf_directory)
    print("--------------------------")
    print(input_hdf_filename)
    # Extract date from hdf file
    hdf_date = extract_date_from_filename(input_hdf_filename)

    if hdf_date:
        formatted_datetime = hdf_date.strftime("%Y-%m-%d_%H.%M")
        print("Extracted Date from HDF Filename:", formatted_datetime)
    else:
        print("Failed to extract date from HDF filename.")

    new_date_output_filenames = add_datetime_to_filenames(
        directory_path, base_filenames, formatted_datetime
    )

    # Split the path from the file name for each file in new_date_output_filenames for later geotiff merge
    file_names_only = [
        os.path.split(file_path)[1] for file_path in new_date_output_filenames
    ]
    print("--------------------------")
    print(upper_left)

    input_hdf_filename = "MOD09.A2024088.2035.061.2024088213921.NRT.hdf"

    # This section modifies the parameter file for the HEGTool to run
    modify_parameter_file(
        parameter_file_path,
        input_hdf_filename,
        new_date_output_filenames,
        upper_left,
        lower_right,
    )
    # This makes sure that the file is still in the correct Unix LF format
    convert_windows_to_unix_line_endings(parameter_file_path)

    # Set environment variables
    os.environ["MRTBINDIR"] = MRTBINDIR
    os.environ["PGSHOME"] = PGSHOME
    os.environ["MRTDATADIR"] = MRTDATADIR

    # Set the working directory
    os.chdir(working_directory)

    # Command to run HegTool with the parameter file
    # https://www.hdfeos.org/software/heg.php

    command = [
        "swtif",
        "-p",
        parameter_file_path,
    ]

    """try:
        # Execute the command
        subprocess.run(command, shell=True)
        print("HegTool executed successfully.")
    except subprocess.CalledProcessError as e:
        # Handle error if the command fails
        print("Error running HegTool:", e)
        """
    directory_path = r"C:\Users\zachs\Desktop\tmp\testing\TIFF_Bands"

    os.chdir(directory_path)

    output_GeoTIFF_combined = (
        r"C:\Users\zachs\Desktop\tmp\testing\Merged_TIFF\MOD9_Merged_test.tif"
    )

    band1_path = r"C:\Users\zachs\Desktop\tmp\testing\TIFF_Bands\MOD09.A2018237.0145.061.2021339074858_MODIS_SWATH_TYPE_L2_Band1.tif"
    band2_path = r"C:\Users\zachs\Desktop\tmp\testing\TIFF_Bands\MOD09.A2018237.0145.061.2021339074858_MODIS_SWATH_TYPE_L2_Band2.tif"
    band3_path = r"C:\Users\zachs\Desktop\tmp\testing\TIFF_Bands\MOD09.A2018237.0145.061.2021339074858_MODIS_SWATH_TYPE_L2_Band3.tif"

    merge_raster(band1_path, band2_path, band3_path, output_GeoTIFF_combined)

    output_GeoTIFF_combined = "MOD9_Merged_test.tif"

    input_image_path = (
        r"C:\Users\zachs\Desktop\tmp\testing\Merged_TIFF\MOD9_Merged_test.tif"
    )

    geotransform, projection = getgt_proj(input_image_path)

    output_image = r"C:\Users\zachs\Desktop\tmp\testing\Merged_TIFF\GepReferemced_test.tif"
    georeference_image(
        input_image_path, output_image, geotransform, projection
    )

    input_tiff = output_image
    output_kmz = (
        r"C:\Users\zachs\Desktop\tmp\testing\Merged_TIFF\MOD9_Test_KML.kml"
    )
    convert_to_kmz(input_tiff, output_kmz)


if __name__ == "__main__":
    main()
