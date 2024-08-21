import requests
import json
import logging
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import time

# Disable warnings for unverified HTTPS requests
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Configure logging
logging.basicConfig(filename='script_log.txt', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to log request and response details
def log_request_response(response, request_name):
    logging.info(f"{request_name} Request URL: {response.request.url}")
    logging.debug(f"{request_name} Request Headers: {response.request.headers}")
    logging.debug(f"{request_name} Request Body: {response.request.body}")
    logging.info(f"{request_name} Response Status Code: {response.status_code}")
    logging.debug(f"{request_name} Response Headers: {response.headers}")
    logging.debug(f"{request_name} Response Text: {response.text}")

# Generate a unique _dc parameter value
def generate_dc_param():
    return str(int(time.time() * 1000))

# Function to poll the PDF generation status
def poll_for_status(session, polling_url, job_id, max_retries=5):
    retries = 0
    backoff_time = 5  # Initial backoff time in seconds

    while True:
        try:
            logging.info("Polling for PDF generation status...")
            response = session.get(polling_url, params={'idElaborazione': job_id, '_dc': generate_dc_param()}, headers=headers, verify=False)
            log_request_response(response, "Poll Status")

            if response.status_code == 200:
                data = response.json()
                des_avanzamento = data.get('data', {}).get('desAvanzamento', 'N/A')
                posizione = data.get('data', {}).get('posizione', 'N/A')
                massimo = data.get('data', {}).get('massimo', 'N/A')

                logging.info(f"Progress: {des_avanzamento}, Position: {posizione}/{massimo}")

                if 'completata' in des_avanzamento.lower() or data.get('data', {}).get('chiudiPopup') == 'T':
                    logging.info("PDF generation complete.")
                    break
                else:
                    logging.info("PDF generation in progress, retrying...")
                    time.sleep(5)  # Wait for 5 seconds before polling again
            else:
                logging.error(f"Failed to poll status with status code: {response.status_code}")
                break

        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error occurred: {e}")
            if retries < max_retries:
                retries += 1
                logging.info(f"Retrying in {backoff_time} seconds... (Attempt {retries}/{max_retries})")
                time.sleep(backoff_time)
                backoff_time *= 2  # Exponential backoff
            else:
                logging.error("Max retries reached. Aborting polling.")
                break

# Start a session
session = requests.Session()

# Define the login URL and credentials
login_url = f'https://pvc003.zucchettihc.it:4445/cba/gen/auth/login?_dc={generate_dc_param()}'
headers = {
    'Accept': '*/*',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Referer': 'https://pvc003.zucchettihc.it:4445/cba/login.html',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
}

login_data = {
    'username': 'VGVyYXBpYSBWZXJh',  # Base64 encoded username (Terapia Vera)
    'password': 'UkJvcnJvbWVhMjAyNA==',  # Base64 encoded password (RBorromea2024)
    'encrypt': 'F',
    'cdc': '',
    'code': '',
    'source': 'sipcar2',
    'oAuthType': '',
    'page': '1',
    'start': '0',
    'limit': '25'
}

# Perform login
logging.info("Attempting login...")
login_response = session.post(login_url, headers=headers, data=login_data, verify=False)

# Log login request and response
log_request_response(login_response, "Login")

if login_response.status_code == 200:
    logging.info("Login successful.")
    
    # Extract JWT token from the response body
    response_json = login_response.json()
    jwt_token = response_json['data'].get('token')
    
    if jwt_token:
        headers['CBA-JWT'] = f'Bearer {jwt_token}'
        logging.info("JWT token found in body and added to headers.")
    else:
        logging.error("JWT token not found in the response body.")
        exit()
else:
    logging.error(f"Login failed with status code: {login_response.status_code}")
    exit()

# Step 1: Reproduce the "newId" request to generate a new ID
new_id_url = f'https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/genCss/statoElab/newId?_dc={generate_dc_param()}'
logging.info(f"Requesting new idAvanzamentoElaborazione from {new_id_url}...")
new_id_response = session.get(new_id_url, headers=headers, verify=False)

# Log new ID request and response
log_request_response(new_id_response, "New ID")

if new_id_response.status_code == 200:
    new_id_json = new_id_response.json()
    id_avanzamento_elaborazione = new_id_json['data']
    logging.info(f"Obtained idAvanzamentoElaborazione: {id_avanzamento_elaborazione}")
else:
    logging.error(f"Failed to obtain idAvanzamentoElaborazione with status code: {new_id_response.status_code}")
    exit()

# Step 2: Reproduce the "new" request related to the operation
new_operation_url = f'https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/genCss/statoElab/new?_dc={generate_dc_param()}'
logging.info(f"Requesting new operation with URL {new_operation_url}...")
new_operation_response = session.get(new_operation_url, headers=headers, verify=False)

# Log new operation request and response
log_request_response(new_operation_response, "New Operation")

if new_operation_response.status_code == 200:
    new_operation_json = new_operation_response.json()
    logging.info(f"New operation initiated successfully with data: {new_operation_json['data']}")
else:
    logging.error(f"Failed to initiate new operation with status code: {new_operation_response.status_code}")
    exit()

# Step 3: Define the URL for the PDF request
url = f'https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/report/terapie?_dc={generate_dc_param()}'
logging.info(f"Sending request for Nucleo A report to {url}...")

# Request body for Nucleo A
data_nucleo_a = {
    'format': 'pdf',
    'ricoveri': '',
    'reparti': '13,27',  # Nucleo A
    'dataDal': '2024-08-01T00:00:00',
    'dataAl': '2024-08-31T23:59:00',
    'viaDiSomm': 'AS,CC,CO,CU,DE,DM,DT,ED,EU,EV,GE,ID,IM,IN,IZ,NA,ND,NN,OD,OF,ON,OR,OT,PA,RE,SC,SD,SG,SL,SP,TD,TP,UN,VG,AD,OS,IPD,PAT,SMI',
    'terapie': 'T',
    'terapieAB': 'T',
    'tipoTerapia': '',
    'tipoRagg': '3',
    'tipoOrd': '0',
    'idProfilo': '3',
    'mensile': 'T',
    'noteMensile': 'T',
    'reportDaEsportare': 'false',
    'idAvanzamentoElaborazione': id_avanzamento_elaborazione  # Use the dynamically obtained ID
}

# Step 4: Send request for Nucleo A and print the entire response
response_nucleo_a = session.post(url, headers=headers, data=data_nucleo_a, verify=False, timeout=300)

# Log Nucleo A request and response
log_request_response(response_nucleo_a, "Nucleo A")

if response_nucleo_a.status_code == 200:
    logging.info("Nucleo A report requested successfully.")
    # Polling for PDF generation status
    polling_url = f'https://pvc003.zucchettihc.it:4445/cba/css/cs/ws/genCss/statoElab/get'
    poll_for_status(session, polling_url, id_avanzamento_elaborazione)
else:
    logging.error(f"Failed to request Nucleo A report with status code: {response_nucleo_a.status_code}")
