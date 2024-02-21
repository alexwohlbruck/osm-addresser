from bs4 import BeautifulSoup
import difflib
import geopandas as gpd
import fileinput
from pprint import pp
from OSMPythonTools.api import Api
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
from math import pi, radians, log, cos, tan, atan, sinh, degrees

# For each address point in the shapefile, we will cross reference with existing OSM data
# We will check if the address exists near the data point, and if it doesn't we will create it
# Within some amount of margin of error, we will prompt the user to confirm the address if needed

TILE_ZOOM_LEVEL = 14

api = Api()
overpass = Overpass()
shapefile_path = "./stage/MAT-filtered.shp"
gdf = gpd.read_file(shapefile_path)

streets = {} # Streets in the area, keyed by id
street_names = [] # Flat list of street names
buildings = {} # Buildings in the area, keyed by id
loaded_tiles = [] # (x, y) coordinates of tiles that have already been loaded

def find_tile_coordinates_for_point(lat, lng):
  lat_rad = radians(lat)
  n = 2.0 ** TILE_ZOOM_LEVEL
  x = int((lng + 180.0) / 360.0 * n)
  y = int((1.0 - log(tan(lat_rad) + (1 / cos(lat_rad))) / pi) / 2.0 * n)
  return x, y

def area_already_loaded(x, y):
  return (x, y) in loaded_tiles

def get_bbox_from_tile(x, y):
  # return bbox coordinates [south, west, north, east]
  n = 2.0 ** TILE_ZOOM_LEVEL
  west = x / n * 360.0 - 180.0
  east = (x + 1) / n * 360.0 - 180.0
  north = atan(sinh(pi * (1 - 2 * y / n))) * 180.0 / pi
  south = atan(sinh(pi * (1 - 2 * (y + 1) / n))) * 180.0 / pi
  return [south, west, north, east]

def fetch_tile(x, y):
  
  bbox = get_bbox_from_tile(x, y)

  buildings = overpass.query(
    overpassQueryBuilder(bbox=bbox, elementType=['way'], selector='"building"', out='skel qt')
  )
  streets = overpass.query(
    overpassQueryBuilder(bbox=bbox, elementType=['way'], selector=['"highway"', '"name"'], out='skel qt tags')
  )

  return buildings.elements(), streets.elements()

def load_data(lat, lng):
  x, y = find_tile_coordinates_for_point(lat, lng)
  
  if area_already_loaded(x, y):
    return
  
  buildings, streets = fetch_tile(x, y)
  
  for building in buildings:
    buildings[building.id()] = building
  
  for street in streets:
    streets[street.id()] = street
    
  generate_street_name_list(streets)
  
  loaded_tiles.append((x, y))

def parse_address_number(address):
  return int(float(address))

def generate_street_name_list(streets):
  street_names = []
  for street in streets:
    tags = street.tags()
    tiger = tags.get('tiger:name_base', tags.get('name', tags.get('ref', '')))
    street_names.append(street_name)
    
# Case-insensitive version of difflib.get_close_matches
def get_close_matches_icase(word, possibilities, *args, **kwargs):
  lword = word.lower()
  lpos = {p.lower(): p for p in possibilities}
  lmatches = difflib.get_close_matches(lword, lpos.keys(), *args, **kwargs)
  return [lpos[m] for m in lmatches]

def match_street(street_name):
  return difflib.get_close_matches_icase(street_name, street_names)[0]

addresses = gdf.iterfeatures()

# address = next(addresses)
for address in addresses:
  properties = address['properties']
  lat = properties['latitude']
  lng = properties['longitude']

  # Load data from the current tile and surrounding tiles
  for i in range(-1, 2):
    for j in range(-1, 2):
      load_data(lat + i, lng + j)

  address_number = parse_address_number(properties['txt_number'])
  street = match_street(properties['txt_street'])
