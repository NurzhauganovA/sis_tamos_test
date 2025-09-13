import requests
import base64
import logging
from django.conf import settings
from urllib.parse import urlencode
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AituPassportService:
    def __init__(self):
        self.config = settings.AITU_PASSPORT_SETTINGS
        self.base_url = self.config['TEST_BASE_URL'] if self.config['USE_TEST'] else self.config['PROD_BASE_URL']
        self.client_id = self.config['CLIENT_ID']
        self.client_secret = self.config['CLIENT_SECRET']
        self.redirect_uri = self.config['REDIRECT_URI']

    def _get_headers(self, access_token: Optional[str] = None) -> Dict[str, str]:
        """Получить заголовки для запросов"""
        headers = {
            'Content-Type': 'application/json',
        }
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'
        return headers

    def upload_pdf_for_signing(self, pdf_file, filename: str, link: Optional[str] = None) -> Optional[str]:
        """
        Загрузить PDF файл для подписания
        Возвращает signable_id при успехе
        """
        try:
            # Читаем файл и конвертируем в base64
            pdf_file.seek(0)
            pdf_content = pdf_file.read()
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            # Подготавливаем данные для запроса
            data = {
                'bytes': pdf_base64,
                'name': filename,
            }

            if link:
                data['link'] = link

            url = f"{self.base_url}/api/v2/oauth/signable/pdf"

            # Делаем запрос с базовой авторизацией
            auth = (self.client_id, self.client_secret)
            response = requests.post(
                url,
                json=data,
                auth=auth,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('signableId')
            else:
                logger.error(f"Ошибка загрузки PDF: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Исключение при загрузке PDF: {str(e)}")
            return None

    def generate_auth_url(self, signable_ids: list, user_phone: Optional[str] = None) -> str:
        """
        Генерация URL для авторизации и подписания
        """
        try:
            # Формируем scope для подписания
            scope_value = f"sign.{','.join(signable_ids)}"

            params = {
                'response_type': 'code',
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'scope': scope_value,
                'state': 'tamos_aitu_passport_string',
            }

            # Если номер телефона верифицируется партнером, добавляем otp_confirmation
            if user_phone:
                otp_confirmation = self.get_otp_confirmation(user_phone)
                if otp_confirmation:
                    params['otp_confirmation'] = otp_confirmation

            auth_url = f"{self.base_url}/oauth2/auth?{urlencode(params)}"
            return auth_url

        except Exception as e:
            logger.error(f"Ошибка генерации URL авторизации: {str(e)}")
            return ""

    def get_otp_confirmation(self, phone: str) -> Optional[str]:
        """
        Получить OTP подтверждение для номера телефона
        """
        try:
            url = f"{self.base_url}/api/v1/trusted-phone"
            data = {'phone': phone}

            auth = (self.client_id, self.client_secret)
            response = requests.post(
                url,
                json=data,
                auth=auth,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('secret')
            else:
                logger.error(f"Ошибка получения OTP: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Исключение при получении OTP: {str(e)}")
            return None

    def exchange_code_for_tokens(self, code: str) -> Optional[Dict[str, str]]:
        """
        Обмен кода авторизации на токены
        """
        try:
            url = f"{self.base_url}/oauth2/token"
            data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.redirect_uri,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }

            response = requests.post(
                url,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка получения токенов: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Исключение при получении токенов: {str(e)}")
            return None

    def get_signed_pdf(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Получить подписанный PDF документ
        """
        try:
            url = f"{self.base_url}/api/v2/oauth/signatures/pdf"
            headers = self._get_headers(access_token)

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка получения подписанного PDF: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Исключение при получении подписанного PDF: {str(e)}")
            return None