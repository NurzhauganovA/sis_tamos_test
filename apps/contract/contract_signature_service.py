import hashlib
import base64
import os
import subprocess
from datetime import datetime
from io import BytesIO

import qrcode
import requests
from typing import Dict, Any, Optional
import logging

from django.conf import settings
from django.core.files.base import ContentFile
from docx import Document
from docx.shared import Inches

from .models import ContractSignature, ContractMS, ContractFileUser, ContractStatusMS
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class ContractSignatureService:
    """Обновленный сервис для работы с подписями контрактов"""

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
        Верифицирует подпись через FastAPI и сохраняет в базу с обновлением PDF
        """
        try:
            # Находим контракт по номеру
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

            # Проверяем соответствие ИИН
            if verification_result['iin'] != user.user_info.iin:
                return {
                    'success': False,
                    'error': 'ИИН подписанта не совпадает с ИИН пользователя',
                    'error_code': 'IIN_MISMATCH'
                }

            # Вычисляем хэш документа/контракта
            document_hash = self._calculate_contract_hash(contract)

            # Сохраняем подпись в базу
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

            # Обновляем статус контракта
            contract.ContractStatusID = ContractStatusMS.objects.using('ms_sql').get(sStatusName='Подписан')
            contract.save(using='ms_sql')

            # Генерируем и обновляем PDF с QR-кодом
            self._update_contract_pdf_with_signature(contract, signature, user)

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
        except Exception as e:
            logger.error(f"Unexpected error while verifying signature: {e}")
            return {
                'success': False,
                'error': f'Неожиданная ошибка при верификации: {str(e)}',
                'error_code': 'UNEXPECTED_ERROR'
            }

    def _update_contract_pdf_with_signature(self, contract, signature, user):
        """Обновляет PDF контракта с добавлением QR-кода подписи"""
        try:
            # Получаем существующий файл контракта или создаем новый
            contract_file = ContractFileUser.objects.filter(contractNum=contract.ContractNum).last()

            if not contract_file:
                # Если файл не найден, создаем базовый контракт
                self._generate_base_contract(contract, user)
                contract_file = ContractFileUser.objects.filter(contractNum=contract.ContractNum).last()

            # Генерируем QR-код для подписи
            qr_signature_data = self._generate_signature_qr_data(signature)
            qr_signature_code = self._create_qr_code(qr_signature_data)

            # Генерируем QR-коды директоров (как в старой версии)
            qr_director_omarov = self._generate_director_qr_code('omarov', contract.ContractNum)
            qr_director_serikov = self._generate_director_qr_code('serikov', contract.ContractNum)

            # Обновляем документ с QR-кодами
            self._add_qr_codes_to_contract(
                contract,
                qr_signature_code,
                qr_director_omarov,
                qr_director_serikov,
                user
            )

            logger.info(f"Contract PDF updated with signature QR code for {contract.ContractNum}")

        except Exception as e:
            logger.error(f"Error updating contract PDF: {e}")
            # Не прерываем процесс подписания из-за ошибки обновления PDF

    def _generate_signature_qr_data(self, signature):
        """Генерирует данные для QR-кода подписи"""
        # URL для проверки подписи на фронтенде
        verification_url = f"{settings.FRONTEND_URL}/signature-verification/{signature.signature_uid}"

        qr_data = {
            "type": "contract_signature",
            "signature_uid": str(signature.signature_uid),
            "contract_num": signature.contract_num,
            "signer_iin": signature.signer_iin,
            "signed_at": signature.signed_at.isoformat(),
            "verification_url": verification_url,
            "message": "Сканируйте для проверки подписи контракта"
        }

        return qr_data

    def _create_qr_code(self, data):
        """Создает QR-код из данных"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )

        # Преобразуем данные в JSON строку для QR-кода
        import json
        qr_text = json.dumps(data, ensure_ascii=False)

        qr.add_data(qr_text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffered = BytesIO()
        img.save(buffered, format='PNG')

        return buffered.getvalue()

    def _generate_director_qr_code(self, director_type, contract_num):
        """Генерирует QR-код директора (аналогично старой логике)"""
        try:
            if director_type == 'omarov':
                certificate_path = 'eds/Omarov/AUTH_RSA256_93af8264ee9fabcf9123ae0c4c2d1373c31cb126.p12'
                password = str(settings.EDS_OMAROV_KEY)
            elif director_type == 'serikov':
                certificate_path = 'eds/Serikov/AUTH_RSA256_ac509efd146861ebcba1a4c0ceca04df1fd1ac1b.p12'
                password = str(settings.EDS_SERIKOV_KEY)
            else:
                return b''

            # Здесь можно добавить логику генерации QR-кода директора
            # Пока возвращаем пустой QR-код
            qr_data = {
                "type": "director_signature",
                "director": director_type,
                "contract_num": contract_num,
                "signed_at": datetime.now().isoformat()
            }

            return self._create_qr_code(qr_data)

        except Exception as e:
            logger.error(f"Error generating director QR code: {e}")
            return b''

    def _add_qr_codes_to_contract(self, contract, qr_signature, qr_director_omarov, qr_director_serikov, user):
        """Добавляет QR-коды в документ контракта"""
        try:
            # Получаем шаблон контракта (аналогично старой логике)
            docx_template = self._get_contract_template(contract)

            if not docx_template:
                logger.error("Contract template not found")
                return

            doc = Document(docx_template)

            # Заменяем плейсхолдеры QR-кодов на реальные изображения
            self._replace_qr_placeholders(doc, qr_signature, qr_director_omarov, qr_director_serikov)

            # Сохраняем обновленный документ
            docx_output_path = f'contracts/signed/docx/contract_{contract.ContractNum}.docx'
            pdf_directory = "contracts/signed/pdf"
            pdf_output_path = f'{pdf_directory}/contract_{contract.ContractNum}.pdf'

            # Создаем директории если не существуют
            os.makedirs(os.path.dirname(docx_output_path), exist_ok=True)
            os.makedirs(pdf_directory, exist_ok=True)

            doc.save(docx_output_path)

            # Конвертируем в PDF
            self._docx_to_pdf(docx_output_path, pdf_directory)

            # Обновляем файл в базе данных
            with open(pdf_output_path, 'rb') as pdf_file:
                file_content = pdf_file.read()

                contract_file = ContractFileUser.objects.filter(contractNum=contract.ContractNum).last()
                if contract_file:
                    contract_file.file = ContentFile(file_content, name=f'{contract.ContractNum}_signed.pdf')
                    contract_file.date = datetime.now()
                    contract_file.save()
                else:
                    ContractFileUser.objects.create(
                        user=user,
                        contractNum=contract.ContractNum,
                        file=ContentFile(file_content, name=f'{contract.ContractNum}_signed.pdf')
                    )

            # Удаляем временные файлы
            os.remove(docx_output_path)
            os.remove(pdf_output_path)

        except Exception as e:
            logger.error(f"Error adding QR codes to contract: {e}")

    def _replace_qr_placeholders(self, doc, qr_signature, qr_director_omarov, qr_director_serikov):
        """Заменяет плейсхолдеры QR-кодов в документе"""
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                if '{QRCodeSignature}' in run.text:
                    run.text = run.text.replace('{QRCodeSignature}', '')
                    if qr_signature:
                        image_stream = BytesIO(qr_signature)
                        run.add_picture(image_stream, width=Inches(1.5), height=Inches(1.5))

                if '{QRCodeDirectorOmarov}' in run.text:
                    run.text = run.text.replace('{QRCodeDirectorOmarov}', '')
                    if qr_director_omarov:
                        image_stream = BytesIO(qr_director_omarov)
                        run.add_picture(image_stream, width=Inches(1.2), height=Inches(1.2))

                if '{QRCodeDirectorSerikov}' in run.text:
                    run.text = run.text.replace('{QRCodeDirectorSerikov}', '')
                    if qr_director_serikov:
                        image_stream = BytesIO(qr_director_serikov)
                        run.add_picture(image_stream, width=Inches(1.2), height=Inches(1.2))

        # Также проверяем таблицы
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            if '{QRCodeSignature}' in run.text:
                                run.text = run.text.replace('{QRCodeSignature}', '')
                                if qr_signature:
                                    image_stream = BytesIO(qr_signature)
                                    run.add_picture(image_stream, width=Inches(1.5), height=Inches(1.5))

    def _get_contract_template(self, contract):
        """Получает шаблон контракта (аналогично старой логике)"""
        try:
            contract_payment_type = contract.PaymentTypeID.sPaymentType
            contract_school_language = getattr(contract.SchoolID, 'sSchool_language', '')
            contract_school_direct = getattr(contract.SchoolID, 'sSchool_direct', '')

            # Логика выбора шаблона (упрощенная версия)
            if contract_payment_type == 'Оплата по месячно':
                if contract_school_language == 'Казахское отделение':
                    return 'apps/contract/templates/contract/signed/Договор_оказания_образовательных_услуг_КАЗ_ОТД_ТОО_по_месячно.docx'
                else:
                    return 'apps/contract/templates/contract/signed/Договор_оказания_образовательных_услуг_Школа_2023_2024_оплата_по_месячно.docx'

            # Добавьте другие варианты шаблонов по необходимости
            return 'apps/contract/templates/contract/signed/Договор_оказания_образовательных_услуг_Школа_2023_2024_оплата_по_месячно.docx'

        except Exception as e:
            logger.error(f"Error getting contract template: {e}")
            return None

    def _generate_base_contract(self, contract, user):
        """Генерирует базовый контракт если файл не существует"""
        # Здесь можно использовать существующую логику генерации контракта
        # из ChangeDocumentContentService
        pass

    def _docx_to_pdf(self, input_path, output_path):
        """Конвертация файла из формата DOCX в PDF"""
        command_strings = ['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', output_path, input_path]
        try:
            subprocess.call(command_strings)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error converting DOCX to PDF: {e}")

    def _calculate_contract_hash(self, contract: ContractMS) -> str:
        """Вычисляет хэш контракта на основе его ключевых данных"""
        contract_data = (
            f"{contract.ContractNum}:"
            f"{contract.ContractAmount}:"
            f"{contract.ContractDate}:"
            f"{getattr(contract, 'StudentID_id', '')}:"
            f"{getattr(contract, 'ContractStatusID_id', '')}"
        )

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