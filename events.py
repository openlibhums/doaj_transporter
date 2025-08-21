"""
Event handlers that can be installed with Janeway's event system
"""
import traceback as tb

from events import logic as events_logic
from utils.logger import get_logger
from utils.setting_handler import get_setting

from plugins.doaj_transporter import logic

logger = get_logger(__name__)


def push_on_publication(article, *args, **kwargs):
    journal = article.journal
    setting = get_setting("plugin", "doaj_api_token", journal=journal)
    if not setting or not setting.value:
        # Check press default
        setting = get_setting("plugin", "doaj_api_token", journal=None)

    if not setting or not setting.value:
        logger.info("Journal has no DOAJ Token, ignoring...")
        return

    enabled = get_setting("plugin", "doaj_publish_push", journal=journal).value
    if enabled:
        try:
            logic.push_article_to_doaj(article)
        except Exception as e:
            logger.error("Failed to push article to DOAJ:")
            tb.print_exc()
    else:
        logger.info("DOAJ push disabled for journal, ignoring...")


def register_for_events():
    events_logic.Events.register_for_event(
        events_logic.Events.ON_ARTICLE_PUBLISHED,
        push_on_publication,
    )

