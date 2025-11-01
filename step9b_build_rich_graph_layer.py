import osmnx as ox
import networkx as nx
import pandas as pd
import os

DATA_FOLDER = "data"
# --- We are now using our NEW rich graph ---
BASE_GRAPH_FILE = "pune_rich_graph.graphml"
FINAL_GRAPH_FILE = "digital_twin_graph_rich_v1.graphml"

print("Starting Task 9 (Part 2): Building the RICH Graph Layer...")
print(f"Loading base road network: {BASE_GRAPH_FILE}...")

# --- 1. Load the base rich graph ---
try:
    G = ox.load_graphml(BASE_GRAPH_FILE)
except FileNotFoundError:
    print(f"--- ERROR: Could not find {BASE_GRAPH_FILE} ---")
    print("Please run step9_get_rich_graph.py again to download it.")
    exit()

print(f"Rich graph loaded: {len(G.nodes)} nodes, {len(G.edges)} edges.")

# --- 2. Create a list of dictionaries for data mapping ---
# This is the same logic as step 5, which we know works.
data_to_map = [
    {
        "file": "healthcare_pune_clean.csv",
        "attr": "healthcare_amenity",
        "lat_col": "latitude",
        "lon_col": "longitude",
        "name_col": "name"
    },
    {
        "file": "bus_stops_clean.csv",
        "attr": "bus_stop",
        "lat_col": "stop_lat",
        "lon_col": "stop_lon",
        "name_col": "stop_name"
    },
    {
        "file": "metro_stations_clean.csv",
        "attr": "metro_station",
        "lat_col": "latitude",
        "lon_col": "longitude",
        "name_col": "station_name"
    },
    {
        "file": "aqi_pune_clean.csv",
        "attr": "aqi_station",
        "lat_col": "latitude",
        "lon_col": "longitude",
        "name_col": "station"
    }
]

for item in data_to_map:
    file_path = os.path.join(DATA_FOLDER, item['file'])
    try:
        print(f"\nProcessing {item['file']}...")
        df = pd.read_csv(file_path)
        
        lat_col = item['lat_col']
        lon_col = item['lon_col']
        df = df.dropna(subset=[lat_col, lon_col])
        
        lats = df[lat_col]
        lons = df[lon_col]

        # Find the nearest road node (intersection) for each point
        nearest_nodes = ox.nearest_nodes(G, X=lons, Y=lats)
        
        # Add this data as an attribute to the graph node
        for i, node_id in enumerate(nearest_nodes):
            name = df.iloc[i].get(item['name_col'], 1) 
            G.nodes[node_id][item['attr']] = name

        print(f"Successfully attached {len(df)} '{item['attr']}' points to the graph.")

    except FileNotFoundError:
        print(f"SKIPPING: File not found: {file_path}")
    except Exception as e:
        print(f"ERROR processing {item['file']}: {e}")

# --- 3. Save the new, enriched graph ---
ox.save_graphml(G, filepath=FINAL_GRAPH_FILE)

print(f"\n--- SUCCESS! ---")
print(f"Saved new ENRICHED graph to: {FINAL_GRAPH_FILE}")
print("This graph now contains all roads, amenities, speeds, and travel times.")
print("\n--- Task 9 (Part 2) Complete ---")