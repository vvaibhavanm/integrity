# pages/page_voter_id_verification.py

import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
import os
from typing import Optional, Dict, Any
import json

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

# --------------------------- Credit Score Verification API Functions ---------------------------

CREDIT_SCORE_VERIFICATION_URL_TEMPLATE = "https://api.invincibleocean.com/invincible/creditScoreCheckV2"

def verify_credit_score(name: str, pan: str, mob: str, clientid: str, secretkey:str) -> Dict[str, Any]:
    if (not clientid) or (not secretkey):
        log_error("Invincible auth is missing.")
        return {}

    url = CREDIT_SCORE_VERIFICATION_URL_TEMPLATE

    headers = {
        'Content-Type': 'application/json',
        'clientId': clientid,
        'secretKey': secretkey
    }

    payload = json.dumps({
        "name": name,
        "panNumber": pan,
        "mobileNumber": mob
    })
    print(payload)
    print(headers)

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        print(response)
        response.raise_for_status()
        data = response.json()
        print(data)
        log_info(f"Credit Score Verification successful for name: '{name}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error during Credit Score verification for name '{name}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error during Credit Score verification for name '{name}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error during Credit Score verification for name '{name}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception during Credit Score verification for name '{name}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for Credit Score verification response of name '{name}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during Credit Score verification for name '{name}': {e}")

    return {}

@st.cache_data
def cache_credit_score_verification(name: str, pan: str, mob: str, clientid: str, secretkey:str) -> Dict[str, Any]:
    
    return verify_credit_score(name, pan, mob, clientid, secretkey)

def process_credit_score_verification(
    file: BytesIO,
    file_type: str,
    clientid: str,
    secretkey: str
) -> Optional[pd.DataFrame]:
    try:
        # Read the file
        if file_type == "csv":
            df = pd.read_csv(file, dtype={'name': 'str', 'pan': 'str', 'mob': 'str'})
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file, dtype={'name': 'str', 'pan': 'str', 'mob': 'str'})
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Define required columns
        required_columns = ['sno', 'name', 'pan', 'mob']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Initialize new columns for results
        result_columns = [
            "credit_score", "credit_report_link", "valid", "message"
        ]
        for col in result_columns:
            if col not in df.columns:
                df[col] = None

        # Iterate through each row and verify name
        for idx, row in df.iterrows():
            sno = row['sno']
            name = row['name']
            pan = row['pan']
            mob = row['mob']

            log_info(f"Processing Sno {sno}: name '{name}'")

            # Validate name
            if pd.isna(name) or str(name).strip() == "" or pd.isna(pan) or str(pan).strip() == "" or pd.isna(mob) or str(mob).strip() == "":
                log_warning(f"Sno {sno}: Details missing. Skipping verification.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "Details missing."
                # Set other fields to default empty values
                for key in result_columns:
                    if key != "valid" and key != "message":
                        df.at[idx, key] = ""
                continue

            # Verify name
            verification_result = cache_credit_score_verification(name, pan, mob, clientid, secretkey)
            print(verification_result.get("result", {}).get("success", False))
            print(verification_result.get("result", {}).get("message", ""))
            print(verification_result.get("result", {}).get("data", {}).get("credit_score", ""))
            print(verification_result.get("result", {}).get("data", {}).get("credit_report_link", ""))
            if verification_result:
                # Populate DataFrame based on response
                df.at[idx, 'valid'] = verification_result.get("result", {}).get("success", False)
                
                df.at[idx, 'message'] = verification_result.get("result", {}).get("message", "")
                if verification_result.get("result", {}).get("success", False):
                    df.at[idx, 'credit_score'] = verification_result.get("result", {}).get("data", {}).get("credit_score", "")
                    df.at[idx, 'credit_report_link'] = verification_result.get("result", {}).get("data", {}).get("credit_report_link", "")
                
            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "No data returned from API."
                # Set other fields to default empty values
                for key in result_columns:
                    if key != "valid" and key != "message":
                        df.at[idx, key] = ""

        log_info("Credit Score Verification processing complete.")
        st.write("### Processed Data", df)

        return df

    except Exception as e:
        log_error(f"An error occurred while processing the Credit Score Verification file: {e}")
        return None

def run():
    st.header("Credit Score check")
    st.write("""
             Enter the details to verify the credit score of an individual.
             """)

    # Access API tokens from session state
    google_api_key = st.session_state.get("google_api_key", "")
    attestr_auth_token = st.session_state.get("attestr_auth_token", "")
    invincible_clientid = st.session_state.get("invincible_clientid", "")
    invincible_secretkey = st.session_state.get("invincible_secretkey", "")
    if (not invincible_clientid) or (not invincible_secretkey):
        st.warning("Please enter your Invincible Auth on the Home page to proceed.")
        return

    # st.write("""
    #     Upload a CSV or XLSX file containing Credit Score details. The input file should have the following columns:
    #     - **sno**: Serial number (unique for each row)
    #     - **name**: name (Credit Score) Number
    # """)

    uploaded_file = st.file_uploader(
        "Upload your Credit Score Verification file (CSV or XLSX).",
        type=["csv", "xlsx"],
        key="voter_id_verification"
    )

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]
        
        if st.button("Run Credit Score Verification", key="run_voter_id_verification"):
            with st.spinner("Processing Credit Score Verification..."):
                processed_df = process_credit_score_verification(
                    file=uploaded_file,
                    file_type=file_type,
                    clientid=invincible_clientid,
                    secretkey=invincible_secretkey
                )

            if processed_df is not None:
                st.success("Credit Score Verification completed successfully.")
                # Uncomment the following line to display the processed DataFrame
                # st.write("### Processed Data", processed_df)

                # Download Button
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="credit_score_verification_results.csv",
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