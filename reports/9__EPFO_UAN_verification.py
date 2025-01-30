# pages/page_epfo_uan_verification.py

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

# --------------------------- EPFO UAN Verification API Functions ---------------------------

EPFO_UAN_VERIFICATION_URL_TEMPLATE = "https://api.attestr.com/api/v2/public/checkx/epfo/uan"

def verify_epfo_uan(uan: str, auth_token: str, version: str = "v2") -> Dict[str, Any]:
    """
    Verifies the provided UAN number using the Attestr EPFO UAN Verification API.

    Args:
        uan (str): The UAN number to verify.
        auth_token (str): Attestr Auth Token.
        version (str, optional): API version. Defaults to "v2".

    Returns:
        Dict[str, Any]: API response data.
    """
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    url = EPFO_UAN_VERIFICATION_URL_TEMPLATE.format(version=version)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    payload = {
        "uan": uan
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        # print(data)
        # print(payload)
        # print(headers)
        log_info(f"EPFO UAN Verification successful for UAN: '{uan}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error during EPFO UAN verification for UAN '{uan}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error during EPFO UAN verification for UAN '{uan}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error during EPFO UAN verification for UAN '{uan}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception during EPFO UAN verification for UAN '{uan}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for EPFO UAN verification response of UAN '{uan}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during EPFO UAN verification for UAN '{uan}': {e}")

    return {}

@st.cache_data
def cache_epfo_uan_verification(uan: str, auth_token: str, version: str = "v2") -> Dict[str, Any]:
    """
    Caches the EPFO UAN verification response.

    Args:
        uan (str): The UAN number to verify.
        auth_token (str): Attestr Auth Token.
        version (str, optional): API version. Defaults to "v2".

    Returns:
        Dict[str, Any]: Cached API response data.
    """
    return verify_epfo_uan(uan, auth_token, version)

def process_epfo_uan_verification(
    file: BytesIO,
    file_type: str,
    auth_token: str,
    version: str = "v2"
) -> Optional[pd.DataFrame]:
    """
    Processes the EPFO UAN verification by reading the uploaded file, verifying each UAN number,
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
            df = pd.read_csv(file, dtype={'uan': 'str'})
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file, dtype={'uan': 'str'})
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Validate required columns
        required_columns = ['sno', 'uan']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Initialize new columns for results
        result_columns = [
            "valid", "message", "items"
        ]
        for col in result_columns:
            if col not in df.columns:
                df[col] = None

        expanded_rows = []
        # Iterate through each row and verify UAN
        for idx, row in df.iterrows():
            sno = row['sno']
            uan = row['uan']

            log_info(f"Processing Sno {sno}: UAN '{uan}'")

            # Validate UAN
            if pd.isna(uan) or str(uan).strip() == "":
                log_warning(f"Sno {sno}: UAN is missing. Skipping verification.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "UAN is missing."
                df.at[idx, 'items'] = []
                continue

            # Verify UAN
            verification_result = cache_epfo_uan_verification(uan, auth_token, version)
            if verification_result:
                # Populate DataFrame based on response
                df.at[idx, 'valid'] = verification_result.get('valid', False)
                df.at[idx, 'message'] = verification_result.get('message', "")

                if verification_result.get('valid', False):
                    items = verification_result.get('items', [])
                    df.at[idx, 'items'] = items  # Storing the list of employment histories
                    # Expand the items column
                    
                    for subsno, item in enumerate(items, start=1):
                        expanded_row = {'sno':sno, 'uan':uan, 'subsno':subsno, **item}
                        expanded_rows.append(expanded_row)
                else:
                    # If UAN is invalid, 'items' should be an empty list
                    df.at[idx, 'items'] = []
            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "No data returned from API."
                df.at[idx, 'items'] = []
        if expanded_rows:
            expanded_df = pd.DataFrame(expanded_rows)
        else:
            expanded_df = pd.DataFrame(columns=['sno', 'uan', 'subsno'])

        log_info("EPFO UAN Verification processing complete.")
        # st.write("### Processed Data", df)
        # st.write("### expanded Data",expanded_df)
        combined_df = pd.merge(df, expanded_df, on=['sno', 'uan'], how='left')
        st.write("### Processed Data",combined_df)
        return combined_df

    except Exception as e:
        log_error(f"An error occurred while processing the EPFO UAN Verification file: {e}")
        return None

def run():
    st.header("EPFO UAN Verification")
    st.write("""
        This section allows you to verify Employees' Provident Fund Organization (EPFO) Universal Account Number (UAN) details using the Attestr API.
        
        Every employee who makes a contribution to the provident fund in India is given a Universal Account Number (UAN) by the Employees' Provident Fund Organization (EPFO), which has been recognized by the Ministry of Labour and Employment, Government of India. No matter how many companies a person worked for, their universal account number, or UAN, never changes.
        UAN Verification Employment History API verifies a given UAN in real time and returns the employment history of an employee. This offers an instant employment verification option and often used in the place of otherwise physical / manual process of employment verification.
        
        Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/epfo-uan-verification-employment-history-api) for more details.
    """)

    # Access API tokens from session state
    google_api_key = st.session_state.get("google_api_key", "")
    attestr_auth_token = st.session_state.get("attestr_auth_token", "")

    if not attestr_auth_token:
        st.warning("Please enter your Attestr Auth Token on the Home page to proceed.")
        return

    st.write("""
        Upload a CSV or XLSX file containing EPFO UAN details. The input file should have the following columns:
        - **sno**: Serial number (unique for each rowi)
        - **uan**: EPFO Universal Account Number
    """)

    uploaded_file = st.file_uploader(
        "Upload your EPFO UAN Verification file (CSV or XLSX).",
        type=["csv", "xlsx"],
        key="epfo_uan_verification"
    )

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]
        version = "v2"

        if st.button("Run EPFO UAN Verification", key="run_epfo_uan_verification"):
            with st.spinner("Processing EPFO UAN Verification..."):
                processed_df = process_epfo_uan_verification(
                    file=uploaded_file,
                    file_type=file_type,
                    auth_token=attestr_auth_token,
                    version=version
                )

            if processed_df is not None:
                st.success("EPFO UAN Verification completed successfully.")
                # Uncomment the following line to display the processed DataFrame
                # st.write("### Processed Data", processed_df)

                # Download Button
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="epfo_uan_verification_results.csv",
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