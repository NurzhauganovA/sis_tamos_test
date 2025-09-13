import hashlib
import uuid

from django.core.validators import FileExtensionValidator
from django.db import models

from ..school.models import SchoolMS, School
from ..user.models import UserMS, User


class BankMS(models.Model):
    account = models.CharField(max_length=255, null=False)
    name = models.CharField(max_length=255, null=False)
    bik = models.CharField(max_length=255, null=False)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'spr_Bank'
        managed = False


class ParentMS(models.Model):
    """ Модель родителей """

    full_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, null=True)
    contacts = models.CharField(max_length=255, null=True)
    email = models.EmailField(null=True)
    iin = models.CharField(max_length=12, null=True)
    is_teacher = models.BooleanField(default=False)
    num_of_doc = models.CharField(max_length=255, null=True)
    issued_by = models.CharField(max_length=255, null=True)
    issue_date = models.DateField(null=True)
    phone = models.CharField(max_length=20, null=True)
    work_place = models.CharField(max_length=255, null=True)
    work_position = models.CharField(max_length=255, null=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name

    class Meta:
        db_table = 't_Parents'
        managed = False


class StudentMS(models.Model):
    """ Модель студентов """

    birthday = models.DateField()
    full_name = models.CharField(max_length=255)
    iin = models.CharField(max_length=12, null=True)
    leave = models.DateField(null=True)
    reason_leave = models.CharField(max_length=255, null=True)
    parent_id = models.ForeignKey(ParentMS, on_delete=models.SET_NULL, null=True, db_column='parent_id')
    sex = models.PositiveSmallIntegerField(null=True)
    email = models.EmailField(null=True)
    phone = models.CharField(max_length=20, null=True)

    def __str__(self):
        return self.full_name

    class Meta:
        db_table = 't_Students'
        managed = False


class PaymentTypeMS(models.Model):
    """ Модель типов оплаты """

    sPaymentType = models.CharField(max_length=255, null=True)

    def __str__(self):
        return self.sPaymentType

    class Meta:
        db_table = 'spr_PaymentType'
        managed = False


class ContractStatusMS(models.Model):
    """ Модель статусов контракта """

    sStatusName = models.CharField(max_length=255, null=True)

    def __str__(self):
        return self.sStatusName

    class Meta:
        db_table = 'spr_Status'
        managed = False


class CompanyMS(models.Model):
    """ Модель компаний """

    address = models.CharField(max_length=255, null=True)
    name = models.CharField(max_length=255, null=True)
    bank = models.CharField(max_length=255, null=True)
    bik = models.CharField(max_length=255, null=True)
    bin = models.CharField(max_length=255, null=True)
    iik = models.CharField(max_length=255, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'spr_Company'
        managed = False


class EduYearMS(models.Model):
    """ Модель учебных годов """

    sEduYear = models.CharField(max_length=255, null=True)
    isActive = models.BooleanField(default=True)

    def __str__(self):
        return self.sEduYear

    class Meta:
        db_table = 'spr_EduYear'
        managed = False


class ClassMS(models.Model):
    """ Модель классов """

    from ..school.models import SchoolMS

    school_id = models.ForeignKey(SchoolMS, on_delete=models.SET_NULL, null=True, db_column='school_id')
    class_num = models.CharField(max_length=255, null=True)
    class_liter = models.CharField(max_length=5, null=True)
    commentary = models.CharField(max_length=255, null=True)
    isActive = models.BooleanField(default=True)

    def __str__(self):
        return self.class_num

    class Meta:
        db_table = 'spr_Classes'
        managed = False


class DiscountTypeMS(models.Model):
    """ Модель типов скидок """

    sDiscountType = models.CharField(max_length=255, null=True)
    sCommentary = models.CharField(max_length=255, null=True)

    def __str__(self):
        return self.sDiscountType

    class Meta:
        db_table = 'spr_DiscountType'
        managed = False


class DiscountMS(models.Model):
    """ Модель скидок """

    sDiscountName = models.CharField(max_length=255, null=True)
    iDiscountPercent = models.PositiveIntegerField(null=True)
    iDiscountType = models.ForeignKey(DiscountTypeMS, on_delete=models.SET_NULL, null=True, related_name='discount_type', db_column='iDiscountType')
    sCommentary = models.CharField(max_length=255, null=True)
    bIsActive = models.BooleanField(default=True)

    def __str__(self):
        return self.sDiscountName

    class Meta:
        db_table = 'spr_Discount'
        managed = False


class ContractMS(models.Model):
    """ Модель контрактов """

    StudentID = models.ForeignKey(StudentMS, on_delete=models.SET_NULL, null=True, db_column='StudentID')
    ContractDate = models.DateField(null=True)
    ContractDateClose = models.DateField(null=True)
    ContractNum = models.CharField(max_length=255, null=True)
    ContractAmount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PaymentTypeID = models.ForeignKey(PaymentTypeMS, on_delete=models.SET_NULL, null=True, db_column='PaymentTypeID')
    ContractStatusID = models.ForeignKey(ContractStatusMS, on_delete=models.SET_NULL, null=True, db_column='ContractStatusID')
    ContractSum = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    CompanyID = models.ForeignKey(CompanyMS, on_delete=models.SET_NULL, null=True, db_column='CompanyID')
    EduYearID = models.ForeignKey(EduYearMS, on_delete=models.SET_NULL, null=True, db_column='EduYearID')
    Contribution = models.PositiveSmallIntegerField(null=True)
    ContSum = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    SchoolID = models.ForeignKey(SchoolMS, on_delete=models.SET_NULL, null=True, db_column='SchoolID')
    ClassID = models.ForeignKey(ClassMS, on_delete=models.SET_NULL, null=True, db_column='ClassID')
    DiscountID = models.ForeignKey(DiscountMS, on_delete=models.SET_NULL, null=True, related_name='discount', db_column='DiscountID')
    signature_uid = models.CharField(max_length=255, null=True)

    @property
    def has_valid_signatures(self):
        """Проверяет есть ли валидные подписи и не изменился ли документ"""
        signatures = self.signatures.filter(is_valid=True)

        for signature in signatures:
            if signature.is_document_modified:
                # Если документ изменился, помечаем подпись как невалидную
                signature.is_valid = False
                signature.save()
                return False

        return signatures.exists()

    @property
    def signature_status(self):
        """Возвращает статус подписания контракта"""
        if not self.signatures.exists():
            return "not_signed"

        valid_signatures = self.signatures.filter(is_valid=True)

        if not valid_signatures.exists():
            return "invalid"

        # Проверяем не изменился ли документ
        for signature in valid_signatures:
            if signature.is_document_modified:
                signature.is_valid = False
                signature.save()
                return "document_modified"

        return "signed"

    def __str__(self):
        return self.ContractNum

    class Meta:
        db_table = 't_Contract'
        managed = False


class ContractDopMS(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    description = models.CharField(max_length=255, null=True)
    is_increase = models.BooleanField(default=False)
    agreement_id = models.ForeignKey(ContractMS, on_delete=models.SET_NULL, null=True, db_column='agreement_id')
    user_id = models.ForeignKey(UserMS, on_delete=models.SET_NULL, null=True, db_column='user_id')
    dop_contr_date = models.DateField(null=True)
    status_id = models.ForeignKey(ContractStatusMS, on_delete=models.SET_NULL, null=True, db_column='status_id')

    def __str__(self):
        return f'{self.description} - {self.amount} - {self.status_id}'

    class Meta:
        db_table = 't_ContractDop'
        managed = False


class ContractMonthPayMS(models.Model):
    ContractID = models.ForeignKey(ContractMS, on_delete=models.SET_NULL, null=True, db_column='ContractID')
    PayDateM = models.DateField(auto_now=True, null=True)
    MonthAmount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    MonthSum = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    IsClosedContract = models.BooleanField(default=False)
    DateClosed = models.DateField(null=True)
    QuarterDig = models.PositiveSmallIntegerField(null=True)

    def __str__(self):
        return f'{self.ContractID} - {self.PayDateM} - {self.MonthSum}'

    class Meta:
        db_table = 't_ContractMonthPay'
        managed = False


class TransactionMS(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    description = models.CharField(max_length=255, null=True)
    is_increase = models.BooleanField(default=True)
    payment_type = models.ForeignKey(PaymentTypeMS, on_delete=models.SET_NULL, null=True, db_column='payment_type')
    agreement_id = models.ForeignKey(ContractMS, on_delete=models.SET_NULL, null=True, db_column='agreement_id')
    user_id = models.ForeignKey(UserMS, on_delete=models.SET_NULL, null=True, db_column='user_id')
    name = models.CharField(max_length=255, null=True)
    contribution = models.BooleanField(default=False)
    trans_date = models.DateTimeField(auto_now=True, null=True)
    bank_id = models.ForeignKey(BankMS, on_delete=models.SET_NULL, null=True, db_column='bank_id')
    is_dop_contr = models.BooleanField(default=False, null=True)
    dop_contr_date = models.DateTimeField(null=True)

    def __str__(self):
        return f'{self.description} - {self.amount}'

    class Meta:
        db_table = 't_Transaction'
        managed = False


class ContractDiscountMS(models.Model):
    ContractID = models.ForeignKey(ContractMS, on_delete=models.SET_NULL, null=True, db_column='ContractID')
    DiscountID = models.ForeignKey(DiscountMS, on_delete=models.SET_NULL, null=True, db_column='DiscountID')
    DiscountSum = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def __str__(self):
        return f'{self.ContractID} --- {self.DiscountID} --- {self.DiscountSum}'

    class Meta:
        db_table = 't_ContractDiscount'
        managed = False


class ContractFoodMS(models.Model):
    """ Модель контрактов на питание """

    StudentID = models.ForeignKey(StudentMS, on_delete=models.SET_NULL, null=True, db_column='StudentID')
    ContractDate = models.DateField(auto_now=True, null=True)
    ContractDateClose = models.DateField(auto_now=True, null=True)
    ContractNum = models.CharField(max_length=255)
    ContractAmount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ContractSum = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PaymentTypeID = models.ForeignKey(PaymentTypeMS, on_delete=models.SET_NULL, null=True, db_column='PaymentTypeID')
    ContractStatusID = models.ForeignKey(ContractStatusMS, on_delete=models.SET_NULL, null=True, db_column='ContractStatusID')
    EduYearID = models.ForeignKey(EduYearMS, on_delete=models.SET_NULL, null=True, db_column='EduYearID')
    SchoolID = models.ForeignKey(SchoolMS, on_delete=models.SET_NULL, null=True, db_column='SchoolID')
    ClassID = models.ForeignKey(ClassMS, on_delete=models.SET_NULL, null=True, db_column='ClassID')
    signature_uid = models.CharField(max_length=255, null=True)
    Comment = models.CharField(max_length=255, null=True)

    def __str__(self):
        return f'{self.ContractNum}'

    class Meta:
        db_table = 't_ContractFood'
        managed = False


class ContractFoodMonthPayMS(models.Model):
    ContractID = models.ForeignKey(ContractFoodMS, on_delete=models.SET_NULL, null=True, db_column='ContractID')
    PayDateM = models.DateField(auto_now=True, null=True)
    MonthAmount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    MonthSum = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    IsClosedContract = models.BooleanField(default=False)
    DateClosed = models.DateField(null=True)

    def __str__(self):
        return f'{self.ContractID} - {self.PayDateM} - {self.MonthSum}'

    class Meta:
        db_table = 't_ContractMonthPayFood'
        managed = False


class TransactionFoodMS(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    description = models.CharField(max_length=255, null=True)
    contract_id = models.ForeignKey(ContractFoodMS, on_delete=models.SET_NULL, null=True, db_column='contract_id')
    user_id = models.ForeignKey(UserMS, on_delete=models.SET_NULL, null=True, db_column='user_id')
    trans_date = models.DateTimeField(auto_now=True, null=True)
    Akt_status = models.CharField(max_length=255, null=True)
    bank_id = models.ForeignKey(BankMS, on_delete=models.SET_NULL, null=True, db_column='bank_id')

    def __str__(self):
        return f'{self.description} - {self.amount}'

    class Meta:
        db_table = 't_TransactionFood'
        managed = False


class ContractFoodDiscountMS(models.Model):
    ContractID = models.ForeignKey(ContractFoodMS, on_delete=models.SET_NULL, null=True, db_column='ContractID')
    DiscountID = models.ForeignKey(DiscountMS, on_delete=models.SET_NULL, null=True, db_column='DiscountID')
    DiscountSum = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def __str__(self):
        return f'{self.ContractID} --- {self.DiscountID} --- {self.DiscountSum}'

    class Meta:
        db_table = 't_ContractFoodDiscount'
        managed = False


class ContractDriverMS(models.Model):
    """ Модель контрактов на развозку """

    StudentID = models.ForeignKey(StudentMS, on_delete=models.SET_NULL, null=True, db_column='StudentID')
    ContractDate = models.DateField(auto_now=True, null=True)
    ContractDateClose = models.DateField(auto_now=True, null=True)
    ContractNum = models.CharField(max_length=255)
    ContractAmount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ContractAmountDis = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    PaymentTypeID = models.ForeignKey(PaymentTypeMS, on_delete=models.SET_NULL, null=True, db_column='PaymentTypeID')
    ContractStatusID = models.ForeignKey(ContractStatusMS, on_delete=models.SET_NULL, null=True, db_column='ContractStatusID')
    EduYearID = models.ForeignKey(EduYearMS, on_delete=models.SET_NULL, null=True, db_column='EduYearID')
    SchoolID = models.ForeignKey(SchoolMS, on_delete=models.SET_NULL, null=True, db_column='SchoolID')
    ClassID = models.ForeignKey(ClassMS, on_delete=models.SET_NULL, null=True, db_column='ClassID')
    DiscountID = models.ForeignKey(DiscountMS, on_delete=models.SET_NULL, null=True, db_column='DiscountID')
    signature_uid = models.CharField(max_length=255, null=True)

    def __str__(self):
        return f'{self.ContractNum}'

    class Meta:
        db_table = 't_ContractDriver'
        managed = False


class ContractDriverMonthPayMS(models.Model):
    ContractID = models.ForeignKey(ContractDriverMS, on_delete=models.SET_NULL, null=True, db_column='ContractID')
    PayDateM = models.DateField(auto_now=True, null=True)
    MonthAmount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    MonthAmountDisc = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    IsClosedContract = models.BooleanField(default=False)
    DateClosed = models.DateField(null=True)
    QuarterDig = models.PositiveSmallIntegerField(null=True)

    def __str__(self):
        return f'{self.ContractID} - {self.PayDateM} - {self.MonthAmount}'

    class Meta:
        db_table = 't_ContractMonthPayDriver'
        managed = False


class TransactionDriverMS(models.Model):
    ContractID = models.ForeignKey(ContractDriverMS, on_delete=models.SET_NULL, null=True, db_column='ContractID')
    Amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    Description = models.CharField(max_length=255, null=True)
    TransactionDate = models.DateTimeField(auto_now=True, null=True)
    UserID = models.ForeignKey(UserMS, on_delete=models.SET_NULL, null=True, db_column='UserID')
    BankID = models.ForeignKey(BankMS, on_delete=models.SET_NULL, null=True, db_column='BankID')

    def __str__(self):
        return f'{self.Description} - {self.Amount}'

    class Meta:
        db_table = 't_TransactionDrive'
        managed = False


class ContractFileUser(models.Model):

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, db_column='user')
    contractNum = models.CharField(max_length=255, null=True)
    file = models.FileField(upload_to='contract/files/', null=False)
    date = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f'{self.contractNum} - {self.file}'

    class Meta:
        db_table = 'ContractFileUser'


class ContractDopFileUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, db_column='user')
    contractNum = models.CharField(max_length=255, null=True)
    file = models.FileField(upload_to='contract_dop/files/', null=False)
    date = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f'{self.contractNum} - {self.file}'

    class Meta:
        db_table = 'ContractDopFileUser'


class RawContractTemplate(models.Model):
    """Шаблон контракта, в который нужно вставить переменные."""

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='raw_contract_templates'
    )
    file = models.FileField(
        upload_to='templates/contracts/raw/',
        validators=[FileExtensionValidator(['doc', 'docx'])]
    )
    created_at = models.DateTimeField(verbose_name='Время создания', auto_now_add=True)
    changed_at = models.DateTimeField(verbose_name='Время изменения', auto_now=True)
    name = models.CharField(
        verbose_name='Название шаблона', max_length=200, null=False, blank=False
    )

    def __str__(self):
        return f'{self.school.sSchool_name} - {self.file.name}'

    class Meta:
        db_table = 'raw_contract_template'


class MarkedUpContractTemplate(models.Model):
    """Размеченный шаблон контракта, готовый для использования."""

    raw_contract_template = models.ForeignKey(
        RawContractTemplate,
        on_delete=models.SET_NULL,
        related_name='marked_up_contracts',
        null=True
    )
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name='marked_up_contracts'
    )
    file = models.FileField(upload_to='templates/contracts/markedup/')
    created_at = models.DateTimeField(verbose_name='Время создания', auto_now_add=True)
    changed_at = models.DateTimeField(verbose_name='Время изменения', auto_now=True)
    name = models.CharField(
        verbose_name='Название размеченного шаблона', max_length=200, null=False, blank=False
    )

    def __str__(self):
        return f'{self.school.sSchool_name} - {self.file.name}'

    class Meta:
        db_table = 'marked_up_contract_template'


class ContractSignature(models.Model):
    """Модель для хранения подписей контрактов"""

    # Ссылка на контракт через номер (НЕ изменяем ContractMS!)
    contract_num = models.CharField(
        max_length=255,
        verbose_name='Номер контракта',
        help_text='Номер контракта из ContractMS.ContractNum'
    )

    # Данные подписи
    cms_signature = models.TextField(
        verbose_name='CMS подпись',
        help_text='Подпись в формате CMS'
    )

    # Данные которые были подписаны (base64)
    signed_data = models.TextField(
        verbose_name='Подписанные данные',
        help_text='Base64 данные которые были подписаны'
    )

    # Контрольная сумма документа на момент подписания
    document_hash = models.CharField(
        max_length=64,
        verbose_name='Хэш документа',
        help_text='SHA256 хэш документа на момент подписания',
        null=True,
        blank=True
    )

    # ИИН подписанта
    signer_iin = models.CharField(
        max_length=12,
        verbose_name='ИИН подписанта',
        help_text='ИИН извлеченный из сертификата'
    )

    # Информация о сертификате
    certificate_info = models.JSONField(
        default=dict,
        verbose_name='Информация о сертификате',
        help_text='Данные сертификата из NCANode ответа'
    )

    # Статус подписи
    is_valid = models.BooleanField(
        default=True,
        verbose_name='Подпись валидна',
        help_text='Результат валидации подписи'
    )

    # Временные метки
    signed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата подписания'
    )

    verified_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последней проверки'
    )

    # Дополнительные поля
    signature_uid = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='Уникальный ID подписи'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_signatures',
        verbose_name='Создано пользователем'
    )

    class Meta:
        db_table = 'contract_signatures'
        verbose_name = 'Подпись контракта'
        verbose_name_plural = 'Подписи контрактов'
        ordering = ['-signed_at']
        # Индекс для быстрого поиска по номеру контракта
        indexes = [
            models.Index(fields=['contract_num']),
            models.Index(fields=['signer_iin']),
            models.Index(fields=['is_valid']),
        ]

    def __str__(self):
        return f'Подпись {self.signature_uid} для контракта {self.contract_num}'

    @property
    def contract(self):
        """Получает связанный контракт через номер"""
        try:
            return ContractMS.objects.using('ms_sql').get(ContractNum=self.contract_num)
        except ContractMS.DoesNotExist:
            return None

    @property
    def is_document_modified(self):
        """Проверяет не был ли изменен документ после подписания"""
        if not self.document_hash:
            return False

        contract = self.contract
        if not contract:
            return True

        current_hash = self._calculate_contract_hash(contract)
        return current_hash != self.document_hash

    @staticmethod
    def _calculate_contract_hash(contract):
        """Вычисляет хэш контракта на основе его ключевых данных"""
        # Используем ключевые поля контракта для хэша
        contract_data = (
            f"{contract.ContractNum}:"
            f"{contract.ContractAmount}:"
            f"{contract.ContractDate}:"
            f"{contract.StudentID_id}:"
            f"{contract.ContractStatusID_id}"
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
        except Exception:
            pass

        return hashlib.sha256(contract_data.encode()).hexdigest()

    @classmethod
    def get_contract_signatures(cls, contract_num):
        """Получает все подписи для контракта"""
        return cls.objects.filter(contract_num=contract_num).order_by('-signed_at')

    @classmethod
    def has_valid_signatures(cls, contract_num):
        """Проверяет есть ли валидные подписи для контракта"""
        signatures = cls.get_contract_signatures(contract_num).filter(is_valid=True)

        # Проверяем каждую подпись на изменение документа
        for signature in signatures:
            if signature.is_document_modified:
                signature.is_valid = False
                signature.save()

        return cls.get_contract_signatures(contract_num).filter(is_valid=True).exists()

    @classmethod
    def get_signature_status(cls, contract_num):
        """Возвращает статус подписания контракта"""
        signatures = cls.get_contract_signatures(contract_num)

        if not signatures.exists():
            return "not_signed"

        valid_signatures = signatures.filter(is_valid=True)

        if not valid_signatures.exists():
            return "invalid"

        # Проверяем не изменился ли документ
        for signature in valid_signatures:
            if signature.is_document_modified:
                signature.is_valid = False
                signature.save()
                return "document_modified"

        return "signed"