import hashlib
import base64
import requests
from typing import Dict, Any, Optional
import logging

from django.conf import settings
from .models import ContractSignature, ContractMS, ContractFileUser, ContractStatusMS
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class ContractSignatureService:
    """Сервис для работы с подписями контрактов"""

    def __init__(self):
        # URL FastAPI сервиса для верификации подписей
        self.fastapi_verify_url = getattr(
            settings,
            'FASTAPI_SIGNATURE_VERIFY_URL',
            'https://cabinet.tamos-education.kz:11443/fastapi/api/v1/contracts/verify-signature'
        )
        self.request_timeout = 30.0

    def verify_and_save_signature(
            self,
            contract_num: str,
            cms_signature: str,
            signed_data: str,
            user: User
    ) -> Dict[str, Any]:
        """
        Верифицирует подпись через FastAPI и сохраняет в базу

        Args:
            contract_num: Номер контракта
            cms_signature: CMS подпись
            signed_data: Подписанные данные в base64
            user: Пользователь который подписывает

        Returns:
            Dict с результатом операции
        """
        try:
            # Находим контракт по номеру (НЕ изменяем ContractMS!)
            try:
                contract = ContractMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractMS.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Контракт не найден',
                    'error_code': 'CONTRACT_NOT_FOUND'
                }

            # Проверяем, нет ли уже валидной подписи для этого контракта
            existing_signature = ContractSignature.objects.filter(
                contract_num=contract_num,
                is_valid=True
            ).first()

            if existing_signature and not existing_signature.is_document_modified:
                return {
                    'success': False,
                    'error': 'Контракт уже подписан',
                    'error_code': 'ALREADY_SIGNED'
                }

            # Верифицируем подпись через FastAPI
            verification_result = self._verify_signature_via_fastapi(
                cms_signature, signed_data
            )

            if not verification_result['success']:
                return verification_result

            # Вычисляем хэш документа/контракта
            document_hash = self._calculate_contract_hash(contract)

            # Сохраняем подпись в базу (используем contract_num вместо FK)
            if verification_result['iin'] != user.user_info.iin:
                return {
                    'success': False,
                    'error': 'ИИН подписанта не совпадает с ИИН пользователя',
                    'error_code': 'IIN_MISMATCH'
                }

            signature = ContractSignature.objects.create(
                contract_num=contract_num,
                cms_signature=cms_signature,
                signed_data=signed_data,
                document_hash=document_hash,
                signer_iin=verification_result['iin'],
                certificate_info=verification_result.get('certificate_info', {}),
                is_valid=True,
                created_by=user
            )

            contract.ContractStatusID = ContractStatusMS.objects.using('ms_sql').get(sStatusName='Подписан')
            contract.save(using='ms_sql')

            logger.info(f"Signature saved successfully for contract {contract_num}, IIN: {verification_result['iin']}")

            return {
                'success': True,
                'signature_uid': str(signature.signature_uid),
                'signer_iin': verification_result['iin'],
                'contract_num': contract.ContractNum,
                'message': 'Подпись успешно верифицирована и сохранена'
            }

        except Exception as e:
            logger.error(f"Error in verify_and_save_signature: {e}")
            return {
                'success': False,
                'error': f'Ошибка при обработке подписи: {str(e)}',
                'error_code': 'PROCESSING_ERROR'
            }

    def _verify_signature_via_fastapi(
            self,
            cms_signature: str,
            signed_data: str
    ) -> Dict[str, Any]:
        """Верифицирует подпись через FastAPI сервис"""

        try:
            payload = {
                'cms': cms_signature,
                'data': signed_data
            }

            logger.info(f"Sending verification request to FastAPI: {self.fastapi_verify_url}")

            response = requests.post(
                self.fastapi_verify_url,
                json=payload,
                timeout=self.request_timeout,
                headers={'Content-Type': 'application/json'}
            )

            logger.info(f"FastAPI response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()

                if result.get('success'):
                    return {
                        'success': True,
                        'iin': result['iin'],
                        'certificate_info': result.get('certificate_info', {})
                    }
                else:
                    return {
                        'success': False,
                        'error': result.get('error', 'Ошибка верификации подписи'),
                        'error_code': result.get('error_code', 'VERIFICATION_FAILED')
                    }
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', {})
                    if isinstance(error_message, dict):
                        error_message = error_message.get('error', 'Ошибка верификации подписи')
                except:
                    error_message = f'HTTP {response.status_code}: {response.text}'

                return {
                    'success': False,
                    'error': error_message,
                    'error_code': 'VERIFICATION_FAILED'
                }

        except requests.exceptions.Timeout:
            logger.error("Timeout while verifying signature")
            return {
                'success': False,
                'error': 'Таймаут при верификации подписи',
                'error_code': 'TIMEOUT'
            }
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error while verifying signature: {e}")
            return {
                'success': False,
                'error': 'Ошибка соединения с сервисом верификации',
                'error_code': 'CONNECTION_ERROR'
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error while verifying signature: {e}")
            return {
                'success': False,
                'error': f'Ошибка запроса к сервису верификации: {str(e)}',
                'error_code': 'REQUEST_ERROR'
            }
        except Exception as e:
            logger.error(f"Unexpected error while verifying signature: {e}")
            return {
                'success': False,
                'error': f'Неожиданная ошибка при верификации: {str(e)}',
                'error_code': 'UNEXPECTED_ERROR'
            }

    def _calculate_contract_hash(self, contract: ContractMS) -> str:
        """Вычисляет хэш контракта на основе его ключевых данных"""

        # Используем ключевые поля контракта для хэша (НЕ изменяем контракт!)
        contract_data = (
            f"{contract.ContractNum}:"
            f"{contract.ContractAmount}:"
            f"{contract.ContractDate}:"
            f"{getattr(contract, 'StudentID_id', '')}:"
            f"{getattr(contract, 'ContractStatusID_id', '')}"
        )

        # Если есть связанный файл, добавляем его хэш
        try:
            file_obj = ContractFileUser.objects.filter(contractNum=contract.ContractNum).first()
            if file_obj and file_obj.file:
                hasher = hashlib.sha256()
                file_obj.file.seek(0)
                for chunk in file_obj.file.chunks():
                    hasher.update(chunk)
                file_hash = hasher.hexdigest()
                contract_data += f":{file_hash}"
        except Exception as e:
            # Если файла нет или ошибка чтения, используем только данные контракта
            logger.warning(f"Could not include file hash for contract {contract.ContractNum}: {e}")
            pass

        return hashlib.sha256(contract_data.encode()).hexdigest()

    def get_contract_signatures(self, contract_num: str) -> Dict[str, Any]:
        """Получает все подписи для контракта"""

        try:
            # Проверяем существование контракта
            try:
                contract = ContractMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractMS.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Контракт не найден',
                    'error_code': 'CONTRACT_NOT_FOUND'
                }

            # Получаем подписи по номеру контракта
            signatures = ContractSignature.objects.filter(
                contract_num=contract_num
            ).order_by('-signed_at')

            signatures_data = []
            for signature in signatures:
                signatures_data.append({
                    'signature_uid': str(signature.signature_uid),
                    'signer_iin': signature.signer_iin,
                    'signed_at': signature.signed_at.isoformat(),
                    'is_valid': signature.is_valid and not signature.is_document_modified,
                    'certificate_info': signature.certificate_info,
                    'is_document_modified': signature.is_document_modified
                })

            # Используем методы из ContractSignature
            signature_status = ContractSignature.get_signature_status(contract.ContractNum)

            return {
                'success': True,
                'contract_num': contract_num,
                'signature_status': signature_status,
                'signatures': signatures_data,
                'total_signatures': len(signatures_data),
                'valid_signatures': len([s for s in signatures_data if s['is_valid']])
            }

        except Exception as e:
            logger.error(f"Error in get_contract_signatures: {e}")
            return {
                'success': False,
                'error': f'Ошибка при получении подписей: {str(e)}',
                'error_code': 'PROCESSING_ERROR'
            }

    def check_signature_validity(self, signature_uid: str) -> Dict[str, Any]:
        """Проверяет актуальность подписи"""

        try:
            signature = ContractSignature.objects.get(signature_uid=signature_uid)

            # Проверяем не изменился ли документ
            is_document_modified = signature.is_document_modified

            if is_document_modified and signature.is_valid:
                # Помечаем подпись как невалидную если документ изменился
                signature.is_valid = False
                signature.save()
                logger.info(f"Signature {signature_uid} marked as invalid due to document modification")

            return {
                'success': True,
                'signature_uid': signature_uid,
                'contract_num': signature.contract_num,
                'is_valid': signature.is_valid,
                'is_document_modified': is_document_modified,
                'signed_at': signature.signed_at.isoformat(),
                'signer_iin': signature.signer_iin
            }

        except ContractSignature.DoesNotExist:
            return {
                'success': False,
                'error': 'Подпись не найдена',
                'error_code': 'SIGNATURE_NOT_FOUND'
            }
        except Exception as e:
            logger.error(f"Error in check_signature_validity: {e}")
            return {
                'success': False,
                'error': f'Ошибка при проверке подписи: {str(e)}',
                'error_code': 'PROCESSING_ERROR'
            }

    def get_contract_summary(self, contract_num: str) -> Dict[str, Any]:
        """Получает краткую сводку по контракту и его подписям"""

        try:
            contract = ContractMS.objects.using('ms_sql').get(ContractNum=contract_num)
            signatures = ContractSignature.get_contract_signatures(contract_num)

            valid_signatures = signatures.filter(is_valid=True)

            return {
                'success': True,
                'contract_num': contract_num,
                'contract_info': {
                    'student_name': getattr(contract.StudentID, 'full_name', '') if hasattr(contract,
                                                                                            'StudentID') and contract.StudentID else '',
                    'contract_amount': str(contract.ContractAmount) if contract.ContractAmount else '',
                    'contract_date': contract.ContractDate.isoformat() if contract.ContractDate else '',
                },
                'signature_summary': {
                    'total_signatures': signatures.count(),
                    'valid_signatures': valid_signatures.count(),
                    'status': ContractSignature.get_signature_status(contract.ContractNum),
                    'last_signed': signatures.first().signed_at.isoformat() if signatures.exists() else None,
                    'has_valid_signatures': valid_signatures.exists()
                }
            }

        except ContractMS.DoesNotExist:
            return {
                'success': False,
                'error': 'Контракт не найден',
                'error_code': 'CONTRACT_NOT_FOUND'
            }
        except Exception as e:
            logger.error(f"Error in get_contract_summary: {e}")
            return {
                'success': False,
                'error': f'Ошибка при получении сводки: {str(e)}',
                'error_code': 'PROCESSING_ERROR'
            }