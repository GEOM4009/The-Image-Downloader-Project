# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 17:07:30 2024

Command Line Converter

This script sets up the proper environment variables and then runs the HegTool
in the proper Working Directory with your Parameter File

@author: zachs
"""

import os
import subprocess


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
