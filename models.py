from django.db import models
from django.utils import timezone


class DOAJDeposit(models.Model):
    article = models.ForeignKey(
        "submission.Article", on_delete=models.SET_NULL,
        blank=True, null=True,
    )
    identifier = models.CharField(max_length=255,blank=True, null=True)
    success = models.BooleanField(default=False)
    result_text = models.TextField(blank=True, null=True)
    date_time = models.DateTimeField(default=timezone.now)
