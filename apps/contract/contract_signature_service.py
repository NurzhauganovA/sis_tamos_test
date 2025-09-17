# apps/contract/contract_signature_service.py

import hashlib
import base64
import os
import subprocess
import json
from datetime import datetime
from io import BytesIO

import qrcode
import requests
from typing import Dict, Any, Optional
import logging

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from docx import Document
from docx.shared import Inches, Cm

from .models import ContractSignature, ContractMS, ContractFileUser, ContractStatusMS, ContractDopMS, \
    ContractDopFileUser
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
        self.frontend_url = getattr(settings, 'FRONTEND_URL', 'https://cabinet.tamos-education.kz:11443')

    def verify_and_save_signature(
            self,
            contract_num: str,
            cms_signature: str,
            signed_data: str,
            user: User,
            is_dop_contract: bool = False
    ) -> Dict[str, Any]:
        """
        Верифицирует подпись через FastAPI и сохраняет в базу с обновлением PDF
        """
        try:
            # Находим контракт по номеру
            try:
                if is_dop_contract:
                    # Для дополнительных договоров
                    contract_dop = ContractDopMS.objects.using('ms_sql').filter(
                        agreement_id__ContractNum=contract_num
                    ).first()
                    if not contract_dop:
                        return {
                            'success': False,
                            'error': 'Дополнительный договор не найден',
                            'error_code': 'CONTRACT_NOT_FOUND'
                        }
                    contract = contract_dop.agreement_id
                else:
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
            if hasattr(user, 'user_info') and hasattr(user.user_info, 'iin'):
                if verification_result['iin'] != user.user_info.iin:
                    return {
                        'success': False,
                        'error': 'ИИН подписанта не совпадает с ИИН пользователя',
                        'error_code': 'IIN_MISMATCH'
                    }

            logger.info(
                f"Signature verification successful for contract {contract_num}, IIN: {verification_result['iin']}")

            # АТОМАРНАЯ ТРАНЗАКЦИЯ: Создаем файл и подпись как единое целое
            with transaction.atomic():
                try:
                    # 1. Генерируем полный подписанный контракт СНАЧАЛА
                    self._generate_complete_signed_contract_for_signature(
                        contract=contract,
                        user=user,
                        is_dop_contract=is_dop_contract,
                        signer_iin=verification_result['iin']
                    )

                    logger.info(f"Contract PDF generated successfully for {contract_num}")

                    # 2. ПОСЛЕ создания файла вычисляем хэш НОВОГО документа
                    document_hash = self._calculate_contract_hash(contract, is_dop_contract)

                    logger.info(f"New document hash calculated: {document_hash[:16]}...")

                    # 3. ТОЛЬКО ТЕПЕРЬ сохраняем подпись с правильным хэшем
                    signature = ContractSignature.objects.create(
                        contract_num=contract_num,
                        cms_signature=cms_signature,
                        signed_data=signed_data,
                        document_hash=document_hash,  # Хэш НОВОГО документа
                        signer_iin=verification_result['iin'],
                        certificate_info=verification_result.get('certificate_info', {}),
                        is_valid=True,
                        created_by=user
                    )

                    logger.info(f"ContractSignature created with hash: {document_hash[:16]}...")

                    # 4. Обновляем статус контракта
                    if is_dop_contract:
                        contract_dop.status_id = ContractStatusMS.objects.using('ms_sql').get(sStatusName='Подписан')
                        contract_dop.save(using='ms_sql')
                    else:
                        contract.ContractStatusID = ContractStatusMS.objects.using('ms_sql').get(sStatusName='Подписан')
                        contract.save(using='ms_sql')

                    # 5. Добавляем подпись директора (автоматически) с тем же хэшем
                    self._add_director_signature(contract_num, signature, document_hash)

                    logger.info(f"Transaction completed successfully for contract {contract_num}")

                except Exception as e:
                    logger.error(f"Error in transaction for contract {contract_num}: {e}")
                    # Транзакция автоматически откатится
                    raise

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

    def _generate_complete_signed_contract_for_signature(self, contract, user, is_dop_contract=False, signer_iin=None):
        """Генерирует полный подписанный контракт специально для процесса подписания"""
        try:
            # Получаем данные студента и родителя
            student = contract.StudentID
            parent = student.parent_id if student else None

            if not student or not parent:
                logger.error("Student or parent not found for contract generation")
                raise ValueError("Student or parent data missing")

            # Генерируем временные QR-коды для подписи (будут обновлены после сохранения подписи)
            temp_qr_data = {
                "type": "contract_signature",
                "contract_num": contract.ContractNum,
                "signer_iin": signer_iin or "pending",
                "signed_at": datetime.now().isoformat(),
                "message": "Подпись в процессе обработки"
            }
            qr_signature_code = self._create_qr_code(temp_qr_data)

            # Генерируем QR-коды директоров
            qr_director_omarov = self._generate_director_qr_code('omarov', contract.ContractNum)
            qr_director_serikov = self._generate_director_qr_code('serikov', contract.ContractNum)

            # Создаем новый документ с заполненными переменными и QR-кодами
            self._generate_complete_signed_contract(
                contract=contract,
                student=student,
                parent=parent,
                qr_signature=qr_signature_code,
                qr_director_omarov=qr_director_omarov,
                qr_director_serikov=qr_director_serikov,
                user=user,
                is_dop_contract=is_dop_contract
            )

            logger.info(f"Contract file generated successfully for signing process: {contract.ContractNum}")

        except Exception as e:
            logger.error(f"Error in _generate_complete_signed_contract_for_signature: {e}")
            raise

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

    def _update_contract_pdf_with_signature(self, contract, signature, user, is_dop_contract=False):
        """Создает полностью новый PDF контракта с заполненными переменными и QR-кодами"""
        try:
            # Всегда генерируем новый контракт с заполненными данными
            logger.info(f"Generating new contract file for {contract.ContractNum}")

            # Получаем данные студента и родителя
            student = contract.StudentID
            parent = student.parent_id if student else None

            if not student or not parent:
                logger.error("Student or parent not found for contract generation")
                return

            # Генерируем QR-коды
            qr_signature_data = self._generate_signature_qr_data(signature)
            qr_signature_code = self._create_qr_code(qr_signature_data)
            qr_director_omarov = self._generate_director_qr_code('omarov', contract.ContractNum)
            qr_director_serikov = self._generate_director_qr_code('serikov', contract.ContractNum)

            # Создаем новый документ с заполненными переменными и QR-кодами
            self._generate_complete_signed_contract(
                contract=contract,
                student=student,
                parent=parent,
                qr_signature=qr_signature_code,
                qr_director_omarov=qr_director_omarov,
                qr_director_serikov=qr_director_serikov,
                user=user,
                is_dop_contract=is_dop_contract
            )

            logger.info(f"Contract PDF created successfully for {contract.ContractNum}")

        except Exception as e:
            logger.error(f"Error creating contract PDF: {e}")
            # Не прерываем процесс подписания из-за ошибки обновления PDF

    def _generate_complete_signed_contract(self, contract, student, parent, qr_signature, qr_director_omarov,
                                           qr_director_serikov, user, is_dop_contract=False):
        """Генерирует полный подписанный контракт с заполненными переменными и QR-кодами"""
        try:
            # Получаем правильный шаблон контракта
            docx_template_path = self._get_contract_template(contract, is_dop_contract)

            if not docx_template_path:
                logger.error("Contract template not found")
                return

            # Проверяем существование файла шаблона
            import os
            if not os.path.exists(docx_template_path):
                logger.error(f"Template file not found: {docx_template_path}")
                return

            # Открываем шаблон
            doc = Document(docx_template_path)

            # Заполняем ВСЕ переменные контракта И добавляем QR-коды
            self._replace_qr_placeholders(doc, qr_signature, qr_director_omarov, qr_director_serikov, contract)

            # Обрабатываем специальные таблицы оплаты если есть
            self._process_payment_tables(doc, contract)

            # Сохраняем готовый документ
            docx_output_path = f'contracts/signed/docx/contract_{contract.ContractNum}_signed.docx'
            pdf_directory = "contracts/signed/pdf"
            pdf_output_path = f'{pdf_directory}/contract_{contract.ContractNum}_signed.pdf'

            # Создаем директории если не существуют
            os.makedirs(os.path.dirname(docx_output_path), exist_ok=True)
            os.makedirs(pdf_directory, exist_ok=True)

            # Сохраняем DOCX
            doc.save(docx_output_path)
            logger.info(f"DOCX saved: {docx_output_path}")

            # Конвертируем в PDF
            self._docx_to_pdf(docx_output_path, pdf_directory)
            logger.info(f"PDF converted: {pdf_output_path}")

            # Проверяем что PDF создался
            if not os.path.exists(pdf_output_path):
                logger.error(f"PDF file was not created: {pdf_output_path}")
                return

            # Сохраняем в базе данных (создаем новую запись или обновляем существующую)
            with open(pdf_output_path, 'rb') as pdf_file:
                file_content = pdf_file.read()

                if is_dop_contract:
                    # Для дополнительных договоров
                    contract_file = ContractDopFileUser.objects.filter(contractNum=contract.ContractNum).first()
                    if contract_file:
                        # Обновляем существующую запись
                        contract_file.file.delete(save=False)  # Удаляем старый файл
                        contract_file.file = ContentFile(file_content, name=f'{contract.ContractNum}_signed.pdf')
                        contract_file.date = datetime.now()
                        contract_file.save()
                        logger.info(f"Updated existing dop contract file: {contract.ContractNum}")
                    else:
                        # Создаем новую запись
                        ContractDopFileUser.objects.create(
                            user=user,
                            contractNum=contract.ContractNum,
                            file=ContentFile(file_content, name=f'{contract.ContractNum}_signed.pdf')
                        )
                        logger.info(f"Created new dop contract file: {contract.ContractNum}")
                else:
                    # Для основных договоров
                    contract_file = ContractFileUser.objects.filter(contractNum=contract.ContractNum).first()
                    if contract_file:
                        # Обновляем существующую запись
                        contract_file.file.delete(save=False)  # Удаляем старый файл
                        contract_file.file = ContentFile(file_content, name=f'{contract.ContractNum}_signed.pdf')
                        contract_file.date = datetime.now()
                        contract_file.save()
                        logger.info(f"Updated existing contract file: {contract.ContractNum}")
                    else:
                        # Создаем новую запись
                        ContractFileUser.objects.create(
                            user=user,
                            contractNum=contract.ContractNum,
                            file=ContentFile(file_content, name=f'{contract.ContractNum}_signed.pdf')
                        )
                        logger.info(f"Created new contract file: {contract.ContractNum}")

            # Удаляем временные файлы
            try:
                os.remove(docx_output_path)
                os.remove(pdf_output_path)
                logger.info("Temporary files cleaned up")
            except Exception as e:
                logger.warning(f"Could not remove temporary files: {e}")

        except Exception as e:
            logger.error(f"Error generating complete signed contract: {e}")
            raise

    def _process_payment_tables(self, doc, contract):
        """Обрабатывает специальные таблицы оплаты в документе"""
        try:
            # Ищем и обрабатываем таблицы в документе
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                if '{customtable_monthpay}' in run.text:
                                    self._process_month_pay_table(cell, contract)
                                    run.text = run.text.replace('{customtable_monthpay}', '')

                                if '{customtable_quarterpay}' in run.text:
                                    self._process_quarter_pay_table(cell, contract)
                                    run.text = run.text.replace('{customtable_quarterpay}', '')

        except Exception as e:
            logger.error(f"Error processing payment tables: {e}")

    def _generate_signature_qr_data(self, signature):
        """Генерирует данные для QR-кода подписи"""
        # URL для проверки подписи на фронтенде
        verification_url = f"{self.frontend_url}/signature-verification/{signature.signature_uid}"

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
        qr_text = json.dumps(data, ensure_ascii=False)

        qr.add_data(qr_text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffered = BytesIO()
        img.save(buffered, format='PNG')

        return buffered.getvalue()

    def _generate_director_qr_code(self, director_type, contract_num):
        """Генерирует QR-код директора"""
        try:
            # Данные директора для QR-кода
            if director_type == 'omarov':
                director_data = {
                    "type": "director_signature",
                    "director": "Омаров",
                    "position": "Директор",
                    "contract_num": contract_num,
                    "signed_at": datetime.now().isoformat(),
                    "certificate_info": {
                        "serial_number": "93af8264ee9fabcf9123ae0c4c2d1373c31cb126",
                        "common_name": "ОМАРОВ"
                    }
                }
            elif director_type == 'serikov':
                director_data = {
                    "type": "director_signature",
                    "director": "Сериков",
                    "position": "Заместитель директора",
                    "contract_num": contract_num,
                    "signed_at": datetime.now().isoformat(),
                    "certificate_info": {
                        "serial_number": "ac509efd146861ebcba1a4c0ceca04df1fd1ac1b",
                        "common_name": "СЕРИКОВ"
                    }
                }
            else:
                return b''

            return self._create_qr_code(director_data)

        except Exception as e:
            logger.error(f"Error generating director QR code: {e}")
            return b''

    def _add_qr_codes_to_contract(self, contract, qr_signature, qr_director_omarov, qr_director_serikov, user,
                                  is_dop_contract=False):
        """Добавляет QR-коды в документ контракта"""
        try:
            # Получаем шаблон контракта
            docx_template = self._get_contract_template(contract, is_dop_contract)

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

                if is_dop_contract:
                    contract_file = ContractDopFileUser.objects.filter(contractNum=contract.ContractNum).last()
                    if contract_file:
                        contract_file.file = ContentFile(file_content, name=f'{contract.ContractNum}_signed.pdf')
                        contract_file.date = datetime.now()
                        contract_file.save()
                    else:
                        ContractDopFileUser.objects.create(
                            user=user,
                            contractNum=contract.ContractNum,
                            file=ContentFile(file_content, name=f'{contract.ContractNum}_signed.pdf')
                        )
                else:
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

    def _replace_qr_placeholders(self, doc, qr_signature, qr_director_omarov, qr_director_serikov, contract):
        """Заменяет все плейсхолдеры в документе: переменные контракта и QR-коды"""
        from .models import ContractMS, ContractDopMS, DiscountMS, ContractDiscountMS
        from .services import ChangeDocumentContentService
        from datetime import timedelta
        import math
        from num2words import num2words

        # Получаем данные контракта
        try:
            if not contract:
                logger.error("Contract not provided for template replacement")
                return

            student = contract.StudentID
            parent = student.parent_id if student else None

            if not student or not parent:
                logger.error("Student or parent not found for contract")
                return

        except Exception as e:
            logger.error(f"Error getting contract data: {e}")
            return

        # Подготавливаем данные для замены
        try:
            # Данные паспорта родителя
            ParentPassport = f'Удостоверение личности: №{parent.num_of_doc}, Орган выдачи: {parent.issued_by}, Дата выдачи: {parent.issue_date}'
            ParentPassportKAZ = f'Жеке куәлік: №{parent.num_of_doc}, Берген орган: {parent.issued_by}, Берілген күні: {parent.issue_date}'
            ParentPassportENG = f'ID: No.{parent.num_of_doc}, Issued by: {parent.issued_by}, Issue date: {parent.issue_date}'

            if '?' in str(parent.issued_by):
                ParentPassport = f'Удостоверение личности: №{parent.num_of_doc}, Орган выдачи: Не указано, Дата выдачи: {parent.issue_date}'
                ParentPassportKAZ = f'Жеке куәлік: №{parent.num_of_doc}, Берген орган: Көрсетілмеген, Берілген күні: {parent.issue_date}'
                ParentPassportENG = f'ID: No.{parent.num_of_doc}, Issued by: Not specified, Issue date: {parent.issue_date}'

            # Расчет суммы со скидкой
            discount = DiscountMS.objects.using('ms_sql').all()
            contract_discount = ContractDiscountMS.objects.using('ms_sql').filter(ContractID=contract)
            contract_amount = float(contract.ContractAmount)

            if contract_discount.exists():
                for i in contract_discount:
                    for j in discount.filter(id=i.DiscountID.id):
                        percent = int(j.iDiscountPercent)
                        contract_amount -= contract_amount * percent / 100
                contract_amount_with_discount = float(round(contract_amount, 2))
            else:
                contract_amount_with_discount = float(round(contract_amount, 2))

            # Дополнительная сумма договора
            try:
                contract_dop_amount = ContractMS.objects.using('ms_sql').filter(
                    ContractNum=contract.ContractNum).first()
                if contract_dop_amount:
                    contract_dop_amount = contract_dop_amount.ContractAmount
                else:
                    contract_dop_amount = 0
            except:
                contract_dop_amount = 0

        except Exception as e:
            logger.error(f"Error calculating contract amounts: {e}")
            contract_amount_with_discount = float(contract.ContractAmount) if contract.ContractAmount else 0
            contract_dop_amount = 0
            ParentPassport = "Данные паспорта недоступны"
            ParentPassportKAZ = "Паспорт деректері қолжетімсіз"
            ParentPassportENG = "Passport data unavailable"

        # Функция для замены переменных в тексте
        def replace_variables_in_text(text):
            """Заменяет все переменные в тексте"""
            try:
                # Основные данные контракта
                text = text.replace('{ContractNum}', str(contract.ContractNum) if contract.ContractNum else '')
                text = text.replace('{ContractYear}',
                                    str(contract.ContractDate.strftime("%Y")) if contract.ContractDate else '')
                text = text.replace('{ContractDate}',
                                    str(contract.ContractDate.strftime("%d.%m.%Y")) if contract.ContractDate else '')
                text = text.replace('{ContractDay}',
                                    str(contract.ContractDate.strftime("%d")) if contract.ContractDate else '')

                # Месяцы на разных языках
                if contract.ContractDate:
                    try:
                        from translate import Translator
                        month_ru = ChangeDocumentContentService.translate_text(contract.ContractDate.strftime("%B"),
                                                                               "ru")
                        month_kz = ChangeDocumentContentService.translate_text(contract.ContractDate.strftime("%B"),
                                                                               "kk")
                        month_en = ChangeDocumentContentService.translate_text(contract.ContractDate.strftime("%B"),
                                                                               "en")
                        text = text.replace('{ContractMonthRUS}', month_ru)
                        text = text.replace('{ContractMonthKAZ}', month_kz)
                        text = text.replace('{ContractMonthENG}', month_en)
                    except:
                        text = text.replace('{ContractMonthRUS}', contract.ContractDate.strftime("%B"))
                        text = text.replace('{ContractMonthKAZ}', contract.ContractDate.strftime("%B"))
                        text = text.replace('{ContractMonthENG}', contract.ContractDate.strftime("%B"))

                # Год окончания контракта
                if contract.ContractDate:
                    data_close = contract.ContractDate + timedelta(days=365)
                    text = text.replace('{ContractYearFinish}', str(data_close.strftime("%Y")))

                # Учебный год
                if contract.EduYearID:
                    text = text.replace('{EduYear}', str(contract.EduYearID.sEduYear))

                # Данные студента и родителя
                text = text.replace('{ParentFullName}', str(parent.full_name) if parent.full_name else '')
                text = text.replace('{StudentFullName}', str(student.full_name) if student.full_name else '')
                text = text.replace('{StudentIIN}', str(student.iin) if student.iin else '')
                text = text.replace('{StudentAddress}', str(parent.address) if parent.address else '')
                text = text.replace('{StudentPhoneNumber}', str(student.phone) if student.phone else '-')
                text = text.replace('{ParentAddress}', str(parent.address) if parent.address else '')
                text = text.replace('{ParentPhoneNumber}', str(parent.phone) if parent.phone else '')
                text = text.replace('{ParentIIN}', str(parent.iin) if parent.iin else '')

                # Данные паспорта
                text = text.replace('{ParentPassport}', ParentPassport)
                text = text.replace('{ParentPassportKAZ}', ParentPassportKAZ)
                text = text.replace('{ParentPassportENG}', ParentPassportENG)

                # Суммы контракта
                text = text.replace('{ContractAmount}',
                                    str(int(contract.ContractAmount)) if contract.ContractAmount else '0')
                text = text.replace('{ContractSum}', str(int(contract.ContractSum)) if contract.ContractSum else '0')
                text = text.replace('{ContractAmountWithDiscount}', str(int(contract_amount_with_discount)))

                # Суммы прописью
                try:
                    text = text.replace('{ContractAmountWords}', num2words(int(contract.ContractAmount),
                                                                           lang="ru") if contract.ContractAmount else '')
                    text = text.replace('{ContractAmountWordsKaz}', num2words(int(contract.ContractAmount),
                                                                              lang="kz") if contract.ContractAmount else '')
                    text = text.replace('{ContractAmountWordsEng}', num2words(int(contract.ContractAmount),
                                                                              lang="en") if contract.ContractAmount else '')
                    text = text.replace('{ContractSumWords}',
                                        num2words(int(contract.ContractSum), lang="ru") if contract.ContractSum else '')
                    text = text.replace('{ContractSumWordsKaz}',
                                        num2words(int(contract.ContractSum), lang="kz") if contract.ContractSum else '')
                    text = text.replace('{ContractSumWordsEng}',
                                        num2words(int(contract.ContractSum), lang="en") if contract.ContractSum else '')
                    text = text.replace('{ContractAmountWithDiscountWords}',
                                        num2words(int(contract_amount_with_discount), lang="ru"))
                    text = text.replace('{ContractAmountWithDiscountWordsKaz}',
                                        num2words(int(contract_amount_with_discount), lang="kz"))
                    text = text.replace('{ContractAmountWithDiscountWordsEng}',
                                        num2words(int(contract_amount_with_discount), lang="en"))
                except:
                    pass

                # Дополнительные суммы
                text = text.replace('{ContractDopAmount}', str(int(contract_dop_amount)))
                try:
                    text = text.replace('{ContractDopAmountWords}', num2words(int(contract_dop_amount), lang="ru"))
                    text = text.replace('{ContractDopAmountWordsKaz}', num2words(int(contract_dop_amount), lang="kz"))
                except:
                    pass

                # Взнос
                if contract.ContSum:
                    text = text.replace('{ContractContr}', str(int(contract.ContSum)))
                    try:
                        text = text.replace('{ContractContrWords}', num2words(int(contract.ContSum), lang="ru"))
                        text = text.replace('{ContractContrWordsKaz}', num2words(int(contract.ContSum), lang="kz"))
                        text = text.replace('{ContractContrWordsEng}', num2words(int(contract.ContSum), lang="en"))
                    except:
                        pass
                else:
                    text = text.replace('{ContractContr}', '0')
                    text = text.replace('{ContractContrWords}', 'ноль')
                    text = text.replace('{ContractContrWordsKaz}', 'нөл')
                    text = text.replace('{ContractContrWordsEng}', 'zero')

                # Тексты для QR-кодов
                text = text.replace('{QRCodeTextRus}',
                                    'QR-код содержит данные об электронно-цифровой подписи подписанта')
                text = text.replace('{QRCodeTextKaz}',
                                    'QR-кодта қол қоюшының электрондық-цифрлық қолтаңбасы туралы деректер қамтылады')
                text = text.replace('{police_kaz}',
                                    'Осы құжат «Электрондық құжат және электрондық цифрлық қолтаңба туралы» Қазақстан Республикасының 2003 жылғы 7 қаңтардағы N 370-II Заңы 7 бабының 1 тармағына сәйкес қағаз тасығыштағы құжатпен бірдей.')
                text = text.replace('{police_rus}',
                                    'Данный документ согласно пункту 1 статьи 7 ЗРК от 7 января 2003 года «Об электронном документе и электронной цифровой подписи» равнозначен документу на бумажном носителе.')

            except Exception as e:
                logger.error(f"Error in replace_variables_in_text: {e}")

            return text

        # Заменяем переменные и QR-коды в параграфах
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                # Сначала заменяем текстовые переменные
                if any(var in run.text for var in
                       ['{ContractNum}', '{StudentFullName}', '{ParentFullName}', '{ContractAmount}']):
                    run.text = replace_variables_in_text(run.text)

                # Затем обрабатываем QR-коды
                if '{QRCode}' in run.text or '{QRCodeSignature}' in run.text:
                    run.text = run.text.replace('{QRCode}', '').replace('{QRCodeSignature}', '')
                    if qr_signature:
                        image_stream = BytesIO(qr_signature)
                        run.add_picture(image_stream, width=Inches(1.5), height=Inches(1.5))

                if '{QRCodeDirectorOmarov}' in run.text or '{QRcodeDirector}' in run.text:
                    run.text = run.text.replace('{QRCodeDirectorOmarov}', '').replace('{QRcodeDirector}', '')
                    if qr_director_omarov:
                        image_stream = BytesIO(qr_director_omarov)
                        run.add_picture(image_stream, width=Inches(1.2), height=Inches(1.2))

                if '{QRCodeDirectorSerikov}' in run.text or '{QRCodeDirector2}' in run.text:
                    run.text = run.text.replace('{QRCodeDirectorSerikov}', '').replace('{QRCodeDirector2}', '')
                    if qr_director_serikov:
                        image_stream = BytesIO(qr_director_serikov)
                        run.add_picture(image_stream, width=Inches(1.2), height=Inches(1.2))

                # Специальные QR-коды
                if 'QRCodeDataSigned' in run.text:
                    # Генерируем QR-код с подписанными данными
                    qr_code_data_signed = self._generate_signed_data_qr_code(contract.ContractNum)
                    if qr_code_data_signed:
                        qr_code_image = BytesIO(qr_code_data_signed)
                        run.add_picture(qr_code_image, width=Inches(1.3), height=Inches(1.3))

        # Также обрабатываем таблицы
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            # Заменяем текстовые переменные в таблицах
                            if any(var in run.text for var in
                                   ['{ContractNum}', '{StudentFullName}', '{ParentFullName}', '{ContractAmount}']):
                                run.text = replace_variables_in_text(run.text)

                            # QR-коды в таблицах
                            if '{QRCode}' in run.text or '{QRCodeSignature}' in run.text:
                                run.text = run.text.replace('{QRCode}', '').replace('{QRCodeSignature}', '')
                                if qr_signature:
                                    image_stream = BytesIO(qr_signature)
                                    run.add_picture(image_stream, width=Inches(1.5), height=Inches(1.5))

                            # Обработка таблиц оплаты
                            if '{customtable_monthpay}' in run.text:
                                self._process_month_pay_table(cell, contract)
                                run.text = run.text.replace('{customtable_monthpay}', '')

                            if '{customtable_quarterpay}' in run.text:
                                self._process_quarter_pay_table(cell, contract)
                                run.text = run.text.replace('{customtable_quarterpay}', '')

    def _process_month_pay_table(self, cell, contract):
        """Обрабатывает таблицу помесячной оплаты"""
        try:
            from .models import ContractMonthPayMS, ContractDiscountMS, DiscountMS
            from docx.shared import Cm
            import math

            # Расчет суммы со скидкой
            discount = DiscountMS.objects.using('ms_sql').all()
            contract_discount = ContractDiscountMS.objects.using('ms_sql').filter(ContractID=contract)
            contract_amount = float(contract.ContractAmount)

            if contract_discount.exists():
                for i in contract_discount:
                    for j in discount.filter(id=i.DiscountID.id):
                        percent = int(j.iDiscountPercent)
                        contract_amount -= contract_amount * percent / 100
                contract_amount_with_discount = float(round(contract_amount, 2))
            else:
                contract_amount_with_discount = float(round(contract_amount, 2))

            # Создаем таблицу
            main_table = cell.add_table(rows=1, cols=3)
            main_table.columns[0].width = Cm(1.0)
            main_table.columns[1].width = Cm(3.0)
            main_table.columns[2].width = Cm(3.0)

            # Заголовки
            header_row = main_table.rows[0]
            header_row.cells[0].text = '№'
            header_row.cells[1].text = 'Сумма'
            header_row.cells[2].text = 'Дата оплаты'

            # Получаем данные о платежах
            contract_month_pays = ContractMonthPayMS.objects.using('ms_sql').filter(ContractID=contract.id)
            count_month = 9
            sum_for_month = math.ceil(contract_amount_with_discount / count_month)

            # Добавляем строки
            for j, pay in enumerate(contract_month_pays):
                row_cells = main_table.add_row().cells
                row_cells[0].text = str(j + 1)
                row_cells[1].text = f"{sum_for_month:,}".replace(',', ' ')
                row_cells[2].text = str(pay.PayDateM) if pay.PayDateM else ''

        except Exception as e:
            logger.error(f"Error processing month pay table: {e}")

    def _process_quarter_pay_table(self, cell, contract):
        """Обрабатывает таблицу квартальной оплаты"""
        try:
            from .models import ContractMonthPayMS, ContractDiscountMS, DiscountMS
            from docx.shared import Cm
            from django.db.models import Sum, Min
            import math

            # Расчет суммы со скидкой
            discount = DiscountMS.objects.using('ms_sql').all()
            contract_discount = ContractDiscountMS.objects.using('ms_sql').filter(ContractID=contract)
            contract_amount = float(contract.ContractAmount)

            if contract_discount.exists():
                for i in contract_discount:
                    for j in discount.filter(id=i.DiscountID.id):
                        percent = int(j.iDiscountPercent)
                        contract_amount -= contract_amount * percent / 100
                contract_amount_with_discount = float(round(contract_amount, 2))
            else:
                contract_amount_with_discount = float(round(contract_amount, 2))

            # Создаем таблицу
            main_table = cell.add_table(rows=1, cols=3)
            main_table.columns[0].width = Cm(1.0)
            main_table.columns[1].width = Cm(3.0)
            main_table.columns[2].width = Cm(3.0)

            # Заголовки
            header_row = main_table.rows[0]
            header_row.cells[0].text = '№'
            header_row.cells[1].text = 'Сумма'
            header_row.cells[2].text = 'Дата оплаты'

            # Получаем квартальные платежи
            contract_quarter_pays = ContractMonthPayMS.objects.using('ms_sql').filter(ContractID=contract.id)
            count_month = 9
            sum_for_month = math.ceil(contract_amount_with_discount / count_month)

            group_by_quarter = contract_quarter_pays.values('QuarterDig').annotate(
                MonthSum=Sum('MonthSum'), PayDateM=Min('PayDateM'))

            count_quarterdig = {}
            for quarter in group_by_quarter:
                count_quarterdig[quarter['QuarterDig']] = contract_quarter_pays.filter(
                    QuarterDig=quarter['QuarterDig']).count()

            # Добавляем строки
            for j, quarter in enumerate(group_by_quarter):
                quarter['MonthSum'] = round(sum_for_month * count_quarterdig[quarter['QuarterDig']], 2)
                row_cells = main_table.add_row().cells
                row_cells[0].text = str(j + 1)
                row_cells[1].text = str(quarter['MonthSum'])
                row_cells[2].text = str(quarter['PayDateM']) if quarter['PayDateM'] else ''

        except Exception as e:
            logger.error(f"Error processing quarter pay table: {e}")

    def _generate_signed_data_qr_code(self, contract_num):
        """Генерирует QR-код с данными подписанного договора"""
        try:
            from datetime import datetime

            qr_data = {
                "contract_num": contract_num,
                "signed_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "status": "Подписан",
                "verification_url": f"{self.frontend_url}/contracts/{contract_num}/signatures"
            }

            return self._create_qr_code(qr_data)

        except Exception as e:
            logger.error(f"Error generating signed data QR code: {e}")
            return b''

    def _get_contract_template(self, contract, is_dop_contract=False):
        """Получает шаблон контракта"""
        try:
            contract_payment_type = contract.PaymentTypeID.sPaymentType
            contract_school_language = getattr(contract.SchoolID, 'sSchool_language', '')
            contract_school_direct = getattr(contract.SchoolID, 'sSchool_direct', '')

            # Логика выбора шаблона из старого кода
            if contract_payment_type == 'Оплата по месячно':
                if contract_school_language == 'Казахское отделение':
                    if is_dop_contract:
                        return 'apps/contract/templates/contract/signed/Договор_оказания_дополнительных_образовательных_услуг_КАЗ_ОТД_ТОО_по_месячно.docx'
                    else:
                        return 'apps/contract/templates/contract/signed/Договор_оказания_образовательных_услуг_КАЗ_ОТД_ТОО_по_месячно.docx'
                else:
                    if contract_school_direct == 'Кембридж':
                        return 'apps/contract/templates/contract/signed/Договор оказания образовательных услуг Кэмбридж 2025-2026 УО_по_месячно.docx'
                    elif is_dop_contract:
                        if contract_school_direct == 'Лингвинистический':
                            return 'apps/contract/templates/contract/signed/Договор_оказания_дополнительных_образовательных_услуг_Лингво_2023_по_месячно.docx'
                        elif contract_school_direct in ['Физико-математический', 'Физико-Математическая']:
                            return 'apps/contract/templates/contract/signed/Договор_оказания_дополнительных_образовательных_услуг_Физмат_Нур_по_месячно.docx'
                        elif contract_school_direct == 'Американская школа Advanced Placement':
                            return 'apps/contract/templates/contract/signed/Договор_оказания_дополнительных_образовательных_услуг_AP_2023_2024_по_месячно.docx'
                        elif contract_school_direct == 'IT-школа на Кекилбайулы':
                            return 'apps/contract/templates/contract/signed/Договор_оказания_дополнительных_образовательных_услуг_IT_отделение_по_месячно.docx'
                        else:
                            return 'apps/contract/templates/contract/signed/Договор_оказания_образовательных_услуг_Школа_2023_2024_оплата_по_месячно.docx'
                    else:
                        return 'apps/contract/templates/contract/signed/Договор_оказания_образовательных_услуг_Школа_2023_2024_оплата_по_месячно.docx'

            # Добавьте другие варианты оплаты по необходимости
            print("Default contract template used")
            logger.info("Default contract template used")
            return 'apps/contract/templates/contract/Договор оказания образовательных услуг_Школа 2025-2026_за_год.docx'

        except Exception as e:
            logger.error(f"Error getting contract template: {e}")
            return None

    def _generate_base_contract(self, contract, user, is_dop_contract=False):
        """Генерирует базовый контракт если файл не существует"""
        # Используем существующую логику из ChangeDocumentContentService
        from .services import ChangeDocumentContentService

        change_doc_service = ChangeDocumentContentService()
        student = contract.StudentID
        parent = student.parent_id

        change_doc_service.change_content(
            request=None,  # Можно передать None если не используется
            contract_num=contract.ContractNum,
            contract=contract,
            student=student,
            parent=parent,
            is_dop_contract=is_dop_contract
        )

    def _docx_to_pdf(self, input_path, output_path):
        """Конвертация файла из формата DOCX в PDF"""
        command_strings = ['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', output_path, input_path]
        try:
            subprocess.call(command_strings)
        except subprocess.CalledProcessError as e:
            logger.error(f"Error converting DOCX to PDF: {e}")

    def _calculate_contract_hash(self, contract, is_dop_contract=False) -> str:
        """Вычисляет хэш контракта на основе его ключевых данных"""
        contract_data = (
            f"{contract.ContractNum}:"
            f"{contract.ContractAmount}:"
            f"{contract.ContractDate}:"
            f"{getattr(contract, 'StudentID_id', '')}:"
            f"{getattr(contract, 'ContractStatusID_id', '')}"
        )

        try:
            if is_dop_contract:
                file_obj = ContractDopFileUser.objects.filter(contractNum=contract.ContractNum).first()
            else:
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

    def _add_director_signature(self, contract_num: str, parent_signature: ContractSignature, document_hash: str):
        """Добавляет автоматическую подпись директора с правильным хэшем"""
        try:
            # Данные директора Омарова (заглушка - позже заполните реальными данными)
            director_omarov_data = {
                "iin": "000000000000",  # Заполните реальным ИИН
                "full_name": "ОМАРОВ",
                "position": "Директор",
                "certificate_info": {
                    "serial_number": "93af8264ee9fabcf9123ae0c4c2d1373c31cb126",
                    "common_name": "ОМАРОВ"
                }
            }

            # Создаем подпись директора с ТЕМ ЖЕ хэшем что и у родителя
            director_signature = ContractSignature.objects.create(
                contract_num=contract_num,
                cms_signature="",  # Заполните данными сертификата директора
                signed_data="",   # Заполните подписанными данными
                document_hash=document_hash,  # Используем ПЕРЕДАННЫЙ хэш
                signer_iin=director_omarov_data["iin"],
                certificate_info=director_omarov_data["certificate_info"],
                is_valid=True,
                created_by=None  # Системная подпись
            )

            logger.info(f"Director signature added for contract {contract_num} with hash {document_hash[:16]}...")

        except Exception as e:
            logger.error(f"Error adding director signature: {e}")

    # Остальные методы остаются такими же как в оригинальном коде...
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