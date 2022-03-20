import json
from base64 import b64decode, b64encode
from datetime import datetime

import requests
import xmltodict
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from requests import PreparedRequest

from src.primitives import FiatOperation


class SberApi(object):
    """
        The class that sends money form card to card (c2c/p2p) and obtain card operation history.

        To obtain guid+pin pair for logging in, use Registration class.
    """
    def __init__(self):
        object.__init__(self)
        self._cookies = {}
        self._ufs_cookies = {}
        self._worflow_headers = {  # todo hardcode off
            'Accept-Charset': 'UTF-8',
            'RSA-Antifraud-Mobile-SDK-Data': '{"TIMESTAMP":"2021-09-22T20:34:28Z","DeviceModel":"Redmi Note 8T","DeviceName":"Redmi0Note08T","DeviceSystemName":"Android","DeviceSystemVersion":"29","Languages":"en_US","WiFiMacAddress":"a4:45:19:42:72:26","WiFiNetworksData":{"BSSID":"02:00:00:00:00:00","SignalStrength":"-45","Channel":"36"},"ScreenSize":"1080x2130","MCC":"250","MNC":"1","AppKey":"25112496-e869-4900-bd07-20cc887cb052","SDK_VERSION":"1.5.1.257","Compromised":0,"MultitaskingSupported":true,"AdvertiserId":"03aae2cc-3d95-41fc-b2fb-9bd172c0e3ec","OS_ID":"8735f6daf1c71e0c","Emulator":0,"GeoLocationInfo":[{"Longitude":"0","Latitude":"0","Altitude":"0","HorizontalAccuracy":"0","AltitudeAccuracy":"0","Heading":"0","Speed":"0","Status":"1","Timestamp":"0"}],"DeveloperTools":1,"GooglePlayProtect":-1,"HoursSinceZoomInstall":13249,"HoursSinceAnyDeskInstall":-1,"HoursSinceQSInstall":-1,"UnknownSources":-1,"AgentBrand":"Xiaomi","AgentBootTime":"2698415","TimeZone":"180","SupportedAPILevel":"29","OSCodeName":"Not Found","AgentAppInfo":"SberBank 12.6.0 arm64-v8a","ApprepInstalledApps":"438","OSFontsNumber":"257","OSFontsHash":1038989955,"ScreenColorDepth":"~320 dpi","TimeZoneDSTOffset":"0","SimCard":"1","AgentSignalStrengthCellular":"-1","AgentConnectionType":"WIFI","AgentSignalTypeCellular":"-1","LocalIPv4":"192.168.0.102","LocalIPv6":"fe80::5418:77ff:fea6:ad78","DnsIP":"192.168.0.1","ApplicationMD5":"7dfc767dd1c49320c287aced308afdfd","RdpConnection":"0","LocationHash":"97bcdaa3a20b2a811cb346012a3a0a900ee3a86392bb9cf76b5a7161361dc547"}',
            'mobileSDKKAV': '{"osVersion":0,"KavSdkId":"","KavSdkVersion":"","KavSdkVirusDBVersion":"","KavSdkVirusDBStatus":"","KavSdkVirusDBStatusDate":"","KavSdkRoot":false,"LowPasswordQuality":false,"NonMarketAppsAllowed":false,"UsbDebugOn":false,"ScanStatus":"NONE"}',
            'UCS_SESSION_ID': 'CZYgLHfLQAiEegBEkaPxXvNkwTLIFp2FFAek5BkM9fpHKqo-XkbGe4ho55CWcNB6',
            'User-Agent': 'Mobile Device',
            'Content-Type': 'application/json; charset=UTF-8',
            'Host': 'mobile-node5-new.online.sberbank.ru:8543',
        }

    @staticmethod
    def _compose_params(params: {}):
        """ {'a': 'b', 'c':d} --> 'a=b&c=d' """
        a = PreparedRequest()  # just let the requests library do the shit
        dummy_url = 'http://a.a'
        a.prepare_url(url=dummy_url, params=params)
        return a.url[len(dummy_url) + 2:]

    def login(self, guid: str, pin: str):
        assert 5 == len(pin) and pin.isdigit()
        response = self._login(guid=guid, pin=pin)
        resp_json = xmltodict.parse(response.text)
        token = resp_json['response']['loginData']['token']
        response = self._post_csa_login(token=token)
        self._cookies.update(response.cookies)

    def get_payments_list(self):
        response = self._get_payments_list()
        body_json = xmltodict.parse(response.text)
        operations_list = body_json['response']['operations']['operation']
        print(json.dumps(operations_list, ensure_ascii=False))
        matches = [op for op in operations_list if 'to' in op and 'operationAmount' in op]
        return [FiatOperation.create(op['to'], float(op['operationAmount']['amount'])) for op in matches]

    def send_money(self, product_id: str, card: str, amount: int, currency='RUB'):
        response = self._get_token_ufs()
        resp_json = xmltodict.parse(response.text)
        print(resp_json)
        token = resp_json['response']['token']
        print('got client session token', token)

        response = self._extend_permissions()

        response = self._create_session(token)
        resp_json = json.loads(response.text)
        print('create session', resp_json['success'])
        self._ufs_cookies.update(response.cookies)
        print(self._ufs_cookies)

        response = self._get_key()
        resp_json = json.loads(response.text)
        print('get key', resp_json['success'])
        rsa_pcks1_key = resp_json['body']['publicKey']  # base64 encoding of ASN.1 encoded RSA public key

        response = self._search_recipient(rsa_pcks1_key, '2202200218741195')
        print(response.text)
        resp_json = json.loads(response.text)
        print('search recipient', resp_json['success'])
        uuid = resp_json['body']['client']['uuid']

        response = self._workflow_start(uuid=uuid, product_id=product_id)
        print(response.text)
        resp_json = json.loads(response.text)
        print(resp_json['success'])
        print('workflow start', resp_json['success'])
        pid = resp_json['body']['pid']
        print(pid)

        response = self._workflow_next(pid=pid, amount=amount, card=product_id, message='hey', currency=currency)
        resp_json = json.loads(response.text)
        print('workflow next', resp_json['success'])

        response = self._workflow_summary(pid=pid)
        resp_json = json.loads(response.text)
        print('workflow summary', resp_json['success'])

        response = self._workflow_confirm(pid=pid)
        resp_json = json.loads(response.text)
        print('workflow confirm', resp_json['success'])

        response = self._workflow_onreturn(pid=pid)
        resp_json = json.loads(response.text)
        print('workflow return', resp_json['success'])

    def _get_token_ufs(self):
        headers = {
            'Accept-Charset': 'windows-1251',
            'Accept': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mobile Device',
            'Host': 'node5.online.sberbank.ru:4477',
        }

        data = {
            'systemName': 'ufs'
        }
        response = requests.post(
            'https://node5.online.sberbank.ru:4477/mobile9/private/unifiedClientSession/getToken.do', headers=headers,
            cookies=self._cookies, data=data)
        return response

    def _create_session(self, token):
        headers = {
            'Accept-Charset': 'UTF-8',
            'analyticsSessionId': '2021-09-22T23:47:50.971+03:00 9e6a1f3007be6035e40983f0620cad22eda70000',
            'User-Agent': 'Mobile Device',
            'Content-Type': 'application/json; charset=UTF-8',
            'Host': 'mobile-node5-new.online.sberbank.ru:8543',
        }

        data = {
            "token": token
        }
        data = json.dumps(data)
        print(data)

        response = requests.post('https://mobile-node5-new.online.sberbank.ru:8543/sm-uko/v2/session/create',
                                 headers=headers, data=data)

        return response

    def _extend_permissions(self):
        headers = {
            'User-Agent': 'Mobile Device',
            'Host': 'node5.online.sberbank.ru:4477',
        }

        response = requests.post('https://node5.online.sberbank.ru:4477/mobile9/private/extendedPermissions.do',
                                 headers=headers, cookies=self._cookies)
        return response

    def _get_key(self):
        headers = {
            'Accept-Charset': 'UTF-8',
            'mobileSDKKAV': '{"osVersion":0,"KavSdkId":"","KavSdkVersion":"","KavSdkVirusDBVersion":"","KavSdkVirusDBStatus":"","KavSdkVirusDBStatusDate":"","KavSdkRoot":false,"LowPasswordQuality":false,"NonMarketAppsAllowed":false,"UsbDebugOn":false,"ScanStatus":"NONE"}',
            'RSA-Antifraud-Mobile-SDK-Data': '{"TIMESTAMP":"2021-09-21T19:37:34Z","DeviceModel":"Redmi Note 8T","DeviceName":"Redmi0Note08T","DeviceSystemName":"Android","DeviceSystemVersion":"29","Languages":"en_US","WiFiMacAddress":"a4:45:19:42:72:26","WiFiNetworksData":{"BSSID":"02:00:00:00:00:00","SignalStrength":"-43","Channel":"36"},"ScreenSize":"1080x2130","MCC":"250","MNC":"1","AppKey":"25112496-e869-4900-bd07-20cc887cb052","SDK_VERSION":"1.5.1.257","Compromised":0,"MultitaskingSupported":true,"AdvertiserId":"03aae2cc-3d95-41fc-b2fb-9bd172c0e3ec","OS_ID":"8735f6daf1c71e0c","Emulator":0,"GeoLocationInfo":[{"Longitude":"0","Latitude":"0","Altitude":"0","HorizontalAccuracy":"0","AltitudeAccuracy":"0","Heading":"0","Speed":"0","Status":"1","Timestamp":"0"}],"DeveloperTools":1,"GooglePlayProtect":-1,"HoursSinceAnyDeskInstall":-1,"HoursSinceZoomInstall":13224,"HoursSinceQSInstall":-1,"UnknownSources":-1,"AgentBrand":"Xiaomi","AgentBootTime":"2608601","TimeZone":"180","SupportedAPILevel":"29","OSCodeName":"Not Found","AgentAppInfo":"\xD0\xA1\xD0\xB1\xD0\xB5\xD1\x80\xD0\x91\xD0\xB0\xD0\xBD\xD0\xBA 12.6.0 arm64-v8a","ApprepInstalledApps":"438","OSFontsNumber":"257","OSFontsHash":1038989955,"ScreenColorDepth":"~320 dpi","TimeZoneDSTOffset":"0","SimCard":"1","AgentSignalStrengthCellular":"-1","AgentConnectionType":"WIFI","AgentSignalTypeCellular":"-1","LocalIPv4":"192.168.0.102","LocalIPv6":"fe80::5418:77ff:fea6:ad78","DnsIP":"192.168.0.1","ApplicationMD5":"7dfc767dd1c49320c287aced308afdfd","RdpConnection":"0","LocationHash":"4f04894fb51f59de8d76cb643c3d1edd35b530cc714d6b2c5e281f4b95196281"}',
            'UCS_SESSION_ID': 'TRGNaZIkT9ipVQ7Di4EwFi89xwzG_1ztsukxNGxBB1rxS0FYU09i3tcbbWANNNTo',
            'User-Agent': 'Mobile Device',
            'Host': 'mobile-node5-new.online.sberbank.ru:8543',
            'If-Modified-Since': 'Sat, 18 Sep 2021 13:10:37 GMT',
        }
        response = requests.get('https://mobile-node5-new.online.sberbank.ru:8543/cltransfer/v1/publickey',
                                headers=headers, cookies=self._ufs_cookies)
        return response

    def _search_recipient(self, rsa_key, card: str):
        headers = {
            'Accept-Charset': 'UTF-8',
            'mobileSDKKAV': '{"osVersion":0,"KavSdkId":"","KavSdkVersion":"","KavSdkVirusDBVersion":"","KavSdkVirusDBStatus":"","KavSdkVirusDBStatusDate":"","KavSdkRoot":false,"LowPasswordQuality":false,"NonMarketAppsAllowed":false,"UsbDebugOn":false,"ScanStatus":"NONE"}',
            'RSA-Antifraud-Mobile-SDK-Data': '{"TIMESTAMP":"2021-09-22T20:34:28Z","DeviceModel":"Redmi Note 8T","DeviceName":"Redmi0Note08T","DeviceSystemName":"Android","DeviceSystemVersion":"29","Languages":"en_US","WiFiMacAddress":"a4:45:19:42:72:26","WiFiNetworksData":{"BSSID":"02:00:00:00:00:00","SignalStrength":"-45","Channel":"36"},"ScreenSize":"1080x2130","MCC":"250","MNC":"1","AppKey":"25112496-e869-4900-bd07-20cc887cb052","SDK_VERSION":"1.5.1.257","Compromised":0,"MultitaskingSupported":true,"AdvertiserId":"03aae2cc-3d95-41fc-b2fb-9bd172c0e3ec","OS_ID":"8735f6daf1c71e0c","Emulator":0,"GeoLocationInfo":[{"Longitude":"0","Latitude":"0","Altitude":"0","HorizontalAccuracy":"0","AltitudeAccuracy":"0","Heading":"0","Speed":"0","Status":"1","Timestamp":"0"}],"DeveloperTools":1,"GooglePlayProtect":-1,"HoursSinceZoomInstall":13249,"HoursSinceAnyDeskInstall":-1,"HoursSinceQSInstall":-1,"UnknownSources":-1,"AgentBrand":"Xiaomi","AgentBootTime":"2698415","TimeZone":"180","SupportedAPILevel":"29","OSCodeName":"Not Found","AgentAppInfo":"\xD0\xA1\xD0\xB1\xD0\xB5\xD1\x80\xD0\x91\xD0\xB0\xD0\xBD\xD0\xBA 12.6.0 arm64-v8a","ApprepInstalledApps":"438","OSFontsNumber":"257","OSFontsHash":1038989955,"ScreenColorDepth":"~320 dpi","TimeZoneDSTOffset":"0","SimCard":"1","AgentSignalStrengthCellular":"-1","AgentConnectionType":"WIFI","AgentSignalTypeCellular":"-1","LocalIPv4":"192.168.0.102","LocalIPv6":"fe80::5418:77ff:fea6:ad78","DnsIP":"192.168.0.1","ApplicationMD5":"7dfc767dd1c49320c287aced308afdfd","RdpConnection":"0","LocationHash":"97bcdaa3a20b2a811cb346012a3a0a900ee3a86392bb9cf76b5a7161361dc547"}',
            'UCS_SESSION_ID': 'CZYgLHfLQAiEegBEkaPxXvNkwTLIFp2FFAek5BkM9fpHKqo-XkbGe4ho55CWcNB6',
            'User-Agent': 'Mobile Device',
            'Content-Type': 'application/json; charset=UTF-8',
            'Host': 'mobile-node5-new.online.sberbank.ru:8543',
        }

        key = b64decode(rsa_key)
        public_key = RSA.importKey(key)
        cipher = PKCS1_v1_5.new(public_key)
        encoded_card = cipher.encrypt(card.encode('cp1251'))
        encoded_card = b64encode(encoded_card).decode('cp1251')
        data = {
            "number": encoded_card,
            "type": "CARD"
        }
        data = json.dumps(data)
        response = requests.post('https://mobile-node5-new.online.sberbank.ru:8543/cltransfer/v1/recipient/search',
                                 headers=headers, cookies=self._ufs_cookies, data=data)
        return response

    def _workflow_start(self, uuid, product_id):
        headers = {  # todo hardcode off
            'Accept-Charset': 'UTF-8',
            'RSA-Antifraud-Mobile-SDK-Data': '{"TIMESTAMP":"2021-09-22T20:34:28Z","DeviceModel":"Redmi Note 8T","DeviceName":"Redmi0Note08T","DeviceSystemName":"Android","DeviceSystemVersion":"29","Languages":"en_US","WiFiMacAddress":"a4:45:19:42:72:26","WiFiNetworksData":{"BSSID":"02:00:00:00:00:00","SignalStrength":"-45","Channel":"36"},"ScreenSize":"1080x2130","MCC":"250","MNC":"1","AppKey":"25112496-e869-4900-bd07-20cc887cb052","SDK_VERSION":"1.5.1.257","Compromised":0,"MultitaskingSupported":true,"AdvertiserId":"03aae2cc-3d95-41fc-b2fb-9bd172c0e3ec","OS_ID":"8735f6daf1c71e0c","Emulator":0,"GeoLocationInfo":[{"Longitude":"0","Latitude":"0","Altitude":"0","HorizontalAccuracy":"0","AltitudeAccuracy":"0","Heading":"0","Speed":"0","Status":"1","Timestamp":"0"}],"DeveloperTools":1,"GooglePlayProtect":-1,"HoursSinceZoomInstall":13249,"HoursSinceAnyDeskInstall":-1,"HoursSinceQSInstall":-1,"UnknownSources":-1,"AgentBrand":"Xiaomi","AgentBootTime":"2698415","TimeZone":"180","SupportedAPILevel":"29","OSCodeName":"Not Found","AgentAppInfo":"SberBank 12.6.0 arm64-v8a","ApprepInstalledApps":"438","OSFontsNumber":"257","OSFontsHash":1038989955,"ScreenColorDepth":"~320 dpi","TimeZoneDSTOffset":"0","SimCard":"1","AgentSignalStrengthCellular":"-1","AgentConnectionType":"WIFI","AgentSignalTypeCellular":"-1","LocalIPv4":"192.168.0.102","LocalIPv6":"fe80::5418:77ff:fea6:ad78","DnsIP":"192.168.0.1","ApplicationMD5":"7dfc767dd1c49320c287aced308afdfd","RdpConnection":"0","LocationHash":"97bcdaa3a20b2a811cb346012a3a0a900ee3a86392bb9cf76b5a7161361dc547"}',
            'mobileSDKKAV': '{"osVersion":0,"KavSdkId":"","KavSdkVersion":"","KavSdkVirusDBVersion":"","KavSdkVirusDBStatus":"","KavSdkVirusDBStatusDate":"","KavSdkRoot":false,"LowPasswordQuality":false,"NonMarketAppsAllowed":false,"UsbDebugOn":false,"ScanStatus":"NONE"}',
            'UCS_SESSION_ID': 'CZYgLHfLQAiEegBEkaPxXvNkwTLIFp2FFAek5BkM9fpHKqo-XkbGe4ho55CWcNB6',
            'User-Agent': 'Mobile Device',
            'Content-Type': 'application/json; charset=UTF-8',
            'Host': 'mobile-node5-new.online.sberbank.ru:8543',
        }
        params = {
            'cmd': 'START',
            'name': 'efsctMain_v3'
        }
        data = {
            'document': {
                'clientUuid': uuid,
                'paymentMeanId': product_id,
                'action': 'CREATE'
            }
        }
        data = json.dumps(data)

        response = requests.post('https://mobile-node5-new.online.sberbank.ru:8543/cltransfer/v1/workflow',
                                 headers=headers, params=params, cookies=self._ufs_cookies, data=data)
        return response

    def _workflow_next(self, pid, amount, card, message, currency):
        headers = {
            'Accept-Charset': 'UTF-8',
            'RSA-Antifraud-Mobile-SDK-Data': '{"TIMESTAMP":"2021-09-22T20:34:51Z","DeviceModel":"Redmi Note 8T","DeviceName":"Redmi0Note08T","DeviceSystemName":"Android","DeviceSystemVersion":"29","Languages":"en_US","WiFiMacAddress":"a4:45:19:42:72:26","WiFiNetworksData":{"BSSID":"02:00:00:00:00:00","SignalStrength":"-47","Channel":"36"},"ScreenSize":"1080x2130","MCC":"250","MNC":"1","AppKey":"25112496-e869-4900-bd07-20cc887cb052","SDK_VERSION":"1.5.1.257","Compromised":0,"MultitaskingSupported":true,"AdvertiserId":"03aae2cc-3d95-41fc-b2fb-9bd172c0e3ec","OS_ID":"8735f6daf1c71e0c","Emulator":0,"GeoLocationInfo":[{"Longitude":"0","Latitude":"0","Altitude":"0","HorizontalAccuracy":"0","AltitudeAccuracy":"0","Heading":"0","Speed":"0","Status":"1","Timestamp":"0"}],"DeveloperTools":1,"GooglePlayProtect":-1,"HoursSinceZoomInstall":13249,"HoursSinceAnyDeskInstall":-1,"HoursSinceQSInstall":-1,"UnknownSources":-1,"AgentBrand":"Xiaomi","AgentBootTime":"2698438","TimeZone":"180","SupportedAPILevel":"29","OSCodeName":"Not Found","AgentAppInfo":"SberBank 12.6.0 arm64-v8a","ApprepInstalledApps":"438","OSFontsNumber":"257","OSFontsHash":1038989955,"ScreenColorDepth":"~320 dpi","TimeZoneDSTOffset":"0","SimCard":"1","AgentSignalStrengthCellular":"-1","AgentConnectionType":"WIFI","AgentSignalTypeCellular":"-1","LocalIPv4":"192.168.0.102","LocalIPv6":"fe80::5418:77ff:fea6:ad78","DnsIP":"192.168.0.1","ApplicationMD5":"7dfc767dd1c49320c287aced308afdfd","RdpConnection":"0","LocationHash":"bd36dd980e07f9389baed0cb6ca54f02a0829033b9187fcdb6f69014b2130d9e"}',
            'mobileSDKKAV': '{"osVersion":0,"KavSdkId":"","KavSdkVersion":"","KavSdkVirusDBVersion":"","KavSdkVirusDBStatus":"","KavSdkVirusDBStatusDate":"","KavSdkRoot":false,"LowPasswordQuality":false,"NonMarketAppsAllowed":false,"UsbDebugOn":false,"ScanStatus":"NONE"}',
            'UCS_SESSION_ID': 'CZYgLHfLQAiEegBEkaPxXvNkwTLIFp2FFAek5BkM9fpHKqo-XkbGe4ho55CWcNB6',
            'User-Agent': 'Mobile Device',
            'Content-Type': 'application/json; charset=UTF-8',
            'Host': 'mobile-node5-new.online.sberbank.ru:8543',
        }

        params = {
            'cmd': 'EVENT',
            'pid': pid,
            'name': 'next'
        }
        data = {
            "fields": {
                "efsct:transfer:sum:currency": currency,
                "efsct:transfer:outcomeAccount": card,
                "efsct:transfer:message": message,
                "efsct:transfer:sum": str(amount)
            }
        }
        data = json.dumps(data)
        response = requests.post('https://mobile-node5-new.online.sberbank.ru:8543/cltransfer/v1/workflow',
                                 headers=headers, params=params, cookies=self._ufs_cookies, data=data)
        return response

    def _workflow_summary(self, pid):
        headers = {
            'Accept-Charset': 'UTF-8',
            'RSA-Antifraud-Mobile-SDK-Data': '{"TIMESTAMP":"2021-09-22T20:34:51Z","DeviceModel":"Redmi Note 8T","DeviceName":"Redmi0Note08T","DeviceSystemName":"Android","DeviceSystemVersion":"29","Languages":"en_US","WiFiMacAddress":"a4:45:19:42:72:26","WiFiNetworksData":{"BSSID":"02:00:00:00:00:00","SignalStrength":"-47","Channel":"36"},"ScreenSize":"1080x2130","MCC":"250","MNC":"1","AppKey":"25112496-e869-4900-bd07-20cc887cb052","SDK_VERSION":"1.5.1.257","Compromised":0,"MultitaskingSupported":true,"AdvertiserId":"03aae2cc-3d95-41fc-b2fb-9bd172c0e3ec","OS_ID":"8735f6daf1c71e0c","Emulator":0,"GeoLocationInfo":[{"Longitude":"0","Latitude":"0","Altitude":"0","HorizontalAccuracy":"0","AltitudeAccuracy":"0","Heading":"0","Speed":"0","Status":"1","Timestamp":"0"}],"DeveloperTools":1,"GooglePlayProtect":-1,"HoursSinceZoomInstall":13249,"HoursSinceAnyDeskInstall":-1,"HoursSinceQSInstall":-1,"UnknownSources":-1,"AgentBrand":"Xiaomi","AgentBootTime":"2698438","TimeZone":"180","SupportedAPILevel":"29","OSCodeName":"Not Found","AgentAppInfo":"SberBank 12.6.0 arm64-v8a","ApprepInstalledApps":"438","OSFontsNumber":"257","OSFontsHash":1038989955,"ScreenColorDepth":"~320 dpi","TimeZoneDSTOffset":"0","SimCard":"1","AgentSignalStrengthCellular":"-1","AgentConnectionType":"WIFI","AgentSignalTypeCellular":"-1","LocalIPv4":"192.168.0.102","LocalIPv6":"fe80::5418:77ff:fea6:ad78","DnsIP":"192.168.0.1","ApplicationMD5":"7dfc767dd1c49320c287aced308afdfd","RdpConnection":"0","LocationHash":"bd36dd980e07f9389baed0cb6ca54f02a0829033b9187fcdb6f69014b2130d9e"}',
            'mobileSDKKAV': '{"osVersion":0,"KavSdkId":"","KavSdkVersion":"","KavSdkVirusDBVersion":"","KavSdkVirusDBStatus":"","KavSdkVirusDBStatusDate":"","KavSdkRoot":false,"LowPasswordQuality":false,"NonMarketAppsAllowed":false,"UsbDebugOn":false,"ScanStatus":"NONE"}',
            'UCS_SESSION_ID': 'CZYgLHfLQAiEegBEkaPxXvNkwTLIFp2FFAek5BkM9fpHKqo-XkbGe4ho55CWcNB6',
            'User-Agent': 'Mobile Device',
            'Content-Type': 'application/json; charset=UTF-8',
            'Host': 'mobile-node5-new.online.sberbank.ru:8543',
        }
        params = {
            'cmd': 'EVENT',
            'pid': pid,
            'name': 'summaryNext'
        }
        data = json.dumps({})
        response = requests.post('https://mobile-node5-new.online.sberbank.ru:8543/cltransfer/v1/workflow',
                                 headers=headers, params=params, cookies=self._ufs_cookies, data=data)
        return response

    def _workflow_confirm(self, pid):
        headers = {
            'Accept-Charset': 'UTF-8',
            'RSA-Antifraud-Mobile-SDK-Data': '{"TIMESTAMP":"2021-09-22T20:34:51Z","DeviceModel":"Redmi Note 8T","DeviceName":"Redmi0Note08T","DeviceSystemName":"Android","DeviceSystemVersion":"29","Languages":"en_US","WiFiMacAddress":"a4:45:19:42:72:26","WiFiNetworksData":{"BSSID":"02:00:00:00:00:00","SignalStrength":"-47","Channel":"36"},"ScreenSize":"1080x2130","MCC":"250","MNC":"1","AppKey":"25112496-e869-4900-bd07-20cc887cb052","SDK_VERSION":"1.5.1.257","Compromised":0,"MultitaskingSupported":true,"AdvertiserId":"03aae2cc-3d95-41fc-b2fb-9bd172c0e3ec","OS_ID":"8735f6daf1c71e0c","Emulator":0,"GeoLocationInfo":[{"Longitude":"0","Latitude":"0","Altitude":"0","HorizontalAccuracy":"0","AltitudeAccuracy":"0","Heading":"0","Speed":"0","Status":"1","Timestamp":"0"}],"DeveloperTools":1,"GooglePlayProtect":-1,"HoursSinceZoomInstall":13249,"HoursSinceAnyDeskInstall":-1,"HoursSinceQSInstall":-1,"UnknownSources":-1,"AgentBrand":"Xiaomi","AgentBootTime":"2698438","TimeZone":"180","SupportedAPILevel":"29","OSCodeName":"Not Found","AgentAppInfo":"SberBank 12.6.0 arm64-v8a","ApprepInstalledApps":"438","OSFontsNumber":"257","OSFontsHash":1038989955,"ScreenColorDepth":"~320 dpi","TimeZoneDSTOffset":"0","SimCard":"1","AgentSignalStrengthCellular":"-1","AgentConnectionType":"WIFI","AgentSignalTypeCellular":"-1","LocalIPv4":"192.168.0.102","LocalIPv6":"fe80::5418:77ff:fea6:ad78","DnsIP":"192.168.0.1","ApplicationMD5":"7dfc767dd1c49320c287aced308afdfd","RdpConnection":"0","LocationHash":"bd36dd980e07f9389baed0cb6ca54f02a0829033b9187fcdb6f69014b2130d9e"}',
            'mobileSDKKAV': '{"osVersion":0,"KavSdkId":"","KavSdkVersion":"","KavSdkVirusDBVersion":"","KavSdkVirusDBStatus":"","KavSdkVirusDBStatusDate":"","KavSdkRoot":false,"LowPasswordQuality":false,"NonMarketAppsAllowed":false,"UsbDebugOn":false,"ScanStatus":"NONE"}',
            'UCS_SESSION_ID': 'CZYgLHfLQAiEegBEkaPxXvNkwTLIFp2FFAek5BkM9fpHKqo-XkbGe4ho55CWcNB6',
            'User-Agent': 'Mobile Device',
            'Content-Type': 'application/json; charset=UTF-8',
            'Host': 'mobile-node5-new.online.sberbank.ru:8543',
        }
        params = {
            'cmd': 'EVENT',
            'pid': pid,
            'name': 'on-enter'
        }
        data = json.dumps({})

        response = requests.post('https://mobile-node5-new.online.sberbank.ru:8543/bh-confirmation/v3/workflow2',
                                 headers=headers, params=params, cookies=self._ufs_cookies, data=data)
        return response

    def _workflow_onreturn(self, pid):
        headers = {
            'Accept-Charset': 'UTF-8',
            'RSA-Antifraud-Mobile-SDK-Data': '{"TIMESTAMP":"2021-09-22T20:34:51Z","DeviceModel":"Redmi Note 8T","DeviceName":"Redmi0Note08T","DeviceSystemName":"Android","DeviceSystemVersion":"29","Languages":"en_US","WiFiMacAddress":"a4:45:19:42:72:26","WiFiNetworksData":{"BSSID":"02:00:00:00:00:00","SignalStrength":"-47","Channel":"36"},"ScreenSize":"1080x2130","MCC":"250","MNC":"1","AppKey":"25112496-e869-4900-bd07-20cc887cb052","SDK_VERSION":"1.5.1.257","Compromised":0,"MultitaskingSupported":true,"AdvertiserId":"03aae2cc-3d95-41fc-b2fb-9bd172c0e3ec","OS_ID":"8735f6daf1c71e0c","Emulator":0,"GeoLocationInfo":[{"Longitude":"0","Latitude":"0","Altitude":"0","HorizontalAccuracy":"0","AltitudeAccuracy":"0","Heading":"0","Speed":"0","Status":"1","Timestamp":"0"}],"DeveloperTools":1,"GooglePlayProtect":-1,"HoursSinceZoomInstall":13249,"HoursSinceAnyDeskInstall":-1,"HoursSinceQSInstall":-1,"UnknownSources":-1,"AgentBrand":"Xiaomi","AgentBootTime":"2698438","TimeZone":"180","SupportedAPILevel":"29","OSCodeName":"Not Found","AgentAppInfo":"SberBank 12.6.0 arm64-v8a","ApprepInstalledApps":"438","OSFontsNumber":"257","OSFontsHash":1038989955,"ScreenColorDepth":"~320 dpi","TimeZoneDSTOffset":"0","SimCard":"1","AgentSignalStrengthCellular":"-1","AgentConnectionType":"WIFI","AgentSignalTypeCellular":"-1","LocalIPv4":"192.168.0.102","LocalIPv6":"fe80::5418:77ff:fea6:ad78","DnsIP":"192.168.0.1","ApplicationMD5":"7dfc767dd1c49320c287aced308afdfd","RdpConnection":"0","LocationHash":"bd36dd980e07f9389baed0cb6ca54f02a0829033b9187fcdb6f69014b2130d9e"}',
            'mobileSDKKAV': '{"osVersion":0,"KavSdkId":"","KavSdkVersion":"","KavSdkVirusDBVersion":"","KavSdkVirusDBStatus":"","KavSdkVirusDBStatusDate":"","KavSdkRoot":false,"LowPasswordQuality":false,"NonMarketAppsAllowed":false,"UsbDebugOn":false,"ScanStatus":"NONE"}',
            'UCS_SESSION_ID': 'CZYgLHfLQAiEegBEkaPxXvNkwTLIFp2FFAek5BkM9fpHKqo-XkbGe4ho55CWcNB6',
            'User-Agent': 'Mobile Device',
            'Content-Type': 'application/json; charset=UTF-8',
            'Host': 'mobile-node5-new.online.sberbank.ru:8543',
        }
        params = {
            'cmd': 'EVENT',
            'pid': pid,
            'name': 'on-return'
        }
        data = json.dumps({})
        response = requests.post('https://mobile-node5-new.online.sberbank.ru:8543/cltransfer/v1/workflow',
                                 headers=headers, params=params, cookies=self._ufs_cookies, data=data)
        return response
    # --------------------------------------------------------------------------

    def _get_payments_list(self, to_date=datetime.today(), days=1):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=windows-1251',
            'User-Agent': 'Mobile Device',
            'Host': 'node5.online.sberbank.ru:4477',
        }

        data = 'from=12.09.2020&to=12.09.2021&usedResource=card%3A618858146&paginationSize=150&paginationOffset=0&includeUfs=true'

        response = requests.post('https://node5.online.sberbank.ru:4477/mobile9/private/payments/list.do',
                                 headers=headers, cookies=self._cookies, data=self._compose_params(data))
        return response

    def _login(self, guid: str, pin: str):
        payload = {
            "operation": "button.login",
            "password": pin,
            "version": "9.20",
            "appType": "android",
            "appVersion": "12.6.0",
            "osVersion": "29.0",
            "deviceName": "Xiaomi_Redmi_Note_8T",
            "isLightScheme": False,
            "isSafe": "true",
            "mGUID": guid,
            "devID": "9e6a1f3007be6035e40983f0620cad22eda70000",
            "mobileSdkData": '{"TIMESTAMP":"2021-09-11T12:41:57Z","DeviceModel":"Redmi Note 8T","DeviceName":"Redmi0Note08T","DeviceSystemName":"Android","DeviceSystemVersion":"29","Languages":"en_US","WiFiMacAddress":"a4:45:19:42:72:26","WiFiNetworksData":{"BSSID":"02:00:00:00:00:00","SignalStrength":"-51","Channel":"3"},"ScreenSize":"1080x2130","MCC":"250","MNC":"1","AppKey":"25112496-e869-4900-bd07-20cc887cb052","SDK_VERSION":"1.5.1.257","Compromised":0,"MultitaskingSupported":true,"AdvertiserId":"03aae2cc-3d95-41fc-b2fb-9bd172c0e3ec","OS_ID":"8735f6daf1c71e0c","Emulator":0,"GeoLocationInfo":[{"Longitude":"0","Latitude":"0","Altitude":"0","HorizontalAccuracy":"0","AltitudeAccuracy":"0","Heading":"0","Speed":"0","Status":"1","Timestamp":"0"}],"DeveloperTools":1,"GooglePlayProtect":-1,"HoursSinceZoomInstall":12977,"HoursSinceQSInstall":-1,"HoursSinceAnyDeskInstall":-1,"UnknownSources":-1,"AgentBrand":"Xiaomi","AgentBootTime":"1719663","TimeZone":"180","SupportedAPILevel":"29","OSCodeName":"Not Found","AgentAppInfo":"СберБанк 12.6.0 arm64-v8a","ApprepInstalledApps":"438","OSFontsNumber":"257","OSFontsHash":1038989955,"ScreenColorDepth":"~320 dpi","TimeZoneDSTOffset":"0","SimCard":"1","AgentSignalStrengthCellular":"-1","AgentConnectionType":"WIFI","AgentSignalTypeCellular":"-1","LocalIPv4":"192.168.1.4","LocalIPv6":"fe80::5418:77ff:fea6:ad78","DnsIP":"192.168.1.1","ApplicationMD5":"7dfc767dd1c49320c287aced308afdfd","RdpConnection":"0","LocationHash":"c2f250a3f92e3be648f817fd934fe5c66e10ba6ae02258933c7c6d1fccdc7241"}',
            "mobileSDKKAV": '{"osVersion":0,"KavSdkId":"","KavSdkVersion":"","KavSdkVirusDBVersion":"","KavSdkVirusDBStatus":"","KavSdkVirusDBStatusDate":"","KavSdkRoot":false,"LowPasswordQuality":false,"NonMarketAppsAllowed":false,"UsbDebugOn":false,"ScanStatus":"NONE","bluetooth":"1","vibracall":"1","f1":"0","f2":"1","f3":"0","f4":"0","f5":"1","f6":"0","f7":"1","f8":"-1","f9":"-1","f10":"-1","build_display":"QKQ1.200114.002 test-keys","build_fingerprint":"xiaomi\/willow_eea\/willow:10\/QKQ1.200114.002\/V12.0.3.0.QCXEUXM:user\/release-keys","build_hardware":"qcom","build_host":"c4-miui-ota-bd29.bj","build_manufacturer":"Xiaomi","build_model":"Redmi Note 8T","build_product":"willow_eea","build_type":"user","build_user":"builder","build_getradioversion":"MPSS.AT.4.3.1-00270-NICOBAR_GEN_PACK-1.374795.2.380402.1","n_cells_wcdma":"-1","n_cells_gsm":"-1","n_cells_lte":"-1","n_contacts":"125","nfc_exists":"1","nfc_on":"1","emulator_files":"0","app_context":"0"}'
        }
        data = self._compose_params(params=payload)

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=windows-1251',
            'User-Agent': 'Mobile Device',
            'Accept-Encoding': 'gzip',
            'Content-Length': str(len(data)),
            'Host': 'online.sberbank.ru:4477',
            'Connection': 'Keep-Alive'
        }

        response = requests.post(url='https://online.sberbank.ru:4477/CSAMAPI/login.do', headers=headers, data=data)
        return response

    def _post_csa_login(self, token):
        body = {
            "token": token,
            "appName": "СберБанк",
            "appBuildOSType": "android",
            "appVersion": "12.6.0",
            "appBuildType": "RELEASE",
            "appFormat": "STANDALONE",
            "deviceName": "Xiaomi_Redmi_Note_8T",
            "deviceType": "Redmi Note 8T",
            "deviceOSType": "android",
            "deviceOSVersion": "10"
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=windows-1251',
            'User-Agent': 'Mobile Device',
            'Host': 'node5.online.sberbank.ru:4477',
        }
        data = self._compose_params(body)  # .encode(encoding='cp1251')
        url = 'https://node5.online.sberbank.ru:4477/mobile9/postCSALogin.do'
        resp = requests.post(url=url, headers=headers, data=data)
        return resp


if __name__ == '__main__':
    """ Kind of manual test """
    client = SberApi()
    client.login(guid='your guid', pin='your 5-digit pin code')

    #  check if it works
    # client.send_money(card='2202200218741195', product_id='card:618858146', amount=2, currency='RUB')

    #  check if it works
    operations = client.get_payments_list()
    for op in operations:
        if op is not None:
            print(op.get_person(), op.get_amount())
