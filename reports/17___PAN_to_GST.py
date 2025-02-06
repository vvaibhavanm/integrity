# pages/page_pan_to_gst_verification.py

import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
import os
from typing import Optional, Dict, Any
import json

# Placeholder URL - replace with actual API endpoint
pan_to_gst_VERIFICATION_URL = "https://api.invincibleocean.com/invincible/panToGSTLite"

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

def verify_pan_to_gst(pan_to_gst: str, clientid: str, secretkey:str) -> Dict[str, Any]:
    if (not clientid) or (not secretkey):
        log_error("Invincible auth is missing.")
        return {}

    url = pan_to_gst_VERIFICATION_URL

    headers = {
        'Content-Type': 'application/json',
        'clientId': clientid,
        'secretKey': secretkey
    }

    payload = json.dumps({
        "panNumber": pan_to_gst
    })
    print(payload)
    print(headers)

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        print(response)
        response.raise_for_status()
        data = response.json()
        print(data)
        log_info(f"PAN to gst Verification successful for pan: '{pan_to_gst}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error during PAN to gst verification for pan '{pan_to_gst}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error during PAN to gst verification for pan '{pan_to_gst}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error during PAN to gst verification for pan '{pan_to_gst}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception during PAN to gst verification for pan '{pan_to_gst}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for PAN to gst verification response of pan '{pan_to_gst}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during PAN to gst verification for pan '{pan_to_gst}': {e}")

    return {}

@st.cache_data
def cache_pan_to_gst_verification(pan: str , clientid: str, secretkey:str) -> Dict[str, Any]:
    return verify_pan_to_gst(pan, clientid, secretkey)


def flatten_json(nested_json,sno,pan, prefix=''):
    """
    Recursively flattens a nested JSON object into a dictionary.
    """
    flattened_dict = {}
    flattened_dict["sno"] = sno
    flattened_dict["pan"] = pan
    for key, value in nested_json.items():
        new_key = f"{prefix}/{key}" if prefix else key
        
        if isinstance(value, dict):
            flattened_dict.update(flatten_json(value,sno,pan, new_key))
        else:
            flattened_dict[new_key] = value
    
    return flattened_dict

def process_pan_to_gst_verification(file: BytesIO, file_type: str, clientid: str, secretkey:str) -> Optional[pd.DataFrame]:
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

        result_df = pd.DataFrame()
        # Iterate through each row
        for idx, row in df.iterrows():
            sno = row['sno']
            pan = row['pan']

            log_info(f"Processing Sno {sno}: pan '{pan}'")

            if pd.isna(pan) or str(pan).strip() == "":
                log_warning(f"Sno {sno}: pan is missing. Skipping verification.")
                continue

            # Verify pan
            verification_result = cache_pan_to_gst_verification(pan, clientid, secretkey)
            flattened_json = flatten_json(verification_result,sno,pan)
            if verification_result:
                result_df = pd.concat([result_df, pd.DataFrame([flattened_json])], ignore_index=True)
            else:
                pass

        log_info("pan Verification processing complete.")
        st.write("### Processed Data", result_df)

        return result_df

    except Exception as e:
        log_error(f"An error occurred while processing the pan verification file: {e}")
        return None

def run():
    st.header("PAN to gst")
    st.write("PAN to gst verification is a process to verify the gst details using the PAN number.")
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
        - **pan**: PAN Number
    """)

    
    uploaded_file = st.file_uploader(
        "Upload your PAN to gst file (CSV or XLSX).",
        type=["csv", "xlsx"],
        key="pan_to_gst_verification"
    )

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]
        if st.button("Run PAN to gst", key="run_pan_to_gst_verification"):
            with st.spinner("Processing PAN to gst..."):
                processed_df = process_pan_to_gst_verification(
                    file=uploaded_file,
                    file_type=file_type,
                    clientid=invincible_clientid,
                    secretkey=invincible_secretkey
                )

            if processed_df is not None:
                st.success("PAN to gst completed successfully.")
                # st.write("### Processed Data", processed_df)

                # Download Button
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="pan_to_gst_verification_results.csv",
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