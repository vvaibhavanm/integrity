# pages/page_mobile_number_verification.py

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

# --------------------------- Mobile Number Verification API Functions ---------------------------

PHONE_VALIDATION_URL_TEMPLATE = "https://api.attestr.com/api/v1/public/checkx/contact"

def verify_mobile_number(number: str, auth_token: str, version: str = "v1") -> Dict[str, Any]:
    """
    Validates a phone number using the Phone Validation API.

    Args:
        number (str): The phone number to validate in E.164 format (e.g., "+911234567890").
        auth_token (str): The Attestr Auth Token for authentication.
        version (str, optional): API version. Defaults to "v1".

    Returns:
        Dict[str, Any]: The API response containing validation details.
    """
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    url = PHONE_VALIDATION_URL_TEMPLATE.format(version=version)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    payload = {
        "number": number
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        log_info(f"Phone Validation successful for Number: '{number}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error occurred during Phone Validation for '{number}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error occurred during Phone Validation for '{number}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error occurred during Phone Validation for '{number}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception occurred during Phone Validation for '{number}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for Phone Validation response of '{number}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during Phone Validation for '{number}': {e}")

    return {}

@st.cache_data
def cache_mobile_verification(number: str, auth_token: str, version: str = "v1") -> Dict[str, Any]:
    """
    Caches the phone number validation result.

    Args:
        number (str): The phone number to validate.
        auth_token (str): The Attestr Auth Token.
        version (str, optional): API version. Defaults to "v1".

    Returns:
        Dict[str, Any]: Cached API response.
    """
    return verify_mobile_number(number, auth_token, version)

def process_mobile_verification(file: BytesIO, file_type: str, auth_token: str) -> Optional[pd.DataFrame]:
    """
    Processes the uploaded file for phone number validation.

    Args:
        file (BytesIO): The uploaded file containing phone numbers.
        file_type (str): The type of the uploaded file ('csv', 'xls', 'xlsx').
        auth_token (str): The Attestr Auth Token for API authentication.

    Returns:
        Optional[pd.DataFrame]: The processed DataFrame with validation results.
    """
    try:
        # Load the uploaded file into a DataFrame
        if file_type == "csv":
            df = pd.read_csv(file, dtype={'number': 'str'})
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file, dtype={'number': 'str'})
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Validate required columns
        required_columns = ['sno', 'number']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Define expected response keys based on API documentation
        expected_keys = [
            "valid", "type", "localF", "intlF", "prefix",
            "code", "country", "area", "carrier", "message"
        ]

        # Initialize new columns if they don't exist
        for key in expected_keys:
            if key not in df.columns:
                df[key] = None

        # Iterate through each row in the DataFrame
        for idx, row in df.iterrows():
            sno = row['sno']
            number = row['number']

            log_info(f"Processing Sno {sno}: Phone Number '{number}'")

            if pd.isna(number) or str(number).strip() == "":
                log_warning(f"Sno {sno}: Phone Number is missing. Skipping validation.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "Phone Number is missing."
                # Set other fields to empty strings
                for key in expected_keys:
                    if key != "valid" and key != "message":
                        df.at[idx, key] = ""
                continue

            # Validate Phone Number using the cached function
            validation_result = cache_mobile_verification(number, auth_token)

            if validation_result:
                # Map response to expected keys
                mapped_data = map_response_to_df(validation_result, expected_keys)

                # Assign 'valid' and 'message' fields
                df.at[idx, 'valid'] = mapped_data.get('valid', False)
                df.at[idx, 'message'] = mapped_data.get('message', "")

                if mapped_data.get('valid', False):
                    # Assign other fields only if the number is valid
                    df.at[idx, 'type'] = mapped_data.get('type', "")
                    df.at[idx, 'localF'] = mapped_data.get('localF', "")
                    df.at[idx, 'intlF'] = mapped_data.get('intlF', "")
                    df.at[idx, 'prefix'] = mapped_data.get('prefix', "")
                    df.at[idx, 'code'] = mapped_data.get('code', "")
                    df.at[idx, 'country'] = mapped_data.get('country', "")
                    df.at[idx, 'area'] = mapped_data.get('area', "")
                    df.at[idx, 'carrier'] = mapped_data.get('carrier', "")
                else:
                    # If not valid, set other fields to empty strings
                    for key in expected_keys:
                        if key != "valid" and key != "message":
                            df.at[idx, key] = ""
            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "No data returned from API."
                # Set other fields to empty strings
                for key in expected_keys:
                    if key != "valid" and key != "message":
                        df.at[idx, key] = ""

        log_info("Phone Number Validation processing complete.")
        st.write("### Processed Data", df)

        return df

    except Exception as e:
        log_error(f"An error occurred while processing the Phone Number Validation file: {e}")
        return None

def run():
    st.header("Mobile Number Verification")
    st.write("This section allows you to verify mobile number details using the Attestr API.")
    st.write("""
        Filters out invalid phone numbers and provides additional details for valid numbers. Useful for:
        Type of service: Identify different types of phone number services such as mobile, landline, toll free, special services and more.
        Carrier information: Find information about the service provider specific to the location at which phone number is registered.
        Registered location: User's registered country name and local area details as registered in service provider's database.
        Country code and prefix: Accurate country code and prefix data for more than 230 supported countries in the world.
        Localized  and international formats: Show localized phone numbers in your application as per user's locale with local and international formats.    
        """)
    
    st.write("Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/phone-validation-api) for more details.")
    
    # Access API tokens from session state
    google_api_key = st.session_state.get("google_api_key", "")
    attestr_auth_token = st.session_state.get("attestr_auth_token", "")

    if not attestr_auth_token:
        st.warning("Please enter your Attestr Auth Token on the Home page to proceed.")
        return

    st.write("""
        Upload a CSV or XLSX file containing mobile number details. The input file should have the following columns:
        - **sno**: Serial number (unique for each row)
        - **number**: Mobile number in E.164 format (e.g., "+911234567890")
    """)

    uploaded_file = st.file_uploader(
        "Upload your Mobile Number Verification file (CSV or XLSX).",
        type=["csv", "xlsx"],
        key="mobile_verification"
    )

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]
        version = "v1"

        if st.button("Run Mobile Number Verification", key="run_mobile_verification"):
            with st.spinner("Processing Mobile Number Verification..."):
                processed_df = process_mobile_verification(
                    file=uploaded_file,
                    file_type=file_type,
                    auth_token=attestr_auth_token
                )

            if processed_df is not None:
                st.success("Mobile Number Verification completed successfully.")
                # st.write("### Processed Data", processed_df)

                # Download Button
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="mobile_number_verification_results.csv",
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