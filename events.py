"""
Event handlers that can be installed with Janeway's event system
"""
import traceback as tb
from utils.setting_handler import get_setting

from plugin.doaj_transporter import logic

def push_on_publication(article, *args, **kwargs):
    journal = article.journal
    setting = get_setting("plugin", "doaj_api_token", journal=journal)
    if not setting or not setting.value
        # Check press default
        setting = get_setting("plugin", "doaj_api_token", journal=None)

    if not setting or not setting.value:
        logger.info("Journal has no DOAJ Token, ignoring...")
        return

    enabled = get_setting("plugin", "doaj_publish_push", journal=journal).value
    if enabled:
        try:
            logic.push_article_to_doaj()
        except Exception as e:
            logger.error("Failed to push article to DOAJ:")
            tb.print_exc()
    else:
        logger.info("Journal has no DOAJ Token, ignoring...")
