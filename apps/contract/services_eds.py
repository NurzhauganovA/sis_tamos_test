import datetime

from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from django.core.files import File
from django.http import HttpResponse, JsonResponse
import qrcode
from xml.etree import ElementTree as ET
from io import BytesIO
from cryptography.hazmat.primitives.serialization import pkcs12
from Crypto.Hash import SHA256
import base64

from rest_framework import status
from rest_framework.response import Response

from apps.contract.models import ContractFileUser, ContractMS, ContractStatusMS, ContractFoodMS, ContractDriverMS, \
    ContractDopMS, ContractDopFileUser
from apps.contract.services import ContractDownloadService
from project_sis import settings


class SignContractWithEDSService:
    """
    Подпись договора с помощью ЭЦП
    Генерировать QR-код с данными подписи
    Использовать логику из документации ncanode.kz
    """

    def __init__(self, contract):
        self.contract = contract

    @staticmethod
    def get_certificate(request) -> bytes:
        """ Получить сертификат в формате .p12 """

        try:
            certificate = request.FILES['certificate']
        except KeyError:
            raise ValueError("Необходимо прикрепить сертификат для подписи договора")

        if certificate.name.startswith('AUTH'):
            raise ValueError("Вы должны прикрепить RSA сертификат для подписи договора")

        elif not certificate.name.endswith('.p12'):
            raise ValueError("Сертификат должен быть в формате .p12")

        return certificate.read()

    @staticmethod
    def check_verify_of_certificate(before_time, after_time):
        """ Проверка сертификата на валидность """

        date_today = datetime.datetime.now().date()
        if before_time.date() > date_today or after_time.date() < date_today:
            raise ValueError("Срок действия сертификата истек")
        else:
            return True

    @staticmethod
    def notification_user_about_certificate_expiration(before_time):
        """
            Уведомление пользователя о скором истечении срока действия сертификата.
            Уведомим пользователя за 2 недели до истечения срока действия сертификата
        """

        date_today = datetime.datetime.now().date()
        expiration_date = (before_time.date() - date_today).days

        if expiration_date <= 14:
            notification_text = f"Хотим уведомить вас о том, что срок действия вашего сертификата истечет через {expiration_date} дней"
            return notification_text

    def get_private_key(self, certificate_data, password: str):
        """ Получение закрытого ключа из сертификата в формате .p12 """

        try:
            private_key = pkcs12.load_key_and_certificates(certificate_data, password.encode())
            self.check_verify_of_certificate(private_key[1].not_valid_before, private_key[1].not_valid_after)
            return private_key
        except Exception as e:
            raise ValueError(f'{e}')

    @staticmethod
    def get_hash(contract_num: str):
        """ Получение хэша договора """
        hash_key = SHA256.new(contract_num.encode())
        return hash_key.digest()

    @staticmethod
    def get_signature(private_key, hash_key):
        """ Получение подписи договора """
        signature = private_key.sign(
            hash_key,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature

    @staticmethod
    def get_signature_base64(signature):
        """ Получение подписи договора в формате base64 """
        signature_base64 = base64.b64encode(signature)
        return signature_base64

    @staticmethod
    def data_to_xml(data):
        """
            Преобразование данных в формат XML.
            Solve error: All strings must be XML compatible: Unicode or ASCII, no NULL bytes or control characters.
        """

        root = ET.Element("Certificate")

        for key, value in data.items():
            ET.SubElement(root, key).text = str(value)

        xml_data = ET.tostring(root, encoding="utf-8").decode("utf-8")

        return xml_data

    def generate_qr_code_directors(self, request, contract_num, certificate, password):
        """ Генерация QR-кода директора """

        data = self.get_data(request, contract_num, certificate, password)

        xml_data = self.data_to_xml(data)

        qr_code = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )

        qr_code.add_data(xml_data)
        qr_code.make(fit=True)

        img = qr_code.make_image(fill_color="black", back_color="white")

        buffered = BytesIO()
        img.save(buffered)

        return buffered.getvalue()

    def generate_qr_code_omarov_to_signed_contract(self, request, contract_num):
        """ Добавить QR-код директора(Омаров) к подписанному договору """

        certificate_path = 'eds/Omarov/AUTH_RSA256_93af8264ee9fabcf9123ae0c4c2d1373c31cb126.p12'

        certificate = open(certificate_path, 'rb').read()
        password = str(settings.EDS_OMAROV_KEY)

        qr_code = self.generate_qr_code_directors(request, contract_num, certificate, password)

        return qr_code

    def generate_qr_code_serikov_to_signed_contract(self, request, contract_num):
        """ Добавить QR-код директора(Сериков) к подписанному договору """

        certificate_path = 'eds/Serikov/AUTH_RSA256_ac509efd146861ebcba1a4c0ceca04df1fd1ac1b.p12'

        certificate = open(certificate_path, 'rb').read()
        password = str(settings.EDS_SERIKOV_KEY)

        qr_code = self.generate_qr_code_directors(request, contract_num, certificate, password)

        return qr_code

    def generate_qr_code(self, request, data, is_dop_contract):
        """
            Генерация QR-кода с данными подписи
            Изображение QR-кода сохраняется в формате SVG
        """

        qr_code = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )

        qr_code.add_data(data)
        qr_code.make(fit=True)

        img = qr_code.make_image(fill_color="black", back_color="white")

        buffered = BytesIO()

        img.save(buffered)

        qr_code_director_omarov = self.generate_qr_code_omarov_to_signed_contract(request, contract_num=f'{self.contract}')
        qr_code_director_serikov = self.generate_qr_code_serikov_to_signed_contract(request, contract_num=f'{self.contract}')

        try:
            contract_download_service = ContractDownloadService(contract_student=self.contract)
            contract_download_service.generate_contract_with_qr_code(request,
                                                                     contract_num=f'{self.contract}',
                                                                     qr_code=buffered.getvalue(),
                                                                     qr_code_director_omarov=qr_code_director_omarov,
                                                                     qr_code_director_serikov=qr_code_director_serikov,
                                                                     is_dop_contract=is_dop_contract)
        except Exception as e:
            raise ValueError(f'{e}')

        return HttpResponse(buffered.getvalue(), content_type="image/svg+xml")

    def generate_qr_code_data_signed(self, contract_num):
        """ Генерация QR-кода с данными подписанного договора """

        qr_code = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1
        )

        data = {
            "contract_num": f"{contract_num}",
            "signed_date": f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "status": "Подписан",
        }

        try:
            data['contract_sum'] = f"{self.contract.ContractSum}"
        except AttributeError:
            data['contract_amount'] = f"{self.contract.ContractAmount}"

        qr_code.add_data(data)
        qr_code.make(fit=True)

        img = qr_code.make_image(fill_color="black", back_color="white")

        buffered = BytesIO()

        img.save(buffered)

        return buffered.getvalue()

    def get_data(self, request, contract_num, certificate, password):
        """ Получение данных для подписи договора """

        try:
            certificate = certificate
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            password = password
        except KeyError:
            return Response({"error": "Необходимо указать пароль от сертификата"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            private_key = self.get_private_key(certificate, password)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            public_key = private_key[1]
            subject = public_key.subject
            issuer = public_key.issuer

            data = dict(VALID="TRUE",
                        CONTRACT_NUMBER=str(contract_num),
                        SERIAL_NUMBER=str(public_key.serial_number),
                        COMMON_NAME=str(subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value),
                        INN=str(subject.get_attributes_for_oid(NameOID.SERIAL_NUMBER)[0].value),
                        ISSURE_COMMON_NAME=str(issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value),
                        NOTIFICATION_TEXT=self.notification_user_about_certificate_expiration(public_key.not_valid_after))
            return data

        except TypeError:
            return {'error': 'Не правильно сформирован данные сертификата или их вообще отсутствует!'}

    def check_data_user_certificate(self, request, contract_num):

        try:
            certificate = self.get_certificate(request)
        except ValueError as e:
            print(f'Exception -> get_certificate(): {e}')
            return JsonResponse({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

        try:
            password = request.data['password']
        except KeyError:
            return JsonResponse({"error": str('Необходимо указать пароль от сертификата')}, status=status.HTTP_403_FORBIDDEN)

        try:
            self.get_private_key(certificate, password)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

        data = self.get_data(request, contract_num, certificate, password)

        return JsonResponse(data, status=status.HTTP_200_OK, safe=False)

    def sign_contract_document(self, request, contract_num, is_dop_contract) -> HttpResponse | Response:
        """ Подпись договора """

        try:
            certificate = self.get_certificate(request)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

        try:
            password = request.data['password']
        except KeyError:
            return Response({"error": str('Необходимо указать пароль от сертификата')}, status=status.HTTP_403_FORBIDDEN)

        try:
            self.get_private_key(certificate, password)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)

        data = self.get_data(request, contract_num, certificate, password)

        xml_data = self.data_to_xml(data)

        if is_dop_contract:
            try:
                contract = ContractDopMS.objects.using('ms_sql').get(agreement_id__ContractNum=contract_num).agreement_id
            except ContractDopMS.DoesNotExist:
                return Response({'error': 'Договор не найден!'}, status=status.HTTP_403_FORBIDDEN)
        else:
            try:
                contract = ContractMS.objects.using('ms_sql').get(ContractNum=contract_num)
            except ContractMS.DoesNotExist:
                try:
                    contract = ContractFoodMS.objects.using('ms_sql').get(ContractNum=contract_num)
                except ContractFoodMS.DoesNotExist:
                    try:
                        contract = ContractDriverMS.objects.using('ms_sql').get(ContractNum=contract_num)
                    except ContractDriverMS.DoesNotExist:
                        contract = None

        if is_dop_contract:
            contract_dop = ContractDopMS.objects.using('ms_sql').get(agreement_id__ContractNum=contract_num)
            try:
                contract_dop_status = contract_dop.status_id.sStatusName
            except AttributeError:
                contract_dop_status = None

            if contract_dop_status is not None and contract_dop_status == 'На рассмотрении':
                try:
                    qr_code = self.generate_qr_code(request, {"data": xml_data},
                                                    is_dop_contract=is_dop_contract)
                except Exception as e:
                    return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({'error': 'Текущий статус договора должен быть - «На рассмотрении»'}, status=status.HTTP_403_FORBIDDEN)

        else:
            if contract.ContractStatusID.sStatusName == 'На рассмотрении' and contract is not None:
                try:
                    qr_code = self.generate_qr_code(request, {xml_data}, is_dop_contract=is_dop_contract)
                except Exception as e:
                    return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
            else:
                print('Текущий статус договора должен быть - «На рассмотрении»')
                return Response({'error': 'Текущий статус договора должен быть - «На рассмотрении»'}, status=status.HTTP_403_FORBIDDEN)

        if not qr_code:
            print('Ошибка при генерации QR-кода')
            return Response({"error": "Ошибка при генерации QR-кода"}, status=status.HTTP_403_FORBIDDEN)

        if is_dop_contract:
            contract_dop = ContractDopMS.objects.using('ms_sql').get(agreement_id__ContractNum=contract_num)
            contract_dop_status = contract_dop.status_id.sStatusName
            if contract_dop_status is not None and contract_dop_status == 'На рассмотрении':
                contract_dop.status_id = ContractStatusMS.objects.using('ms_sql').get(sStatusName='Подписан')
                contract_dop.save()
        else:
            if contract is not None:
                if contract.ContractStatusID.sStatusName != 'На рассмотрении':
                    print('Текущий статус договора должен быть - «На рассмотрении»')
                    return Response({'error': 'Текущий статус договора должен быть - «На рассмотрении»'}, status=status.HTTP_403_FORBIDDEN)
                contract.ContractStatusID = ContractStatusMS.objects.using('ms_sql').get(sStatusName='Подписан')
                contract.save()
            else:
                print('Договор не найден!')
                return Response({'error': 'Договор не найден!'}, status=status.HTTP_403_FORBIDDEN)

        if is_dop_contract:
            signed_contract = ContractDopFileUser.objects.filter(contractNum=contract_num).last().file.path
        else:
            signed_contract = ContractFileUser.objects.filter(contractNum=contract_num).last().file.path

        with open(signed_contract, 'rb') as file:
            response = HttpResponse(File(file), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{contract_num}.pdf"'
            return response
