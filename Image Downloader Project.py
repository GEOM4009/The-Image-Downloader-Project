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
from owslib.wms import WebMapService
import rasterio
from rasterio.merge import merge
from rasterio.enums import Resampling
from osgeo import gdal, ogr, osr
import subprocess
import argparse
from configparser import RawConfigParser
import sys


# Place Code Here for API and image download (Collin) -------------------------------------------
def wms_image(layer_name, bbox, time, output_format="image/png"):
    """
    Grabs an image from a Web Map Service (WMS version 1.3.0) and returns the image data as either png or jpeg.
    An example use case can use the entire worldview boudning box of (-180, -90, 180, 90)
    As of right now the imagery cannot be accessed in NRT, but it says on the API documentation that it is possible see: https://nasa-gibs.github.io/gibs-api-docs/access-basics/
    To grab the wms imagery I referenced the GIBS API examples that can be found here: https://nasa-gibs.github.io/gibs-api-docs/python-usage/
    Params:
    - layer_name (str): The name of the satellite layer.
    - bbox (tuple): The bounding box coordinates for the image.
    - time (str): The time of the data in ISO8601 format (supposed to be sub-daily but will not accept it despite offering NRT imagery)
    - output_format (str): The format of the image to save. Default is 'image/png'.

    Returns:
    - img_data: The binary image data from WMS.
    """
    # Connect to the GIBS WMS Service
    wms = WebMapService(
        "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi?",
        version="1.3.0",
    )

    # Get the image from the WMS service GIBS endpoint
    img = wms.getmap(
        layers=[layer_name],  # Layer name
        srs="epsg:4326",  # Map projection
        bbox=bbox,  # Bounding box
        size=(1200, 600),  # Image size
        time=time,  # Time variable
        format=output_format,  # Image format
        transparent=True,
    )  # Nodata transparency

    # Read the binary image data
    img_data = img.read()

    return img_data


def save_image(img_data, output_file):
    """
    Saves the given image data to an output file.
    The code was inspired by Derek's code using Rasterio to open and save the imagery. I decided to use the Python built in file handling operations
    Such as .write to write the binary data as the rasterio expects an array.

    Args:
    - img_data: The binary image data to save grabbed from the wms function.
    - output_file (str): The path to the output file.
    """
    # Save the image data to a file using Python's built in file operations
    with open(output_file, "wb") as f:
        f.write(img_data)


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

    # Use glob to find all HDF files in the directory
    hdf_files = glob.glob(os.path.join(hdf_directory, "*.hdf"))

    # Sort the HDF files by modification time (newest first)
    hdf_files.sort(key=os.path.getmtime, reverse=True)
    # Grab the newest HDF file
    if hdf_files:
        newest_hdf_file = hdf_files[0]
        print("Newest HDF file:", newest_hdf_file)
    else:
        print("No HDF files found in the directory.")

    input_hdf_filename = newest_hdf_file

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
