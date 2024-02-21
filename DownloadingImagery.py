# -*- coding: utf-8 -*-
"""
Created on Wed Feb 21 13:41:41 2024

This code will be to pull the info needed to download the image off of the 
web site

@author: Zacharie Sauve
"""

import os
from datetime import datetime
current_directory = os.getcwd()
print("Current directory:", current_directory)
os.chdir(current_directory)


# Get the current date and time
current_time = datetime.now().strftime("%H:%M:%S")


# Print the current time
print("Current time:", current_time)

#These variables will depend on the website and what we need I am just making
#Some that I think we will need

Band1 = 
Band2 = 
Band3 = 
Coordinates = 
bounding_box = #Use function from CreatingBoxShapefile
