from django.db import models
from django.utils import timezone


class DOAJDeposit(models.Model):
    identifier = models.ForeignKey(
        "identifiers.Identifier", on_delete=models.CASCADE)
    exported = models.DateTimeField(blank=True, null=True)
    last_updated = models.DateTimeField(blank=True, null=True)
    success = models.BooleanField(default=False)
    result_text = models.TextField(blank=True, null=True)
    date_time = models.DateTimeField(default=timezone.now)
