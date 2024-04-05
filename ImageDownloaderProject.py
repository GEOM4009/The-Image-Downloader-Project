"""
Created on Fri Mar 12 11:42:00 2024

@author: Philip, Shea, Collin and Zacharie

# $ need a proper docstring for the file
"""

# import dependencies

import os
import subprocess
from datetime import datetime
import rasterio
from rasterio.enums import ColorInterp
import numpy as np
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
fiona.supported_drivers["LIBKML"] = (
    "rw"  # $ you might want to put this line near the imports above the functions
)


def download_txt_file(base_txt_url, auth_token, metadata_file):
    """
    This function runs the command line request to download the txt metadata
    file

    Parameters
    ----------
    base_txt_url : STRING
        base url for metadata download.
    auth_token : STRING
        Your MODIS authentication token.
    metadata_file : STRING
        The path and new name to your designated folder for the TXT file.

    Returns
    -------
    None.

    """

    command = [
        "wget",
        base_txt_url,
        "--header",
        f"Authorization: Bearer {auth_token}",  # $ changed the quoting behaviour for shell=False
        "-O",
        metadata_file,  # This variable is a file not a dir so maybe rename it?
    ]
    # $ check that the words Authorization Bearer: is not in there x2 by removing that in config file
    # $ I got a missing url error, check that there is no problem with quotes.
    # $ also I am running on linux so my behaviour is different from yours I think.  https://stackoverflow.com/questions/15109665/subprocess-call-using-string-vs-using-list

    try:
        # Execute the wget command
        subprocess.run(
            command, shell=False
        )  # $ Derek changed this to shell=False, see stack overflow above
        print("TXT file downloaded successfully.")  # $ this is not an HDF File
    except subprocess.CalledProcessError as e:
        # Handle error if the command fails
        print("Error downloading HDF file:", e)


# New API download from LANCE NRT with token access (Zacharie)
def download_HDF_file(base_HDF_url, auth_token, download_HDF_folder):
    """
    This function runs the command line request to download the HDF file
    from MODIS

    Parameters
    ----------
    base_HDF_url : STRING
        The base url for the HDF request.
    auth_token : STRING
        Your MODIS authentication token.
    download_HDF_folder : STRING
        The path to your designated folder for the HDF files.

    Returns
    -------
    str
        Runs the command line request then returns if the download succeded or not.

    """

    command = [
        "wget",
        base_HDF_url,
        "--header",
        f"Authorization: Bearer {auth_token}",  # $ changed the quoting behaviour for shell=False
        "-P",
        download_HDF_folder,
    ]

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
            print(
                "HDF file download didn't work out... Try debugging the code"
            )
            return "error"

    except subprocess.CalledProcessError as e:
        # Handle error if the command fails
        print("Error downloading HDF file:", e)


# Text file processing function--------- (Collin)
def extract_granule_id(metadata_file, kml_AOI_file, testmode):
    """
    This function extracts the granule id from the metadata file. It also extracts
    the bounding box coordinates for the HegTool
    It includes a test mode that will designate a specific test time.


    Parameters
    ----------
    metadata_file : STRING
        Metadata file path.
    kml_file : STRING
        KML file path.
    testmode : STRING
        A specific date and time to run the function in test mode.

    Returns
    -------
    TYPE
        DESCRIPTION.
    granule_id: STRING
        Granule ID.
    upper_left : STRING
        The upper left coordinates in the proper format for the Bounding box.
    lower_right : STRING
        The lower right coordinates in the proper format for the Bounding box.

    """

    # Read the text file into a DataFrame skipping the first two rows as they are info
    df_txt = pd.read_csv(metadata_file, skiprows=2)

    # Import KML driver for reading the KML file
    # fiona.supported_drivers[
    #    "KML"
    # ] = "rw"  # $ you might want to put this line near the imports above the functions

    # Read the kml file and extract the aoi polygon
    poly_aoi = gpd.read_file(kml_AOI_file, driver="LIBKML", crs="EPSG:4326")

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
    selected_granules = selected_granules[
        selected_granules.DayNightFlag == "D"
    ]
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

    return str(selected_granule["# GranuleID"]), upper_left, lower_right


# Place Code Here for HDF to GeoTIFF conversion (Zacharie)--------------------------------------


# This section of the code was taken from and AI generated script to search the
# hdf file for the time
def extract_date_from_filename(hdf_filename):
    """
    This function read the date time from the HDF file.

    Parameters
    ----------
    hdf_filename : STRING
        HDF file name.

    Returns
    -------
    hdf_date : datetime object
        Formated date time of the HDF file.

    """

    dt = os.path.basename(hdf_filename)[
        7:19
    ]  # $ note that you can use position to get info too.
    hdf_date = datetime.strptime(dt, "%Y%j.%H%M")
    return hdf_date


def add_datetime_to_filenames(
    GeoTIFF_folder, base_filenames, formatted_datetime
):
    """
    This function builds the final GeoTIFF file names to place in the HEGTool
    parameter file based off of designated GeoTIFF folder, base name and date.

    Parameters
    ----------
    GeoTIFF_folder : STRING
        GeoTIFF folder path.
    base_filenames : LIST
        List of the 3 bands file names.
    formatted_datetime : datetime object
        The formatted datetime taken from extract_date_from_filename function.

    Returns
    -------
    new_filenames : LIST
        A list containing the final 3 GeoTIFF names with dates added for the parameter file.

    """

    new_filenames = []
    for filename in base_filenames:
        # Split the file name and extension
        base_name, extension = os.path.splitext(filename)
        # Create the new filename with datetime and the original extension
        new_filename = os.path.join(
            GeoTIFF_folder,
            f"{formatted_datetime}_MODIS_SWATH_TYPE_L2_{base_name}{extension}",
        )
        new_filenames.append(new_filename)

    return new_filenames


# Only changing the output file sequentially was taken from AI,and
# https://www.geeksforgeeks.org/python-program-to-replace-specific-line-in-file/
# I used this site to get started on how to modify lines of text
def modify_parameter_file(
    parameter_file,
    HDF_input_filename,
    GeoTIFF_output_filenames,
    ul_corner_coordinates,
    lr_corner_coordinates,
):
    """
    This function goes in and modifies the inputted parameter file to change
    the HDF_input_filename, GEOTIFF_output_filenames, the ul_corner_coordinates and the
    lr_corner_coordinates. This is to adjust the HEGTool parameters to take in the
    proper files and bounding boxes.

    Parameters
    ----------
    parameter_file : STRING
        Parameter file path.
    HDF_input_filename : STRING
        HDF file path.
    GeoTIFF_output_filenames : LIST
        A list containing the 3 GeoTIFF output names.
    ul_corner_coordinates : STRING
        Upper left bounding box coordinates.
    lr_corner_coordinates : TYPE
        Lower right bounding box coordinates.

    Returns
    -------
    None.

    """

    with open(parameter_file, "r", newline="") as file:
        lines = file.readlines()

    modified_lines = []
    for line in lines:
        if line.strip().startswith("INPUT_FILENAME"):
            modified_lines.append(f"INPUT_FILENAME = {HDF_input_filename}\n")
        elif line.strip().startswith("OUTPUT_FILENAME"):
            modified_lines.append(
                f"OUTPUT_FILENAME = {GeoTIFF_output_filenames.pop(0)}\n"
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

    with open(parameter_file, "w", newline="") as file:
        file.writelines(modified_lines)
        print("The parameter file has been modified")


# I found out that the file was in Windows CR LF not in Unix LF
# https://stackoverflow.com/questions/36422107/how-to-convert-crlf-to-lf-on-a-windows-machine-in-python
def convert_windows_to_unix_line_endings(parameter_file):
    """
    This function takes the entire parameter file txt and converts it into
    the proper Unix (LF) that it need to be in for the HegTool to run

    Parameters
    ----------
    parameter_file : STRING
        Parameter file path.

    Returns
    -------
    None.

    """

    WINDOWS_LINE_ENDING = b"\r\n"
    UNIX_LINE_ENDING = b"\n"

    try:
        with open(parameter_file, "rb") as open_file:
            content = open_file.read()

        content = content.replace(WINDOWS_LINE_ENDING, UNIX_LINE_ENDING)

        with open(parameter_file, "wb") as open_file:
            open_file.write(content)

        print(
            f"Line endings converted from Windows (CRLF) to Unix (LF) in {parameter_file}"
        )
    except IOError:
        print(f"Error: Unable to open or modify file {parameter_file}")


# Place Code here for GeoTIFF merge (Philip) -------------------------------------------
# Resources used: Code snippet provided by Derek, AI and https://rasterio.readthedocs.io/en/stable/topics/color.html
def merge_raster(band1, band2, band3, output_name):
    """
    This functions takes 3 bands and merges them together in one GeoTIFF file.

    Parameters
    ----------
    band1 : STRING
        Band 1 GeoTIFF file path.
    band2 : STRING
        Band 2 GeoTIFF file path.
    band3 : STRING
        Band 3 GeoTIFF file path.
    output_name : STRING
        Final combined GeoTIFF file path with name.

    Returns
    -------
    None.

    """
    # Open grayscale GeoTIFF files
    with rasterio.open(band1) as src1, rasterio.open(
        band2
    ) as src2, rasterio.open(band3) as src3:
        b1 = src1.read(1)  # Read band 1
        b2 = src2.read(1)  # Read band 2
        b3 = src3.read(1)  # Read band 3

    # Stack bands into an array
    b123 = np.stack([b1, b2, b3], axis=-1)

    # $ rescale the image to byte
    # $ create a masked image that ignores the no data value
    # https://stackoverflow.com/questions/49922460/scale-a-numpy-array-with-from-0-1-0-2-to-0-255
    b123masked = np.ma.masked_equal(
        b123, -28672
    )  # $ this is the no data value
    scaled = (
        (b123masked - np.min(b123masked))
        * (1 / (np.max(b123masked) - np.min(b123masked)) * 255)
    ).astype("uint8")
    # scaled = np.interp(b123masked, (np.min(b123masked), np.max(b123masked)), (0, 255)).astype("uint8")
    # Get metadata from one of the input files
    with rasterio.open(band1) as src:
        meta = src.meta.copy()
        meta.update(count=3)  # Update the band count to 3 for RGB
        # $ if you want to do this you need to actually change the data from int16 to uint8, otherwise it won't work... Look up scale numpy array to 0-255
        meta.update(
            dtype="uint8"
        )  # Update the data type to ensure RGB interpretation
        meta.update(nodata=0)  # Remove nodata value

    # Write stacked RGB image to output file
    with rasterio.open(output_name, "w", **meta) as dst:
        for i in range(3):  # Loop through each band
            dst.write(
                scaled[:, :, i], i + 1
            )  # Write each band with the correct index (starting from 1)

    # # Update color interpretation of bands
    with rasterio.open(output_name, "r+") as src:
        src.colorinterp = [
            ColorInterp.red,
            ColorInterp.green,
            ColorInterp.blue,
        ]

    print("RGB image saved as '{}'".format(output_name))


# Place Code here for GeoTIFF to KML conversion (Shea) ------------------------------
def convert_to_kmz(input_tiff, output_kmz, gdal_translate_path):
    """
    This function converts a GeoTIFF file into a superoverlay kmz file.

    Parameters
    ----------
    input_tiff : STRING
        GeoTIFF file path.
    output_kmz : STRING
        KMZ file path.
    gdal_translate_path : STRING
        Path to the computers gdal_translate.exe.

    Returns
    -------
    None.

    """

    # 'gdal_translate' is a GDAL utility used to convert raster data between different formats, '-of' 'KMLSUPEROVERLAY' specify the output format
    command = [
        gdal_translate_path,
        "-of",
        "KMLSUPEROVERLAY",
        input_tiff,
        output_kmz,
    ]
    # Run the command
    try:
        subprocess.run(command, shell=False)
        print("Conversion to KMZ complete.")
    except Exception as e:
        print(f"Error during conversion to KMZ: {e}")


# Place Code to Read from config file (Zacharie) -------------------------------------------------


def getargs():
    """
    This function retrieves the configuration file path.

    Returns
    -------
    cfg_path : STRING
        Configuration file path.

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
    This function retrieves the information from the config file and places it into variables

    Parameters
    ----------
    cfg_path : STRING
        Configuration file path.

    Returns
    -------
    TYPE
        DESCRIPTION.
    GeoTIFF_folder : STRING
        GeoTIFF folder path.
    TIFF_Final : STRING
        Final merged GeoTIFF file path.
    base_filenames : LIST
        List of 3 base file names.
    HEGTool_directory : STRING
        Required HEGTool directory path.
    MRTBINDIR : STRING
        Required HEGTool computer environment path.
    PGSHOME : STRING
        Required HEGTool computer environment path.
    MRTDATADIR : STRING
        Required HEGTool computer environment path.
    auth_token : STRING
        Required HEGTool NASA Authentication Token.
    download_HDF_folder : STRING
        HDF download folder path.
    metadata_file : STRING
        Metadata file path.
    base_txt_url : STRING
        Base url for the txt download for MODIS.
    base_HDF_url : STRING
        Base url for the HDF download for MODIS.
    test_time : STRING
        Date and time for test mode.
    gdal_translate_path : STRING
        gdal translate exe path on computer.
    kml_AOI_file : STRING
        KML Area of Interest file path.
    kmz_folder : STRING
        KMZ output folder path.

    """

    cfg = os.path.expanduser(cfg_path)
    config = RawConfigParser()  # run the parser

    try:
        config.read(cfg)  # read file
        # now get the variables stored in the config file
        # there are 4 categories - Paths, Name, HEGTool, BoundingBox

        parameter_file = config.get("Paths", "parameter_file")
        GeoTIFF_folder = config.get("Paths", "GeoTIFF_folder")
        TIFF_Final = config.get("Paths", "TIFF_Final")
        base_filenames = config.get("Names", "base_filenames")
        HEGTool_directory = config.get("HegTool", "HEGTool_directory")
        MRTBINDIR = config.get("HegTool", "MRTBINDIR")
        PGSHOME = config.get("HegTool", "PGSHOME")
        MRTDATADIR = config.get("HegTool", "MRTDATADIR")
        auth_token = config.get("LANCE", "auth_token")
        download_HDF_folder = config.get("LANCE", "download_HDF_folder")
        metadata_file = config.get("LANCE", "metadata_file")
        base_txt_url = config.get("LANCE", "base_txt_url")
        base_HDF_url = config.get("LANCE", "base_HDF_url")
        test_time = config.get("LANCE", "test_time")
        gdal_translate_path = config.get("Paths", "gdal_translate_path")
        kml_AOI_file = config.get("BoundingBox", "kml_AOI_file")
        kmz_folder = config.get("Paths", "kmz_folder")

    except:
        print(
            "Trouble reading config file, please check the file and path are valid\n"
        )
        sys.exit(1)

    return (  # $ maybe a dictionary would be an easier way to gather this all together?
        parameter_file,
        GeoTIFF_folder,
        TIFF_Final,
        base_filenames,
        HEGTool_directory,
        MRTBINDIR,
        PGSHOME,
        MRTDATADIR,
        auth_token,
        download_HDF_folder,
        metadata_file,
        base_txt_url,
        base_HDF_url,
        test_time,
        gdal_translate_path,
        kml_AOI_file,
        kmz_folder,
    )


def main():
    """
    This ks the main function that runs the script.

    Returns
    -------
    None.

    """

    # get the config file name
    configfile = getargs()
    # read in the config info
    (
        parameter_file,
        GeoTIFF_folder,
        TIFF_Final,
        base_filenames,
        HEGTool_directory,
        MRTBINDIR,
        PGSHOME,
        MRTDATADIR,
        auth_token,
        download_HDF_folder,
        metadata_file,
        base_txt_url,
        base_HDF_url,
        test_time,
        kml_AOI_file,
        gdal_translate_path,
        kmz_folder,
    ) = getconfig(configfile)

    # Split the string using a space delimiter (you can change this based on the actual delimiter)
    try:
        # $ update this comment --> there are no contestants here!
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

    # Construct the full URL for the text file download
    txt_url_full = base_txt_url + datetime.strftime(t, "%Y/") + txt_file_name

    # Download the txt file for that day
    download_txt_file(txt_url_full, auth_token, metadata_file)

    print("--------------------------")

    granule_id, upper_left, lower_right = extract_granule_id(
        metadata_file, kml_AOI_file, test_time
    )

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
    if not os.path.isfile(os.path.join(download_HDF_folder, granule_id)):
        msg = download_HDF_file(hdf_url_full, auth_token, download_HDF_folder)

        # $ no sense going on without the image you need.
        if msg != "ok":
            sys.exit(1)

    input_hdf_filename = os.path.join(download_HDF_folder, granule_id)
    # Extract date from hdf file
    hdf_date = extract_date_from_filename(input_hdf_filename)
    # $ note only date is retrieved, not time?!
    if hdf_date:
        formatted_datetime = hdf_date.strftime(
            "%Y-%m-%d_%H%M"
        )  # $ replaced . with :
        print("Extracted Date from HDF Filename:", formatted_datetime)
    else:
        print("Failed to extract date from HDF filename.")

    new_date_output_filenames = add_datetime_to_filenames(
        GeoTIFF_folder, base_filenames, formatted_datetime
    )

    # $ copy the list above to a tuple because it gets modified by the function below
    tifbands = tuple(new_date_output_filenames)

    # This section modifies the parameter file for the HEGTool to run
    modify_parameter_file(
        parameter_file,
        input_hdf_filename,
        new_date_output_filenames,
        upper_left,  # $ lat and lon reversed!
        lower_right,  # $ lat and lon reversed!
    )
    # This makes sure that the file is still in the correct Unix LF format
    convert_windows_to_unix_line_endings(parameter_file)

    # Set environment variables
    os.environ["MRTBINDIR"] = MRTBINDIR
    os.environ["PGSHOME"] = PGSHOME
    os.environ["MRTDATADIR"] = MRTDATADIR

    # Set the working directory
    os.chdir(HEGTool_directory)

    # Command to run HegTool with the parameter file
    # https://www.hdfeos.org/software/heg.php

    command = [
        "swtif",
        "-p",
        parameter_file,
    ]

    try:
        # Execute the command
        subprocess.run(command, shell=False)
        print("HegTool executed successfully.")
    except subprocess.CalledProcessError as e:
        # Handle error if the command fails
        print("Error running HegTool:", e)

    # $ use values from config file and what you have done above!
    output_GeoTIFF_combined = os.path.join(
        TIFF_Final, f"{formatted_datetime}_aqua.tif"
    )

    merge_raster(
        tifbands[0], tifbands[1], tifbands[2], output_GeoTIFF_combined
    )

    # Go into the kmz folder directory
    os.chdir(kmz_folder)

    # Name the output kml file path
    output_kmz = os.path.join(kmz_folder, f"{formatted_datetime}_aqua.kml")

    convert_to_kmz(output_GeoTIFF_combined, output_kmz, gdal_translate_path)
    os.chdir("..")

    shutil.make_archive(
        f"{formatted_datetime}_aqua.kmz", "zip", root_dir="tmp", base_dir=None
    )
    shutil.move(
        f"{formatted_datetime}_aqua.kmz.zip", f"{formatted_datetime}_aqua.kmz"
    )

    # $ after you convert to kml you could zip the files in to a kmz, then there would be no conflict between
    # $ the subdirectories here...

    # $ Clean up temporary files  - uncomment this when you are ready to deploy the code
    os.remove(tifbands[0])
    os.remove(tifbands[1])
    os.remove(tifbands[2])
    shutil.rmtree("tmp")
    os.remove(output_GeoTIFF_combined)
    # $ can clean up old hdf files too...


if __name__ == "__main__":
    main()
