import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
import os
import time
from typing import Optional, Dict, Any, Tuple

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

# --------------------------- Court Record Verification API Functions ---------------------------

COURT_RECORD_PERSON_SEARCH_URL_TEMPLATE = "https://api.attestr.com/api/v2/public/riskx/person/ecourt"
COURT_RECORD_BUSINESS_SEARCH_URL_TEMPLATE = "https://api.attestr.com/api/v2/public/riskx/business/ecourt"
COURT_RECORD_RESULT_QUERY_URL_TEMPLATE = "https://api.attestr.com/api/v2/public/async/{asyncId}"

def verify_court_record_search(
    search_type: str,
    tag: str,
    auth_token: str,
    name: Optional[str] = None,
    father_name: Optional[str] = None,
    birth_date: Optional[str] = None,
    address: Optional[str] = None,
    business_name: Optional[str] = None,
    reg_company_number: Optional[str] = None,
    mode: str = "Quick",
    webhook: bool = False,
    version: str = "v1"
) -> Dict[str, Any]:
    """
    Submits a court record search request.

    Args:
        search_type (str): 'person' or 'business'.
        tag (str): Unique reference ID for the request.
        auth_token (str): Attestr Auth Token.
        name (str, optional): Name of the person.
        father_name (str, optional): Father's name of the person.
        birth_date (str, optional): Birth date in DD-MM-YYYY format.
        address (str, optional): Complete address.
        business_name (str, optional): Name of the business.
        reg_company_number (str, optional): Registration number of the company.
        mode (str): Report mode ('Quick' or 'Extended').
        webhook (bool): Whether to trigger webhook after processing.
        version (str): API version.

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
        "tag": str(tag),
        "mode": mode,
        "webhook": webhook
    }

    if search_type == "person":
        if not all([name, father_name, birth_date, address]):
            log_error("Missing required parameters for person search.")
            return {}
        payload.update({
            "name": name,
            "fatherName": father_name,
            "birthDate": birth_date,
            "address": address
        })
        url = COURT_RECORD_PERSON_SEARCH_URL_TEMPLATE.format(version=version)
    elif search_type == "business":
        if not all([business_name, address]):
            log_error("Missing required parameters for business search.")
            return {}
        payload.update({
            "businessName": business_name,
            "address": address
        })
        if reg_company_number:
            payload["reg"] = reg_company_number
        url = COURT_RECORD_BUSINESS_SEARCH_URL_TEMPLATE.format(version=version)
    else:
        log_error("Invalid search type. Must be 'person' or 'business'.")
        return {}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        log_info(f"Court Record Search successful for tag: '{tag}'")
        return data
    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error during court record search for tag '{tag}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error during court record search for tag '{tag}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error during court record search for tag '{tag}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception during court record search for tag '{tag}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for court record search response for tag '{tag}': {json_err}")
    except Exception as e:
        log_error(f"Unexpected error during court record search for tag '{tag}': {e}")

    return {}

@st.cache_data
def cache_court_record_search(
    search_type: str,
    tag: str,
    auth_token: str,
    name: Optional[str],
    father_name: Optional[str],
    birth_date: Optional[str],
    address: Optional[str],
    business_name: Optional[str],
    reg_company_number: Optional[str],
    mode: str,
    webhook: bool,
    version: str = "v1"
) -> Dict[str, Any]:
    return verify_court_record_search(
        search_type,
        tag,
        auth_token,
        name,
        father_name,
        birth_date,
        address,
        business_name,
        reg_company_number,
        mode,
        webhook,
        version
    )

def get_court_record_result(async_id: str, auth_token: str, version: str = "v1") -> Dict[str, Any]:
    """
    Retrieves the result of a court record search request.

    Args:
        async_id (str): The asynchronous request ID.
        auth_token (str): Attestr Auth Token.
        version (str): API version.

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

    url = COURT_RECORD_RESULT_QUERY_URL_TEMPLATE.format(asyncId=async_id)

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        print(data)
        log_info(f"Retrieved court record result for async ID: '{async_id}'")
        return data
    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error during court record result retrieval for async ID '{async_id}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error during court record result retrieval for async ID '{async_id}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error during court record result retrieval for async ID '{async_id}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception during court record result retrieval for async ID '{async_id}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for court record result retrieval for async ID '{async_id}': {json_err}")
    except Exception as e:
        log_error(f"Unexpected error during court record result retrieval for async ID '{async_id}': {e}")

    return {}

def process_court_record_verification(
    file: BytesIO,
    file_type: str,
    auth_token: str,
    search_type: str,
    mode: str,
    webhook: bool,
    version: str = "v1"
) -> Optional[pd.DataFrame]:
    """
    Processes the court record verification by reading the uploaded file, submitting search requests,
    polling for results, and compiling them into a DataFrame.

    Args:
        file (BytesIO): Uploaded file.
        file_type (str): Type of the file ('csv' or 'xlsx').
        auth_token (str): Attestr Auth Token.
        search_type (str): 'person' or 'business'.
        mode (str): 'Quick' or 'Extended'.
        webhook (bool): Whether to trigger webhook after processing.
        version (str): API version.

    Returns:
        Optional[pd.DataFrame]: Processed DataFrame with results.
    """
    try:
        # Read the file
        if file_type == "csv":
            df = pd.read_csv(file, dtype=str)
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file, dtype=str)
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Define required columns based on search type
        if search_type == "person":
            required_columns = ['sno', 'tag', 'name', 'fatherName', 'birthDate', 'address']
        elif search_type == "business":
            required_columns = ['sno', 'tag', 'businessName', 'address']
        else:
            log_error("Invalid search type. Must be 'person' or 'business'.")
            return None

        # Validate required columns
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Initialize new columns for results
        result_columns = [
            "valid", "finalRiskSummary", "casesCount", "records",
            "finalRiskLevel", "asyncId", "number"
        ]
        for col in result_columns:
            if col not in df.columns:
                df[col] = None

        # Iterate through each row and submit search requests
        for idx, row in df.iterrows():
            sno = row['sno']
            tag = row['tag']

            log_info(f"Processing Sno {sno}: Tag '{tag}'")

            # Validate tag
            if pd.isna(tag) or str(tag).strip() == "":
                log_warning(f"Sno {sno}: Tag is missing. Skipping court record search.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'finalRiskSummary'] = ""
                df.at[idx, 'casesCount'] = 0
                df.at[idx, 'records'] = ""
                df.at[idx, 'finalRiskLevel'] = 0
                df.at[idx, 'asyncId'] = ""
                df.at[idx, 'number'] = "Tag is missing."
                continue

            # Prepare search parameters
            if search_type == "person":
                name = str(row.get('name', ''))
                father_name = str(row.get('fatherName', ''))
                birth_date = str(row.get('birthDate', ''))
                address = str(row.get('address', ''))
                business_name = None
                reg_company_number = None
            elif search_type == "business":
                name = None
                father_name = None
                birth_date = None
                address = str(row.get('address', ''))
                business_name = str(row.get('businessName', ''))
                reg_company_number = str(row.get('reg', ''))
            else:
                log_error("Invalid search type. Must be 'person' or 'business'.")
                return None

            # Submit search request
            search_response = cache_court_record_search(
                search_type=search_type,
                tag=tag,
                auth_token=auth_token,
                name=name,
                father_name=father_name,
                birth_date=birth_date,
                address=address,
                business_name=business_name,
                reg_company_number=reg_company_number,
                mode=mode,
                webhook=webhook,
                version=version
            )

            if not search_response:
                log_error(f"Sno {sno}: Court record search failed.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'finalRiskSummary'] = ""
                df.at[idx, 'casesCount'] = 0
                df.at[idx, 'records'] = ""
                df.at[idx, 'finalRiskLevel'] = 0
                df.at[idx, 'asyncId'] = ""
                df.at[idx, 'number'] = "Search request failed."
                continue

            items = search_response.get('items', [])
            if not items:
                log_error(f"Sno {sno}: No items found in court record search response.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'finalRiskSummary'] = ""
                df.at[idx, 'casesCount'] = 0
                df.at[idx, 'records'] = ""
                df.at[idx, 'finalRiskLevel'] = 0
                df.at[idx, 'asyncId'] = ""
                df.at[idx, 'number'] = "No items in response."
                continue

            async_id = items[0].get('_id', '')
            number = items[0].get('number', '')

            if not async_id:
                log_error(f"Sno {sno}: Missing async ID in response.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'finalRiskSummary'] = ""
                df.at[idx, 'casesCount'] = 0
                df.at[idx, 'records'] = ""
                df.at[idx, 'finalRiskLevel'] = 0
                df.at[idx, 'asyncId'] = ""
                df.at[idx, 'number'] = "Async ID missing."
                continue

            df.at[idx, 'asyncId'] = async_id
            df.at[idx, 'number'] = number
            print(async_id)
            # Polling for the result (with a maximum number of retries)
            max_retries = 15
            retry_interval = 15  # seconds
            for attempt in range(max_retries):
                log_info(f"Sno {sno}: Checking status (Attempt {attempt + 1}/{max_retries})")
                result_response = get_court_record_result(async_id, auth_token, version)
                status = result_response.get('status', '')
                if status == "COMPLETED":
                    output = result_response.get('output', {})
                    df.at[idx, 'valid'] = output.get('valid', False)
                    df.at[idx, 'finalRiskSummary'] = output.get('finalRiskSummary', '')
                    df.at[idx, 'casesCount'] = output.get('casesCount', 0)
                    df.at[idx, 'records'] = output.get('records', [])
                    df.at[idx, 'finalRiskLevel'] = output.get('finalRiskLevel', 0)
                    log_info(f"Sno {sno}: Court record search completed.")
                    break
                elif status == "ERRORED":
                    df.at[idx, 'valid'] = False
                    df.at[idx, 'finalRiskSummary'] = ""
                    df.at[idx, 'casesCount'] = 0
                    df.at[idx, 'records'] = ""
                    df.at[idx, 'finalRiskLevel'] = 0
                    error = result_response.get('error', {}).get('message', 'Unknown error.')
                    df.at[idx, 'number'] = f"Error: {error}"
                    log_error(f"Sno {sno}: Court record search errored with message: {error}")
                    break
                else:
                    st.write(f"Sno {sno}: Status '{status}'. Retrying in {retry_interval} seconds...")
                    time.sleep(retry_interval)  # Wait before next retry
            else:
                # Max retries reached
                log_warning(f"Sno {sno}: Court record search did not complete within expected time.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'finalRiskSummary'] = ""
                df.at[idx, 'casesCount'] = 0
                df.at[idx, 'records'] = ""
                df.at[idx, 'finalRiskLevel'] = 0
                df.at[idx, 'number'] = "Search did not complete in time."

        log_info("Court Record Verification processing complete.")
        st.write("### Processed Data", df)

        return df
    except Exception as e:
        log_error(f"An error occurred during Court Record Verification processing: {e}")
        return None

def run():
        st.header("Court Record Verification")
        st.write("""
            This section allows you to perform court record searches for individuals or businesses using the Attestr API.
            
            Search through digital court records published by Honorable Supreme court, High courts, session and magistrate courts, district civil courts and tribunals in India.
            **Features:**
            - **Person Search:** Verify court records based on personal details.
            - **Business Search:** Verify court records based on business details.
            
            Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/court-record-check-api) for more details.
        """)

        # Access API tokens from session state
        attestr_auth_token = st.session_state.get("attestr_auth_token", "")

        if not attestr_auth_token:
            st.warning("Please enter your Attestr Auth Token on the Home page to proceed.")
            return

        st.write("""
            **Select Search Type:**
        """)

        search_type = st.radio(
            "Choose the type of court record search:",
            options=["person", "business"],
            index=0
        )

        if search_type == "person":
            required_columns = ['sno', 'tag', 'name', 'fatherName', 'birthDate', 'address']
            st.write("""
                **Person Search Parameters:**
                - **sno**: Serial number (unique for each row)
                - **tag**: Unique reference ID for the request
                - **name**: Name of the person
                - **fatherName**: Father's name of the person
                - **birthDate**: Birth date in DD-MM-YYYY format
                - **address**: Complete address
            """)
        else:
            required_columns = ['sno', 'tag', 'businessName', 'address']
            st.write("""
                **Business Search Parameters:**
                - **sno**: Serial number (unique for each row)
                - **tag**: Unique reference ID for the request
                - **businessName**: Name of the business
                - **address**: Complete address
                - **reg**: Registration number of the company (optional)
            """)

        st.write("""
            **Additional Options:**
        """)

        mode = st.selectbox(
            "Select Report Mode:",
            options=["Quick", "Extended"],
            index=0,
            help="Choose 'Quick' for basic reports or 'Extended' for detailed reports."
        )

        # webhook = st.checkbox(
        #     "Enable Webhook Callback",
        #     value=False,
        #     help="Check this box to enable webhook callbacks after processing."
        # )
        
        webhook = False

        st.write("""
            **Upload File:**
        """)

        uploaded_file = st.file_uploader(
            "Upload your Court Record Verification file (CSV or XLSX).",
            type=["csv", "xlsx"],
            key="court_record_verification"
        )

        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1].lower()

            if st.button("Run Court Record Verification", key="run_court_record_verification"):
                with st.spinner("Processing Court Record Verification..."):
                    processed_df = process_court_record_verification(
                        file=uploaded_file,
                        file_type=file_type,
                        auth_token=attestr_auth_token,
                        search_type=search_type,
                        mode=mode,
                        webhook=webhook
                    )

                if processed_df is not None:
                    st.success("Court Record Verification completed successfully.")
                    # Uncomment the following line to display the processed DataFrame
                    # st.write("### Processed Data", processed_df)

                    # Download Button
                    csv = processed_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Processed Data as CSV",
                        data=csv,
                        file_name="court_record_verification_results.csv",
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