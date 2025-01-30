# pages/page_email_verification.py

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

# --------------------------- Email Verification API Functions ---------------------------

EMAIL_VERIFICATION_URL = "https://api.attestr.com/api/v1/public/checkx/email"

def verify_email(email: str, auth_token: str) -> Dict[str, Any]:
    """
    Verifies the provided email using the Attestr Email Verification API.

    Args:
        email (str): The email address to verify.
        auth_token (str): Attestr Auth Token.

    Returns:
        Dict[str, Any]: API response data.
    """
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    payload = {
        "email": email
    }
    try:
        response = requests.post(EMAIL_VERIFICATION_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        log_info(f"Email Verification successful for Email: '{email}'")
        return data

    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error during Email verification for '{email}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error during Email verification for '{email}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error during Email verification for '{email}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception during Email verification for '{email}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for Email verification response of '{email}': {json_err}")
    except Exception as e:
        log_error(f"An unexpected error occurred during Email verification for '{email}': {e}")

    return {}

@st.cache_data
def cache_email_verification(email: str, auth_token: str) -> Dict[str, Any]:
    """
    Caches the Email verification response.

    Args:
        email (str): The email address to verify.
        auth_token (str): Attestr Auth Token.

    Returns:
        Dict[str, Any]: Cached API response data.
    """
    return verify_email(email, auth_token)

def process_email_verification(
    file: BytesIO,
    file_type: str,
    auth_token: str
) -> Optional[pd.DataFrame]:
    """
    Processes the Email verification by reading the uploaded file, verifying each email address,
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
            df = pd.read_csv(file)
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file)
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Define required columns
        required_columns = ['sno', 'email']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Initialize new columns for results
        result_columns = [
            "message", "disposable", "role",
            "tags", "deliverable", "risk"
        ]
        for col in result_columns:
            if col not in df.columns:
                df[col] = None

        # Iterate through each row and verify Email
        for idx, row in df.iterrows():
            sno = row['sno']
            email = row['email']

            log_info(f"Processing Sno {sno}: Email '{email}'")

            # Validate Email
            if pd.isna(email) or str(email).strip() == "":
                log_warning(f"Sno {sno}: Email is missing. Skipping verification.")
                df.at[idx, 'message'] = "Email is missing."
                df.at[idx, 'disposable'] = False
                df.at[idx, 'role'] = False
                df.at[idx, 'tags'] = []
                df.at[idx, 'deliverable'] = "UNKNOWN"
                df.at[idx, 'risk'] = "UNKNOWN"
                continue

            # Verify Email
            verification_result = cache_email_verification(email, auth_token)
            if verification_result:
                # Populate DataFrame based on response
                df.at[idx, 'message'] = verification_result.get('message', "")
                
                df.at[idx, 'disposable'] = verification_result.get('disposable', False)
                df.at[idx, 'role'] = verification_result.get('role', False)
                df.at[idx, 'tags'] = verification_result.get('tags', [])
                df.at[idx, 'deliverable'] = verification_result.get('deliverable', "UNKNOWN")
                df.at[idx, 'risk'] = verification_result.get('risk', "UNKNOWN")
                
            else:
                # In case of empty response
                df.at[idx, 'message'] = "No data returned from API."
                df.at[idx, 'disposable'] = False
                df.at[idx, 'role'] = False
                df.at[idx, 'tags'] = []
                df.at[idx, 'deliverable'] = "UNKNOWN"
                df.at[idx, 'risk'] = "UNKNOWN"

        log_info("Email Verification processing complete.")
        st.write("### Processed Data", df)

        return df

    except Exception as e:
        log_error(f"An error occurred while processing the Email Verification file: {e}")
        return None

def run():
    st.header("Email Verification")
    st.write("This section allows you to verify email details using the Attestr API.")
    st.write("""Group / role based email identification Mails sent to group and role based email addresses are associated with higher chances of being ignored, bounced by mail server or tagged as spam. Fine tune your email leads database by filtering such emails.
Disposable mailbox protection Disposable emails are one time temporary email address typically used by spammers and are self destructed after a certain time. Mails sent to disposed mailboxes are almost certainly bounced.
Delivery status projection Validate email deliverability upfront by classifying addresses into success, failure, avoid and unknown delivery status categories and reduce bounce rate up to 90 percent for targeted delivery.
Risk level assessment Sending emails to high risk email addresses affects your domain's reputation and may lead to being tagged as spam sender by leading mail servers. Access the risk level of recipient mailbox before sending.
Auto suggestion Never lose a lead due to spelling errors in email addresses. Our auto suggestion feature recommends closest valid potential match in case a typo is detected.""")
    st.write("Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/email-validation-api) for more details.")
    # Access API tokens from session state
    google_api_key = st.session_state.get("google_api_key", "")
    attestr_auth_token = st.session_state.get("attestr_auth_token", "")

    if not attestr_auth_token:
        st.warning("Please enter your Attestr Auth Token on the Home page to proceed.")
        return

    st.write("""
        Upload a CSV or XLSX file containing email details. The input file should have the following columns:
        - **sno**: Serial number (unique for each row)
        - **email**: Email address to verify
    """)

    uploaded_file = st.file_uploader(
        "Upload your Email Verification file (CSV or XLSX).",
        type=["csv", "xlsx"],
        key="email_verification"
    )

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1]
        if st.button("Run Email Verification", key="run_email_verification"):
            with st.spinner("Processing Email Verification..."):
                processed_df = process_email_verification(
                    file=uploaded_file,
                    file_type=file_type,
                    auth_token=attestr_auth_token
                )

            if processed_df is not None:
                st.success("Email Verification completed successfully.")
                # st.write("### Processed Data", processed_df)

                # Download Button
                csv = processed_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Processed Data as CSV",
                    data=csv,
                    file_name="email_verification_results.csv",
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