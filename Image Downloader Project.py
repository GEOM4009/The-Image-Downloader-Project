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
    # Get the newest HDF file (including just the filename with extension)
    newest_hdf_filename = os.path.basename(hdf_files[0])
    print("Newest HDF filename:", newest_hdf_filename)
else:
    print("No HDF files found in the directory.")


# Set parameter file path, input and output file names
parameter_file_path = (
    r"C:\Users\zachs\Desktop\tmp\Phillip_Data\image_project_swath.prm"
)
input_hdf_filename = newest_hdf_filename
output_filenames = [
    r"C:\Users\zachs\Desktop\tmp\MODIS_SWATH_TYPE_L2_cmdtest1.tif",
    r"C:\Users\zachs\Desktop\tmp\MODIS_SWATH_TYPE_L2_cmdtest2.tif",
    r"C:\Users\zachs\Desktop\tmp\MODIS_SWATH_TYPE_L2_cmdtest3.tif",
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
command = r"swtif -p C:\Users\zachs\Desktop\tmp\Template_swath.prm"

try:
    # Execute the command
    subprocess.run(command, check=True)
    print("HegTool executed successfully.")
except subprocess.CalledProcessError as e:
    # Handle error if the command fails
    print("Error running HegTool:", e)


# Place Code here for GeoTIFF merge-------------------------------------------


# Place Code here for GeoTIFF to KML conversion------------------------------


# Place Code here for Georeferencing------------------------------------------
