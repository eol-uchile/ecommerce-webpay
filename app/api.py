import yaml
import json

from json.decoder import JSONDecodeError

from flask import Flask, request, jsonify, abort
from transbank.webpay.webpay_plus import WebpayPlus
from transbank.webpay.webpay_plus.transaction import Transaction

app = Flask(__name__)

with open('certs/config.yml') as file:
    config_file = yaml.load(file, Loader=yaml.FullLoader)

def configure_webpay():
  """
  Get the webpay client for the ENVIRONMENT
  """
  if config_file['ENVIRONMENT'] == 'PRODUCCION':
    WebpayPlus.configure_for_production(config_file['COMMERCE_CODE'], config_file['API_KEY'])
  elif config_file['ENVIRONMENT'] == 'INTEGRACION':
    WebpayPlus.configure_for_integration(config_file['COMMERCE_CODE'], config_file['API_KEY'])
  else:
    raise Exception("Invalid ENVIRONMENT type {}".format(config_file['ENVIRONMENT']))

  if config_file['API_SECRET'] == '':
    raise Exception('API_SECRET can\'t be empty')

@app.route('/process-webpay', methods=['POST'])
def process_payment():
  # Get POST data
  try:
    basket = json.loads(request.data)
  except JSONDecodeError as e:
    print(e)
    return abort(403)

  if 'api_secret' not in basket or config_file['API_SECRET'] != basket['api_secret']:
    return abort(403)

  # Initilialize webpay
  configure_webpay()

  result = Transaction.create(
          buy_order=basket['order_number'],
          session_id=basket['order_number'],
          amount=float(basket['total_incl_tax']),
          return_url=basket['notify_url'])

  return {"token": result.token, "url": result.url}

@app.route('/get-transaction', methods=['POST'])
def get_transaction_data():
  # Get POST data
  try:
    data = json.loads(request.data)
  except JSONDecodeError:
    return abort(403)

  if 'api_secret' not in data or config_file['API_SECRET'] != data['api_secret']:
    return abort(403)

  # Initilialize webpay
  configure_webpay()

  # ACK the transaction
  response = Transaction.commit(token=data['token'])

  return json.dumps(response.__dict__)

if __name__ == "__main__":
  if 'DEBUG' in config_file and config_file['DEBUG']:
    app.run(host='0.0.0.0', port=5000, debug=True)
  app.run(host='0.0.0.0', port=5000)
