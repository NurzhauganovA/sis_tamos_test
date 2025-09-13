from django.db import models

from apps.contract.models import ContractMS


class KaspiTransactionMS(models.Model):
    clazz = models.CharField(max_length=255, blank=True, null=True)
    contract_id = models.ForeignKey(ContractMS, on_delete=models.SET_NULL, blank=True, null=True, db_column='contract_id')
    transaction_id = models.IntegerField()
    txn_id = models.IntegerField()
    date = models.DateTimeField(auto_now_add=True)
    sum = models.IntegerField()

    class Meta:
        verbose_name = 'Kaspi Transaction'
        verbose_name_plural = 'Kaspi Transactions'
        db_table = 'kaspi_transactions'
        managed = False
