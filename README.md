# Image Downloader Project

## Introduction
This script is developed for the Polar Continental Shelf Program (PCSP) under Natural Resources Canada. It automates the downloading and processing of satellite imagery for a designated area of interest KML file, facilitating the logistical coordination of the PCSP's activities. The Imagery is taken from MODIS AQUA using LANCE and results in a KMZ around your area of interest for use in Google Earth or other software. The batch file is set up to run through the python script once, for continual use we recomend using Task Scheduler for Windows systems or any other equivalent software. For ease of utlility we recommend that you set up your folder in a similar configuration that we have set up the GitHub repository. It will be easier to keep all the config, python, environment, area of interest kml, batch and metadata file in the main Image Downloader Project folder. The HDF, GEOTIFF_Bands, TIFF_Final and KMZ are each specific outputs created while running the script. They are kept seperate for organizational benefit and help with the debugging process if errors appear. If this file structure does not work to your benefit feel free to change folder names or paths which you can easily do in the configuration file. You will find an example KML (cambridge.kml) file in the GitHub repository as well as a coresponding KMZ in the KMZ folder.

## Getting Started
This README file is intended to provide brief instruction on how to set up the application and where to find guides/resources to specific tools. 

### Prerequisites
Before you begin, ensure you have met the following requirements:
- Windows Operating System
- Python 3.8 or higher
- imagedownload_env.yml
- Heg Tool 
- Task Scheduler for Windows
- Area of Interest KML
- Config File
- Parameter File

### Installation
1. For environment installation demo, see Installation Guide folder
2. For Heg Tool installation demo, see Installation Guide folder
3. For Task Scheduler demo, see Installation Guide folder

### Set-up Configuration File
1. Open config file in a text editor
2. Update all necessary paths to reflect your operating system paths
3. See config file for *** paths (to be filled)

### Workflow Set-up
1. Install all dependencie programs
2. Create Area of Interest KML file
3. Set-up Configuration File
4. Create Task in Task Manager (see Task Scheduler Demo in Installation Guide folder)
5. Run Task Scheduler

### Troubleshooting
If you encounter issues, please refer to the Imager Download Project Git Hub for troubleshooting. 

## Contributing to Image Downloader Project
If you wish to contribute to the Image Downloader Project: 
1. Clone the repository: <https://github.com/GEOM4009/The-Image-Downloader-Project>
2. Create a branch
3. Make your adjustments/contributions
4. Commit your changes and describe your workflow
5. Request for merge to the main branch

## Contributors
Thanks to the main contributors of this project:
- Zacharie Sauvé
- Derek Mueller
- Collin Godsell
- Philip Ishola
- Shea Timmins

## Contact
If you wish to contact any contributors, reach out through the Image Downloader Project Git Hub community page.

## License
This project uses the MIT License. For licensing detials please refer to the MIT License text document in the main repository. 
