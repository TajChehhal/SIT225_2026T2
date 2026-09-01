import time  
import threading  # Imports threading to run data collection in the background
from typing import List, Dict  

from oauthlib.oauth2 import BackendApplicationClient  # Set up Arduino Cloud login
from requests_oauthlib import OAuth2Session  # Connect using OAuth
import iot_api_client as iot  # Arduino IoT Cloud tools
from iot_api_client.api import properties_v2_api  # Access Arduino Cloud properties

import csv  # Save data to a CSV file
import os  # Work with files


CLIENT_ID = "Hs7NYE32jfaCj835ccIU2upXdPVdx1LM" # Use specific client id
CLIENT_SECRET = "8J173Xd8X2p6loTpJ2OS7DdXOJe2mxD6fb7RAI5L5OvxEtqonbzQmkXqcz6aV5F4"  # Use specific client secret key 
THING_ID = "b81682ae-6491-4650-8103-37947edd4286" # Use Thing iD from metadata tab 

VARIABLE_NAMES = {"x": "Accelerometer_X", "y": "Accelerometer_Y", "z": "Accelerometer_Z"}  # Names of the accelerometer values
POLL_INTERVAL_S = 0.5  # how often to poll the REST API for new values
TOKEN_URL = "https://api2.arduino.cc/iot/v1/clients/token"  # Address used to get an access token
API_AUDIENCE = "https://api2.arduino.cc/iot"  # Arduino IoT API address



def _get_access_token(client_id: str, client_secret: str) -> str:
    oauth_client = BackendApplicationClient(client_id=client_id)  # Creates the login client
    oauth = OAuth2Session(client=oauth_client)  # Starts an OAuth session
    token = oauth.fetch_token(  # Requests an access token
        token_url=TOKEN_URL,
        client_id=client_id,
        client_secret=client_secret,
        include_client_id=True,
        audience=API_AUDIENCE,
    )
    return token["access_token"]  # Returns the access token


class AccelReceiver:

    def __init__(self, client_id: str, client_secret: str, thing_id: str,
                 variable_names: Dict[str, str], poll_interval_s: float = 0.5):
        self._thing_id = thing_id  # Stores the Arduino Thing ID
        self._variable_names = variable_names  # Stores the variable names
        self._poll_interval_s = poll_interval_s  # Stores how often data is checked
        self._lock = threading.Lock()  # Prevents data being changed at the same time
        self._pending: List[Dict] = []  # Stores new readings
        self._start_time = time.time()  # Records the starting time
        self._running = False  # Data collection starts as off

        self._log_path = "accel_data_log.csv"  # Name of the CSV log file
        write_header = not os.path.exists(self._log_path)  # Checks if the file is new
        self._log_file = open(self._log_path, "a", newline="")  # Opens the CSV file
        self._log_writer = csv.writer(self._log_file)  # Prepares the CSV for writing
        if write_header:
            self._log_writer.writerow(["t", "x", "y", "z"])  # Adds the column names

        access_token = _get_access_token(client_id, client_secret)  # Gets permission to access Arduino Cloud
        config = iot.Configuration(access_token=access_token)  # Sets up the Arduino Cloud connection
        api_client = iot.ApiClient(config)  # Creates the API client
        self._props_api = properties_v2_api.PropertiesV2Api(api_client)  # Accesses the Thing properties

    def polling_loop(self):
        while self._running:  # Keeps checking while the receiver is running
            try:
                props = self._props_api.properties_v2_list(id=self._thing_id)  # Gets the latest Cloud values
                axis_values = {}  # Stores x, y and z values
                for prop in props:
                    for axis, var_name in self._variable_names.items():
                        if prop.name == var_name:
                            axis_values[axis] = prop.last_value  # Saves the latest value
                if len(axis_values) == len(self._variable_names):  # Checks that all values were received
                    reading = {"t": time.time() - self._start_time, **axis_values}  # Creates a new reading
                    with self._lock:
                        self._pending.append(reading)  # Adds the reading to the pending list
                        self._log_writer.writerow([reading["t"], reading["x"], reading["y"], reading["z"]])  # Saves the reading to CSV
                        self._log_file.flush()  # Writes the data to the file immediately
            except Exception as e:
                print(f"[AccelReceiver] poll error: {e}")  # Displays any connection error
            time.sleep(self._poll_interval_s)  # Waits before checking again

    def start(self):
        self._running = True  # Starts data collection
        threading.Thread(target=self.polling_loop, daemon=True).start()  # Runs data collection in the background

    def get_new_readings(self) -> List[Dict]:
        """Return and clear all readings received since the last call.
        This is the exact interface smooth_stream_dash.py expects."""
        with self._lock:
            readings, self._pending = self._pending, []  # Gets readings and clear the pending list
            return readings  # Returns the new readings


def build_receiver() -> AccelReceiver:
    receiver = AccelReceiver(CLIENT_ID, CLIENT_SECRET, THING_ID, VARIABLE_NAMES, POLL_INTERVAL_S)  # Creates the receiver
    receiver.start()  # Starts collecting data
    return receiver  # Returns the receiver