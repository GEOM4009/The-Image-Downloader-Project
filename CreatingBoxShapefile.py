# -*- coding: utf-8 -*-
"""
Created on Wed Feb 21 13:05:39 2024

This is the code that will create a bounding box based on a location for the
Northern Exploration Group Project we are working on

@author: Zacharie
"""


import os
import shapely
from shapely.geometry import Point
import geopandas as gpd


os.chdir(
    r"C:\Users\zachs\Documents\Carleton\2024_Winter\GEOM 4009 Custom Geomatics Applications\Team Project"
)


def box_bounds(center_lon, center_lat, buff_distance_m=10000):
    """
    Creates a bounding box GeoSeries from a coordinate point with a 10km
    buffered distance from the middle.

    Parameters
    ----------
    center_x : TYPE
        DESCRIPTION.
    center_y : TYPE
        DESCRIPTION.
    clip_distance_m : TYPE, optional
        DESCRIPTION. The default is 4000.

    Returns
    -------
    bbox_geos : TYPE
        DESCRIPTION.

    """
    center_pt = Point(center_lon, center_lat)  # Create a center point
    bounds = center_pt.buffer(
        buff_distance_m
    ).bounds  # Buffer the center point by default 4km
    bbox_shply = shapely.box(
        *bounds
    )  # Create a shapely bounding box from buffered bounds
    bbox_geos = gpd.GeoSeries(
        bbox_shply
    )  # Convert bounding box into a GeoSeries
    return bbox_geos


bbox1 = box_bounds(-76.532229, 43.080069)


def create_shp(bbox):
    bbox_gdf = gpd.GeoDataFrame(geometry=bbox)
    bbox_gdf.crs = "EPSG:4326"
    bbox_gdf.to_file("bounding_box.shp")


create_shp(bbox1)
