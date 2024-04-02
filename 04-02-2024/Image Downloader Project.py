# -*- coding: utf-8 -*-
"""
Created on Fri Mar 12 11:42:00 2024

@author: Philip, Shea, Collin and Zacharie

# $ need a proper docstring for the file
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
import shutil

# Import KML driver for reading the KML file
# $ I don't seem to have that driver and so I put LIBKML here
fiona.supported_drivers[
    "LIBKML"
] = "rw"  # $ you might want to put this line near the imports above the functions


# New API download from LANCE NRT with token access (Zacharie)
def download_HDF_file(url, auth_token, download_HDF_dir):
    """
    Download an HDF file using wget command.

    Parameters:
    - url (str): URL of the HDF file to download.
    - auth_token (str): Authorization token for the request.
    - download_dir (str): Directory where the HDF file will be saved.


    # $ This and many other function docstrings don't follow the numpydoc convention, this
    will be problem for Sphinx.

    """
    # $ check that the words Authorization Bearer: is not in there x2 by removing that in config file
    # $ I got a missing url error, check that there is no problem with quotes.
    # $ also I am running on linux so my behaviour is different from yours I think.  https://stackoverflow.com/questions/15109665/subprocess-call-using-string-vs-using-list

    command = [
        "wget",
        url,
        "--header",
        f"Authorization: Bearer {auth_token}",  # $ changed the quoting behaviour for shell=False
        "-P",
        download_HDF_dir,
    ]

    """
        try:
            # Execute the wget command
            subprocess.run(
                command, shell=False
            )  # $ Derek changed this to shell=False, see stack overflow above
            print("HDF file downloaded successfully.")
        except subprocess.CalledProcessError as e:
            # Handle error if the command fails
            print("Error downloading HDF file:", e)
    """
    # $ need more refined erorr handling here. It may be that the latest file is not there yet.

    try:
        # Execute the wget command
        result = subprocess.run(
            command, shell=False
        )  # $ Derek changed this to shell=False, see stack overflow above
        if result.returncode == 0:
            print("HDF file downloaded successfully.")
            return "ok"
        elif result.returncode == 8:
            print("HDF file not found...  it may not be available yet...")
            return "not found"
        else:
            print("HDF file download didn't work out... Try debugging the code")
            return "error"

    except subprocess.CalledProcessError as e:
        # Handle error if the command fails
        print("Error downloading HDF file:", e)


def download_txt_file(url, auth_token, download_txt_dir):
    """
    Download an txt file using wget command.
    # $ don't copy paste your docstrings, some of this info is confusing/wrong'
    Parameters:
    - url (str): URL of the HDF file to download.
    - auth_token (str): Authorization token for the request.
    - download_dir (str): Directory where the HDF file will be saved.
    """
    command = [
        "wget",
        url,
        "--header",
        f"Authorization: Bearer {auth_token}",  # $ changed the quoting behaviour for shell=False
        "-O",
        download_txt_dir,  # This variable is a file not a dir so maybe rename it?
    ]
    # $ check that the words Authorization Bearer: is not in there x2 by removing that in config file
    # $ I got a missing url error, check that there is no problem with quotes.
    # $ also I am running on linux so my behaviour is different from yours I think.  https://stackoverflow.com/questions/15109665/subprocess-call-using-string-vs-using-list

    try:
        # Execute the wget command
        subprocess.run(
            command, shell=False
        )  # $ Derek changed this to shell=False, see stack overflow above
        print("HDF file downloaded successfully.")  # $ this is not an HDF File
    except subprocess.CalledProcessError as e:
        # Handle error if the command fails
        print("Error downloading HDF file:", e)


# Text file processing function--------- (Collin)
def extract_granule_id(txt_file, kml_path, testmode):
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
        testmode (str): A string representing the date/time for a test run (yyyy-mm-dd hh:mm)
    Returns:
        selected_granuleID (str): A string containing the GranuleID for the hdf download request.
        selected_granuleID (str): The selected granuleID.
        upper_left (str): Coordinates of the upper left corner in the HEG tool format.
        lower_right (str): Coordinates of the lower right corner in the HEG tool format.
    """
    # Read the text file into a DataFrame skipping the first two rows as they are info
    df_txt = pd.read_csv(txt_file, skiprows=2)

    # Import KML driver for reading the KML file
    # fiona.supported_drivers[
    #    "KML"
    # ] = "rw"  # $ you might want to put this line near the imports above the functions

    # Read the kml file and extract the aoi polygon
    poly_aoi = gpd.read_file(kml_path, driver="LIBKML", crs="EPSG:4326")

    # Extract geometry of the AOI
    aoi_geometry = poly_aoi.geometry.iloc[0]

    # Extract upper left and lower right coordinates and put it into the HEG readable format
    (
        xmin,
        ymin,
        xmax,
        ymax,
    ) = (
        aoi_geometry.bounds
    )  # .bounds gets the minumum bounding box (so the xmin, ymax, xmax, ymin) coordinates

    # $ for the parameter file you need lat and then lon - I reversed these
    upper_left = "( " + str(ymax) + " " + str(xmin) + " )"
    lower_right = "( " + str(ymin) + " " + str(xmax) + " )"

    # Convert bounding coordinates to Polygon geometries to display where the imagery is
    # $ just so you know, this doesn't work for images crossing -180degs.  You might filter them out
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
    # $ this will export the df:
    # gdf.to_file("test_allmodis.kml", driver="KML")
    # Filter based on AOI polygon kml
    # $ Should trap errors here if no modis images intersect!
    selected_granules = gdf[gdf.intersects(aoi_geometry)]
    # $ remove night images
    selected_granules = selected_granules[selected_granules.DayNightFlag == "D"]
    selected_granules.reset_index(drop=True, inplace=True)
    # $ this will export the df:
    selected_granules.to_file("test_selectedmodis.kml", driver="LIBKML")
    # $ adding here for testmode
    if testmode == "":
        selected_granule = selected_granules.iloc[-1]
    else:
        # $ test mode always gets the closest image in time to the time specified
        t = datetime.strptime(testmode, "%Y-%m-%d %H:%M")
        # $ should use loc instead..  come back to fix...
        selected_granules["StartDateTime"] = pd.to_datetime(
            selected_granules["StartDateTime"]
        )
        deltat = selected_granules["StartDateTime"] - t
        selected_granule = selected_granules.iloc[deltat.dt.seconds.idxmin()]

    # $ this code here in the comment doesn't work
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
    """    
    match = re.search(r"A(\d{4})(\d{3})", filename)
    if match:
        year = match.group(1)
        day_of_year = match.group(2)
        hdf_date = datetime.strptime(year + day_of_year, "%Y%j")
        else:
            
        return hdf_date
    else:
        return None
    """
    # $ rewriting this function to make it simpler and more complete (no error handling though!)
    dt = os.path.basename(filename)[
        7:19
    ]  # $ note that you can use position to get info too.
    hdf_date = datetime.strptime(dt, "%Y%j.%H%M")
    return hdf_date


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
            modified_lines.append(f"OUTPUT_FILENAME = {output_filenames.pop(0)}\n")
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

        print(f"Line endings converted from Windows (CRLF) to Unix (LF) in {file_path}")
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


def add_datetime_to_filenames(directory_path, base_filenames, formatted_datetime):
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

    # $ rescale the image to byte
    # $ create a masked image that ignores the no data value
    # https://stackoverflow.com/questions/49922460/scale-a-numpy-array-with-from-0-1-0-2-to-0-255
    b123masked = np.ma.masked_equal(b123, -28672)  # $ this is the no data value
    scaled = (
        (b123masked - np.min(b123masked))
        * (1 / (np.max(b123masked) - np.min(b123masked)) * 255)
    ).astype("uint8")
    # scaled = np.interp(b123masked, (np.min(b123masked), np.max(b123masked)), (0, 255)).astype("uint8")
    # $ to view?!
    # from matplotlib import pyplot as plt
    # plt.imshow(scaled_img)
    # Get metadata from one of the input files
    with rasterio.open(band1_path) as src:
        meta = src.meta.copy()
        meta.update(count=3)  # Update the band count to 3 for RGB
        # $ if you want to do this you need to actually change the data from int16 to uint8, otherwise it won't work... Look up scale numpy array to 0-255
        meta.update(dtype="uint8")  # Update the data type to ensure RGB interpretation
        meta.update(nodata=0)  # Remove nodata value

    # Write stacked RGB image to output file
    with rasterio.open(output_path, "w", **meta) as dst:
        for i in range(3):  # Loop through each band
            dst.write(
                scaled[:, :, i], i + 1
            )  # Write each band with the correct index (starting from 1)

    # # Update color interpretation of bands
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
    metadata_file : TYPE
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
        metadata_file = config.get("LANCE", "metadata_file")
        base_txt_url = config.get("LANCE", "base_txt_url")
        base_HDF_url = config.get("LANCE", "base_HDF_url")
        test_time = config.get("LANCE", "test_time")
        kml_path = config.get("BoundingBox", "kml_path")

    except:
        print("Trouble reading config file, please check the file and path are valid\n")
        sys.exit(1)

    return (  # $ maybe a dictionary would be an easier way to gather this all together?
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
        metadata_file,
        base_txt_url,
        base_HDF_url,
        test_time,
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
        metadata_file,
        base_txt_url,
        base_HDF_url,
        test_time,
        kml_path,
    ) = getconfig(configfile)

    # Split the string using a space delimiter (you can change this based on the actual delimiter)
    try:
        # $ update this comment --> there are no contestants here!
        # need to parse out the names of the contestants
        # first put each line in a list and remove spaces
        base_filenames = [x.strip() for x in base_filenames.splitlines()]
        # then remove empty rows
        base_filenames = [
            base_filenames for base_filenames in base_filenames if base_filenames
        ]

        print(base_filenames)
    except:
        print("There was an error in splitting the base file names")

    # Get the date from today in UTC time to build the correct url for txt download
    # $ I suggest you add a variable in the config file called testmode (or similar).
    # $ if test mode is true, then it might override the t = now and put in a timestamp that would
    # $ result in a given image, that way when you run the script it will give exactly the same kmz as
    # $ you have in the test output file

    # Get the current UTC date and time
    if test_time == "":
        t = datetime.utcnow()
    else:
        t = datetime.strptime(test_time, "%Y-%m-%d %H:%M")

    # Format the date string for the text file name
    txt_file_name = datetime.strftime(t, "MYD03_%Y-%m-%d.txt")

    # $ I removed the quotes here since I think they caused an error
    # Construct the full URL for the text file download
    txt_url_full = base_txt_url + datetime.strftime(t, "%Y/") + txt_file_name

    # Download the txt file for that day
    # $ This line was commented out, but you need it to run your script!
    download_txt_file(txt_url_full, auth_token, metadata_file)

    print("--------------------------")

    hdf_year = datetime.strftime(t, "%Y/0")
    day_of_year = str(t.timetuple().tm_yday)

    granule_id, upper_left, lower_right = extract_granule_id(
        metadata_file, kml_path, test_time
    )

    """
    # $ this code doesn't work. replaced with lines below    
    print("--------------------------")
    print(granule_id)
    print("--------------------------")

    # This part read the txt file and places all the HDF ID's in lists with their info and bounding coordinates
    
    hdf_url_full = (
        base_HDF_url + hdf_year + day_of_year + "/" + granule_id
    )  # $ removed extra quoting here
    """

    # $ you can't work with the MYD03 file you have retrieved from the metadata.
    # $ Remember you need the equivalent MYD09 file!!!
    # $ you must modfify granule_id to match the MYD09 filename you want:
    granule_id = granule_id[:4] + "9" + granule_id[5:19] + ".061.NRT.hdf"

    print("--------------------------")
    print(f"Found matching MODIS image: {granule_id}")
    print("--------------------------")

    # $ you need to replace the base_HDF_url in the config file with:
    # $ base_HDF_url = https://nrt3.modaps.eosdis.nasa.gov/api/v2/content/archives/allData/61/MYD09/Recent

    # $ here is the new wa
    hdf_url_full = base_HDF_url + "/" + granule_id
    print(f"Downloding... {hdf_url_full}....")
    # This line downloads the hdf file with the full url with new hdf file name
    # $ this line of code needs to be uncommented for the code to work!
    # $ added a condition so you don't download the file more than once
    if not os.path.isfile(os.path.join(download_HDF_directory, granule_id)):
        msg = download_HDF_file(hdf_url_full, auth_token, download_HDF_directory)

        # $ no sense going on without the image you need.
        if msg != "ok":
            sys.exit(1)

    # $ not sure what this is needed for... replacing with the name of the file that was just downloaded
    """
    # This line takes the newest file in the hdf directory
    input_hdf_filename = get_newest_hdf_file(
        download_HDF_directory
    )  # $ you want the download_HDF_directory here
    print("--------------------------")
    print(input_hdf_filename)
    """
    input_hdf_filename = os.path.join(download_HDF_directory, granule_id)
    # Extract date from hdf file
    hdf_date = extract_date_from_filename(input_hdf_filename)
    # $ note only date is retrieved, not time?!
    if hdf_date:
        formatted_datetime = hdf_date.strftime("%Y-%m-%d_%H:%M")  # $ replaced . with :
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

    # $ comment this out! input_hdf_filename = "MOD09.A2024088.2035.061.2024088213921.NRT.hdf"
    # $ copy the list above to a tuple because it gets modified by the function below
    tifbands = tuple(new_date_output_filenames)

    # This section modifies the parameter file for the HEGTool to run
    modify_parameter_file(
        parameter_file_path,
        input_hdf_filename,
        new_date_output_filenames,
        upper_left,  # $ lat and lon reversed!
        lower_right,  # $ lat and lon reversed!
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
        "./swtif",  # $ I added ./ here due to linux path issues... but don't do this for windows
        "-p",
        parameter_file_path,
    ]

    try:
        # Execute the command
        subprocess.run(command, shell=False)  # $ changed shell from true to false
        print("HegTool executed successfully.")
    except subprocess.CalledProcessError as e:
        # Handle error if the command fails
        print("Error running HegTool:", e)

    # $ comment this out! directory_path = r"C:\Users\zachs\Desktop\tmp\testing\TIFF_Bands"
    os.chdir(
        directory_path
    )  # $ just a comment here 'directory_path' is not a helpful variable name

    # $ use values from config file and what you have done above!
    output_GeoTIFF_combined = os.path.join(
        download_HDF_directory, f"{formatted_datetime}_aqua.tif"
    )

    merge_raster(tifbands[0], tifbands[1], tifbands[2], output_GeoTIFF_combined)

    """
    # $ code not needed was removed from here
    
    """
    # $ make a temp dir for kml
    os.chdir(download_HDF_directory)
    if not os.path.isdir("tmp"):
        os.mkdir("tmp")
    os.chdir("tmp")

    # $ If you name the file the same every time, there will only be one kml.
    # $ You might want a directory to hold all the output kmz files?
    output_kmz = f"{formatted_datetime}_aqua.kml"
    convert_to_kmz(output_GeoTIFF_combined, output_kmz)
    os.chdir("..")

    shutil.make_archive(
        f"{formatted_datetime}_aqua.kmz", "zip", root_dir="tmp", base_dir=None
    )
    shutil.move(f"{formatted_datetime}_aqua.kmz.zip", f"{formatted_datetime}_aqua.kmz")

    # $ after you convert to kml you could zip the files in to a kmz, then there would be no conflict between
    # $ the subdirectories here...

    # $ Clean up temporary files  - uncomment this when you are ready to deploy the code
    os.remove(tifbands[0])
    os.remove(tifbands[1])
    os.remove(tifbands[2])
    shutil.rmtree("tmp")
    # os.remove(output_GeoTIFF_combined)
    # $ can clean up old hdf files too...


if __name__ == "__main__":
    main()
