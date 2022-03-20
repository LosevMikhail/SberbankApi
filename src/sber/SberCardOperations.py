from datetime import date, timedelta

from requests import PreparedRequest

from src.CookieAccumulator import CookieAccumulator
from src.banking.ICardOperations import ICardOperations as Interface
from src.primitives import FiatOperation, Person


class SberCardOperations(Interface):
    _cookie: str = None
    _url: str = 'https://node5.online.sberbank.ru/PhizIC/clientapi/private/payments/list.do'

    def __init__(self):
        Interface.__init__(self)
        self._connection = CookieAccumulator(cookies={
            '__zzat2': 'MDA0dBA=Fz2+aQ==',
            'sbrf.pers_notice': '1',
            'sa': 'SA1.9e402116-ad3e-4eb7-909f-b15c4518a055.1631047159',
            '_ga': 'GA1.2.1298225314.1631047160',
            '_gid': 'GA1.2.1536667078.1631047160',
            '_sas': 'SA1.9e402116-ad3e-4eb7-909f-b15c4518a055.1631047159.1631047160',
            '_gat_ua211694381': '1'
        })

    def login(self, login: str, password: str):
        """ ---------------- Step 0. Getting JSESSIONID ---------------- """
        url = 'https://online.sberbank.ru/CSAFront/index.do#/'
        headers = {
            'Host': 'online.sberbank.ru',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-site'
        }
        response = self._connection.get(url=url, headers=headers)
        print(self._connection.get_cookies())

        """ ---------------- Step 1. Logging in ---------------- """
        url = 'https://online.sberbank.ru/CSAFront/authMainJson.do'
        body = {
            'deviceprint': "version=1.7.3&pm_br=Firefox&pm_brmjv=91&iframed=0&intip=&pm_expt=&pm_fpacn=Mozilla&pm_fpan=Netscape&pm_fpasw=&pm_fpco=1&pm_fpjv=0&pm_fpln=lang=en-US|syslang=|userlang=&pm_fpol=true&pm_fposp=&pm_fpsaw=1848&pm_fpsbd=&pm_fpsc=24|1920|1080|1053&pm_fpsdx=&pm_fpsdy=&pm_fpslx=&pm_fpsly=&pm_fpspd=24&pm_fpsui=&pm_fpsw=&pm_fptz=3&pm_fpua=mozilla/5.0 (x11; ubuntu; linux x86_64; rv:91.0) gecko/20100101 firefox/91.0|5.0 (X11)|Linux x86_64&pm_fpup=&pm_inpt=&pm_os=Linux&adsblock=0=false|1=false|2=false|3=false|4=false&audio=baseLatency=0|outputLatency=0|sampleRate=44100|state=suspended|maxChannelCount=2|numberOfInputs=1|numberOfOutputs=1|channelCount=2|channelCountMode=max|channelInterpretation=speakers|fftSize=2048|frequencyBinCount=1024|minDecibels=-100|maxDecibels=-30|smoothingTimeConstant=0.8&pm_fpsfse=true&webgl=ver=webgl2|vendor=Intel Open Source Technology Center|render=Intel(R) HD Graphics",
            'jsEvents': "",
            'domElements': "",
            'operation': "button.begin",
            'login': login,
            'loginInputType': "BY_LOGIN",
            'pageInputType': "INDEX",
            'password': password,
            'storeLogin': "true"
        }
        data = self._compose_params(body)
        headers = {
            'Host': 'online.sberbank.ru',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Page-Id': '#/',
            'Content-Length': str(len(data)),
            'Origin': 'https://online.sberbank.ru',
            'Connection': 'keep-alive',
            'Referer': 'https://online.sberbank.ru/CSAFront/index.do',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        response = self._connection.post(url=url, headers=headers, data=data)
        body_json = response.json()
        print(body_json)
        print('step 1: ', self._connection.get_cookies())

        """ ---------------- Step 1.5. Getting JSESSIONID, DPJSESSIONID ---------------- """
        headers = {
            'Host': 'node5.online.sberbank.ru',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://online.sberbank.ru/',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-User': '?1'
        }
        url = body_json['redirect']
        for i in range(2):
            response = self._connection.get(url=url, headers=headers)
            print('step 1.5: ', self._connection.get_cookies())
            print(response.cookies.items())

        """ ---------------- Lotta shit ---------------- """
        jsessionid = self._connection.get_cookies()['JSESSIONID']
        self._connection.get(url=f'https://node5.online.sberbank.ru/PhizIC/updateAPI.do;jsessionid={jsessionid}',
                             headers=headers)
        self._connection.get(url='https://node5.online.sberbank.ru/PhizIC/private/environment.do',
                             headers=headers)
        self._connection.get(url='https://node5.online.sberbank.ru/PhizIC/login/self-registration.do',
                             headers=headers)
        self._connection.get(url='https://node5.online.sberbank.ru/PhizIC/login/checkOldPassword.do',
                             headers=headers)
        self._connection.get(url='https://node5.online.sberbank.ru/PhizIC/region.do',
                             headers=headers)
        self._connection.get(url='https://node5.online.sberbank.ru/PhizIC/private/redirect.do',
                             headers=headers)
        self._connection.get(url='https://node5.online.sberbank.ru/PhizIC/private/switchDesignTo.do?design=3',
                             headers=headers)

    @staticmethod
    def _compose_params(params: {}):
        """ {'a': 'b', 'c':d} --> 'a=b&c=d' """
        a = PreparedRequest()  # just let the requests library do the shit
        dummy_url = 'http://a.a'
        a.prepare_url(url=dummy_url, params=params)
        return a.url[len(dummy_url) + 2:]

    def _get_cookie(self):
        """ Cookie may not be hardcoded cuz it is sensitive """
        if self._cookie is None or self._cookie == '':
            with open('res/crypt/sber_cookie.txt', 'r') as fp:
                self._cookie = fp.read()
        return self._cookie

    @staticmethod
    def _create_payload_history(from_date: date, to_date: date, amount=100, offset=0):
        """ Creates a payload for the operation history request """
        return {
            'from': from_date.strftime('%d.%m.%Y'),
            'to': to_date.strftime('%d.%m.%Y'),
            'paginationSize': amount,
            'paginationOffset': offset,
            'includeUfs': 'true',
            'showExternal': 'true',
            'filterName': 'UFSClaims'
        }

    def _create_headers_history(self):
        """ Creates a header set for the operation history request """
        return {
            'Host': 'node5.online.sberbank.ru',
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'text/plain;charset=UTF-8',
            'Content-Length': '0',
            'Origin': 'https://web5.online.sberbank.ru',
            'Connection': 'keep-alive',
            'Referer': 'https://web5.online.sberbank.ru/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Cache-Control': 'max-age=0',
            # 'Cookie': self._get_cookie()
        }

    def _get_operations_json(self):
        today, yesterday = date.today(), date.today() - timedelta(days=10)
        payload = self._create_payload_history(from_date=yesterday, to_date=today)
        headers = self._create_headers_history()
        response = self._connection.post(url=self._url, params=payload, headers=headers)
        body_json = response.json()
        return body_json

    def get_operations(self, from_date=None, to_date=None, amount=100) -> [FiatOperation]:
        """ overrides the interface method """
        # print('step 3: ', self._connection.get_cookies())
        today, yesterday = date.today(), date.today() - timedelta(days=10)
        payload = self._create_payload_history(from_date=yesterday, to_date=today)
        headers = self._create_headers_history()
        response = self._connection.post(url=self._url, params=payload, headers=headers)
        body_json = response.json()

        operations_list = body_json['response']['operations']['operation']
        matches = [op for op in operations_list if 'to' in op and 'operationAmount' in op]
        return [FiatOperation(Person(op['to']), float(op['operationAmount']['amount'])) for op in matches]

    def send(self, card, amount, currency='RUB') -> None:
        # todo implement
        pass
