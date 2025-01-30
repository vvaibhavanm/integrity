# pages/page_vehicle_rc_check.py

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

# --------------------------- Vehicle RC Check API Functions ---------------------------

VEHICLE_RC_CHECK_URL_TEMPLATE = "https://api.attestr.com/api/v2/public/checkx/rc"

def verify_rc(reg_number: str, auth_token: str, version: str = "v2") -> Dict[str, Any]:
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    url = VEHICLE_RC_CHECK_URL_TEMPLATE.format(version=version)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    payload = {
        "reg": reg_number
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        log_info(f"Vehicle RC Check successful for Registration Number: '{reg_number}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error occurred during Vehicle RC Check for '{reg_number}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error occurred during Vehicle RC Check for '{reg_number}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error occurred during Vehicle RC Check for '{reg_number}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception occurred during Vehicle RC Check for '{reg_number}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for Vehicle RC Check response of '{reg_number}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during Vehicle RC Check for '{reg_number}': {e}")

    return {}

@st.cache_data
def cache_vehicle_rc_verification(reg_number: str, auth_token: str, version: str = "v2") -> Dict[str, Any]:
    return verify_rc(reg_number, auth_token, version)

def process_vehicle_rc_check(file: BytesIO, file_type: str, auth_token: str, version: str = "v2") -> Optional[pd.DataFrame]:
    try:
        if file_type == "csv":
            df = pd.read_csv(file)
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file)
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Validate required columns
        required_columns = ['sno', 'reg']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Define expected response keys
        expected_keys = [
            "valid", "status", "registered", "owner", "masked", "ownerNumber",
            "father", "currentAddress", "permanentAddress", "mobile", "category",
            "categoryDescription", "chassisNumber", "engineNumber", "makerDescription",
            "makerModel", "makerVariant", "bodyType", "fuelType", "colorType",
            "normsType", "fitnessUpto", "financed", "lender", "insuranceProvider",
            "insurancePolicyNumber", "insuranceUpto", "manufactured", "rto",
            "cubicCapacity", "grossWeight", "wheelBase", "unladenWeight", "cylinders",
            "seatingCapacity", "sleepingCapacity", "standingCapacity",
            "pollutionCertificateNumber", "pollutionCertificateUpto", "permitNumber",
            "permitIssued", "permitFrom", "permitUpto", "permitType", "taxUpto",
            "taxPaidUpto", "nationalPermitNumber", "nationalPermitIssued",
            "nationalPermitFrom", "nationalPermitUpto", "nationalPermitIssuedBy",
            "commercial", "blacklistStatus", "nocDetails", "challanDetails",
            "exShowroomPrice", "nonUseStatus", "nonUseFrom", "nonUseTo",
            "blacklistDetails", "message"
        ]

        # Initialize new columns if they don't exist
        for key in expected_keys:
            if key not in df.columns:
                df[key] = None

        # Iterate through each row
        for idx, row in df.iterrows():
            sno = row['sno']
            reg_number = row['reg']

            log_info(f"Processing Sno {sno}: Registration Number '{reg_number}'")
            if (pd.isna(reg_number)) or (str(reg_number).strip() == ""):
                log_warning(f"Sno {sno}: Registration Number is missing. Skipping verification.")
                # Assign default values for invalid entries
                for key in expected_keys:
                    if key == "valid":
                        df.at[idx, key] = False
                    elif key == "message":
                        df.at[idx, key] = "Registration Number is missing."
                    else:
                        df.at[idx, key] = ""
                continue
            
            # Verify RC
            verification_result = cache_vehicle_rc_verification(reg_number, auth_token, version)
            if verification_result:
                # Map response to expected keys
                mapped_data = map_response_to_df(verification_result, expected_keys)
                for key in expected_keys:
                    df.at[idx, key] = mapped_data.get(key, "")
            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'status'] = ""
                df.at[idx, 'registered'] = ""
                df.at[idx, 'owner'] = ""
                df.at[idx, 'masked'] = ""
                df.at[idx, 'ownerNumber'] = ""
                df.at[idx, 'father'] = ""
                df.at[idx, 'currentAddress'] = ""
                df.at[idx, 'permanentAddress'] = ""
                df.at[idx, 'mobile'] = ""
                df.at[idx, 'category'] = ""
                df.at[idx, 'categoryDescription'] = ""
                df.at[idx, 'chassisNumber'] = ""
                df.at[idx, 'engineNumber'] = ""
                df.at[idx, 'makerDescription'] = ""
                df.at[idx, 'makerModel'] = ""
                df.at[idx, 'makerVariant'] = ""
                df.at[idx, 'bodyType'] = ""
                df.at[idx, 'fuelType'] = ""
                df.at[idx, 'colorType'] = ""
                df.at[idx, 'normsType'] = ""
                df.at[idx, 'fitnessUpto'] = ""
                df.at[idx, 'financed'] = ""
                df.at[idx, 'lender'] = ""
                df.at[idx, 'insuranceProvider'] = ""
                df.at[idx, 'insurancePolicyNumber'] = ""
                df.at[idx, 'insuranceUpto'] = ""
                df.at[idx, 'manufactured'] = ""
                df.at[idx, 'rto'] = ""
                df.at[idx, 'cubicCapacity'] = ""
                df.at[idx, 'grossWeight'] = ""
                df.at[idx, 'wheelBase'] = ""
                df.at[idx, 'unladenWeight'] = ""
                df.at[idx, 'cylinders'] = ""
                df.at[idx, 'seatingCapacity'] = ""
                df.at[idx, 'sleepingCapacity'] = ""
                df.at[idx, 'standingCapacity'] = ""
                df.at[idx, 'pollutionCertificateNumber'] = ""
                df.at[idx, 'pollutionCertificateUpto'] = ""
                df.at[idx, 'permitNumber'] = ""
                df.at[idx, 'permitIssued'] = ""
                df.at[idx, 'permitFrom'] = ""
                df.at[idx, 'permitUpto'] = ""
                df.at[idx, 'permitType'] = ""
                df.at[idx, 'taxUpto'] = ""
                df.at[idx, 'taxPaidUpto'] = ""
                df.at[idx, 'nationalPermitNumber'] = ""
                df.at[idx, 'nationalPermitIssued'] = ""
                df.at[idx, 'nationalPermitFrom'] = ""
                df.at[idx, 'nationalPermitUpto'] = ""
                df.at[idx, 'nationalPermitIssuedBy'] = ""
                df.at[idx, 'commercial'] = ""
                df.at[idx, 'blacklistStatus'] = ""
                df.at[idx, 'nocDetails'] = ""
                df.at[idx, 'challanDetails'] = ""
                df.at[idx, 'exShowroomPrice'] = ""
                df.at[idx, 'nonUseStatus'] = ""
                df.at[idx, 'nonUseFrom'] = ""
                df.at[idx, 'nonUseTo'] = ""
                df.at[idx, 'blacklistDetails'] = ""
                df.at[idx, 'message'] = "No data returned from API."

        log_info("Vehicle RC Check processing complete.")
        st.write("### Processed Data", df)

        return df
    
    except Exception as e:
        log_error(f"An error occurred while processing the GSTIN verification file: {e}")
        return None
    
def run():
    
        st.header("Vehicle RC Check")
        st.write("This section allows you to verify Vehicle Registration Certificate (RC) details using the Attestr API.")
        st.write("Vehicle Registration number (RC) also knows as Vehicle License number is a unique number assigned to every motorised vehicle by the regional transport authorities. The information of the vehicle thus registered, is digitally stored in a central transport database known as Parivahan maintained by the Ministry of Road, Transport and Highways (MoRTH) in India. This API offers a real time verification of vehicle registration numbers and fetches live vehicle data as registered in the Parivahan database.")
        st.write("Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/vehicle-rc-check-api) for more details.")
        # Access API tokens from session state
        google_api_key = st.session_state.get("google_api_key", "")
        attestr_auth_token = st.session_state.get("attestr_auth_token", "")

        if not attestr_auth_token:
            st.warning("Please enter your Attestr Auth Token on the Home page to proceed.")
            return

        st.write("""
            Upload a CSV or XLSX file containing Vehicle Registration details. The input file should have the following columns:
            - **sno**: Serial number (unique for each row)
            - **reg**: Registration Number,""")
        st.write("""
            where registration number is Input vehicle RC number to be verified eg: AP09CU7296
        """)

        uploaded_file = st.file_uploader(
            "Upload your Vehicle RC Check file (CSV or XLSX).",
            type=["csv", "xlsx"],
            key="vehicle_rc_check"
        )

        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1]
            version = "v2"

            if st.button("Run Vehicle RC Check", key="run_vehicle_rc_check"):
                with st.spinner("Processing Vehicle RC Check..."):
                    processed_df = process_vehicle_rc_check(
                        file=uploaded_file,
                        file_type=file_type,
                        auth_token=attestr_auth_token,
                        version=version
                    )

                if processed_df is not None:
                    st.success("Vehicle RC Check completed successfully.")
                    # st.write("### Processed Data", processed_df)

                    # Download Button
                    csv = processed_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Processed Data as CSV",
                        data=csv,
                        file_name="vehicle_rc_check_results.csv",
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