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
# We will use the rich graph, even though it has strings
GRAPH_FILE = "digital_twin_graph_rich_v1.graphml" 

# --- CALIBRATION SETTINGS ---
CALIBRATION_COLUMN = '2017-18' 
PERCENT_OF_CARS_ON_ROAD = 0.001 # 0.1% for a manageable test
NUM_STEPS = 10 

# --- CONGESTION MODEL SETTINGS ---
CAPACITY_PER_LANE = 10 
RECALCULATE_PATH_STEPS = 5 

# --- 1. AGENT AND MODEL DEFINITION (CONGESTION-AWARE) ---

class VehicleAgent(ap.Agent):
    """A 'smart' vehicle agent that reacts to congestion."""
    
    def setup(self):
        self.pos = None 
        self.destination = self.model.random.choice(self.model.graph_nodes)
        self.path = [] 

    def calculate_new_path(self):
        """Calculates a new shortest path using 'travel_time'."""
        if self.pos is None:
            self.path = []
            return
        try:
            self.path = nx.shortest_path(self.model.G, 
                                         source=self.pos, 
                                         target=self.destination, 
                                         weight='travel_time') # Use travel_time!
            self.path.pop(0) 
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self.destination = self.model.random.choice(self.model.graph_nodes)
            self.path = []

    def step(self):
        """Defines the agent's behavior in one time step."""
        if self.model.t % RECALCULATE_PATH_STEPS == 0:
            self.calculate_new_path()

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
        print("Loading rich graph for simulation...")
        try:
            self.G = ox.load_graphml(GRAPH_FILE)
            self.graph_nodes = list(self.G.nodes())
            print(f"Rich graph loaded with {len(self.graph_nodes)} nodes.")
        except FileNotFoundError:
            print(f"--- FATAL ERROR: Cannot find {GRAPH_FILE} ---")
            return

        # --- THIS IS THE FIX: CAST DATA TYPES ON LOAD ---
        # The .graphml file saved all numbers as strings.
        # We must convert them back to numbers in memory.
        print("Fixing data types (converting strings to numbers)...")
        for u, v, k, data in self.G.edges(keys=True, data=True):
            # 1. Get lanes, default to 1
            lanes_str = data.get('lanes', '1') # Get string, default to '1'
            if isinstance(lanes_str, list):
                lanes_str = lanes_str[0]
            data['lanes'] = int(float(lanes_str)) # Force to int
            
            # 2. Get speed, default to 30
            speed_str = data.get('speed_kph', '30')
            data['speed_kph'] = float(speed_str) # Force to float
            
            # 3. Get base travel time
            travel_time_str = data.get('base_travel_time', '10.0') # Default
            data['base_travel_time'] = float(travel_time_str) # Force to float
            
            # 4. Set the initial travel_time
            data['travel_time'] = data['base_travel_time']
        # --- END OF FIX ---

        # 1. Create our own 'grid'
        print("Initializing manual grid...")
        self.grid = {node_id: set() for node_id in self.G.nodes()}
        self.agent_positions = {}
        
        # Get number of agents
        num_agents = self.p.num_agents
        print(f"Creating {num_agents} smart agents (this may take a moment)...")

        # 3. Create agents
        self.agents = ap.AgentList(self, num_agents, VehicleAgent)
        
        # 4. Place agents on the grid manually
        initial_positions = self.random.choices(self.graph_nodes, k=num_agents) 
        
        print("Assigning positions and calculating initial paths...")
        for i, agent in enumerate(self.agents):
            pos = initial_positions[i]
            agent.pos = pos                
            self.grid[pos].add(agent)      
            self.agent_positions[agent.id] = pos 
            agent.calculate_new_path() # Agents get their first path

        print("All smart agents created and placed on manual grid.")

    def move_agent(self, agent, new_pos):
        current_pos = agent.pos
        self.grid[current_pos].remove(agent)
        self.grid[new_pos].add(agent)
        agent.pos = new_pos
        self.agent_positions[agent.id] = new_pos
        
    def step(self):
        """Called in each step of the simulation."""
        self.agents.step()

    def update(self):
        """Called after each step. This is where we update congestion."""
        
        # 1. Reset all travel times to their 'base'
        for u, v, k, data in self.G.edges(keys=True, data=True):
            data['travel_time'] = data['base_travel_time']
            
        # 2. Calculate node congestion
        node_congestion = {node: len(agents) for node, agents in self.grid.items() if len(agents) > 0}

        # 3. Apply congestion to edges
        for u, v, k, data in self.G.edges(keys=True, data=True):
            cong_u = node_congestion.get(u, 0)
            cong_v = node_congestion.get(v, 0)
            total_congestion = cong_u + cong_v
            
            # This comparison will now be INT > INT
            capacity = data['lanes'] * CAPACITY_PER_LANE 
            
            if total_congestion > capacity:
                congestion_factor = total_congestion / capacity
                data['travel_time'] = data['base_travel_time'] * congestion_factor
                
        # Let's track Agent 0
        agent_0 = self.agents[0]
        pos_0 = agent_0.pos 
        print(f"Position of Agent 0: {pos_0} (Path length: {len(agent_0.path)})")

    def end(self):
        """Called at the end of the simulation."""
        print("\n--- Congestion-Aware Simulation Complete ---")

# --- 2. CALIBRATION AND EXECUTION ---

def calibrate_agent_count():
    # (This function is unchanged)
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
    
    print("--- Starting Task 9 (Final): Congestion-Aware Simulation ---")
    
    NUM_AGENTS = calibrate_agent_count()
    
    if NUM_AGENTS:
        parameters = { 'num_agents': NUM_AGENTS, 'steps': NUM_STEPS }
        model = CityModel(parameters)
        print("\n--- Running Simulation Steps ---")
        results = model.run()
    else:
        print("--- Simulation HALTED due to calibration error. ---")