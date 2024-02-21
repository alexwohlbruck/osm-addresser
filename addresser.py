from bs4 import BeautifulSoup
import difflib
import geopandas as gpd
import fileinput
from pprint import pp
from OSMPythonTools.api import Api
from OSMPythonTools.overpass import Overpass, overpassQueryBuilder
from math import pi, radians, log, sin, cos, tan, atan, atan2, sinh, degrees, sqrt

# For each address point in the shapefile, we will cross reference with existing OSM data
# We will check if the address exists near the data point, and if it doesn't we will create it
# Within some amount of margin of error, we will prompt the user to confirm the address if needed

TILE_ZOOM_LEVEL = 14

api = Api()
overpass = Overpass()
shapefile_path = "./stage/MAT-filtered.shp"
city = "Charlotte"
state = "NC"

gdf = gpd.read_file(shapefile_path)

all_buildings = {} # Buildings in the area, keyed by id
all_streets = {} # Streets in the area, keyed by id
street_names = [] # Flat list of street names
buildings = [] # Flat list of buildings
known_zips = []
known_cities = []
known_states = []
known_countries = []
loaded_tiles = [] # (x, y) coordinates of tiles that have already been loaded

def find_tile_coordinates_for_point(lat, lng):
  lat_rad = radians(lat)
  n = 2.0 ** TILE_ZOOM_LEVEL
  x = int((lng + 180.0) / 360.0 * n)
  y = int((1.0 - log(tan(lat_rad) + (1 / cos(lat_rad))) / pi) / 2.0 * n)
  return x, y

def haversine(lat1, lng1, lat2, lng2):
  R = 6371.0 # Radius of the Earth
  lat1_rad = radians(lat1)
  lng1_rad = radians(lng1)
  lat2_rad = radians(lat2)
  lng2_rad = radians(lng2)
  
  dlat = lat2_rad - lat1_rad
  dlng = lng2_rad - lng1_rad
  
  a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng / 2) ** 2
  c = 2 * atan2(sqrt(a), sqrt(1 - a))
  
  return R * c

def get_bbox_from_tile(x, y):
  # return bbox coordinates [south, west, north, east]
  n = 2.0 ** TILE_ZOOM_LEVEL
  west = x / n * 360.0 - 180.0
  east = (x + 1) / n * 360.0 - 180.0
  north = atan(sinh(pi * (1 - 2 * y / n))) * 180.0 / pi
  south = atan(sinh(pi * (1 - 2 * (y + 1) / n))) * 180.0 / pi
  return [south, west, north, east]

def area_already_loaded(x, y):
  return (x, y) in loaded_tiles

def fetch_tile(x, y):
  
  bbox = get_bbox_from_tile(x, y)

  buildings = overpass.query(
    overpassQueryBuilder(
      bbox=bbox,
      elementType=['way'],
      selector='"building"',
      out='skel qt center'
    )
  )
  streets = overpass.query(
    overpassQueryBuilder(
      bbox=bbox,
      elementType=['way'],
      selector=['"highway"',
      '"name"'],
      out='skel qt tags'
    )
  )
    
  return buildings.elements(), streets.elements()


def load_data(x, y):
  if area_already_loaded(x, y):
    return
  
  buildings, streets = fetch_tile(x, y)
  
  for building in buildings:
    all_buildings[building.id()] = building
  
  for street in streets:
    all_streets[street.id()] = street
    
  flatten_data()
  
  loaded_tiles.append((x, y))

def load_surrounding_tiles(x, y):
  for i in range(-1, 2):
    for j in range(-1, 2):
      load_data(x + i, y + j)

def parse_address_number(address):
  return int(float(address))

def flatten_data():
  street_names.clear()
  for street in all_streets.values():
    tags = street.tags()
    street_name = tags.get('tiger:name_base', tags.get('name', tags.get('ref', '')))
    street_names.append(street_name)
  
  buildings.clear()
  for building in all_buildings.values():
    tags = building.tags()
    buildings.append({
      'id': building.id(),
      'lat': building.centerLat(),
      'lng': building.centerLon(),
      'nodes': building.nodes(),
      'tags': tags
    })
    
# Case-insensitive version of difflib.get_close_matches
def get_close_matches_icase(word, possibilities, *args, **kwargs):
  lword = word.lower()
  lpos = {p.lower(): p for p in possibilities}
  lmatches = difflib.get_close_matches(lword, lpos.keys(), *args, **kwargs)
  return [lpos[m] for m in lmatches]

def match_street(street_name):
  return get_close_matches_icase(street_name, street_names)[0]

def find_nearest_building(lat, lng):
  nearest_building = None
  nearest_distance = float('inf')
  
  for building in buildings:
    distance = haversine(lat, lng, building['lat'], building['lng'])
    if distance < nearest_distance:
      nearest_distance = distance
      nearest_building = building
      
  return nearest_building

addresses = gdf.iterfeatures()

address = next(addresses)

for address in addresses:

  properties = address['properties']
  lat = properties['latitude']
  lng = properties['longitude']

  pp(properties)
  
  x, y = find_tile_coordinates_for_point(lat, lng)
  load_data(x, y)
  # load_surrounding_tiles(x, y)

  address_number = str(parse_address_number(properties['txt_street']))
  street = match_street(properties['nme_street'] + ' ' + properties['cde_roadwa'])
  zip_code = properties['cde_zip1']
  
  full_address = f"{address_number} {street}, {city}, {state} {zip_code}"

  building = find_nearest_building(lat, lng)

  print(f"ID: {building['id']}, Address: {full_address}")
