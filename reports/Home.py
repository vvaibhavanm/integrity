# main.py
import streamlit as st
from PIL import Image
import os
import requests_cache
import requests
import logging
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

requests_cache.install_cache('api_cache', backend='sqlite', expire_after=86400*7)  # 1 day
logging.basicConfig(
    filename='app.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger()

if 'logger' not in st.session_state:
    st.session_state['logger']= logger

# Set initial page configuration with a default favicon
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

# Initialize session state variables
if 'google_api_key' not in st.session_state:
    st.session_state.google_api_key = ""
if 'attestr_auth_token' not in st.session_state:
    st.session_state.attestr_auth_token = ""

def main():
    st.header("Integrity Due-Diligence Co-Pilot")
    
    # Display favicon.png as an image
    favicon_path = os.path.join("assets", "favicon.png")
    if os.path.exists(favicon_path):
        image = Image.open(favicon_path)
        st.image(image, width=150)  # Adjust width as needed
    else:
        st.warning("favicon.png not found in assets folder.")
    
    st.write("""
            Welcome to the Integrity Due-Diligence Co-Pilot. Use the sidebar to select the task you want to perform.
            Upload the appropriate file (CSV or XLSX) for the selected task. The app will process the data, perform the verification or calculation, and provide the results for download.
    
            Follow file format instructions carefully.  
                """)
    
    st.markdown("---")  # Separator
    
    # Create two columns for API token inputs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Google API Configuration")
        google_api_key = st.text_input(
            "Enter your Google API Key", 
            type="password", 
            value=st.session_state.get("google_api_key", ""), 
            key="google_api_key_input"
        )
        if google_api_key:
            st.session_state.google_api_key = google_api_key
            st.success("Google API Key is set for the session.")
        else:
            st.warning("Google API Key is not set.")
    
    with col2:
        st.subheader("Attestr API Configuration")
        attestr_auth_token = st.text_input(
            "Enter your Attestr Auth Token", 
            type="password", 
            value=st.session_state.get("attestr_auth_token", ""), 
            key="attestr_auth_token_input"
        )
        if attestr_auth_token:
            st.session_state.attestr_auth_token = attestr_auth_token
            st.success("Attestr Auth Token is set for the session.")
        else:
            st.warning("Attestr Auth Token is not set.")
            
    with col3:
        st.subheader("Probe42 API Configuration")
        probe_api_key = st.text_input(
            "Enter your Probe42 Auth Token", 
            type="password", 
            value=st.session_state.get("probe_api_key", ""), 
            key="probe_api_key_input"
        )
        if probe_api_key:
            st.session_state.probe_api_key = probe_api_key
            st.success("Probe Auth Token is set for the session.")
        else:
            st.warning("Probe Auth Token is not set.")
    
    st.markdown("---")  # Separator
    
    st.write("""
        After setting up your API tokens, use the sidebar to navigate to the desired task.
    """)
    
    
    # mca_page = st.Page('reports/1_MCA Operations.py')
    # mca_page_probe = st.Page('reports/0_MCA Operations Probe42.py')
    # pan_page = st.Page('reports/2_PAN_Verification.py')
    # gst_page = st.Page('reports/3_GST_Verification.py')
    # vehicle_rc = st.Page('reports/4_Vehicle_RC_Check.py')
    # driving_license = st.Page('reports/5_Driving_License_Verification.py')
    # mobile_number = st.Page('reports/6_Mobile_Number_Verification.py')
    # email_id = st.Page('reports/7_Email_Verification.py')
    # bank_account = st.Page('reports/8_Bank_Verification.py')
    # epfo_uan = st.Page('reports/9_EPFO_UAN_Verification.py')
    # voter_id = st.Page('reports/10_Voter_ID_Verification.py')
    # company_itr = st.Page('reports/11_Company_ITR_Verification.py')
    # court_records = st.Page('reports/12_Court_Record_Check.py')
    # geocoding = st.Page('reports/13_Geocoding_Distance.py')
    # home = st.Page('🏠_Home.py')
    
    # pg = st.navigation(
    #     {
    #         "Homepage": [home],
    #         "Corporate":[mca_page, mca_page_probe, court_records, gst_page, company_itr],
    #         "Individual":[pan_page, driving_license, mobile_number, email_id, voter_id, vehicle_rc, bank_account, epfo_uan],
    #         "Miscellaneous":[geocoding],
    #     }
    # )
    # pg.run()

# Execute the page content
if True:
    with open('auth/config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)


    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

    if "authenticator" not in st.session_state:
        st.session_state["authenticator"] = authenticator
        
    try:
        # pass
        authenticator.login('main')
    except Exception as e:
        st.error(e)
     
    
    if 'authentication_status' not in st.session_state:
        st.session_state['authentication_status'] = True   
        st.success('Login Successful')
        print("auth succesful")
        main()
        
    if st.session_state['authentication_status']:
        main()
        
    elif st.session_state['authentication_status'] is False:
        st.error('Username/password is incorrect')
    elif st.session_state['authentication_status'] is None:
        st.warning('Please enter your username and password')



# No additional content here; content is managed by individual page scripts
