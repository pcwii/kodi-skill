import requests


def kodi_request():
    #  "xbmc.addon.video"
    kodi_ip = "192.168.0.32"
    kodi_port = "8080"
    kodi_user = ""
    kodi_pass = ""
    kodi_path = "http://" + kodi_ip + ":" + kodi_port + "/jsonrpc"
    json_header = {'content-type': 'application/json'}
    json_response = ""
    kodi_payload = '{ "jsonrpc": "2.0", "method": "Addons.GetAddons","params":{"type": "kodi.addon.video"}, "id": "1"}}}'
    try:
        json_response = requests.post(kodi_path, data=kodi_payload, headers=json_header)  # start directly with json request
        print(json_response)
    except Exception as e:
        print(e)


kodi_request()