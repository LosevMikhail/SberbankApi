import requests
import xmltodict
from requests import PreparedRequest


class SberbankLoggerIn:
    """ This one obtains JSESSIONID cookie that is used as JWT that validates the user. """

    def __init__(self):
        self._headers = {  # defaults. taken from web-client
            'JSESSIONID': '0000Y2MHNrU4ETzpHUlE5bMbzKe:-1',
            "SWJSESSIONID": '96532f36c3b58ea5277da781831501cc'
        }

    def login(self, guid: str, pin: str):
        token = self._login(guid, pin)
        return self._post_csa_login(token)

    def _login(self, guid: str, pin: str):
        body = {
            "operation": "button.login",
            "password": pin,
            "version": "9.20",
            "appType": "android",
            "appVersion": "10.2.0",
            "osVersion": "28.0",
            "deviceName": "HUAWEI_ANE-LX1",
            "isLightScheme": False,
            "isSafe": "true",
            "mGUID": guid,
            "devID": "607d725604d1f032e50bb3c0622e791d3f400001",
            "mobileSdkData": "{\"TIMESTAMP\":\"2021-09-13T07:23:14Z\",\"HardwareID\":\"-1\",\"SIM_ID\":\"-1\",\"PhoneNumber\":\"-1\",\"GeoLocationInfo\":[{\"Timestamp\":\"0\",\"Status\":\"1\"}],\"DeviceModel\":\"ANE-LX1\",\"MultitaskingSupported\":true,\"DeviceName\":\"marky\",\"DeviceSystemName\":\"Android\",\"DeviceSystemVersion\":\"28\",\"Languages\":\"ru\",\"WiFiMacAddress\":\"02:00:00:00:00:00\",\"WiFiNetworksData\":{\"BBSID\":\"02:00:00:00:00:00\",\"SignalStrength\":\"-47\",\"Channel\":\"null\"},\"CellTowerId\":\"-1\",\"LocationAreaCode\":\"-1\",\"ScreenSize\":\"1080x2060\",\"RSA_ApplicationKey\":\"2C501591EA5BF79F1C0ABA8B628C2571\",\"MCC\":\"286\",\"MNC\":\"02\",\"OS_ID\":\"1f32651b72df5515\",\"SDK_VERSION\":\"3.10.0\",\"Compromised\":0,\"Emulator\":0}",
            "mobileSDKKAV": "{\"osVersion\":0,\"KavSdkId\":\"\",\"KavSdkVersion\":\"\",\"KavSdkVirusDBVersion\":\"SdkVirusDbInfo(year=0, month=0, day=0, hour=0, minute=0, second=0, knownThreatsCount=0, records=0, size=0)\",\"KavSdkVirusDBStatus\":\"\",\"KavSdkVirusDBStatusDate\":\"\",\"KavSdkRoot\":false,\"LowPasswordQuality\":false,\"NonMarketAppsAllowed\":false,\"UsbDebugOn\":false,\"ScanStatus\":\"NONE\"}"
        }
        resp = requests.post(url='https://online.sberbank.ru:4477/CSAMAPI/login.do', headers=self._headers, data=body)
        print(resp.text)
        resp_json = xmltodict.parse(resp.text)
        print(resp_json)
        token = resp_json['response']['loginData']['token']
        return token

    def _post_csa_login(self, token):
        url = 'https://node5.online.sberbank.ru:4477/mobile9/postCSALogin.do'
        body = {
            "token": token,
            "appName": "aaa",
            "appBuildOSType": "android",
            "appVersion": "10.2.0",
            "appBuildType": "RELEASE",
            "appFormat": "STANDALONE",
            "deviceName": "HUAWEI_ANE-LX1",
            "deviceType": "ANE-LX1",
            "deviceOSType": "android",
            "deviceOSVersion": "9"
        }
        resp = requests.post(url='https://online.sberbank.ru:4477/CSAMAPI/login.do', headers=self._headers, data=body)
        print(resp.text)
        jsessionid = resp.cookies['JSESSIONID']
        return jsessionid

    @staticmethod
    def _compose_params(params: {}):
        """ {'a': 'b', 'c':d} --> 'a=b&c=d' """
        a = PreparedRequest()  # just let the requests library do the shit
        dummy_url = 'http://a.a'
        a.prepare_url(url=dummy_url, params=params)
        return a.url[len(dummy_url) + 2:]
