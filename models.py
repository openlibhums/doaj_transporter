from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone
from submission import models as sm_models


class DOAJDeposit(models.Model):
    article = models.ForeignKey(
        "submission.Article", on_delete=models.SET_NULL,
        blank=True, null=True,
    )
    identifier = models.CharField(max_length=255,blank=True, null=True)
    success = models.BooleanField(default=False)
    result_text = models.TextField(blank=True, null=True)
    date_time = models.DateTimeField(default=timezone.now)


class ArticleManager(sm_models.Article.objects.__class__):
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.prefetch_related("identifier_set").prefetch_related(
            "doajdeposit_set"
        )


class Article(sm_models.Article):
    objects = ArticleManager()

    class Meta:
        proxy = True

    def get_doaj_id(self):
        try:
            return self.identifier_set.get(
                id_type="doaj",
            )
        except ObjectDoesNotExist:
            return None

    def can_push(self):
        return (
            self.date_published
            and self.stage == sm_models.STAGE_PUBLISHED
            and self.get_doi()
        )

    def latest_deposit(self):
        try:
            return self.doajdeposit_set.all(
            ).order_by(
                "-date_time",
            ).first()
        except ObjectDoesNotExist:
            return None

