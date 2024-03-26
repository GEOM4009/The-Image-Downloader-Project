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
from rasterio.merge import merge
from rasterio.enums import Resampling
from osgeo import gdal
import argparse
from configparser import RawConfigParser
import sys


# Place Code Here for API and image download (Collin) -------------------------------------------


# New API download from LANCE NRT with token access (Zacharie)
def download_lance_file(url, auth_token, download_dir):
    """
    Download an HDF file using wget command.

    Parameters:
    - url (str): URL of the HDF file to download.
    - auth_token (str): Authorization token for the request.
    - download_dir (str): Directory where the HDF file will be saved.
    """
    command = [
        "wget",
        "-e",
        "robots=off",
        "-m",
        "-np",
        "-R",
        ".html,.tmp",
        "-nH",
        "--cut-dirs=4",
        url,
        "--header",
        f"Authorization: Bearer {auth_token}",
        "-P",
        download_dir,
    ]

    try:
        # Execute the wget command
        subprocess.run(command, check=True)
        print("HDF file downloaded successfully.")
    except subprocess.CalledProcessError as e:
        # Handle error if the command fails
        print("Error downloading HDF file:", e)


def extract_granule_data(filename):
    granule_data = {}  # Initialize empty dictionary to store data

    with open(filename, "r") as file:
        next(file)  # Skip header lines

        for line in file:
            elements = line.strip().split(",")  # Split line into elements

            granule_id = elements[0]
            start_datetime = elements[1]
            east_coord = float(elements[5])
            north_coord = float(elements[6])
            south_coord = float(elements[7])
            west_coord = float(elements[8])

            # Check if GranuleID already exists in the dictionary
            if granule_id in granule_data:
                # Append data to existing lists
                granule_data[granule_id]["StartDateTime"].append(
                    start_datetime
                )
                granule_data[granule_id]["EastBoundingCoord"].append(
                    east_coord
                )
                granule_data[granule_id]["NorthBoundingCoord"].append(
                    north_coord
                )
                granule_data[granule_id]["SouthBoundingCoord"].append(
                    south_coord
                )
                granule_data[granule_id]["WestBoundingCoord"].append(
                    west_coord
                )
            else:
                # Create new lists for the GranuleID
                granule_data[granule_id] = {
                    "StartDateTime": [start_datetime],
                    "EastBoundingCoord": [east_coord],
                    "NorthBoundingCoord": [north_coord],
                    "SouthBoundingCoord": [south_coord],
                    "WestBoundingCoord": [west_coord],
                }

    return granule_data  # Return the extracted data


# Place Code Here for HDF to GeoTIFF conversion (Zacharie)--------------------------------------


# This section of the code was taken from and AI generated script to search the
# hdf file for the time
def extract_date_from_filename(filename):
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
    parameter_file_path, input_filename, output_filenames
):
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
        else:
            modified_lines.append(line)

    with open(parameter_file_path, "w", newline="") as file:
        file.writelines(modified_lines)
        print("The parameter file has been modified")


# I found out that the file was in Windows CR LF not in Unix LF
# https://stackoverflow.com/questions/36422107/how-to-convert-crlf-to-lf-on-a-windows-machine-in-python
def convert_windows_to_unix_line_endings(file_path):
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
def merge_geotiffs(input_files, output_file, resampling=Resampling.nearest):
    """
    Merge multiple GeoTIFF files with 3 bands (RGB) into a single GeoTIFF file.

    Parameters:
    - input_files: List of input GeoTIFF file paths
    - output_file: Output GeoTIFF file path for the merged image
    - resampling: Resampling method (default: nearest)
    """
    # Open all input GeoTIFF files
    src_files_to_mosaic = []
    for input_file in input_files:
        src = rasterio.open(input_file)
        src_files_to_mosaic.append(src)

    # Merge the GeoTIFFs with resampling
    mosaic, out_transform = merge(
        src_files_to_mosaic, method="first", resampling=resampling
    )

    # Update metadata of the merged GeoTIFF
    out_meta = src.meta.copy()
    out_meta.update(
        {
            "driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_transform,
        }
    )

    # Write the merged GeoTIFF to disk
    with rasterio.open(output_file, "w", **out_meta) as dest:
        dest.write(mosaic)

    print("Merge complete. Output file:", output_file)


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
    ) = getconfig(configfile)

    # Get the date from today in UTC time
    t = datetime.utcnow()
    url_file_name = datetime.strftime(t, "MOD03_%Y-%m-%d.txt")
    url_year = datetime.strftime(t, "%Y/")
    url_full = (
        '"'
        + "https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/archives/archive/geoMetaMODIS/61/AQUA/"
        + url_year
        + url_file_name
        + '"'
    )
    # Start Looking through the txt file to see if there is a new HDF file with the correct AOI

    download_lance_file(url_full, auth_token, download_HDF_directory)

    # This part read the txt file and places all the HDF ID's in lists with their info and bounding coordinates

    # We need to create a function that takes our basic repository url and add the correct HDF file
    hdf_url = "https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/archives/archive/geoMetaMODIS/61/AQUA/2024/MYD03.A2024085.1650.061.2024085172648.NRT.hdf"
    # This is what needs to run in the command line to download HDF data.
    download_lance_file(hdf_url, auth_token, download_HDF_directory)
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

    input_hdf_filename = get_newest_hdf_file(hdf_directory)

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

    # Split the path from the file name for each file in new_date_output_filenames
    file_names_only = [
        os.path.split(file_path)[1] for file_path in new_date_output_filenames
    ]

    modify_parameter_file(
        parameter_file_path, input_hdf_filename, new_date_output_filenames
    )
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

    try:
        # Execute the command
        subprocess.run(command, check=True)
        print("HegTool executed successfully.")
    except subprocess.CalledProcessError as e:
        # Handle error if the command fails
        print("Error running HegTool:", e)

    os.chdir(directory_path)

    input_GeoTIFF_files = [
        file_names_only[0],
        file_names_only[1],
        file_names_only[2],
    ]

    output_GeoTIFF_combined = "MOD9_Merged_test.tif"

    # Use the integer value for nearest neighbor resampling (0)
    merge_geotiffs(input_GeoTIFF_files, output_GeoTIFF_combined, resampling=0)

    output_image = "MOD9_GeoReferenced.tif"
    input_image = output_GeoTIFF_combined

    geotransform, projection = getgt_proj(output_GeoTIFF_combined)
    georeference_image(input_image, output_image, geotransform, projection)

    input_tiff = output_image
    output_kmz = "MOD9_KML.kml"
    convert_to_kmz(input_tiff, output_kmz)


if __name__ == "__main__":
    main()
