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


# Place Code Here for API and image download -------------------------------------------


# Place Code Here for HDF to GeoTIFF conversion (Zacharie)--------------------------------------


# This section of the code was taken from and AI generated script to search the
# hdf file for the time
def extract_date_from_filename(filename):
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if match:
        year = match.group(1)
        day_of_year = match.group(2)
        # Convert day of year to datetime
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
    # Read the contents of the parameter file
    with open(parameter_file_path, "r") as file:
        lines = file.readlines()

    # Modify the lines containing INPUT_FILENAME
    modified_lines = []
    for line in lines:
        if line.strip().startswith("INPUT_FILENAME"):
            modified_lines.append(f"INPUT_FILENAME = {input_filename}\n")
        elif line.strip().startswith("OUTPUT_FILENAME"):
            # Change the output filename sequentially
            modified_lines.append(
                f"OUTPUT_FILENAME = {output_filenames.pop(0)}\n"
            )
        else:
            modified_lines.append(line)

    # Write the modified contents back to the parameter file
    with open(parameter_file_path, "w") as file:
        file.writelines(modified_lines)
        print("The parameter file has been modified")


# Define the directory containing HDF files
hdf_directory = r"C:\Users\zachs\Desktop\tmp\Phillip_Data"

# Use glob to find all HDF files in the directory
hdf_files = glob.glob(os.path.join(hdf_directory, "*.hdf"))

# Sort the HDF files by modification time (newest first)
# https://www.geeksforgeeks.org/get-sorted-file-names-from-a-directory-by-creation-date-in-python/
# https://docs.python.org/3/howto/sorting.html
# I used these to get know how to get time and sort
hdf_files.sort(key=os.path.getmtime, reverse=True)

if hdf_files:
    # Get the newest HDF file
    newest_hdf_file = hdf_files[0]
    print("Newest HDF file:", newest_hdf_file)
else:
    print("No HDF files found in the directory.")


# Set parameter file path, input and output file names
parameter_file_path = (
    r"C:\Users\zachs\Desktop\tmp\Phillip_Data\image_project_swath.prm"
)
input_hdf_filename = newest_hdf_file
output_filenames = [
    r"C:\Users\zachs\Desktop\tmp\MODIS_SWATH_TYPE_L2_Band1.tif",
    r"C:\Users\zachs\Desktop\tmp\MODIS_SWATH_TYPE_L2_Band2.tif",
    r"C:\Users\zachs\Desktop\tmp\MODIS_SWATH_TYPE_L2_Band3.tif",
]


# Extract date from hdf file
hdf_date = extract_date_from_filename(input_hdf_filename)

if hdf_date:
    formatted_datetime = hdf_date.strftime("%Y-%m-%d_%H:%M")
    print("Extracted Date from HDF Filename:", formatted_datetime)
else:
    print("Failed to extract date from HDF filename.")


# Create new output filenames with datetime before "MODIS_SWATH_TYPE_L2_cmdtest3.tif"
datetime_output_filenames = []
for filename in output_filenames:
    # Get the directory path
    directory_path = os.path.dirname(filename)
    # Get the filename without extension
    base_filename = os.path.splitext(os.path.basename(filename))[0]
    # Create the new filename
    new_filename = f"{directory_path}\\{formatted_datetime}_MODIS_SWATH_TYPE_L2_{base_filename.split('_')[-1]}.tif"
    # Append new filename to the list
    datetime_output_filenames.append(new_filename)

modify_parameter_file(
    parameter_file_path, input_hdf_filename, datetime_output_filenames
)


# Set environment variables
# https://developer.vonage.com/en/blog/python-environment-variables-a-primer#how-to-set-python-environment-variables
# Used this to find out how to set environment variable
os.environ["MRTBINDIR"] = r"C:\Users\zachs\Desktop\HEGTool\HEG_Win\bin"
os.environ["PGSHOME"] = r"C:\Users\zachs\Desktop\HEGTool\HEG_Win\TOOLKIT_MTD"
os.environ["MRTDATADIR"] = r"C:\Users\zachs\Desktop\HEGTool\HEG_Win\data"

# Set the working directory
os.chdir(r"C:\Users\zachs\Desktop\HEGTool\HEG_Win\bin")


# Command to run HegTool with the parameter file
# https://www.hdfeos.org/software/heg.php
command = (
    r"swtif -p C:\Users\zachs\Desktop\tmp\Phillip_Data\image_project_swath.prm"
)

try:
    # Execute the command
    subprocess.run(command, check=True)
    print("HegTool executed successfully.")
except subprocess.CalledProcessError as e:
    # Handle error if the command fails
    print("Error running HegTool:", e)


# Place Code here for GeoTIFF merge-------------------------------------------


# Place Code here for Georeferencing------------------------------------------

from osgeo import gdal, ogr, osr
import subprocess


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


# Place Code here for GeoTIFF to KML conversion------------------------------
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
