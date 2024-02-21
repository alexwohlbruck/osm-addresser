# OSM Addresser
This tool assists with batch uploading address data to OpenStreetMap. Currently only designed to work with Charlotte Mecklenburg county's Open Mapping [master address dataset](https://www.arcgis.com/apps/mapviewer/index.html?url=https://meckgis.mecklenburgcountync.gov/server/rest/services/MasterAddressPoints/FeatureServer/0), although I intend to implement a general solution if this project finds success.

## Todo
- Support for multifamily units
- Generalize for other datasets and formats
- Match street names to physically nearest name match
- Support for multiple cities, states, and countries
- OSM account Oauth support
- Automatically generate and upload OSM changeset
- Manual user review for non-confident matches
- Support for other address formats
- GUI?

## **Installation**
### Requirements
- Python 3

### Instructions
1. Clone the repository
```bash
git clone https://github.com/alexwohlbruck/osm-addresser.git
cd osm-addresser
```

2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install the required packages
```bash
pip3 install -r requirements.txt
```

## Usage
1. Download your address dataset. As of now, this must be a shapefile with a format that matches the Mecklenburg County GIS Master Address Table. You can download a copy [here](https://maps.mecknc.gov/openmapping/data.html).
2. Unzip the downloaded file and place all unzipped files in the `stage` directory. Replace existing files if necessary.
3. Activate the virtual environment
```bash
source venv/bin/activate
```
4. Run the script
```bash
python3 addresser.py ./stage/{shapefile name}.shp {city name} {state abbreviation}
```
Example for the Mecklenburg County dataset:
```bash
python3 addresser.py ./stage/MAT-filtered.shp Charlotte NC
```