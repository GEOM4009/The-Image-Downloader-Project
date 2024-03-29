# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 17:07:30 2024

Command Line Converter

This script sets up the proper environment variables and then runs the HegTool
in the proper Working Directory with your Parameter File.

All these 

@author: zachs
"""

import os
import subprocess
from datetime import datetime
import re


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


# Assuming input filename is MOD09.A2024056.1435.061.2024058042139.hdf
hdf_filename = r"MOD09.A2018237.0145.061.2021339074858.hdf"
hdf_date = extract_date_from_filename(hdf_filename)

if hdf_date:
    formatted_datetime = hdf_date.strftime("%Y-%m-%d_%H:%M")
    print("Extracted Date from HDF Filename:", formatted_datetime)
else:
    print("Failed to extract date from HDF filename.")


# Set parameter file path, input and output file names

parameter_file_path = (
    r"C:\Users\zachs\Desktop\tmp\Phillip_Data\image_project_swath.prm"
)
input_filename = r"MOD09.A2018237.0145.061.2021339074858.hdf"
output_filenames = [
    r"C:\Users\zachs\Desktop\tmp\MODIS_SWATH_TYPE_L2_cmdtest1.tif",
    r"C:\Users\zachs\Desktop\tmp\MODIS_SWATH_TYPE_L2_cmdtest2.tif",
    r"C:\Users\zachs\Desktop\tmp\MODIS_SWATH_TYPE_L2_cmdtest3.tif",
]


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
    parameter_file_path, input_filename, datetime_output_filenames
)


# Set environment variables
os.environ["MRTBINDIR"] = r"C:\Users\zachs\Desktop\HEGTool\HEG_Win\bin"
os.environ["PGSHOME"] = r"C:\Users\zachs\Desktop\HEGTool\HEG_Win\TOOLKIT_MTD"
os.environ["MRTDATADIR"] = r"C:\Users\zachs\Desktop\HEGTool\HEG_Win\data"

# Set the working directory
os.chdir(r"C:\Users\zachs\Desktop\HEGTool\HEG_Win\bin")


# Command to run HegTool with the parameter file
command = r"swtif -p C:\Users\zachs\Desktop\tmp\Template_swath.prm"

try:
    # Execute the command
    subprocess.run(command, check=True)
    print("HegTool executed successfully.")
except subprocess.CalledProcessError as e:
    # Handle error if the command fails
    print("Error running HegTool:", e)
