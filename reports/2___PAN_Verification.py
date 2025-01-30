# pages/page_pan_verification.py

import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
import os
from typing import Optional, Dict, Any

# Placeholder URL - replace with actual API endpoint
PAN_VERIFICATION_URL = "https://api.attestr.com/api/v2/public/checkx/pan"

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

def verify_pan(pan: str, auth_token: str) -> Dict[str, Any]:
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    payload = {
        "pan": pan
    }

    try:
        response = requests.post(PAN_VERIFICATION_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        log_info(f"PAN Verification successful for PAN: '{pan}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error occurred during PAN verification for PAN '{pan}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error occurred during PAN verification for PAN '{pan}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error occurred during PAN verification for PAN '{pan}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception occurred during PAN verification for PAN '{pan}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for PAN verification response of PAN '{pan}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during PAN verification for PAN '{pan}': {e}")

    return {}

@st.cache_data
def cache_pan_verification(pan: str, auth_token: str) -> Dict[str, Any]:
    return verify_pan(pan, auth_token)

def process_pan_verification(file: BytesIO, file_type: str, auth_token: str) -> Optional[pd.DataFrame]:
    try:
        if file_type == "csv":
            df = pd.read_csv(file)
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file)
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Validate required columns
        required_columns = ['sno', 'pan']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Define expected response keys
        expected_keys = ['valid', 'category', 'name', 'aadhaarLinked', 'message']

        # Initialize new columns if they don't exist
        for key in expected_keys:
            if key not in df.columns:
                df[key] = None

        # Iterate through each row
        for idx, row in df.iterrows():
            sno = row['sno']
            pan = row['pan']

            log_info(f"Processing Sno {sno}: PAN '{pan}'")

            if pd.isna(pan) or str(pan).strip() == "":
                log_warning(f"Sno {sno}: PAN is missing. Skipping verification.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'category'] = ""
                df.at[idx, 'name'] = ""
                df.at[idx, 'aadhaarLinked'] = ""
                df.at[idx, 'message'] = "PAN is missing."
                continue

            # Verify PAN
            verification_result = cache_pan_verification(pan, auth_token)
            if verification_result:
                # Map response to expected keys
                mapped_data = map_response_to_df(verification_result, expected_keys)
                df.at[idx, 'valid'] = mapped_data.get('valid', False)
                df.at[idx, 'category'] = mapped_data.get('category', "")
                df.at[idx, 'name'] = mapped_data.get('name', "")
                df.at[idx, 'aadhaarLinked'] = mapped_data.get('aadhaarLinked', "")
                df.at[idx, 'message'] = mapped_data.get('message', "")
            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'category'] = ""
                df.at[idx, 'name'] = ""
                df.at[idx, 'aadhaarLinked'] = ""
                df.at[idx, 'message'] = "No data returned from API."

        log_info("PAN Verification processing complete.")
        st.write("### Processed Data", df)

        return df

    except Exception as e:
        log_error(f"An error occurred while processing the PAN verification file: {e}")
        return None

def run():
    st.header("PAN Verification")
    st.write("This section allows you to verify PAN details using the Attestr API.")
    st.write("Instant verification of Permanent Account Number (PAN) and validate taxpayer's name, status, Aadhaar linking status, and taxpayer category as registered with National Securities Depositories Limited (NSDL).")
    st.write("Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/pan-verification-api) for more details.")

    # Access API tokens from session state
    google_api_key = st.session_state.get("google_api_key", "")
    attestr_auth_token = st.session_state.get("attestr_auth_token", "")

    if not attestr_auth_token:
        st.warning("Please enter your Attestr Auth Token on the Home page to proceed.")
        return

    st.write("""
        Upload a CSV or XLSX file containing PAN details. The input file should have the following columns:
        - **sno**: Serial number (unique for each row)
        - **pan**: Permanent Account Number (PAN)
    """)

    
    uploaded_file = st.file_uploader(
        "Upload your PAN Verification file (CSV or XLSX).",
        type=["csv", "xlsx"],
        key="pan_verification"
    )

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]
        if st.button("Run PAN Verification", key="run_pan_verification"):
            with st.spinner("Processing PAN Verification..."):
                processed_df = process_pan_verification(
                    file=uploaded_file,
                    file_type=file_type,
                    auth_token=attestr_auth_token
                )

            if processed_df is not None:
                st.success("PAN Verification completed successfully.")
                # st.write("### Processed Data", processed_df)

                # Download Button
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="pan_verification_results.csv",
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