# pages/page_gstin_verification.py

import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
import os
from typing import Optional, Dict, Any

# Placeholder URL - replace with actual API endpoint
GST_VERIFICATION_URL = "https://api.attestr.com/api/v2/public/corpx/gstin"

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

def verify_gstin(gstin: str, auth_token: str, fetch_filings: bool = False, fy: Optional[str] = None) -> Dict[str, Any]:
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    if fetch_filings and not fy:
        log_error("Financial year ('fy') must be provided if 'fetch_filings' is set to True.")
        return {}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    payload = {
        "gstin": gstin,
        "fetchFilings": fetch_filings
    }

    if fetch_filings:
        payload["fy"] = fy

    try:
        response = requests.post(GST_VERIFICATION_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        log_info(f"GSTIN Verification successful for GSTIN: '{gstin}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error occurred during GSTIN verification for GSTIN '{gstin}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error occurred during GSTIN verification for GSTIN '{gstin}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error occurred during GSTIN verification for GSTIN '{gstin}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception occurred during GSTIN verification for GSTIN '{gstin}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for GSTIN verification response of GSTIN '{gstin}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during GSTIN verification for GSTIN '{gstin}': {e}")

    return {}

@st.cache_data
def cache_gstin_verification(gstin: str, auth_token: str, fetch_filings: bool, fy: Optional[str]) -> Dict[str, Any]:
    return verify_gstin(gstin, auth_token, fetch_filings, fy)

def process_gstin_verification(file: BytesIO, file_type: str, auth_token: str, fetch_filings: bool, fy: Optional[str]="") -> Optional[pd.DataFrame]:
    try:
        if file_type == "csv":
            df = pd.read_csv(file)
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file)
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Validate required columns
        required_columns = ['sno', 'gstin']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Define expected response keys
        expected_keys = [
            "valid", "active", "legalName", "tradeName", "pan", "constitution",
            "nature", "type", "registered", "updated", "expiry", "state", "stateCode",
            "center", "centerCode", "einvoiceEnabled", "message"
        ]

        # Initialize new columns if they don't exist
        for key in expected_keys:
            if key not in df.columns:
                df[key] = None

        # Iterate through each row
        for idx, row in df.iterrows():
            sno = row['sno']
            gstin = row['gstin']

            log_info(f"Processing Sno {sno}: GSTIN '{gstin}'")

            if pd.isna(gstin) or str(gstin).strip() == "":
                log_warning(f"Sno {sno}: GSTIN is missing. Skipping verification.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'active'] = ""
                df.at[idx, 'legalName'] = ""
                df.at[idx, 'tradeName'] = ""
                df.at[idx, 'pan'] = ""
                df.at[idx, 'constitution'] = ""
                df.at[idx, 'nature'] = ""
                df.at[idx, 'type'] = ""
                df.at[idx, 'registered'] = ""
                df.at[idx, 'updated'] = ""
                df.at[idx, 'expiry'] = ""
                df.at[idx, 'state'] = ""
                df.at[idx, 'stateCode'] = ""
                df.at[idx, 'center'] = ""
                df.at[idx, 'centerCode'] = ""
                df.at[idx, 'einvoiceEnabled'] = ""
                df.at[idx, 'message'] = "GSTIN is missing."
                continue

            # Verify GSTIN
            verification_result = cache_gstin_verification(gstin, auth_token, fetch_filings, fy)
            if verification_result:
                # Map response to expected keys
                mapped_data = map_response_to_df(verification_result, expected_keys)
                df.at[idx, 'valid'] = mapped_data.get('valid', False)
                df.at[idx, 'active'] = mapped_data.get('active', "")
                df.at[idx, 'legalName'] = mapped_data.get('legalName', "")
                df.at[idx, 'tradeName'] = mapped_data.get('tradeName', "")
                df.at[idx, 'pan'] = mapped_data.get('pan', "")
                df.at[idx, 'constitution'] = mapped_data.get('constitution', "")
                df.at[idx, 'nature'] = mapped_data.get('nature', "")
                df.at[idx, 'type'] = mapped_data.get('type', "")
                df.at[idx, 'registered'] = mapped_data.get('registered', "")
                df.at[idx, 'updated'] = mapped_data.get('updated', "")
                df.at[idx, 'expiry'] = mapped_data.get('expiry', "")
                df.at[idx, 'state'] = mapped_data.get('state', "")
                df.at[idx, 'stateCode'] = mapped_data.get('stateCode', "")
                df.at[idx, 'center'] = mapped_data.get('center', "")
                df.at[idx, 'centerCode'] = mapped_data.get('centerCode', "")
                df.at[idx, 'einvoiceEnabled'] = mapped_data.get('einvoiceEnabled', "")
                df.at[idx, 'message'] = mapped_data.get('message', "")
            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'active'] = ""
                df.at[idx, 'legalName'] = ""
                df.at[idx, 'tradeName'] = ""
                df.at[idx, 'pan'] = ""
                df.at[idx, 'constitution'] = ""
                df.at[idx, 'nature'] = ""
                df.at[idx, 'type'] = ""
                df.at[idx, 'registered'] = ""
                df.at[idx, 'updated'] = ""
                df.at[idx, 'expiry'] = ""
                df.at[idx, 'state'] = ""
                df.at[idx, 'stateCode'] = ""
                df.at[idx, 'center'] = ""
                df.at[idx, 'centerCode'] = ""
                df.at[idx, 'einvoiceEnabled'] = ""
                df.at[idx, 'message'] = "No data returned from API."

        log_info("GSTIN Verification processing complete.")
        st.write("### Processed Data", df)

        return df
    
    except Exception as e:
        log_error(f"An error occurred while processing the GSTIN verification file: {e}")
        return None


def run():
        st.header("GSTIN Verification")
        st.write("This section allows you to verify GSTIN details using the Attestr API.")

        st.write("Indian Goods And Service Tax Act was implemented in July 2017 which replaced many indirect taxes. GSTIN is a unique number assigned to companies registered under this Act. GSTIN verification is the process of verifying the registration of an entity.")
        st.write("Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/gstin-verification-api) for more details.")

        # Access API tokens from session state
        google_api_key = st.session_state.get("google_api_key", "")
        attestr_auth_token = st.session_state.get("attestr_auth_token", "")

        if not attestr_auth_token:
            st.warning("Please enter your Attestr Auth Token on the Home page to proceed.")
            return

        st.write("""
            Upload a CSV or XLSX file containing GSTIN details. The input file should have the following columns:
            - **sno**: Serial number (unique for each row)
            - **gstin**: Goods and Services Tax Identification Number (GSTIN)
        """)

        uploaded_file = st.file_uploader(
            "Upload your GSTIN Verification file (CSV or XLSX).",
            type=["csv", "xlsx"],
            key="gstin_verification"
        )

        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1]
            # fetch_filings = st.checkbox("Fetch Filings", value=False)
            fetch_filings = False
            fy=""
            # fy = ""
            # if fetch_filings:
            #     fy = st.text_input("Enter Financial Year (e.g., 2021-22)", value="")

            if st.button("Run GSTIN Verification", key="run_gstin_verification"):
                with st.spinner("Processing GSTIN Verification..."):
                    processed_df = process_gstin_verification(
                        file=uploaded_file,
                        file_type=file_type,
                        auth_token=attestr_auth_token,
                        fetch_filings=fetch_filings,
                        fy=fy
                    )

                if processed_df is not None:
                    st.success("GSTIN Verification completed successfully.")
                    # st.write("### Processed Data", processed_df)

                    # Download Button
                    csv = processed_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Processed Data as CSV",
                        data=csv,
                        file_name="gstin_verification_results.csv",
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