import json
import qrcode
from io import BytesIO
from datetime import datetime
from typing import Dict, Any, Optional
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class QRCodeGenerator:
    """Генератор QR-кодов для подписей контрактов"""

    def __init__(self):
        self.frontend_url = getattr(settings, 'FRONTEND_URL', 'https://cabinet.tamos-education.kz:11443')

    def create_qr_code_image(self, data: Dict[str, Any], size: str = 'medium') -> bytes:
        """
        Создает изображение QR-кода из данных

        Args:
            data: Данные для кодирования
            size: Размер QR-кода ('small', 'medium', 'large')

        Returns:
            bytes: Изображение QR-кода в формате PNG
        """
        try:
            # Настройки размера в зависимости от параметра
            size_settings = {
                'small': {'version': 1, 'box_size': 8, 'border': 2},
                'medium': {'version': 1, 'box_size': 10, 'border': 4},
                'large': {'version': 1, 'box_size': 12, 'border': 4}
            }

            settings_dict = size_settings.get(size, size_settings['medium'])

            qr = qrcode.QRCode(
                version=settings_dict['version'],
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=settings_dict['box_size'],
                border=settings_dict['border']
            )

            # Преобразуем данные в JSON строку для QR-кода
            qr_text = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

            qr.add_data(qr_text)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            buffered = BytesIO()
            img.save(buffered, format='PNG')

            return buffered.getvalue()

        except Exception as e:
            logger.error(f"Error creating QR code: {e}")
            return b''

    def generate_signature_qr_data(self, signature) -> Dict[str, Any]:
        """
        Генерирует данные для QR-кода подписи контракта

        Args:
            signature: Объект ContractSignature

        Returns:
            Dict: Данные для QR-кода
        """
        verification_url = f"{self.frontend_url}/signature-verification/{signature.signature_uid}"

        return {
            "type": "contract_signature",
            "version": "1.0",
            "signature_uid": str(signature.signature_uid),
            "contract_num": signature.contract_num,
            "signer_iin": signature.signer_iin,
            "signed_at": signature.signed_at.isoformat(),
            "verification_url": verification_url,
            "message_ru": "Сканируйте для проверки подписи контракта",
            "message_kz": "Контракт қолтаңбасын тексеру үшін сканерлеңіз",
            "message_en": "Scan to verify contract signature"
        }

    def generate_director_qr_data(self, director_type: str, contract_num: str,
                                  certificate_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Генерирует данные для QR-кода подписи директора

        Args:
            director_type: Тип директора ('omarov', 'serikov')
            contract_num: Номер контракта
            certificate_info: Информация о сертификате

        Returns:
            Dict: Данные для QR-кода
        """
        director_info = self._get_director_info(director_type)

        return {
            "type": "director_signature",
            "version": "1.0",
            "director": director_info["name"],
            "position": director_info["position"],
            "contract_num": contract_num,
            "signed_at": datetime.now().isoformat(),
            "certificate_info": certificate_info or director_info["certificate_info"],
            "message_ru": f"Подпись {director_info['position']}",
            "message_kz": f"{director_info['position_kz']} қолы",
            "message_en": f"{director_info['position_en']} signature"
        }

    def generate_contract_qr_data(self, contract_num: str, additional_info: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Генерирует данные для QR-кода контракта (общая информация)

        Args:
            contract_num: Номер контракта
            additional_info: Дополнительная информация

        Returns:
            Dict: Данные для QR-кода
        """
        contract_url = f"{self.frontend_url}/contracts/{contract_num}/signatures"

        data = {
            "type": "contract_info",
            "version": "1.0",
            "contract_num": contract_num,
            "contract_url": contract_url,
            "generated_at": datetime.now().isoformat(),
            "message_ru": "Информация о подписях контракта",
            "message_kz": "Контракт қолтаңбалары туралы ақпарат",
            "message_en": "Contract signatures information"
        }

        if additional_info:
            data.update(additional_info)

        return data

    def _get_director_info(self, director_type: str) -> Dict[str, Any]:
        """
        Получает информацию о директоре

        Args:
            director_type: Тип директора

        Returns:
            Dict: Информация о директоре
        """
        directors = {
            'omarov': {
                "name": "Омаров",
                "position": "Директор",
                "position_kz": "Директор",
                "position_en": "Director",
                "certificate_info": {
                    "serial_number": "93af8264ee9fabcf9123ae0c4c2d1373c31cb126",
                    "common_name": "ОМАРОВ"
                }
            },
            'serikov': {
                "name": "Сериков",
                "position": "Заместитель директора",
                "position_kz": "Директор орынбасары",
                "position_en": "Deputy Director",
                "certificate_info": {
                    "serial_number": "ac509efd146861ebcba1a4c0ceca04df1fd1ac1b",
                    "common_name": "СЕРИКОВ"
                }
            }
        }

        return directors.get(director_type, {
            "name": "Неизвестный директор",
            "position": "Неизвестная должность",
            "position_kz": "Белгісіз лауазым",
            "position_en": "Unknown position",
            "certificate_info": {}
        })

    def create_signature_qr_code(self, signature, size: str = 'medium') -> bytes:
        """
        Создает QR-код для подписи контракта

        Args:
            signature: Объект ContractSignature
            size: Размер QR-кода

        Returns:
            bytes: Изображение QR-кода
        """
        qr_data = self.generate_signature_qr_data(signature)
        return self.create_qr_code_image(qr_data, size)

    def create_director_qr_code(self, director_type: str, contract_num: str, size: str = 'medium') -> bytes:
        """
        Создает QR-код для подписи директора

        Args:
            director_type: Тип директора
            contract_num: Номер контракта
            size: Размер QR-кода

        Returns:
            bytes: Изображение QR-кода
        """
        qr_data = self.generate_director_qr_data(director_type, contract_num)
        return self.create_qr_code_image(qr_data, size)

    def create_contract_qr_code(self, contract_num: str, additional_info: Optional[Dict] = None,
                                size: str = 'medium') -> bytes:
        """
        Создает QR-код для контракта

        Args:
            contract_num: Номер контракта
            additional_info: Дополнительная информация
            size: Размер QR-кода

        Returns:
            bytes: Изображение QR-кода
        """
        qr_data = self.generate_contract_qr_data(contract_num, additional_info)
        return self.create_qr_code_image(qr_data, size)


class QRCodeValidator:
    """Валидатор QR-кодов"""

    @staticmethod
    def validate_qr_data(qr_text: str) -> Dict[str, Any]:
        """
        Валидирует и парсит данные из QR-кода

        Args:
            qr_text: Текст из QR-кода

        Returns:
            Dict: Распарсенные и валидированные данные
        """
        try:
            data = json.loads(qr_text)

            # Проверяем обязательные поля
            if not isinstance(data, dict):
                raise ValueError("QR-код должен содержать JSON объект")

            qr_type = data.get('type')
            if not qr_type:
                raise ValueError("QR-код должен содержать поле 'type'")

            version = data.get('version', '1.0')

            # Валидируем в зависимости от типа
            if qr_type == 'contract_signature':
                QRCodeValidator._validate_signature_qr(data)
            elif qr_type == 'director_signature':
                QRCodeValidator._validate_director_qr(data)
            elif qr_type == 'contract_info':
                QRCodeValidator._validate_contract_qr(data)
            else:
                logger.warning(f"Unknown QR code type: {qr_type}")

            return {
                'valid': True,
                'data': data,
                'type': qr_type,
                'version': version
            }

        except json.JSONDecodeError as e:
            return {
                'valid': False,
                'error': f'Некорректный JSON в QR-коде: {e}',
                'data': None
            }
        except ValueError as e:
            return {
                'valid': False,
                'error': str(e),
                'data': None
            }
        except Exception as e:
            logger.error(f"Error validating QR code: {e}")
            return {
                'valid': False,
                'error': f'Ошибка валидации QR-кода: {e}',
                'data': None
            }

    @staticmethod
    def _validate_signature_qr(data: Dict) -> None:
        """Валидирует QR-код подписи"""
        required_fields = ['signature_uid', 'contract_num', 'signer_iin', 'signed_at']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"QR-код подписи должен содержать поле '{field}'")

    @staticmethod
    def _validate_director_qr(data: Dict) -> None:
        """Валидирует QR-код директора"""
        required_fields = ['director', 'position', 'contract_num', 'signed_at']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"QR-код директора должен содержать поле '{field}'")

    @staticmethod
    def _validate_contract_qr(data: Dict) -> None:
        """Валидирует QR-код контракта"""
        required_fields = ['contract_num']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"QR-код контракта должен содержать поле '{field}'")