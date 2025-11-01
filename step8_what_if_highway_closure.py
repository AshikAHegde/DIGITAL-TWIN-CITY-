import pandas as pd
import os
import networkx as nx
import osmnx as ox
import random

# --- We import from agentpy ---
import agentpy as ap

# --- CONFIGURATION ---
DATA_FOLDER = "data"
VEHICLE_FILE = "pune-vehicle_registrations_2014-2020.csv"
GRAPH_FILE = "digital_twin_graph_v1.graphml"

# --- CALIBRATION SETTINGS ---
CALIBRATION_COLUMN = '2017-18' 
PERCENT_OF_CARS_ON_ROAD = 0.001 # 0.1% for a manageable test
NUM_STEPS = 10 

# --- 1. "WHAT-IF" SCENARIO FUNCTION ---

def apply_highway_closure(G):
    """
    Simulates a highway closure by removing all 'motorway' edges.
    In OSM, 'motorway' is the tag for major highways.
    """
    print("\n--- APPLYING 'WHAT-IF' SCENARIO: HIGHWAY CLOSURE ---")
    
    # 1. Find all edges that are motorways
    edges_to_remove = []
    for u, v, key, data in G.edges(keys=True, data=True):
        if 'highway' in data and data['highway'] == 'motorway':
            edges_to_remove.append((u, v, key))
            
    if not edges_to_remove:
        print("No 'motorway' edges found. Trying 'primary' roads instead...")
        for u, v, key, data in G.edges(keys=True, data=True):
            if 'highway' in data and data['highway'] == 'primary':
                edges_to_remove.append((u, v, key))

    # 2. Remove those edges from the graph
    G.remove_edges_from(edges_to_remove)
    
    print(f"Removed {len(edges_to_remove)} highway/primary road segments.")
    print("Agents will now be forced to find new routes.\n")
    return G

# --- 2. AGENT AND MODEL DEFINITION (Same as Task 7) ---

class VehicleAgent(ap.Agent):
    """A 'smart' vehicle agent that follows a shortest path."""
    def setup(self):
        self.pos = None 
        self.destination = self.model.random.choice(self.model.graph_nodes)
        self.path = [] 
    def calculate_new_path(self):
        if self.pos is None:
            self.path = []
            return
        try:
            self.path = nx.shortest_path(self.model.G, source=self.pos, target=self.destination, weight='length')
            self.path.pop(0) 
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self.destination = self.model.random.choice(self.model.graph_nodes)
            self.path = []
    def step(self):
        if not self.path:
            self.destination = self.model.random.choice(self.model.graph_nodes)
            self.calculate_new_path()
            if not self.path:
                return 
        new_pos = self.path.pop(0)
        self.model.move_agent(self, new_pos)

class CityModel(ap.Model):
    """The main model for the city simulation."""
    def setup(self):
        """Called once when model is created."""
        print("Loading graph for simulation...")
        try:
            self.G_base = ox.load_graphml(GRAPH_FILE)
            print(f"Base graph loaded with {len(self.G_base.nodes)} nodes.")
            
            # --- APPLY THE SCENARIO ---
            # We apply the 'what-if' function to a copy of the graph
            self.G = self.G_base.copy()
            self.G = apply_highway_closure(self.G)
            
            self.graph_nodes = list(self.G.nodes())
            
        except FileNotFoundError:
            print(f"--- FATAL ERROR: Cannot find {GRAPH_FILE} ---")
            return

        print("Initializing manual grid...")
        self.grid = {node_id: set() for node_id in self.G.nodes()}
        self.agent_positions = {}
        
        num_agents = self.p.num_agents
        print(f"Creating {num_agents} smart agents (this may take a moment)...")

        self.agents = ap.AgentList(self, num_agents, VehicleAgent)
        
        initial_positions = self.random.choices(self.graph_nodes, k=num_agents) 
        
        print("Assigning positions and calculating initial paths (this will be slow)...")
        for i, agent in enumerate(self.agents):
            pos = initial_positions[i]
            # Ensure agent spawns on a valid, non-isolated node
            if pos not in self.G:
                pos = random.choice(self.graph_nodes) # Pick a new valid node

            agent.pos = pos                
            self.grid[pos].add(agent)      
            self.agent_positions[agent.id] = pos 
            agent.calculate_new_path()

        print("All smart agents created and placed on manual grid.")

    def move_agent(self, agent, new_pos):
        current_pos = agent.pos
        self.grid[current_pos].remove(agent)
        self.grid[new_pos].add(agent)
        agent.pos = new_pos
        self.agent_positions[agent.id] = new_pos
        
    def step(self):
        self.agents.step() 

    def update(self):
        agent_0 = self.agents[0]
        pos_0 = agent_0.pos 
        print(f"Position of Agent 0: {pos_0} (Path length: {len(agent_0.path)})")

    def end(self):
        print("\n--- 'What-If' Simulation Complete ---")


# --- 3. CALIBRATION AND EXECUTION (Same as Task 7) ---

def calibrate_agent_count():
    try:
        file_path = os.path.join(DATA_FOLDER, VEHICLE_FILE)
        df = pd.read_csv(file_path)
        total_vehicles = df[CALIBRATION_COLUMN].sum()
        realistic_num_agents = int(total_vehicles * PERCENT_OF_CARS_ON_ROAD)
        print(f"--- CALIBRATION SUCCESS ---")
        print(f"Total vehicles (from '{CALIBRATION_COLUMN}' column): {total_vehicles:,}")
        print(f"Agent count (at {PERCENT_OF_CARS_ON_ROAD*100}%): {realistic_num_agents:,}")
        return realistic_num_agents
    except Exception as e:
        print(f"--- ERROR during calibration: {e} ---")
        return None

# --- Main function to run the simulation ---
if __name__ == "__main__":
    
    print("--- Starting Task 8: 'What-If' Highway Closure Simulation ---")
    
    NUM_AGENTS = calibrate_agent_count()
    
    if NUM_AGENTS:
        parameters = { 'num_agents': NUM_AGENTS, 'steps': NUM_STEPS }
        model = CityModel(parameters)
        print("\n--- Running Simulation Steps ---")
        results = model.run()
    else:
        print("--- Simulation HALTED due to calibration error. ---")