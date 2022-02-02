from modeltranslation.translator import register, TranslationOptions

from submission import translation as sm_translation

from plugins.doaj_transporter import models


@register(models.Article)
class NoTranslationOptions(TranslationOptions):
    fields = ()
