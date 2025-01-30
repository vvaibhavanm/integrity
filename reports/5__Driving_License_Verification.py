# pages/page_parivahan_verification.py

import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
import os
import time
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
    # st.success(f"ℹ️ {message}")

def log_warning(message: str):
    logger.warning(message)
    # st.warning(f"⚠️ {message}")

def log_error(message: str):
    logger.error(message)
    # st.error(f"❌ {message}")

# Utility function to map API response to DataFrame columns
def map_response_to_df(response: Dict[str, Any], expected_keys: list) -> Dict[str, Any]:
    return {key: response.get(key, "") for key in expected_keys}

# --------------------------- Parivahan DL Verification API Functions ---------------------------

PARIVAHAN_VERIFICATION_URL_TEMPLATE = "https://api.attestr.com/api/{version}/public/checkx/dl"

def initiate_dl_verification(dl_number: str, dob: str, auth_token: str, version: str = "v1", webhook: bool = False) -> Dict[str, Any]:
    """
    Initiates the Driving License verification process.

    Args:
        dl_number (str): Driving License Number to verify.
        dob (str): Date of Birth of the license holder in DD-MM-YYYY format.
        auth_token (str): Attestr Auth Token for authentication.
        version (str, optional): API version. Defaults to "v1".
        webhook (bool, optional): Whether to enable webhook callback. Defaults to False.

    Returns:
        Dict[str, Any]: API response containing request IDs.
    """
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    url = PARIVAHAN_VERIFICATION_URL_TEMPLATE.format(version=version)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    payload = {
        "reg": dl_number,
        "dob": dob,
        "webhook": webhook
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        log_info(f"Parivahan Verification initiated for DL Number: '{dl_number}' with Async ID: '{data.get('_id')}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error occurred during Parivahan verification for DL '{dl_number}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error occurred during Parivahan verification for DL '{dl_number}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error occurred during Parivahan verification for DL '{dl_number}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception occurred during Parivahan verification for DL '{dl_number}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for Parivahan verification response of DL '{dl_number}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during Parivahan verification for DL '{dl_number}': {e}")

    return {}

def get_async_dl_verification_result(async_id: str, auth_token: str, version: str = "v1") -> Dict[str, Any]:
    """
    Retrieves the result of an asynchronous DL verification request.

    Args:
        async_id (str): The _id received from the initiation response.
        auth_token (str): Attestr Auth Token for authentication.
        version (str, optional): API version. Defaults to "v1".

    Returns:
        Dict[str, Any]: API response containing the verification result.
    """
    url = f"https://api.attestr.com/api/v1/public/async/{async_id}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        # print(data)
        log_info(f"Retrieved async result for Async ID: '{async_id}' with status: '{data.get('status')}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error occurred while retrieving async result for Async ID '{async_id}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error occurred while retrieving async result for Async ID '{async_id}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error occurred while retrieving async result for Async ID '{async_id}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception occurred while retrieving async result for Async ID '{async_id}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for async result of Async ID '{async_id}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred while retrieving async result for Async ID '{async_id}': {e}")

    return {}

@st.cache_data
def cache_parivahan_verification(dl_number: str, dob: str, auth_token: str, version: str, webhook: bool) -> Dict[str, Any]:
    return initiate_dl_verification(dl_number, dob, auth_token, version, webhook)

def process_parivahan_verification(file: BytesIO, file_type: str, auth_token: str, webhook: bool, version: str = "v1") -> Optional[pd.DataFrame]:
    """
    Processes the Parivahan DL verification by reading the uploaded file, initiating verification,
    polling for results, and compiling the outcomes into a DataFrame.

    Args:
        file (BytesIO): Uploaded file containing DL details.
        file_type (str): Type of the uploaded file ('csv' or 'xlsx').
        auth_token (str): Attestr Auth Token for API authentication.
        webhook (bool): Whether to enable webhook callback.
        version (str, optional): API version. Defaults to "v1".

    Returns:
        Optional[pd.DataFrame]: Processed DataFrame with verification results.
    """
    try:
        if file_type == "csv":
            df = pd.read_csv(file, dtype={'dl_number': 'str', 'dob': 'str'})
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file, dtype={'dl_number': 'str', 'dob': 'str'})
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Validate required columns
        required_columns = ['sno', 'dl_number', 'dob']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Define expected response keys
        expected_keys = [
            "valid", "active", "owner", "issued", "rto", "ntpIssued", "ntpExpiry",
            "tpIssued", "tpExpiry", "type", "categories", "message"
        ]

        # Initialize new columns if they don't exist
        for key in expected_keys:
            if key not in df.columns:
                df[key] = None
        expanded_rows = []
        # Iterate through each row
        for idx, row in df.iterrows():
            sno = row['sno']
            dl_number = row['dl_number']
            dob = row['dob']

            log_info(f"Processing Sno {sno}: DL Number '{dl_number}', DOB '{dob}'")

            if pd.isna(dl_number) or str(dl_number).strip() == "" or pd.isna(dob) or str(dob).strip() == "":
                log_warning(f"Sno {sno}: DL Number or DOB is missing. Skipping verification.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'active'] = ""
                df.at[idx, 'owner'] = ""
                df.at[idx, 'issued'] = ""
                df.at[idx, 'rto'] = ""
                df.at[idx, 'ntpIssued'] = ""
                df.at[idx, 'ntpExpiry'] = ""
                df.at[idx, 'tpIssued'] = ""
                df.at[idx, 'tpExpiry'] = ""
                df.at[idx, 'type'] = ""
                df.at[idx, 'categories'] = ""
                df.at[idx, 'message'] = "DL Number or DOB is missing."
                continue

            # Initiate DL Verification
            verification_initiation = cache_parivahan_verification(dl_number, dob, auth_token, version, webhook)
            async_id = verification_initiation.get('_id')
            if not async_id:
                log_error(f"Sno {sno}: Failed to initiate verification for DL '{dl_number}'.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "Failed to initiate verification."
                continue
            # print(async_id)
            # Poll for the result
            max_attempts = 20
            attempt = 0
            sleep_duration = 10  # seconds

            verification_result = {}
            while attempt < max_attempts:
                time.sleep(sleep_duration)
                # print(attempt)
                # print(time.time())
                result = get_async_dl_verification_result(async_id, auth_token, version)
                status = result.get('status')
                if status == "COMPLETED":
                    verification_result = result.get('output', {})
                    break
                elif status == "ERRORED":
                    error = result.get('error', {}).get('message', "An error occurred during verification.")
                    log_error(f"Sno {sno}: Verification errored for DL '{dl_number}': {error}")
                    verification_result = {}
                    break
                else:
                    log_info(f"Sno {sno}: Verification status for DL '{dl_number}' is '{status}'. Retrying...")
                    attempt += 1

            if not verification_result and status != "COMPLETED":
                log_error(f"Sno {sno}: Verification did not complete for DL '{dl_number}' after {max_attempts} attempts.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "Verification did not complete."
                continue

            if verification_result:
                # Map response to expected keys
                mapped_data = map_response_to_df(verification_result, expected_keys)
                df.at[idx, 'valid'] = mapped_data.get('valid', False)
                df.at[idx, 'active'] = mapped_data.get('active', "")
                df.at[idx, 'owner'] = mapped_data.get('owner', "")
                df.at[idx, 'issued'] = mapped_data.get('issued', "")
                df.at[idx, 'rto'] = mapped_data.get('rto', "")
                df.at[idx, 'ntpIssued'] = mapped_data.get('ntpIssued', "")
                df.at[idx, 'ntpExpiry'] = mapped_data.get('ntpExpiry', "")
                df.at[idx, 'tpIssued'] = mapped_data.get('tpIssued', "")
                df.at[idx, 'tpExpiry'] = mapped_data.get('tpExpiry', "")
                df.at[idx, 'type'] = mapped_data.get('type', "")
                # For 'categories' which is a list of dicts, convert to string
                categories = mapped_data.get('categories', [])
                if isinstance(categories, list):
                    df.at[idx, 'categories'] = str(categories)
                    for subsno, cat in enumerate(categories, start=1):
                        expanded_row = {'sno':sno, 'dl_number': df.at[idx,'dl_number'], 'dob': df.at[idx,'dob'],'subsno':subsno, **cat}
                        expanded_rows.append(expanded_row)
                else:
                    df.at[idx, 'categories'] = ""
                df.at[idx, 'message'] = mapped_data.get('message', "")
            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'active'] = ""
                df.at[idx, 'owner'] = ""
                df.at[idx, 'issued'] = ""
                df.at[idx, 'rto'] = ""
                df.at[idx, 'ntpIssued'] = ""
                df.at[idx, 'ntpExpiry'] = ""
                df.at[idx, 'tpIssued'] = ""
                df.at[idx, 'tpExpiry'] = ""
                df.at[idx, 'type'] = ""
                df.at[idx, 'categories'] = ""
                df.at[idx, 'message'] = "No data returned from API."


        if expanded_rows:
            expanded_df = pd.DataFrame(expanded_rows)
        else:
            expanded_df = pd.DataFrame(columns=['sno', 'dl_number', 'dob', 'subsno'])
       
        log_info("Parivahan Verification processing complete.")
        combined_df = pd.merge(df, expanded_df, on=['sno', 'dl_number', 'dob'], how='left')
        st.write("### Processed Data", combined_df)

        return combined_df

    except Exception as e:
        log_error(f"An error occurred while processing the Parivahan verification file: {e}")
        return None

def run():
    st.header("DL Verification")
    st.write("""
        This section allows you to verify Driving License (DL) details using the Attestr API.

        The Parivahan DL Verification API provides the following details about a driving license based on the DL number and date of birth (DOB):
        - **Name Of Holder**: Name of the driving license holder.
        - **Category**: Category, class of vehicle, and issued date for each class.
        - **License Type**: Transport or non-transport type.
        - **Registered Location**: Office of Road Transport where the license is registered.
        - **Associated Dates**: Issued and expiry dates.
        
        Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/driving-license-check-api) for more details.
    """)

    # Access API tokens from session state
    google_api_key = st.session_state.get("google_api_key", "")
    attestr_auth_token = st.session_state.get("attestr_auth_token", "")

    if not attestr_auth_token:
        st.warning("Please enter your Attestr Auth Token on the Home page to proceed.")
        return

    st.write("""
        Upload a CSV or XLSX file containing DL details. The input file should have the following columns:
        - **sno**: Serial number (unique for each row)
        - **dl_number**: Driving License Number
        - **dob**: Date of Birth (format: DD-MM-YYYY)
    """)

    uploaded_file = st.file_uploader(
        "Upload your DL Verification file (CSV or XLSX).",
        type=["csv", "xlsx"],
        key="parivahan_verification"
    )

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]
        webhook = False
        # webhook = st.checkbox("Enable Webhook Callback", value=False)
        version = "v1"

        if st.button("Run DL Verification", key="run_parivahan_verification"):
            with st.spinner("Processing DL Verification..."):
                processed_df = process_parivahan_verification(
                    file=uploaded_file,
                    file_type=file_type,
                    auth_token=attestr_auth_token,
                    webhook=webhook,
                    version=version
                )

            if processed_df is not None:
                st.success("DL Verification completed successfully.")
                # st.write("### Processed Data", processed_df)

                # Download Button
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="dl_verification_results.csv",
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