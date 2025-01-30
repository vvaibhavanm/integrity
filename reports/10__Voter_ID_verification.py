# pages/page_voter_id_verification.py

import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
import os
from typing import Optional, Dict, Any

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

# --------------------------- Voter ID Verification API Functions ---------------------------

VOTER_ID_VERIFICATION_URL_TEMPLATE = "https://api.attestr.com/api/v1/public/checkx/epic"

def verify_voter_id(epic: str, auth_token: str, version: str = "v1") -> Dict[str, Any]:
    """
    Verifies the provided EPIC number using the Attestr Voter ID Verification API.

    Args:
        epic (str): The EPIC number to verify.
        auth_token (str): Attestr Auth Token.
        version (str, optional): API version. Defaults to "v1".

    Returns:
        Dict[str, Any]: API response data.
    """
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    url = VOTER_ID_VERIFICATION_URL_TEMPLATE.format(version=version)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    payload = {
        "epic": epic
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        log_info(f"Voter ID Verification successful for EPIC: '{epic}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error during Voter ID verification for EPIC '{epic}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error during Voter ID verification for EPIC '{epic}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error during Voter ID verification for EPIC '{epic}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception during Voter ID verification for EPIC '{epic}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for Voter ID verification response of EPIC '{epic}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during Voter ID verification for EPIC '{epic}': {e}")

    return {}

@st.cache_data
def cache_voter_id_verification(epic: str, auth_token: str, version: str = "v1") -> Dict[str, Any]:
    """
    Caches the Voter ID verification response.

    Args:
        epic (str): The EPIC number to verify.
        auth_token (str): Attestr Auth Token.
        version (str, optional): API version. Defaults to "v1".

    Returns:
        Dict[str, Any]: Cached API response data.
    """
    return verify_voter_id(epic, auth_token, version)

def process_voter_id_verification(
    file: BytesIO,
    file_type: str,
    auth_token: str,
    version: str = "v1"
) -> Optional[pd.DataFrame]:
    """
    Processes the Voter ID verification by reading the uploaded file, verifying each EPIC number,
    and compiling the results into a DataFrame.

    Args:
        file (BytesIO): Uploaded file.
        file_type (str): Type of the file ('csv' or 'xlsx').
        auth_token (str): Attestr Auth Token.

    Returns:
        Optional[pd.DataFrame]: Processed DataFrame with verification results.
    """
    try:
        # Read the file
        if file_type == "csv":
            df = pd.read_csv(file, dtype={'epic': 'str'})
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file, dtype={'epic': 'str'})
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Define required columns
        required_columns = ['sno', 'epic']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Initialize new columns for results
        result_columns = [
            "valid", "name", "gender", "relationName", "relationType", "dob",
            "age", "houseNumber", "area", "district", "state",
            "assemblyConstituency", "assemblyConstituencyNumber",
            "pollingStation", "partNumber", "partName",
            "serialNumber", "parliamentaryConstituency", "message"
        ]
        for col in result_columns:
            if col not in df.columns:
                df[col] = None

        # Iterate through each row and verify EPIC
        for idx, row in df.iterrows():
            sno = row['sno']
            epic = row['epic']

            log_info(f"Processing Sno {sno}: EPIC '{epic}'")

            # Validate EPIC
            if pd.isna(epic) or str(epic).strip() == "":
                log_warning(f"Sno {sno}: EPIC is missing. Skipping verification.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "EPIC is missing."
                # Set other fields to default empty values
                for key in result_columns:
                    if key != "valid" and key != "message":
                        df.at[idx, key] = ""
                continue

            # Verify EPIC
            verification_result = cache_voter_id_verification(epic, auth_token, version)
            if verification_result:
                # Populate DataFrame based on response
                df.at[idx, 'valid'] = verification_result.get('valid', False)
                df.at[idx, 'name'] = verification_result.get('name', "")
                df.at[idx, 'gender'] = verification_result.get('gender', "")
                df.at[idx, 'relationName'] = verification_result.get('relationName', "")
                df.at[idx, 'relationType'] = verification_result.get('relationType', "")
                df.at[idx, 'dob'] = verification_result.get('dob', "")
                df.at[idx, 'age'] = verification_result.get('age', "")
                df.at[idx, 'houseNumber'] = verification_result.get('houseNumber', "")
                df.at[idx, 'area'] = verification_result.get('area', "")
                df.at[idx, 'district'] = verification_result.get('district', "")
                df.at[idx, 'state'] = verification_result.get('state', "")
                df.at[idx, 'assemblyConstituency'] = verification_result.get('assemblyConstituency', "")
                df.at[idx, 'assemblyConstituencyNumber'] = verification_result.get('assemblyConstituencyNumber', "")
                df.at[idx, 'pollingStation'] = verification_result.get('pollingStation', "")
                df.at[idx, 'partNumber'] = verification_result.get('partNumber', "")
                df.at[idx, 'partName'] = verification_result.get('partName', "")
                df.at[idx, 'serialNumber'] = verification_result.get('serialNumber', "")
                df.at[idx, 'parliamentaryConstituency'] = verification_result.get('parliamentaryConstituency', "")
                df.at[idx, 'message'] = verification_result.get('message', "")
            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "No data returned from API."
                # Set other fields to default empty values
                for key in result_columns:
                    if key != "valid" and key != "message":
                        df.at[idx, key] = ""

        log_info("Voter ID Verification processing complete.")
        st.write("### Processed Data", df)

        return df

    except Exception as e:
        log_error(f"An error occurred while processing the Voter ID Verification file: {e}")
        return None

def run():
    st.header("Voter ID Verification")
    st.write("""
        This section allows you to verify Voter ID (EPIC) details using the Attestr API.
        
        **Features:**
        - Validates the existence and status of a Voter ID.
        - Retrieves personal and electoral details associated with the EPIC.
        
        Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/voter-id-verification-api) for more details.
    """)

    # Access API tokens from session state
    google_api_key = st.session_state.get("google_api_key", "")
    attestr_auth_token = st.session_state.get("attestr_auth_token", "")

    if not attestr_auth_token:
        st.warning("Please enter your Attestr Auth Token on the Home page to proceed.")
        return

    st.write("""
        Upload a CSV or XLSX file containing Voter ID details. The input file should have the following columns:
        - **sno**: Serial number (unique for each row)
        - **epic**: EPIC (Voter ID) Number
    """)

    uploaded_file = st.file_uploader(
        "Upload your Voter ID Verification file (CSV or XLSX).",
        type=["csv", "xlsx"],
        key="voter_id_verification"
    )

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]
        version = "v1"

        if st.button("Run Voter ID Verification", key="run_voter_id_verification"):
            with st.spinner("Processing Voter ID Verification..."):
                processed_df = process_voter_id_verification(
                    file=uploaded_file,
                    file_type=file_type,
                    auth_token=attestr_auth_token,
                    version=version
                )

            if processed_df is not None:
                st.success("Voter ID Verification completed successfully.")
                # Uncomment the following line to display the processed DataFrame
                # st.write("### Processed Data", processed_df)

                # Download Button
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="voter_id_verification_results.csv",
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