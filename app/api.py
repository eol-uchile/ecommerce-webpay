import yaml
import json
from flask import Flask, request, jsonify, abort
from suds.client import Client
from suds.transport.https import HttpTransport
from suds.wsse import Security, Timestamp
from wsse.suds import WssePlugin

app = Flask(__name__)

ENVIRONMNENT_URLS = {
    'INTEGRACION': 'https://webpay3gint.transbank.cl/WSWebpayTransaction/cxf/WSWebpayService?wsdl',
    'CERTIFICACION': 'https://webpay3gint.transbank.cl/WSWebpayTransaction/cxf/WSWebpayService?wsdl',
    'PRODUCCION': 'https://webpay3g.transbank.cl/WSWebpayTransaction/cxf/WSWebpayService?wsdl',
}

with open('certs/config.yml') as file:
    config_file = yaml.load(file, Loader=yaml.FullLoader)

def get_client():
  """
  Get the webpay client for the environment
  """
  transport = HttpTransport()
  wsse = Security()
  wsdl_url = ENVIRONMNENT_URLS[config_file['environment']]
  return Client(
      wsdl_url,
      transport=transport,
      wsse=wsse,
      plugins=[
          WssePlugin(
              keyfile=config_file['our_keyfile'],
              certfile=config_file['our_certificate'],
              their_certfile=config_file['their_certificate'],
          ),
      ],
  )

@app.route('/process-webpay', methods=['POST'])
def process_payment():

  # Get POST data
  basket = json.loads(request.data)
  if config_file['api_secret'] != basket['api_secret']:
    return abort(403)

  # Initilialize webpay
  client = get_client()
  client.options.cache.clear()
  init = client.factory.create('wsInitTransactionInput')

  init.wSTransactionType = client.factory.create('wsTransactionType').TR_NORMAL_WS
  init.commerceId = config_file['commerce_code']


  init.buyOrder = basket['order_number']
  init.sessionId = basket['order_number']
  init.returnURL = basket['notify_url']
  init.finalURL = basket['return_url']


  detail = client.factory.create('wsTransactionDetail')
  detail.amount = str(basket['total_incl_tax'])

  detail.commerceCode = config_file['commerce_code']
  detail.buyOrder = basket['order_number']

  init.transactionDetails.append(detail)
  init.wPMDetail = client.factory.create('wpmDetailInput')

  result = client.service.initTransaction(init)

  return {"token": result['token'], "url": result['url']}

@app.route('/get-transaction', methods=['POST'])
def get_transaction_data():
  # Get POST data
  data = json.loads(request.data)
  if config_file['api_secret'] != data['api_secret']:
    return abort(403)

  client = get_client()
  client.options.cache.clear()
  result = client.service.getTransactionResult(data['token'])
  client.service.acknowledgeTransaction(data['token'])

  detailOutput = result.detailOutput[0]

  return {
    "accountingDate": str(result.accountingDate),
    "buyOrder": str(result.buyOrder),
    #"cardDetail": result.cardDetail.cardNumber,
    "detailOutput": [{
      "sharesNumber": detailOutput.sharesNumber,
      "amount": detailOutput.amount,
      "commerceCode": detailOutput.commerceCode,
      "buyOrder": detailOutput.buyOrder,
      "authorizationCode": detailOutput.authorizationCode,
      "paymentTypeCode": detailOutput.paymentTypeCode,
      "responseCode": detailOutput.responseCode,
    }],
    "sessionId": result.sessionId,
    "transactionDate": str(result.transactionDate),
    "urlRedirection": result.urlRedirection,
    #"VCI": result.VCI,
  }

if __name__ == "__main__":
  if 'DEBUG' in config_file and config_file['DEBUG']:
    app.run(host='0.0.0.0', port=5000, debug=True)
  app.run(host='0.0.0.0', port=5000)
