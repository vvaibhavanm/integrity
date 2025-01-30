# pages/page_bank_account_verification.py

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

# --------------------------- Bank Account Verification API Functions ---------------------------

BANK_VERIFICATION_URL_TEMPLATE = "https://api.attestr.com/api/v1/public/finanx/acc"

def verify_bank_account(acc: str, ifsc: str, auth_token: str, fetch_ifsc: bool = False, version: str = "v1") -> Dict[str, Any]:
    """
    Verifies the provided bank account using the Attestr Bank Account Verification API.

    Args:
        acc (str): Bank account number to verify.
        ifsc (str): IFSC code of the bank branch.
        auth_token (str): Attestr Auth Token for authentication.
        fetch_ifsc (bool, optional): Whether to fetch IFSC details. Defaults to False.
        version (str, optional): API version. Defaults to "v1".

    Returns:
        Dict[str, Any]: API response data.
    """
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    url = BANK_VERIFICATION_URL_TEMPLATE.format(version=version)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    payload = {
        "acc": acc,
        "ifsc": ifsc,
        "fetchIfsc": fetch_ifsc
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        log_info(f"Bank Account Verification successful for Account: '{acc}', IFSC: '{ifsc}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error occurred during Bank Account verification for Account '{acc}', IFSC '{ifsc}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error occurred during Bank Account verification for Account '{acc}', IFSC '{ifsc}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error occurred during Bank Account verification for Account '{acc}', IFSC '{ifsc}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception occurred during Bank Account verification for Account '{acc}', IFSC '{ifsc}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for Bank Account verification response of Account '{acc}', IFSC '{ifsc}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during Bank Account verification for Account '{acc}', IFSC '{ifsc}': {e}")

    return {}

@st.cache_data
def cache_bank_verification(acc: str, ifsc: str, auth_token: str, fetch_ifsc: bool, version: str = "v1") -> Dict[str, Any]:
    """
    Caches the Bank Account verification response.

    Args:
        acc (str): Bank account number to verify.
        ifsc (str): IFSC code of the bank branch.
        auth_token (str): Attestr Auth Token.
        fetch_ifsc (bool): Whether to fetch IFSC details.
        version (str, optional): API version. Defaults to "v1".

    Returns:
        Dict[str, Any]: Cached API response data.
    """
    return verify_bank_account(acc, ifsc, auth_token, fetch_ifsc, version)

def process_bank_verification(file: BytesIO, file_type: str, auth_token: str, fetch_ifsc: bool = False, version: str = "v1") -> Optional[pd.DataFrame]:
    """
    Processes the Bank Account verification by reading the uploaded file, verifying each account,
    and compiling the results into a DataFrame.

    Args:
        file (BytesIO): Uploaded file containing bank account details.
        file_type (str): Type of the uploaded file ('csv' or 'xlsx').
        auth_token (str): Attestr Auth Token for API authentication.
        fetch_ifsc (bool, optional): Whether to fetch IFSC details. Defaults to False.
        version (str, optional): API version. Defaults to "v1".

    Returns:
        Optional[pd.DataFrame]: Processed DataFrame with verification results.
    """
    try:
        if file_type == "csv":
            df = pd.read_csv(file, dtype={'acc': 'str', 'ifsc': 'str'})
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file, dtype={'acc': 'str', 'ifsc': 'str'})
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Validate required columns
        required_columns = ['sno', 'acc', 'ifsc']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Define expected response keys
        expected_keys = [
            "valid", "name", "status", "message", "suggestion", "ifsc"
        ]

        # Initialize new columns if they don't exist
        for key in expected_keys:
            if key not in df.columns:
                df[key] = None

        # Iterate through each row
        for idx, row in df.iterrows():
            sno = row['sno']
            acc = row['acc']
            ifsc = row['ifsc']

            log_info(f"Processing Sno {sno}: Account '{acc}', IFSC '{ifsc}'")

            if pd.isna(acc) or str(acc).strip() == "" or pd.isna(ifsc) or str(ifsc).strip() == "":
                log_warning(f"Sno {sno}: Account Number or IFSC is missing. Skipping verification.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'name'] = ""
                df.at[idx, 'status'] = ""
                df.at[idx, 'message'] = "Account Number or IFSC is missing."
                df.at[idx, 'suggestion'] = ""
                df.at[idx, 'ifsc'] = ifsc
                continue

            # Verify Bank Account
            verification_result = cache_bank_verification(acc, ifsc, auth_token, fetch_ifsc, version)
            if verification_result:
                # Map response to expected keys
                mapped_data = map_response_to_df(verification_result, expected_keys)
                df.at[idx, 'valid'] = mapped_data.get('valid', False)
                df.at[idx, 'name'] = mapped_data.get('name', "")
                df.at[idx, 'status'] = mapped_data.get('status', "")
                df.at[idx, 'message'] = mapped_data.get('message', "")
                df.at[idx, 'suggestion'] = mapped_data.get('suggestion', "")
                # Handle 'ifsc' object if fetch_ifsc is True
                if fetch_ifsc and isinstance(mapped_data.get('ifsc'), dict):
                    ifsc_details = mapped_data['ifsc']
                    # Convert ifsc_details dictionary to string for DataFrame
                    df.at[idx, 'ifsc'] = ifsc
                else:
                    df.at[idx, 'ifsc'] = ifsc
            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'name'] = ""
                df.at[idx, 'status'] = ""
                df.at[idx, 'message'] = "No data returned from API."
                df.at[idx, 'suggestion'] = ""
                df.at[idx, 'ifsc'] = ifsc

        log_info("Bank Account Verification processing complete.")
        st.write("### Processed Data", df)

        return df

    except Exception as e:
        log_error(f"An error occurred while processing the Bank Account verification file: {e}")
        return None

def run():
    st.header("Bank Account Verification")
    st.write("""
        Bank account verification API offers an instant verification of active savings and current bank account, given account number and IFSC code. This API can be used to filter out inactive or invalid bank accounts
        
        **Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/bank-account-verification-api) for more details.**
    """)
    
    # Access API tokens from session state
    google_api_key = st.session_state.get("google_api_key", "")
    attestr_auth_token = st.session_state.get("attestr_auth_token", "")

    if not attestr_auth_token:
        st.warning("Please enter your Attestr Auth Token on the Home page to proceed.")
        return

    st.write("""
        Upload a CSV or XLSX file containing Bank Account details. The input file should have the following columns:
        - **sno**: Serial number (unique for each row)
        - **acc**: Bank Account Number
        - **ifsc**: IFSC Code of the bank branch
    """)

    uploaded_file = st.file_uploader(
        "Upload your Bank Account Verification file (CSV or XLSX).",
        type=["csv", "xlsx"],
        key="bank_verification"
    )

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]
        fetch_ifsc = False
        # fetch_ifsc = st.checkbox("Fetch IFSC Details", value=False)
        version = "v1"

        if st.button("Run Bank Account Verification", key="run_bank_verification"):
            with st.spinner("Processing Bank Account Verification..."):
                processed_df = process_bank_verification(
                    file=uploaded_file,
                    file_type=file_type,
                    auth_token=attestr_auth_token,
                    fetch_ifsc=fetch_ifsc,
                    version=version
                )

            if processed_df is not None:
                st.success("Bank Account Verification completed successfully.")
                # Uncomment the following line to display the processed DataFrame
                # st.write("### Processed Data", processed_df)

                # Download Button
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="bank_account_verification_results.csv",
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