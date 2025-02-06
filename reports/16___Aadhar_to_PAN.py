# pages/page_aadhar_to_pan_verification.py

import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
import os
from typing import Optional, Dict, Any
import json

# Placeholder URL - replace with actual API endpoint
aadhar_to_pan_VERIFICATION_URL = "https://api.invincibleocean.com/invincible/aadhaarToPan"

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
    return {key: response.get("result",{}).get(key, "") for key in expected_keys}

def verify_aadhar_to_pan(aadhar_to_pan: str, clientid: str, secretkey:str) -> Dict[str, Any]:
    if (not clientid) or (not secretkey):
        log_error("Invincible auth is missing.")
        return {}

    url = aadhar_to_pan_VERIFICATION_URL

    headers = {
        'Content-Type': 'application/json',
        'clientId': clientid,
        'secretKey': secretkey
    }

    payload = json.dumps({
        "aadharNumber": aadhar_to_pan
    })
    print(payload)
    print(headers)

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        print(response)
        response.raise_for_status()
        data = response.json()
        print(data)
        log_info(f"Aadhar to pan Verification successful for pan: '{aadhar_to_pan}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error during Aadhar to pan verification for pan '{aadhar_to_pan}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error during Aadhar to pan verification for pan '{aadhar_to_pan}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error during Aadhar to pan verification for pan '{aadhar_to_pan}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception during Aadhar to pan verification for pan '{aadhar_to_pan}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for Aadhar to pan verification response of pan '{aadhar_to_pan}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during Aadhar to pan verification for pan '{aadhar_to_pan}': {e}")

    return {}

@st.cache_data
def cache_aadhar_to_pan_verification(pan: str , clientid: str, secretkey:str) -> Dict[str, Any]:
    return verify_aadhar_to_pan(pan, clientid, secretkey)

def process_aadhar_to_pan_verification(file: BytesIO, file_type: str, clientid: str, secretkey:str) -> Optional[pd.DataFrame]:
    try:
        if file_type == "csv":
            df = pd.read_csv(file)
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file)
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Validate required columns
        required_columns = ['sno', 'aadhar']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Define expected response keys
        expected_keys = [
            "PAN",
            "success",
            "message"
        ]

        # Initialize new columns if they don't exist
        for key in expected_keys:
            if key not in df.columns:
                df[key] = None

        # Iterate through each row
        for idx, row in df.iterrows():
            sno = row['sno']
            aadhar = str(row['aadhar'])

            log_info(f"Processing Sno {sno}: aadhar '{aadhar}'")

            if pd.isna(aadhar) or str(aadhar).strip() == "":
                log_warning(f"Sno {sno}: aadhar is missing. Skipping verification.")
                continue

            # Verify aadhar
            verification_result = cache_aadhar_to_pan_verification(aadhar, clientid, secretkey)
            if verification_result:
                df.at[idx, "success"] = True
                df.at[idx, "message"] = "Verification successful."
                df.at[idx, "PAN"] = verification_result.get("result", {}).get("data", {}).get("pan_number", "")
            else:
                pass

        log_info("aadhar Verification processing complete.")
        st.write("### Processed Data", df)

        return df

    except Exception as e:
        log_error(f"An error occurred while processing the aadhar verification file: {e}")
        return None

def run():
    st.header("Aadhar to PAN")
    st.write("Aadhar to PAN verification is a process to verify the PAN details using the Aadhar number.")
    # Access API tokens from session state
    google_api_key = st.session_state.get("google_api_key", "")
    attestr_auth_token = st.session_state.get("attestr_auth_token", "")
    invincible_clientid = st.session_state.get("invincible_clientid", "")
    invincible_secretkey = st.session_state.get("invincible_secretkey", "")
    
    if (not invincible_clientid) or (not invincible_secretkey):
        st.warning("Please enter your Invincible Auth on the Home page to proceed.")
        return

    st.write("""
        Upload a CSV or XLSX file containing PAN details. The input file should have the following columns:
        - **sno**: Serial number (unique for each row)
        - **aadhar**: Aadhar Number
    """)

    
    uploaded_file = st.file_uploader(
        "Upload your Aadhar to PAN file (CSV or XLSX).",
        type=["csv", "xlsx"],
        key="aadhar_to_pan_verification"
    )

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]
        if st.button("Run Aadhar to aadhar_to_pan", key="run_aadhar_to_pan_verification"):
            with st.spinner("Processing Aadhar to aadhar_to_pan..."):
                processed_df = process_aadhar_to_pan_verification(
                    file=uploaded_file,
                    file_type=file_type,
                    clientid=invincible_clientid,
                    secretkey=invincible_secretkey
                )

            if processed_df is not None:
                st.success("Aadhar to pan completed successfully.")
                # st.write("### Processed Data", processed_df)

                # Download Button
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="aadhar_to_pan_verification_results.csv",
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