import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
import itertools
from itertools import combinations
from scipy import spatial
import pickle as pickle
from pylab import *
from mpl_toolkits.mplot3d import Axes3D
# %matplotlib inline
import io
from PIL import Image, ImageDraw, ImageChops, ImageFont
import io
from tqdm import tqdm

import invr

import warnings

# Ignore FutureWarnings
warnings.simplefilter(action='ignore', category=FutureWarning)

Washington_Arlington_Alexandria_DC_VA_MD_WV_Counties = gpd.read_file('./data/DCMetroArea/DC_Metro_counties/Washington_Arlington_Alexandria_DC_VA_MD_WV_Counties.shp')
county_fips_list = Washington_Arlington_Alexandria_DC_VA_MD_WV_Counties['GEOID'].tolist()
us_svi = gpd.read_file('./data/DCMetroArea/SVI2020_US_tract.gdb')
dcmetro_svi = us_svi[us_svi['STCNTY'].isin(county_fips_list)]
dcmetro_svi.reset_index(drop=True)
dcmetro_svi['RPL_THEMES'] = dcmetro_svi['RPL_THEMES'].replace(-999.00, 0)

df_less = dcmetro_svi[['COUNTY','FIPS','LOCATION','RPL_THEMES','geometry']]
# Sorting the DataFrame based on the 'rate' column
df_less.sort_values(by='RPL_THEMES', inplace=True)

# Adding a new column 'new_ID' with ID values starting from zero
df_less['sortedID'] = range(len(df_less))

df_less = df_less[['FIPS', 'sortedID', 'RPL_THEMES','geometry']]

# Convert the DataFrame to a GeoDataFrame
gdf = gpd.GeoDataFrame(df_less, geometry='geometry')

# Set the CRS to a simple Cartesian coordinate system
gdf.crs = "EPSG:3395"  # This is a commonly used projected CRS

gdf.sort_values(by='sortedID', inplace=True)

def generate_adjacent_counties(dataframe,filtration_threshold):
    # filtered_df = dataframe[dataframe['Value_2'] < filtration_threshold]
    filtered_df = dataframe

    # Perform a spatial join to find adjacent precincts
    adjacent_counties = gpd.sjoin(filtered_df, filtered_df, predicate='intersects', how='left')

    # Filter the results to include only the adjacent states
    adjacent_counties = adjacent_counties.query('sortedID_left != sortedID_right')

    # Group the resulting dataframe by the original precinct Name and create a list of adjacent precinct Name
    adjacent_counties = adjacent_counties.groupby('sortedID_left')['sortedID_right'].apply(list).reset_index()

    adjacent_counties.rename(columns={'sortedID_left': 'county', 'sortedID_right': 'adjacent'}, inplace=True)

    adjacencies_list = adjacent_counties['adjacent'].tolist()

    merged_df = pd.merge(adjacent_counties, dataframe, left_on='county',right_on='sortedID', how='left')
    merged_df = gpd.GeoDataFrame(merged_df, geometry='geometry')

    return adjacencies_list,merged_df

adjacencies_list,adjacent_counties_df = generate_adjacent_counties(gdf,17)

def form_simplicial_complex(adjacent_county_list):
    max_dimension = 3

    V = []
    V = invr.incremental_vr(V, adjacent_county_list, max_dimension)

    return V

V = form_simplicial_complex(adjacencies_list)

def fig2img(fig):
     #convert matplot fig to image and return it

     buf = io.BytesIO()
     fig.savefig(buf)
     buf.seek(0)
     img = Image.open(buf)
     return img

def plot_simplicial_complex(dataframe,V,list_gif):

    #city centroids
    city_coordinates = {city.sortedID: np.array((city.geometry.centroid.x, city.geometry.centroid.y)) for _, city in dataframe.iterrows()}

    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(20, 20))
    ax.set_axis_off() 

    # Plot the "wyoming_svi" DataFrame
    dataframe.plot(ax=ax, edgecolor='black', linewidth=0.3, color="white")

    # Plot the centroid of the large square with values
    # for i, row in dataframe.iterrows():
        # centroid = row['geometry'].centroid
        # text_to_display = f"FIPS: {row['FIPS']}\nFilteration: {row['RPL_THEMES']}"
        # plt.text(centroid.x, centroid.y, str(row['FIPS']), fontsize=15, ha='center', color="black")
        # plt.text(centroid.x, centroid.y, text_to_display, fontsize=15, ha='center', color="black")

    for edge_or_traingle in V:

        
        if len(edge_or_traingle) == 2:
            # Plot an edge
            ax.plot(*zip(*[city_coordinates[vertex] for vertex in edge_or_traingle]), color='red', linewidth=2)
            img = fig2img(fig)
            list_gif.append(img)
        elif len(edge_or_traingle) == 3:
            # Plot a triangle
            ax.add_patch(plt.Polygon([city_coordinates[vertex] for vertex in edge_or_traingle], color='green', alpha=0.2))
            img = fig2img(fig)
            list_gif.append(img)
    plt.close()

    return list_gif

list_gif = []

list_gif = plot_simplicial_complex(adjacent_counties_df,V,list_gif)

list_gif[0].save('DCMetroArea.gif',
                 save_all=True,append_images=list_gif[1:],optimize=False,duration=25,loop=0)
