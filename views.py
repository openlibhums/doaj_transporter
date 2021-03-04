from django.db.models import Count
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect

from core import forms as core_forms
from journal import models as journal_models
from submission import models as sm_models
from utils import setting_handler

from plugins.doaj_transporter import plugin_settings, logic


def index(request):
    token = setting_handler.get_setting(
        "plugin", "doaj_api_token", journal=request.journal).value

    articles = sm_models.Article.objects.filter(
        stage=sm_models.STAGE_PUBLISHED)
    if request.journal:
        articles = articles.filter(journal=request.journal)
        push_enabled = 'On' if setting_handler.get_setting(
            "plugin", "doaj_publish_push",
            journal=request.journal,
        ).value else "Off"
    else:
        total = 0
        enabled = 0
        for journal in request.press.journals.all():
            journal_enabled = setting_handler.get_setting(
                "plugin", "doaj_publish_push", journal=journal).value
            if journal_enabled:
                enabled += 1
            total += 1
        push_enabled = "%d/%d" % (enabled, total)
    in_doaj = "%d/%d" % (
        articles.filter(identifier__id_type="doaj").count(), articles.count())

    issues = []
    if request.journal:
        issues = journal_models.Issue.objects.filter(
            issue_type__code="issue",
            journal=request.journal,
            articles__stage=sm_models.STAGE_PUBLISHED,
        ).annotate(
            count_articles=Count("articles"),
        ).filter(
            articles__identifier__id_type="doaj",
        ).annotate(
            count_doaj=Count("articles__identifier"),
        )


    template = 'doaj_transporter/index.html'
    context = {
        "api_token": bool(token),
        "push_enabled": push_enabled,
        "in_doaj": in_doaj,
        "issues": issues,
    }

    return render(request, template, context)


def configure(request):
    token = setting_handler.get_setting(
        "plugin", "doaj_api_token", journal=request.journal)
    journals = {}
    push_enabled = False
    if request.journal:
        push_enabled = setting_handler.get_setting(
            "plugin", "doaj_publish_push", journal=request.journal,
                default=False,
        )
    else:
        for journal in request.press.journals():
            enabled = setting_handler.get_setting(
                "plugin", "doaj_publish_push", journal=journal,
                default=False,
            )
            if enabled:
                journals[journal] = True
            else:
                journals[journal] = False


    if token.journal == request.journal:
        initial_token = token.value
    else:
        initial_token = None
    token_form = core_forms.EditKey(
            key_type=token.setting.types,
            value=initial_token or None,
    )
    if request.POST:
        token_form
        posted_codes = set(request.POST.getlist("journal_push", []))
        posted_token = request.POST.get("value")
        if posted_token:
            setting_handler.save_setting(
                "plugin", "doaj_api_token", journal=request.journal,
                value=posted_token
            )
        if request.journal:
                #If blank, delete potential override
            if not posted_token and token.journal:
                token.delete()
            if request.journal.code in posted_codes:
                setting_handler.save_setting(
                    "plugin", "doaj_publish_push", journal=request.journal,
                    value=True,
                )
            else:
                push_enabled = setting_handler.get_setting(
                    "plugin", "doaj_publish_push",
                    journal=request.journal,
                    default=False,
                )
                if push_enabled:
                    push_enabled.delete()
        else:
            for journal in request.press.journals():
                if journal.code in posted_codes:
                    setting_handler.save_setting(
                        "plugin", "doaj_publish_push", journal=journal,
                        value=True,
                )
                else:
                    enabled = setting_handler.get_setting(
                        "plugin", "doaj_publish_push", journal=journal,
                        default=False,
                    )
                    if enabled:
                        enabled.delete()
        return redirect(reverse("doaj_configure"))


    template = 'doaj_transporter/configure.html'
    context = {
        "token_form": token_form,
        "token": token,
        "journals": journals,
        "push_enabled": push_enabled,
    }

    return render(request, template, context)
