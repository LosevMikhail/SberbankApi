import requests
import xmltodict


class SberbankRegistration:
    """
        Performs the registration of a device with Sberbank client installed.
        The pair of (mGUID, pin) received simulates a device. It is reusable.
    """
    def __init__(self):
        self._url = 'https://online.sberbank.ru:4477/CSAMAPI/registerApp.do'
        self._headers = {  # defaults. taken from web-client
            'JSESSIONID': '0000Y2MHNrU4ETzpHUlE5bMbzKe:-1',
            "SWJSESSIONID": '96532f36c3b58ea5277da781831501cc'
        }

    """ Returns (m_guid, pin). They are going to be used for logging in """
    def register(self, login: str, pin: str):
        m_guid = self._register(login)
        sms_code = self._get_sms_code()
        a = self._confirm(m_guid, sms_code)
        print(a)
        a = self._create_pin(m_guid, pin)
        print(a)
        return m_guid, pin

    @staticmethod
    def _get_sms_code():
        return input('Enter the code: ')

    def _register(self, login: str):
        body = {
            "operation": "register",
            "login": login,
            "version": "9.20",
            "appType": "android",
            "appVersion": "10.2.0",
            "deviceName": "HUAWEI_ANE-LX1",
            "devID": "607d725604d1f032e50bb3c0622e791d3f400001",
            "devIDOld": "63c103d506178038cb0964403f372ae5af1e0001",
            "mobileSdkData": "{\"TIMESTAMP\":\"2021-09-13T07:23:14Z\",\"HardwareID\":\"-1\",\"SIM_ID\":\"-1\",\"PhoneNumber\":\"-1\",\"GeoLocationInfo\":[{\"Timestamp\":\"0\",\"Status\":\"1\"}],\"DeviceModel\":\"ANE-LX1\",\"MultitaskingSupported\":true,\"DeviceName\":\"marky\",\"DeviceSystemName\":\"Android\",\"DeviceSystemVersion\":\"28\",\"Languages\":\"ru\",\"WiFiMacAddress\":\"02:00:00:00:00:00\",\"WiFiNetworksData\":{\"BBSID\":\"02:00:00:00:00:00\",\"SignalStrength\":\"-47\",\"Channel\":\"null\"},\"CellTowerId\":\"-1\",\"LocationAreaCode\":\"-1\",\"ScreenSize\":\"1080x2060\",\"RSA_ApplicationKey\":\"2C501591EA5BF79F1C0ABA8B628C2571\",\"MCC\":\"286\",\"MNC\":\"02\",\"OS_ID\":\"1f32651b72df5515\",\"SDK_VERSION\":\"3.10.0\",\"Compromised\":0,\"Emulator\":0}",
            "mobileSDKKAV": "{\"osVersion\":0,\"KavSdkId\":\"\",\"KavSdkVersion\":\"\",\"KavSdkVirusDBVersion\":\"SdkVirusDbInfo(year=0, month=0, day=0, hour=0, minute=0, second=0, knownThreatsCount=0, records=0, size=0)\",\"KavSdkVirusDBStatus\":\"\",\"KavSdkVirusDBStatusDate\":\"\",\"KavSdkRoot\":false,\"LowPasswordQuality\":false,\"NonMarketAppsAllowed\":false,\"UsbDebugOn\":false,\"ScanStatus\":\"NONE\"}"
        }
        resp = requests.post(url=self._url, headers=self._headers, data=body)
        resp_json = xmltodict.parse(resp.text)
        m_guid = resp_json['response']['confirmRegistrationStage']['mGUID']
        return m_guid

    def _confirm(self, m_guid, sms_code):
        body = {
            "operation": "confirm",
            "mGUID": m_guid,
            "smsPassword": sms_code,
            "version": "9.20",
            "appType": "android",
            "mobileSdkData": "{\"TIMESTAMP\":\"2019-09-13T07:23:14Z\",\"HardwareID\":\"-1\",\"SIM_ID\":\"-1\",\"PhoneNumber\":\"-1\",\"GeoLocationInfo\":[{\"Timestamp\":\"0\",\"Status\":\"1\"}],\"DeviceModel\":\"ANE-LX1\",\"MultitaskingSupported\":true,\"DeviceName\":\"marky\",\"DeviceSystemName\":\"Android\",\"DeviceSystemVersion\":\"28\",\"Languages\":\"ru\",\"WiFiMacAddress\":\"02:00:00:00:00:00\",\"WiFiNetworksData\":{\"BBSID\":\"02:00:00:00:00:00\",\"SignalStrength\":\"-47\",\"Channel\":\"null\"},\"CellTowerId\":\"-1\",\"LocationAreaCode\":\"-1\",\"ScreenSize\":\"1080x2060\",\"RSA_ApplicationKey\":\"2C501591EA5BF79F1C0ABA8B628C2571\",\"MCC\":\"286\",\"MNC\":\"02\",\"OS_ID\":\"1f32651b72df5515\",\"SDK_VERSION\":\"3.10.0\",\"Compromised\":0,\"Emulator\":0}",
            "mobileSDKKAV": "{\"osVersion\":0,\"KavSdkId\":\"\",\"KavSdkVersion\":\"\",\"KavSdkVirusDBVersion\":\"SdkVirusDbInfo(year=0, month=0, day=0, hour=0, minute=0, second=0, knownThreatsCount=0, records=0, size=0)\",\"KavSdkVirusDBStatus\":\"\",\"KavSdkVirusDBStatusDate\":\"\",\"KavSdkRoot\":false,\"LowPasswordQuality\":false,\"NonMarketAppsAllowed\":false,\"UsbDebugOn\":false,\"ScanStatus\":\"NONE\"}",
            "confirmData": sms_code,
            "confirmOperation": "confirmSMS"
        }
        return requests.post(url=self._url, headers=self._headers, data=body).text

    def _create_pin(self, m_guid, pin):
        body = {
            "operation": "createPIN",
            "mGUID": m_guid,
            "password": pin,
            "version": "9.20",
            "appType": "android",
            "appVersion": "10.2.0",
            "deviceName": "HUAWEI_ANE-LX1",
            "devID": "607d725604d1f032e50bb3c0622e791d3f400001",
            "devIDOld": "63c103d506178038cb0964403f372ae5af1e0001",
            "mobileSdkData": "{\"TIMESTAMP\":\"2019-09-13T07:23:14Z\",\"HardwareID\":\"-1\",\"SIM_ID\":\"-1\",\"PhoneNumber\":\"-1\",\"GeoLocationInfo\":[{\"Timestamp\":\"0\",\"Status\":\"1\"}],\"DeviceModel\":\"ANE-LX1\",\"MultitaskingSupported\":true,\"DeviceName\":\"marky\",\"DeviceSystemName\":\"Android\",\"DeviceSystemVersion\":\"28\",\"Languages\":\"ru\",\"WiFiMacAddress\":\"02:00:00:00:00:00\",\"WiFiNetworksData\":{\"BBSID\":\"02:00:00:00:00:00\",\"SignalStrength\":\"-47\",\"Channel\":\"null\"},\"CellTowerId\":\"-1\",\"LocationAreaCode\":\"-1\",\"ScreenSize\":\"1080x2060\",\"RSA_ApplicationKey\":\"2C501591EA5BF79F1C0ABA8B628C2571\",\"MCC\":\"286\",\"MNC\":\"02\",\"OS_ID\":\"1f32651b72df5515\",\"SDK_VERSION\":\"3.10.0\",\"Compromised\":0,\"Emulator\":0}",
            "mobileSDKKAV": "{\"osVersion\":0,\"KavSdkId\":\"\",\"KavSdkVersion\":\"\",\"KavSdkVirusDBVersion\":\"SdkVirusDbInfo(year=0, month=0, day=0, hour=0, minute=0, second=0, knownThreatsCount=0, records=0, size=0)\",\"KavSdkVirusDBStatus\":\"\",\"KavSdkVirusDBStatusDate\":\"\",\"KavSdkRoot\":false,\"LowPasswordQuality\":false,\"NonMarketAppsAllowed\":false,\"UsbDebugOn\":false,\"ScanStatus\":\"NONE\"}"
        }
        return requests.post(url=self._url, headers=self._headers, data=body).text
