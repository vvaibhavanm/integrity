# pages/page_company_itr_verification.py

import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
import os
import logging
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

# --------------------------- Company ITR Verification API Functions ---------------------------

COMPANY_ITR_VERIFICATION_URL_TEMPLATE = "https://api.attestr.com/api/v2/public/corpx/itr"

def verify_company_itr(pan: str, birth_or_incorporated_date: str, name: str, auth_token: str, version: str = "v1") -> Dict[str, Any]:
    """
    Verifies the provided PAN number and retrieves ITR and gross revenue details using the Attestr Company ITR Verification API.

    Args:
        pan (str): The business PAN number to verify.
        birth_or_incorporated_date (str): Date of incorporation in DD/MM/YYYY format.
        name (str): Registered legal name as per PAN.
        auth_token (str): Attestr Auth Token.
        version (str, optional): API version. Defaults to "v1".

    Returns:
        Dict[str, Any]: API response data.
    """
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    url = COMPANY_ITR_VERIFICATION_URL_TEMPLATE.format(version=version)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    payload = {
        "pan": pan,
        "birthOrIncorporatedDate": birth_or_incorporated_date,
        "name": name
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        log_info(f"Company ITR Verification successful for PAN: '{pan}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error during Company ITR verification for PAN '{pan}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error during Company ITR verification for PAN '{pan}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error during Company ITR verification for PAN '{pan}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception during Company ITR verification for PAN '{pan}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for Company ITR verification response of PAN '{pan}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during Company ITR verification for PAN '{pan}': {e}")

    return {}

@st.cache_data
def cache_company_itr_verification(pan: str, birth_or_incorporated_date: str, name: str, auth_token: str, version: str = "v1") -> Dict[str, Any]:
    """
    Caches the Company ITR verification response.

    Args:
        pan (str): The business PAN number to verify.
        birth_or_incorporated_date (str): Date of incorporation in DD/MM/YYYY format.
        name (str): Registered legal name as per PAN.
        auth_token (str): Attestr Auth Token.
        version (str, optional): API version. Defaults to "v1".

    Returns:
        Dict[str, Any]: Cached API response data.
    """
    return verify_company_itr(pan, birth_or_incorporated_date, name, auth_token, version)

def process_company_itr_verification(
    file: BytesIO,
    file_type: str,
    auth_token: str,
    version: str = "v1"
) -> Optional[pd.DataFrame]:
    """
    Processes the Company ITR verification by reading the uploaded file, verifying each PAN number,
    and compiling the results into a DataFrame.

    Args:
        file (BytesIO): Uploaded file.
        file_type (str): Type of the file ('csv' or 'xlsx').
        auth_token (str): Attestr Auth Token.
        version (str, optional): API version. Defaults to "v1".

    Returns:
        Optional[pd.DataFrame]: Processed DataFrame with verification results.
    """
    try:
        # Read the file
        if file_type == "csv":
            df = pd.read_csv(file, dtype={'pan': 'str', 'birthOrIncorporatedDate': 'str', 'name': 'str'})
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file, dtype={'pan': 'str', 'birthOrIncorporatedDate': 'str', 'name': 'str'})
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Define required columns
        required_columns = ['sno', 'pan', 'birthOrIncorporatedDate', 'name']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Define expected response keys
        expected_keys = [
            "valid", "message", "panStatus", "fy", "itrFiled",
            "itrType", "grossTurnover", "grossTurnoverFormatted",
            "exportTurnover", "exportTurnoverFormatted"
        ]

        # Initialize new columns if they don't exist
        for key in expected_keys:
            if key not in df.columns:
                df[key] = None

        # Iterate through each row and verify PAN
        for idx, row in df.iterrows():
            sno = row['sno']
            pan = row['pan']
            birth_or_incorporated_date = row['birthOrIncorporatedDate']
            name = row['name']

            log_info(f"Processing Sno {sno}: PAN '{pan}'")

            # Validate PAN
            if pd.isna(pan) or str(pan).strip() == "":
                log_warning(f"Sno {sno}: PAN is missing. Skipping verification.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "PAN is missing."
                df.at[idx, 'panStatus'] = ""
                df.at[idx, 'fy'] = ""
                df.at[idx, 'itrFiled'] = False
                df.at[idx, 'itrType'] = ""
                df.at[idx, 'grossTurnover'] = ""
                df.at[idx, 'grossTurnoverFormatted'] = ""
                df.at[idx, 'exportTurnover'] = ""
                df.at[idx, 'exportTurnoverFormatted'] = ""
                continue

            # Verify PAN
            verification_result = cache_company_itr_verification(pan, birth_or_incorporated_date, name, auth_token, version)
            if verification_result:
                # Populate DataFrame based on response
                df.at[idx, 'valid'] = verification_result.get('valid', False)
                df.at[idx, 'message'] = verification_result.get('message', "")
                df.at[idx, 'panStatus'] = verification_result.get('panStatus', "")
                df.at[idx, 'fy'] = verification_result.get('fy', "")
                df.at[idx, 'itrFiled'] = verification_result.get('itrFiled', False)
                df.at[idx, 'itrType'] = verification_result.get('itrType', "")
                df.at[idx, 'grossTurnover'] = verification_result.get('grossTurnover', "")
                df.at[idx, 'grossTurnoverFormatted'] = verification_result.get('grossTurnoverFormatted', "")
                df.at[idx, 'exportTurnover'] = verification_result.get('exportTurnover', "")
                df.at[idx, 'exportTurnoverFormatted'] = verification_result.get('exportTurnoverFormatted', "")
            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "No data returned from API."
                df.at[idx, 'panStatus'] = ""
                df.at[idx, 'fy'] = ""
                df.at[idx, 'itrFiled'] = False
                df.at[idx, 'itrType'] = ""
                df.at[idx, 'grossTurnover'] = ""
                df.at[idx, 'grossTurnoverFormatted'] = ""
                df.at[idx, 'exportTurnover'] = ""
                df.at[idx, 'exportTurnoverFormatted'] = ""

        log_info("Company ITR Verification processing complete.")
        st.write("### Processed Data", df)

        return df

    except Exception as e:
        log_error(f"An error occurred while processing the Company ITR Verification file: {e}")
        return None

def run():
    st.header("Company ITR Verification")
    st.write("""
        This section allows you to verify Company Income Tax Returns (ITR) and gross revenue details using the Attestr API.
        
        This API provides instant access to the latest details of Income Tax Return (ITR) filings and the gross revenue of a company based on the provided business PAN number. It's especially useful for conducting real-time analysis of company/vendor credit risks for compliance purposes.
        **Features:**
        - Validates the existence and status of a company's PAN.
        - Retrieves ITR filing details and gross turnover information.
        
        Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/business-itr-and-gross-turnover-by-pan-number-api) for more details.
    """)

    # Access API tokens from session state
    google_api_key = st.session_state.get("google_api_key", "")
    attestr_auth_token = st.session_state.get("attestr_auth_token", "")

    if not attestr_auth_token:
        st.warning("Please enter your Attestr Auth Token on the Home page to proceed.")
        return

    st.write("""
        Upload a CSV or XLSX file containing Company ITR details. The input file should have the following columns:
        - **sno**: Serial number (unique for each row)
        - **pan**: Business PAN Number
        - **birthOrIncorporatedDate**: Date of incorporation in DD/MM/YYYY format
        - **name**: Registered legal name as per PAN
    """)

    uploaded_file = st.file_uploader(
        "Upload your Company ITR Verification file (CSV or XLSX).",
        type=["csv", "xlsx"],
        key="company_itr_verification"
    )

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1].lower()
        version = "v2"

        if st.button("Run Company ITR Verification", key="run_company_itr_verification"):
            with st.spinner("Processing Company ITR Verification..."):
                processed_df = process_company_itr_verification(
                    file=uploaded_file,
                    file_type=file_type,
                    auth_token=attestr_auth_token,
                    version=version
                )

            if processed_df is not None:
                st.success("Company ITR Verification completed successfully.")
                # Uncomment the following line to display the processed DataFrame
                # st.write("### Processed Data", processed_df)

                # Download Button
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="company_itr_verification_results.csv",
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