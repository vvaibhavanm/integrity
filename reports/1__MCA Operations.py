# pages/page_mca.py

import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
import os
from typing import Optional, Dict, Any

# Placeholder URLs - replace with actual API endpoints
MCA_COMPANY_MASTER_DATA_URL = "https://api.attestr.com/api/v2/public/corpx/business/master"
MCA_DIRECTOR_MASTER_DATA_URL_TEMPLATE = "https://api.attestr.com/api/v2/public/corpx/director/master"
MCA_DIRECTOR_SEARCH_URL_TEMPLATE = "https://api.attestr.com/api/v2/public/corpx/director/search"

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
    
# --------------------------- MCA Company Master Data API Functions ---------------------------

def initiate_mca_company_master_data(cin: str, auth_token: str, charges: bool = False, efilings: bool = False, live: bool = False, fetch_live_on_cache_miss: bool = False) -> Dict[str, Any]:
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    url = MCA_COMPANY_MASTER_DATA_URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    payload = {
        "reg": cin,
        "charges": charges,
        "efilings": efilings,
        "live": live,
        "fetchLiveOnCacheMiss": fetch_live_on_cache_miss
    }

    # st.write(f"Payload for CIN '{cin}': {payload}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        # st.write(f"Response for CIN '{cin}': {data}")
        log_info(f"MCA Company Master Data retrieval successful for CIN: '{cin}'")
        return data
    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error during MCA Company Master Data retrieval for CIN '{cin}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error during MCA Company Master Data retrieval for CIN '{cin}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error during MCA Company Master Data retrieval for CIN '{cin}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception during MCA Company Master Data retrieval for CIN '{cin}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for MCA Company Master Data response of CIN '{cin}': {json_err}")
    except Exception as e:
        log_error(f"Unexpected error during MCA Company Master Data retrieval for CIN '{cin}': {e}")

    return {}

@st.cache_data
def cache_mca_company_master_data(cin: str, auth_token: str, charges: bool, efilings: bool, live: bool, fetch_live_on_cache_miss: bool) -> Dict[str, Any]:
    return initiate_mca_company_master_data(cin, auth_token, charges, efilings, live, fetch_live_on_cache_miss)

def process_mca_company_master_data(file: BytesIO, file_type: str, auth_token: str, charges: bool, efilings: bool, live: bool, fetch_live_on_cache_miss: bool) -> Optional[pd.DataFrame]:
    try:
        if file_type == "csv":
            df = pd.read_csv(file, dtype={'regInput': 'str'})
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file, dtype={'regInput': 'str'})
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Validate required columns
        required_columns = ['sno', 'regInput']
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Define expected response keys
        expected_keys = [
            "valid", "cin", "llpin", "fllpin", "fcrn", "reg", "active", "businessName",
            "rocCode", "registrationNumber", "category", "subCategory", "class",
            "authorizedCapital", "paidCapital", "incorporatedDate", "registeredAddress",
            "email", "listed", "lastAGMDate", "lastBSDate", "active", "partners",
            "designatedPartners", "previousName", "obligation", "industryDivision",
            "industrySection", "incorporatedCountry", "shareCapital", "officeType",
            "companyType", "type", "status", "inc22AFiled", "soatDate",
            "regionalDirector", "region", "suspendedAtStockExchange", "insolvencyStatus",
            "subscribedCapital", "directorsAndSignatories", "charges", "efilings",
            "indexId", "updated", "message"
        ]

        # Initialize new columns if they don't exist
        for key in expected_keys:
            if key not in df.columns:
                df[key] = None
        expanded_rows=[]
        # Iterate through each row
        for idx, row in df.iterrows():
            sno = row['sno']
            cin = row['regInput']

            log_info(f"Processing Sno {sno}: CIN '{cin}'")

            if pd.isna(cin) or str(cin).strip() == "":
                log_warning(f"Sno {sno}: CIN is missing. Skipping verification.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "CIN is missing."
                continue

            # Verify MCA Company Master Data
            verification_result = cache_mca_company_master_data(cin, auth_token, charges, efilings, live, fetch_live_on_cache_miss)
            if verification_result:
                # Map response to expected keys
                mapped_data = map_response_to_df(verification_result, expected_keys)
                for key in expected_keys:
                    df.at[idx, key] = mapped_data.get(key, "")
                dns = verification_result.get('directorsAndSignatories', [])
                for subsno, dn in enumerate(dns, start=1):
                    expanded_row = {'sno':sno, 'regInput': cin,'subsno':subsno, **dn}
                    expanded_rows.append(expanded_row)

            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "No data returned from API."
        if expanded_rows:
            expanded_df = pd.DataFrame(expanded_rows)
        else:
            expanded_df = pd.DataFrame(columns=['sno', 'regInput', 'subsno'])

        log_info("MCA Company Master Data processing complete.")
        combined_df = pd.merge(df, expanded_df, on=['sno', 'regInput'], how='left')
        st.write("### Processed Data", combined_df)

        return combined_df

    except Exception as e:
        log_error(f"An error occurred while processing the MCA Company Master Data file: {e}")
        return None

# --------------------------- MCA Director Master Data DIN API Functions ---------------------------

def initiate_mca_director_master_data(din: str, auth_token: str, live: bool = False, fetch_live_on_cache_miss: bool = False, advanced: bool = False) -> Dict[str, Any]:
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    url = MCA_DIRECTOR_MASTER_DATA_URL_TEMPLATE.format(version="v2")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    payload = {
        "reg": din,
        "live": live,
        "fetchLiveOnCacheMiss": fetch_live_on_cache_miss,
        "advanced": advanced
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        log_info(f"MCA Director Master Data retrieval successful for DIN: '{din}'")
        return data
    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error during MCA Director Master Data retrieval for DIN '{din}': {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error during MCA Director Master Data retrieval for DIN '{din}': {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error during MCA Director Master Data retrieval for DIN '{din}': {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception during MCA Director Master Data retrieval for DIN '{din}': {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for MCA Director Master Data response of DIN '{din}': {json_err}")
    except Exception as e:
        log_error(f"Unexpected error during MCA Director Master Data retrieval for DIN '{din}': {e}")

    return {}

@st.cache_data
def cache_mca_director_master_data(din: str, auth_token: str, live: bool, fetch_live_on_cache_miss: bool, advanced: bool) -> Dict[str, Any]:
    return initiate_mca_director_master_data(din, auth_token, live, fetch_live_on_cache_miss, advanced)

def process_mca_director_master_data(file: BytesIO, file_type: str, auth_token: str, live: bool, fetch_live_on_cache_miss: bool, advanced: bool) -> Optional[pd.DataFrame]:
    try:
        if file_type == "csv":
            df = pd.read_csv(file, dtype={'reg': 'str'})
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file, dtype={'reg': 'str'})
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
            "valid", "din", "status", "firstName", "middleName", "lastName", "fullName",
            "dinAllocationDate", "disqualified", "disqualificationRemovalDate",
            "disqualificationSection", "disqualificationDate", "disqualificationReason",
            "dinSurrenderDate", "dinSurrenderDeactivationReason", "dir3KYCFiled",
            # "dir3KYCFiledFY", "associations",  "pastAssociations",
            "dir3KYCFiledFY", "associations", "signatoryAssociations", "pastAssociations",
            "indexId", "updated", "message"
        ]

        # Initialize new columns if they don't exist
        for key in expected_keys:
            if key not in df.columns:
                df[key] = None

        expanded_rows = []
        # Iterate through each row
        for idx, row in df.iterrows():
            sno = row['sno']
            din = row['reg']

            log_info(f"Processing Sno {sno}: DIN '{din}'")

            if pd.isna(din) or str(din).strip() == "":
                log_warning(f"Sno {sno}: DIN is missing. Skipping verification.")
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "DIN is missing."
                continue

            # Verify MCA Director Master Data
            verification_result = cache_mca_director_master_data(din, auth_token, live, fetch_live_on_cache_miss, advanced)
            if verification_result:
                # Map response to expected keys
                mapped_data = map_response_to_df(verification_result, expected_keys)
                for key in expected_keys:
                    df.at[idx, key] = mapped_data.get(key, "")
                
                # print("here1")
                oldassc = df.at[idx, 'associations']
                oldpastassc = df.at[idx, 'pastAssociations']
                newassc = [*oldassc, *oldpastassc]
                asscns = newassc
                df.at[idx, 'associations'] = newassc
                # print('old assc', oldassc )
                # print('past assc', oldpastassc)
                # print('new assc', asscns )
                for subsno, assc in enumerate(asscns, start=1):
                    expanded_row = {'sno': sno, 'din': din, 'subsno':subsno, **assc}
                    expanded_rows.append(expanded_row)

                # print("here2")
                

            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "No data returned from API."

        if expanded_rows:
            expanded_df = pd.DataFrame(expanded_rows)
        else:
            expanded_df = pd.DataFrame(columns=['sno', 'din', 'subsno'])
        log_info("MCA Director Master Data processing complete.")
        combined_df = pd.merge(df, expanded_df, on=['sno', 'din'], how='left')
        st.write("### Processed Data", combined_df)

        return combined_df

    except Exception as e:
        log_error(f"An error occurred while processing the MCA Director Master Data file: {e}")
        return None

# --------------------------- MCA Director Search API Functions ---------------------------

def initiate_mca_director_search(search_params: Dict[str, Any], auth_token: str) -> Dict[str, Any]:
    if not auth_token:
        log_error("Attestr Auth Token is missing.")
        return {}

    url = MCA_DIRECTOR_SEARCH_URL_TEMPLATE.format(version="v2")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {auth_token}"
    }

    try:
        response = requests.post(url, headers=headers, json=search_params, timeout=10)
        response.raise_for_status()
        data = response.json()
        log_info("MCA Director Search API call successful.")
        return data
    except requests.exceptions.HTTPError as http_err:
        log_error(f"HTTP error during MCA Director Search API call: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        log_error(f"Connection error during MCA Director Search API call: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        log_error(f"Timeout error during MCA Director Search API call: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        log_error(f"Request exception during MCA Director Search API call: {req_err}")
    except ValueError as json_err:
        log_error(f"JSON decoding failed for MCA Director Search API response: {json_err}")
    except Exception as e:
        log_error(f"Unexpected error during MCA Director Search API call: {e}")

    return {}

@st.cache_data
def cache_mca_director_search(search_params: Dict[str, Any], auth_token: str) -> Dict[str, Any]:
    return initiate_mca_director_search(search_params, auth_token)

def process_mca_director_search(file: BytesIO, file_type: str, auth_token: str, available: str) -> Optional[pd.DataFrame]:
    try:
        if file_type == "csv":
            df = pd.read_csv(file)
        elif file_type in ["xls", "xlsx"]:
            df = pd.read_excel(file)
        else:
            log_error("Unsupported file type. Please upload a CSV or XLSX file.")
            return None

        # Validate required columns based on search type
        required_columns = ['sno']
        if available == "fullName":
            required_columns.append('fullName')
            if 'fullName' not in df.columns:
                log_error("Uploaded file must contain the column 'fullName'.")
                st.error("Uploaded file must contain the column 'fullName'.")
                return None
            
        elif available == "pan":
            required_columns.append('pan')
            if 'pan' not in df.columns:
                log_error("Uploaded file must contain the column 'pan'.")
                st.error("Uploaded file must contain the column 'pan'.")
                return None
            
        else:
            log_error("Please select the column available in the file.")
            return None
        
        if not all(column in df.columns for column in required_columns):
            log_error(f"Uploaded file must contain the following columns: {', '.join(required_columns)}")
            return None

        log_info("File successfully uploaded and validated.")
        st.write("### Uploaded Data", df)

        # Define expected response keys
        expected_keys = [
            "firstName", "middleName", "lastName", "disqualified", "status",
            "dir3KYCFiled", "associations", "indexId", "fullName"
        ]

        # Initialize new columns if they don't exist
        for key in expected_keys:
            if key not in df.columns:
                df[key] = None

        # Iterate through each row
        expanded_rows=[]
        
        for idx, row in df.iterrows():
            sno = row['sno']
            
            if available == "fullName":
                full_name = row.get('fullName', "")
                log_info(f"Processing Sno {sno}: Full Name '{full_name}'")
                search_params = {}
                if pd.notna(full_name) and str(full_name).strip() != "":
                    search_params['fullName'] = {
                        "matchCriteria": "CONTAINS",
                        "matchValue": full_name,
                        "enableFuzzy": True
                    }
                else:
                    log_warning(f"Sno {sno}: Full Name is not provided. Skipping search.")
                    df.at[idx, 'valid'] = False
                    df.at[idx, 'message'] = "Full Name is not provided."
                    continue
                
            elif available == "pan":
                pan = row.get('pan', "")
                log_info(f"Processing Sno {sno}: PAN '{pan}'")
                search_params = {}
                if pd.notna(pan) and str(pan).strip() != "":
                    search_params['pan'] = pan
                else:
                    log_warning(f"Sno {sno}: PAN is not provided. Skipping search.")
                    df.at[idx, 'valid'] = False
                    df.at[idx, 'message'] = "PAN is not provided."
                    continue
            
            # Perform MCA Director Search
            verification_result = cache_mca_director_search(search_params, auth_token)
            if verification_result:
                if isinstance(verification_result, list) and len(verification_result) > 0:
                    # For simplicity, take the first match
                    mapped_data = verification_result[0]
                    for key in expected_keys:
                        df.at[idx, key] = mapped_data.get(key, "")
                    df.at[idx, 'valid'] = True
                    dns = df.at[idx,'associations']
                    for subsno, dn in enumerate(dns, start=1):
                        if available=="pan":
                            expanded_row = {'sno':sno, 'pan': row.get('pan', ""),'subsno':subsno, **dn}
                        else:
                            expanded_row = {'sno':sno, 'fullName': row.get('fullName', ""),'subsno':subsno, **dn}
                        expanded_rows.append(expanded_row)
                else:
                    df.at[idx, 'valid'] = False
                    df.at[idx, 'message'] = "No matching records found."
            else:
                # In case of empty response
                df.at[idx, 'valid'] = False
                df.at[idx, 'message'] = "No matching records found."
        if expanded_rows:
            expanded_df = pd.DataFrame(expanded_rows)
        else:
            if available=='pan':
                expanded_df = pd.DataFrame(columns=['sno', 'pan', 'subsno'])
            else:
                expanded_df = pd.DataFrame(columns=['sno', 'fullName', 'subsno'])


        log_info("MCA Director Search processing complete.")
        if available=='pan':
            combined_df = pd.merge(df, expanded_df, on=['sno', 'pan'], how='left')
            st.write("### Processed Data", combined_df)
            return combined_df
        else:
            combined_df = pd.merge(df, expanded_df, on=['sno', 'fullName'], how='left')
            st.write("### Processed Data", combined_df)
            return combined_df

    except Exception as e:
        log_error(f"An error occurred while processing the MCA Director Search file: {e}")
        return None

def run():
    st.header("MCA Operations")
    st.write("This section allows you to perform various MCA-related verifications and searches.")
    
    # Access API tokens from session state
    google_api_key = st.session_state.get("google_api_key", "")
    attestr_auth_token = st.session_state.get("attestr_auth_token", "")
    
    if not attestr_auth_token:
        st.warning("Please enter your Attestr Auth Token on the Home page to proceed.")
        return
    
    
    # Create tabs for different MCA functionalities
    tabs = st.tabs(["Company Master", "Director Master", "Director Search"])
    
    with tabs[0]:
        st.subheader("Company Master Data Verification")
        st.write("The Ministry of Corporate Affairs' (MCA) Registrar of Companies (ROC) office is responsible for overseeing company registration and administration. For a given CIN/LLPIN/FLLPIN/FCRN, this API retrieves the live company information, directors list, filing history, index of charges and other details as registered in the  MCA database.")
        st.write("Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/company-master-data-api) for more details.")
        st.write(""" 
            The input should have the columns 
            - **sno**, and 
            - **regInput** (case-sensitive),""") 
        st.write("""Where sno is serial number (unique for each row) and regInput corresponds to CIN/LLPIN/FLLPIN/FCRN.
                 """)
        uploaded_file = st.file_uploader("""Upload your Company Master Data file (CSV or XLSX).""", type=["csv", "xlsx"], key="mca_company")
        
        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1]
            # Additional options
            # charges = st.checkbox("Include Charges", value=False)
            # efilings = st.checkbox("Include e-Filings", value=False)
            # live = st.checkbox("Live Data", value=False)
            # fetch_live_on_cache_miss = st.checkbox("Fetch Live on Cache Miss", value=False)
            
            charges = False
            efilings = False
            live = False
            fetch_live_on_cache_miss = False
            
            if st.button("Run Company Master Data Verification", key="run_mca_company"):
                with st.spinner("Processing Company Master Data..."):
                    processed_df = process_mca_company_master_data(
                        file=uploaded_file,
                        file_type=file_type,
                        auth_token=attestr_auth_token,
                        charges=charges,
                        efilings=efilings,
                        live=live,
                        fetch_live_on_cache_miss=fetch_live_on_cache_miss
                    )
                
                if processed_df is not None:
                    st.success("Company Master Data Verification completed successfully.")
                    # st.write("### Processed Data", processed_df)
                    
                    # Download Button
                    csv = processed_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Processed Data as CSV",
                        data=csv,
                        file_name="company_master_data_results.csv",
                        mime='text/csv',
                    )
    
    with tabs[1]:
        st.subheader("Director Master Data Verification")
        st.write("The Ministry of Corporate Affairs' (MCA) Registrar of Companies (ROC) office is responsible for overseeing company registration and administration. For a given Director Identification Number (DIN), this API retrieves the live director information as registered in the  MCA database.")
        st.write("Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/director-master-data-api) for more details.")
        st.write(""" 
            The input should have the columns 
            - **sno**, and 
            - **reg** (case-sensitive)""") 
        st.write("""Where sno is serial number (unique for each row) and regInput corresponds to Director Identification Number (DIN).
                 """)
        uploaded_file = st.file_uploader("Upload your Director Master Data file (CSV or XLSX).", type=["csv", "xlsx"], key="mca_director")
        
        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1]
            # Additional options
            # live = st.checkbox("Live Data", value=False)
            # fetch_live_on_cache_miss = st.checkbox("Fetch Live on Cache Miss", value=False)
            # advanced = st.checkbox("Advanced Search", value=False)
            
            live = False
            fetch_live_on_cache_miss = False
            advanced = False

            if st.button("Run Director Master Data Verification", key="run_mca_director"):
                with st.spinner("Processing Director Master Data..."):
                    processed_df = process_mca_director_master_data(
                        file=uploaded_file,
                        file_type=file_type,
                        auth_token=attestr_auth_token,
                        live=live,
                        fetch_live_on_cache_miss=fetch_live_on_cache_miss,
                        advanced=advanced, 
                    )
                
                if processed_df is not None:
                    st.success("Director Master Data Verification completed successfully.")
                    # st.write("### Processed Data", processed_df)
                    
                    # Download Button
                    csv = processed_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Processed Data as CSV",
                        data=csv,
                        file_name="director_master_data_results.csv",
                        mime='text/csv',
                    )
    
    with tabs[2]:
        st.subheader("Director Search")
        st.write("The Ministry of Corporate Affairs' (MCA) Registrar of Companies (ROC) office is responsible for overseeing company registration and administration. For a given name/pan, this API retrieves the live director information as registered in the  MCA database.")
        st.write("Please refer to the [API documentation](https://docs.attestr.com/attestr-docs/director-search-api-name-to-din) for more details.")
        st.write(""" 
            The input should have the columns 
            - **sno**, and 
            - **fullName** (case-sensitive) or **pan**,""") 
        st.write("""Where sno is serial number (unique for each row) and fullName corresponds to director's full name, pan refers to Permanent Account Number (PAN). You can search with either one of name and pan, please specify using the button below.
        """)
        
        uploaded_file = st.file_uploader("Upload your Director Search file (CSV or XLSX).", type=["csv", "xlsx"], key="mca_search")
    
        available =  st.radio(
                "What column is available in the file?",
                ["pan", "fullName"],
                captions=[
                    "Permanent Account Number (PAN)",   
                    "Director's Full Name"
                ],
            )
        
        
        if uploaded_file:
            file_type = uploaded_file.name.split('.')[-1]
            if not available:
                log_error("Please select the column available in the file.")
                return
            # No additional options for search
            if st.button("Run Director Search", key="run_mca_search"):
                with st.spinner("Processing Director Search..."):
                    processed_df = process_mca_director_search(
                        file=uploaded_file,
                        file_type=file_type,
                        auth_token=attestr_auth_token,
                        available=available
                    )
                
                if processed_df is not None:
                    st.success("Director Search completed successfully.")
                    # st.write("### Processed Data", processed_df)
                    
                    # Download Button
                    csv = processed_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Processed Data as CSV",
                        data=csv,
                        file_name="director_search_results.csv",
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

