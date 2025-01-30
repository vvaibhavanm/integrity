# pages/page_geocoding_distance.py

import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
import os
import time
from typing import Optional, Dict, Any, Tuple

# Add favicon and set page configuration
favicon_path = os.path.join("assets", "favicon.png")
if os.path.exists(favicon_path):
    image = Image.open(favicon_path)
    # st.set_page_config(
    #     page_title="Integrity Due-Diligence Co-Pilot",
    #     layout="wide",
    #     page_icon=image
    # )
else:
    st.set_page_config(
        page_title="Integrity Due-Diligence Co-Pilot",
        layout="wide",
        page_icon=":information_source:"  # Fallback icon
    )

# Initialize logger from session state
if 'logger' in st.session_state:
    logger = st.session_state.logger

def log_info(message: str):
    logger.info(message)
    # Uncomment the following line if you want inline success messages
    # st.success(f"ℹ️ {message}")

def log_warning(message: str):
    logger.warning(message)
    # Uncomment the following line if you want inline warning messages
    # st.warning(f"⚠️ {message}")

def log_error(message: str):
    logger.error(message)
    # Uncomment the following line if you want inline error messages
    # st.error(f"❌ {message}")

# Utility function to map API response to DataFrame columns
def map_response_to_df(response: Dict[str, Any], expected_keys: list) -> Dict[str, Any]:
    return {key: response.get(key, "") for key in expected_keys}

# --------------------------- Geocoding Distance API Functions ---------------------------

GEOCODING_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"
DIRECTIONS_API_URL = "https://maps.googleapis.com/maps/api/directions/json"

def geocode_address(address: str, api_key: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Geocodes the provided address to obtain latitude and longitude.

    Args:
        address (str): The address to geocode.
        api_key (str): Google Geocoding API key.

    Returns:
        Tuple[Optional[float], Optional[float]]: Latitude and Longitude if successful, else (None, None).
    """
    if not api_key:
        log_error("Google API key is missing.")
        return None, None

    params = {
        'address': address,
        'key': api_key
    }

    try:
        response = requests.get(GEOCODING_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('status') == 'OK':
            result = data['results'][0]
            location = result['geometry']['location']
            lat, lng = location['lat'], location['lng']
            log_info(f"Geocoding successful for address: '{address}' -> (Lat: {lat}, Lng: {lng})")
            return lat, lng
        elif data.get('status') == 'ZERO_RESULTS':
            log_warning(f"No geocoding results found for address: '{address}'")
        elif data.get('status') == 'OVER_QUERY_LIMIT':
            log_error("Over query limit. Please check your API usage and billing.")
        elif data.get('status') == 'REQUEST_DENIED':
            error_message = data.get('error_message', 'Request denied by Google API.')
            log_error(f"Geocoding request denied: {error_message}")
        elif data.get('status') == 'INVALID_REQUEST':
            log_error(f"Invalid geocoding request for address: '{address}'. Address may be missing.")
        else:
            log_error(f"Unexpected geocoding status '{data.get('status')}' for address: '{address}'")

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error occurred while geocoding address '{address}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error occurred while geocoding address '{address}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error occurred while geocoding address '{address}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception occurred while geocoding address '{address}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for geocoding response of address '{address}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred while geocoding address '{address}': {e}")

    return None, None

def get_driving_distance(source_coords: Tuple[float, float], destination_coords: Tuple[float, float], api_key: str) -> Optional[float]:
    """
    Calculates the driving distance between source and destination coordinates.

    Args:
        source_coords (Tuple[float, float]): (Latitude, Longitude) of the source.
        destination_coords (Tuple[float, float]): (Latitude, Longitude) of the destination.
        api_key (str): Google Directions API key.

    Returns:
        Optional[float]: Driving distance in kilometers if successful, else None.
    """
    if not api_key:
        log_error("Google API key is missing.")
        return None

    origin = f"{source_coords[0]},{source_coords[1]}"
    destination = f"{destination_coords[0]},{destination_coords[1]}"

    params = {
        'origin': origin,
        'destination': destination,
        'key': api_key,
        'mode': 'driving'
    }

    try:
        response = requests.get(DIRECTIONS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('status') == 'OK':
            route = data['routes'][0]
            leg = route['legs'][0]
            distance_meters = leg['distance']['value']
            distance_km = distance_meters / 1000
            log_info(f"Driving distance from '{origin}' to '{destination}': {distance_km:.2f} km")
            return distance_km
        elif data.get('status') == 'ZERO_RESULTS':
            log_warning(f"No driving route found from '{origin}' to '{destination}'")
        elif data.get('status') == 'OVER_QUERY_LIMIT':
            log_error("Over query limit. Please check your API usage and billing.")
        elif data.get('status') == 'REQUEST_DENIED':
            error_message = data.get('error_message', 'Request denied by Google API.')
            log_error(f"Directions request denied: {error_message}")
        elif data.get('status') == 'INVALID_REQUEST':
            log_error(f"Invalid directions request from '{origin}' to '{destination}'.")
        else:
            log_error(f"Unexpected directions status '{data.get('status')}' for route from '{origin}' to '{destination}'")

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error occurred while fetching directions from '{origin}' to '{destination}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error occurred while fetching directions from '{origin}' to '{destination}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error occurred while fetching directions from '{origin}' to '{destination}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception occurred while fetching directions from '{origin}' to '{destination}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for directions response from '{origin}' to '{destination}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred while fetching directions from '{origin}' to '{destination}': {e}")

    return None

def parse_coordinates(coord_str: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parses a coordinate string into latitude and longitude.

    Args:
        coord_str (str): Coordinate string in the format "lat,lng".

    Returns:
        Tuple[Optional[float], Optional[float]]: (Latitude, Longitude) if successful, else (None, None).
    """
    try:
        lat_str, lon_str = coord_str.split(',')
        lat = float(lat_str.strip())
        lon = float(lon_str.strip())
        return lat, lon
    except Exception as e:
        log_error(f"Error parsing coordinates '{coord_str}': {e}")
        return None, None

@st.cache_data
def cache_geocode(address: str, api_key: str) -> Tuple[Optional[float], Optional[float]]:
    return geocode_address(address, api_key)

@st.cache_data
def cache_directions(source_coords: Tuple[float, float], destination_coords: Tuple[float, float], api_key: str) -> Optional[float]:
    return get_driving_distance(source_coords, destination_coords, api_key)

def process_geocoding_distance(file: BytesIO, file_type: str, api_key: str) -> Optional[pd.DataFrame]:
    """
    Processes the Geocoding Distance verification by reading the uploaded file, geocoding addresses,
    calculating driving distances, and compiling the results into a DataFrame.

    Args:
        file (BytesIO): Uploaded file containing address details.
        file_type (str): Type of the file ('csv' or 'xlsx').
        api_key (str): Google API key for Geocoding and Directions.

    Returns:
        Optional[pd.DataFrame]: Processed DataFrame with verification results.
    """
    try:
        # Read the file
        if file_type == "csv":
            df = pd.read_csv(file, dtype={'original_address': 'str', 'source': 'str', 'destination': 'str'})
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file, dtype={'original_address': 'str', 'source': 'str', 'destination': 'str'})
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Define required columns
        required_columns = ['sno', 'original_address', 'source', 'destination']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Initialize new columns if they don't exist
        if 'distance_km' not in df.columns:
            df['distance_km'] = None

        # Iterate through each row
        for idx, row in df.iterrows():
            sno = row['sno']
            original_address = row['original_address']
            source_coord_str = row['source']
            destination_coord_str = row['destination']

            log_info(f"Processing Sno {sno}: '{original_address}' -> '{destination_coord_str}'")

            # Geocode Source Address if 'source' is empty or invalid
            if pd.isna(source_coord_str) or str(source_coord_str).strip() == "":
                log_info(f"Sno {sno}: Geocoding source address '{original_address}'")
                lat, lng = cache_geocode(original_address, api_key)
                if lat is not None and lng is not None:
                    df.at[idx, 'source'] = f"{lat},{lng}"
                else:
                    df.at[idx, 'source'] = ""
            else:
                log_info(f"Sno {sno}: Source coordinates already provided.")

            # Parse Destination Coordinates
            dest_lat, dest_lng = parse_coordinates(destination_coord_str)
            if dest_lat is None or dest_lng is None:
                log_warning(f"Sno {sno}: Invalid destination coordinates '{destination_coord_str}'. Skipping distance calculation.")
                df.at[idx, 'distance_km'] = ""
                continue

            # Parse Source Coordinates
            source_coord_str = df.at[idx, 'source']
            source_lat, source_lng = parse_coordinates(source_coord_str)
            if source_lat is None or source_lng is None:
                log_warning(f"Sno {sno}: Invalid source coordinates '{source_coord_str}'. Skipping distance calculation.")
                df.at[idx, 'distance_km'] = ""
                continue

            # Calculate Driving Distance
            distance = cache_directions((source_lat, source_lng), (dest_lat, dest_lng), api_key)
            if distance is not None:
                df.at[idx, 'distance_km'] = round(distance, 2)
            else:
                df.at[idx, 'distance_km'] = ""

        log_info("Processing complete.")
        st.write("### Processed Data", df)

        return df

    except Exception as e:
        log_error(f"An error occurred while processing the file: {e}")
        return None

def run():
    st.header("Geocoding Distance Verification")
    st.write("""
        This section allows you to calculate the driving distance between two locations using the Google Geocoding and Directions APIs.
        
        **Features:**
        - **Geocode Address**: Convert a physical address into geographic coordinates (latitude and longitude).
        - **Calculate Driving Distance**: Compute the driving distance between source and destination coordinates.
        
        **Please refer to the [API documentation](https://developers.google.com/maps/documentation) for more details.**
    """)

    # Access API keys from session state
    google_api_key = st.session_state.get("google_api_key", "")

    if not google_api_key:
        st.warning("Please enter your Google API Key on the Home page to proceed.")
        return

    st.write("""
        Upload a CSV or XLSX file containing Geocoding Distance details. The input file should have the following columns:
        - **sno**: Serial number (unique for each row)
        - **original_address**: The physical address to geocode (used if 'source' is empty)
        - **source**: Source coordinates in "lat,lng" format (optional; if empty, 'original_address' will be geocoded)
        - **destination**: Destination coordinates in "lat,lng" format
    """)

    uploaded_file = st.file_uploader(
        "Upload your Geocoding Distance Verification file (CSV or XLSX).",
        type=["csv", "xlsx"],
        key="geocoding_distance_verification"
    )

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1].lower()

        if st.button("Run Geocoding Distance Verification", key="run_geocoding_distance_verification"):
            with st.spinner("Processing Geocoding Distance Verification..."):
                processed_df = process_geocoding_distance(
                    file=uploaded_file,
                    file_type=file_type,
                    api_key=google_api_key
                )

            if processed_df is not None:
                st.success("Geocoding Distance Verification completed successfully.")
                # Uncomment the following line to display the processed DataFrame
                # st.write("### Processed Data", processed_df)

                # Download Button
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="geocoding_distance_verification_results.csv",
                    mime='text/csv',
                )

if True:
    # if "authenticator" in st.session_state:
    #     authenticator = st.session_state["authenticator"]
    #     try:
    #     # pass
    #         authenticator.login('unrendered')
    #     except Exception as e:
    #         st.error(e)
            
    if 'authentication_status' not in st.session_state:
        st.warning('Please enter your username and password on Home page')
    elif st.session_state['authentication_status']:
        # st.write(f'Welcome *{st.session_state["name"]}*')
        run()
    elif st.session_state['authentication_status'] is False:
        st.error('Username/password is incorrect')

    elif st.session_state['authentication_status'] is None:
        st.warning('Please enter your username and password on Home page')