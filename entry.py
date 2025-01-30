import streamlit as st
import PIL
from PIL import Image
import os

favicon_path = os.path.join("assets", "favicon.png")
image = Image.open(favicon_path)
st.set_page_config(
        page_title="Integrity Due-Diligence Co-Pilot",
        layout="wide",
        page_icon=image
    )

mca_page = st.Page('reports/1__MCA Operations.py',icon='🔍')
mca_page_probe = st.Page('reports/0__MCA Operations Probe42.py',icon='🔍')
pan_page = st.Page('reports/2___PAN_Verification.py',icon='🆔')
gst_page = st.Page('reports/3__GST_Verification.py',icon='💼')
vehicle_rc = st.Page('reports/4__Vehicle_RC_Check.py',icon='🚙')
driving_license = st.Page('reports/5__Driving_License_Verification.py',icon='🚗')
mobile_number = st.Page('reports/6__Mobile_Number_Verification.py',icon='📱')
email_id = st.Page('reports/7__Email_Verification.py',icon='✉️')
bank_account = st.Page('reports/8__Bank_verification.py',icon='🏦')
epfo_uan = st.Page('reports/9__EPFO_UAN_verification.py',icon='🏢')
voter_id = st.Page('reports/10__Voter_ID_verification.py',icon='🗳️')
company_itr = st.Page('reports/11__Company_ITR_Verification.py',icon='📄')
court_records = st.Page('reports/12__Court_Record_Check.py',icon='⚖️')
geocoding = st.Page('reports/13__Geocoding_Distance.py',icon='📍')
home = st.Page('reports/Home.py',icon='🏠')
    
pg = st.navigation(
{
"Homepage": [home],
"Corporate":[mca_page, mca_page_probe, court_records, gst_page, company_itr],
"Individual":[pan_page, driving_license, mobile_number, email_id, voter_id, vehicle_rc, bank_account, epfo_uan],
"Miscellaneous":[geocoding],
}
)
pg.run()