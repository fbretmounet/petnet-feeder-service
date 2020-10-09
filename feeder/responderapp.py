#!/usr/bin/env python3

from hashlib import sha1
from uvicorn import Config, Server
from tortoise.contrib.starlette import register_tortoise
import json
import logging
import os
import responder
import sys

from models import Gateways
import config

description = "A PetNet Feeder V2 controller server"
contact = {
  "url": "https://github.com/tedder/petnet-feeder-service",
}
license = {
  "name": "MIT License",
  "url": "https://opensource.org/licenses/MIT",
}

# Create the RESPONDER app
# https://responder.kennethreitz.org/en/latest/quickstart.html
app = responder.API(
  title="PetNet Feeder Service",
  version="1.0",
  openapi="3.0.2",
  description=description,
  contact=contact,
  license=license,
)

register_tortoise(
  app, db_url=config.DB_DSN, modules={"models": ["models"]}, generate_schemas=True
)

# Application we will run as
APPLICATION_ID = "38973487e8241ea4483e88ef8ca7934c8663dc25"

mqtt_client = None

log = logging.getLogger('responderapp')

# Prevent uvicorn installing signal handlers that block ours
class SignalableServer(Server):
  def install_signal_handlers(self):
    pass

# Generate "hardware IDs" per device
def generateHid(uid):
  if uid == 'smartfeeder-795ae773737d-prod': # ted
    return 'e954822c15b4e7a0c23a92b73edc1280722c3b34'
  log.info(f"generating based on incoming uid: {uid}")
  return sha1(uid.encode('utf-8')).hexdigest()

def generateGatewayHid(uid):
  if uid == 'smartfeeder-795ae773737d': # ted
    return '6ec68eb4db216f61822a9aa4333d9824ae7d1abc'
  log.warning(f"seeing unknown feeder uid: {uid}")
  return sha1(uid.encode('utf-8')).hexdigest()


def toListing(objList):
  listSize = len(objList)
  return {
    'size' : listSize,
    'data' : objList,
    'page' : 0,
    'totalSize' : listSize,
    'totalPages' : 1,
  }

def jsonResponse(resp, obj):
  resp.content = json.dumps(obj)
  log.debug(f"response json: {resp.content}")
  resp.headers.update({'Content-Type' : 'application/json;charset=UTF-8'})


@app.route('/api/gateways')
async def list_gateways(req, resp):
  gateways = await Gateways.all()
  resp.media = {"gateways": [{gateway.hid: gateway.name} for gateway in gateways]}

@app.route('/api/{gateway_id}/button')
class ButtonResource:
  async def on_post(self, req, resp, *, gateway_id):
    global mqtt_client
    data = await req.media(format='json')
    enable = data['enable'] if 'enable' in data else True
    log.debug(f"got remote_button_enable request for {gateway_id} to value {enable}")
    await mqtt_client.send_cmd_button(gateway_id, enable=enable)
    resp.media = {'success': 'ok'}


@app.route('/api/{gateway_id}/reboot')
class RebootResource:
  async def on_post(self, req, resp, *, gateway_id):
    global mqtt_client
    log.debug(f"got reboot request for {gateway_id}")
    await mqtt_client.send_cmd_reboot(gateway_id)
    resp.media = {'success': 'ok'}

@app.route('/api/{gateway_id}/utc_offset')
class FeedResource:
  async def on_post(self, req, resp, *, gateway_id):
    global mqtt_client
    data = await req.media(format='json')
    portion = data['utc_offset'] if 'utc_offset' in data else -7
    log.debug(f"got utc_offset request for {gateway_id} for utc_offset {utc_offset}")
    await mqtt_client.send_cmd_utc_offset(gateway_id, utc_offset=utc_offset)
    resp.media = {'success': 'ok'}

@app.route('/api/{gateway_id}/feed')
class FeedResource:
  async def on_post(self, req, resp, *, gateway_id):
    global mqtt_client
    data = await req.media(format='json')
    portion = data['portion'] if 'portion' in data else 0.0625
    log.debug(f"got feed request for {gateway_id} of portion {portion}")
    await mqtt_client.send_cmd_feed(gateway_id, portion=portion)
    resp.media = {'success': 'ok'}


# if there's MQTT, it should come over this:
# https://social.microsoft.com/Forums/azure/en-US/ca68041a-d098-4d11-b108-fe3c76420281/using-mqtt-over-websockets-on-port-443?forum=azureiothub
@app.route('/$iothub/websocket', websocket=True)
async def welcome_websocket(ws):
  await ws.accept()
  log.info("in a websocket")
  await ws.close()


# Welcome :) using this as a catch-all for all the methods we haven't implemented.
# stolen from here: https://flask.palletsprojects.com/en/1.1.x/patterns/singlepageapplications/
@app.route('/api/?P<api_path>.*')
async def welcome(req, resp):
  jsonResponse(resp, {"default": f"🤖😻\n"})

@app.route('/', default=True)
async def welcome_html(req, resp):
  gateways = await Gateways.all()
  resp.html = app.template('welcome.html', gateways=[x.hid for x in gateways])

async def get_gateways(req, resp):
  gateways = await Gateways.all()
  gatewayObjects = [{
    "hid" : x.hid,
    "pri" : "arw:pgs:gwy:" + x.hid,
    "applicationHid" : APPLICATION_ID,
    "softwareName" : "SMART FEEDER",
    "softwareReleaseName" : "SMART FEEDER",
    "type" : "SMART FEEDER"
  } for x in gateways]
  jsonResponse(resp, toListing(gatewayObjects))

@app.route('/api/v1/kronos/gateways')
async def manage_gateways(req, resp):
  if not req.method == 'post':
    return await get_gateways(req, resp)
  #example of input data: {"name":"SF Gateway","uid":"smartfeeder-795ae773737d","osName":"FreeRTOS","type":"Local","softwareName":"SMART FEEDER","softwareVersion":"2.8.0","sdkVersion":"1.3.12"}
  payload = await req.media()
  log.info(f"gateways payload: {payload}")
  log.info(f"gateways headers: {req.headers}")

  # Ensure all gateways have a "uid"
  if 'uid' not in payload:
    log.warning("gateway didn't contain a UID, returning 400")
    resp.status_code = app.status_codes.HTTP_400
    return

  # Generate the gateway HID
  #log.info(f"generating based on incoming uid: {uid}")
  gatewayHid = generateGatewayHid(payload['uid'])

  # Check if we already have this gateway
  gateway, created = await Gateways.get_or_create(hid=gatewayHid)
  if not created:
    jsonResponse(resp, {
      "hid" : gateway.hid,
      #"links" : {},
      "message" : "gateway is already registered"
    })
    resp.set_cookie('JSESSIONID', value='pjbKBnNnas6qblrovritCihhHivY2WjFHc--S97u')
    return
  else:
    # Add to our gateways
    gateways[gatewayHid] = {}
    jsonResponse(resp, {
      "hid": gateway.hid,
      #"links": {},
      "message": "OK"
    })
    resp.set_cookie('JSESSIONID', value='pjbKBnNnas6qblrovritCihhHivY2WjFHc--S97u')
    return


# Fetch or create a device
# this is the one currently failing. possibly relevant:
# https://github.com/konexios/konexios-sdk-android/blob/master/sample/src/main/java/com/konexios/sample/device/DeviceAbstract.java
# https://github.com/konexios/moonstone-docs/blob/master/kronos/device-firmware-management.pdf
# 
# this is called "register" in the C code, so we can think of this call as "device registration"
# https://github.com/konexios/konexios-sdk-c/blob/master/src/arrow/api/device/device.c#L14
@app.route('/api/v1/kronos/devices')
async def manage_devices(req, resp):
  if not req.method == 'post':
    return await get_devices(req, resp)
  # Handle POST (create)
  device = await req.media()
  log.info(f"devices payload: {device}")
  log.info(f"devices headers: {req.headers}")

  # Ensure all devices have a "gatewayHid"
  if 'gatewayHid' not in device:
    log.warning("device didn't contain a gatewayHid, returning 400")
    resp.status_code = app.status_codes.HTTP_400
    return
  # Ensure all devices have a "uid"
  if 'uid' not in device:
    log.warning("device didn't contain a UID, returning 400")
    resp.status_code = app.status_codes.HTTP_400
    return

  # Ensure the gateway exists
  gateway = await Gateways.get(hid=device['gatewayHid'])
  if gateway is None:
    log.warning("device's gateway does not exist, returning 400")
    resp.status_code = app.status_codes.HTTP_400
    return

  # Generate the HID
  hid = generateHid(device['uid'])

  ret = {
    'hid': hid,
    'links' : {},
    'message' : 'device is already registered',
    # guessing at the following, they would be undocumented. hooray cargo culting!
    'pri' : 'arw:krn:dev:' + hid,
    #'deviceHid': hid,
    #'externalId': 'hello',
    #'enabled': True,
  }

  # returning "already registered" (above) always.
  jsonResponse(resp, ret)


async def get_devices(req, resp):
  # Handle GET (fetch)
  # Check if we want the devices of a specific gateway
  gatewayHid = req.params.get('gatewayHid')
  if gatewayHid:
    # Ensure the gateway exists
    gateway = await Gateways.get(hid=gatewayHid)
    if gateway is None:
      resp.status_code = app.status_codes.HTTP_400
      return
    jsonResponse(resp, toListing(list(gateway)))
    return
  else:
    # No specific gateway specified, return all devices for now
    gateways = await Gateways.all()
    jsonResponse(resp, toListing(gateways))
    return


# this response can (also) be seen here:
# https://github.com/konexios/konexios-sdk-c/blob/master/src/arrow/api/gateway/gateway.c#L30
@app.route('/api/v1/kronos/gateways/{gateway_id}/config')
async def gateway_config(req, resp, *, gateway_id):
  gateway = await Gateways.get(hid=gateway_id)
  log.info(f"Gateway {gateway.name} config headers: {req.headers}")
  jsonResponse(resp, {
    "cloudPlatform": "IotConnect",
    "key": {
      "apiKey": "efa2396b6f0bae3cc5fe5ef34829d60d91b96a625e55afabcea0e674f1a7ac43",
      "secretKey": "gEhFrm2hRvW2Km47lgt9xRBCtT9uH2Lx77WxYliNGJI="
    }
  })
  resp.set_cookie('JSESSIONID', value='pjbKBnNnas6qblrovritCihhHivY2WjFHc--S97u')


@app.route('/api/v1/kronos/gateways/{gateway_id}/checkin')
async def gateway_checkin(req, resp, *, gateway_id):
  log.info(f"gw config headers: {req.headers}")
  gateway, created = await Gateways.get_or_create(hid=gateway_id)
  log.info(f"Gateway {gateway.name} just checked in! Created={created}")
  jsonResponse(resp, {})
  resp.set_cookie('JSESSIONID', value='pjbKBnNnas6qblrovritCihhHivY2WjFHc--S97u')


@app.route('/api/v1/core/events/{gateway_id}/received')
async def events_received(req, resp, *, gateway_id):
  log.info(f"gw config headers: {req.headers}")
  gateway = await Gateways.get(hid=gateway_id)
  data = await req.content
  log.info(f"Gateway {gateway.name} requests: {data}")
  jsonResponse(resp, {})
  resp.set_cookie('JSESSIONID', value='pjbKBnNnas6qblrovritCihhHivY2WjFHc--S97u')


def create(loop, config, *, mqtt=None, debug=False):
  global mqtt_client
  mqtt_client = mqtt

  if debug:
    log_level = logging.DEBUG
  else:
    log_level = logging.INFO

  servers = []
  for listener in config['listeners']:
    webapp_config = Config(app=app.app, loop=loop, log_config=None, log_level=log_level, debug=debug, **config['listeners'][listener])
    server = SignalableServer(webapp_config)
    servers.append(server)
  return servers
