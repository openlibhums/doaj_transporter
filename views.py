from django.db.models import Count
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render, redirect

from core import forms as core_forms
from journal import models as journal_models
from submission import models as sm_models
from security.decorators import editor_user_required
from utils import setting_handler
from utils.logger import get_logger

from plugins.doaj_transporter import logic, plugin_settings, models

logger = get_logger(__name__)


@editor_user_required
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
        for journal in request.press.journals():
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
            articles__date_published__isnull=False,
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


@editor_user_required
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

@require_POST
@editor_user_required
def push_issue(request):
    issue_id = request.POST.get("issue_id")
    issue = get_object_or_404(journal_models.Issue,
        id=issue_id,
        journal=request.journal,
    )
    errors = logic.push_issue_to_doaj(issue, raise_on_error=False)
    if errors:
        messages.add_message(
            request, messages.ERROR,
            "Failed to push %d articles" % len(errors),
        )
    else:
        messages.add_message(
            request, messages.SUCCESS,
            "%s articles pushed to DOAJ" % issue.articles.count(),
        )
    return redirect(request.META.get("HTTP_REFERER"))


@require_POST
@editor_user_required
def push_article(request):
    article_id = request.POST.get("article_id")
    article = get_object_or_404(sm_models.Article,
        id=article_id,
        journal=request.journal,
    )
    try:
        logic.push_article_to_doaj(article)
    except Exception as e:
        messages.add_message(
            request, messages.ERROR,
            "Push failed: %s" % e,
        )
        logger.error("[DOAJ] Error pushing article %s to doaj:", article.pk)
        logger.error("[DOAJ] %s", e)
    else:
        messages.add_message(
            request, messages.SUCCESS,
            "Article pushed to DOAJ",
        )

    return redirect(request.META.get("HTTP_REFERER"))


@editor_user_required
def list_issue(request, issue_id=None):
    articles = models.Article.objects.filter(
        issues__id=issue_id,
        journal=request.journal
    ).order_by(
        "date_published"
    )

    template = 'doaj_transporter/listing.html'
    context = {
        "articles": articles,
    }

    return render(request, template, context)

@editor_user_required
def article_json(request, article_id=None):
    article = get_object_or_404(sm_models.Article,
        id=article_id,
        journal=request.journal,
    )
    json_data = logic.encode_article_to_doaj_json(article)

    return HttpResponse(json_data, content_type="application/json")
