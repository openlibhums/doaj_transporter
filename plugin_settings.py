import os

from utils import models
from utils.install import update_settings
from plugins.doaj_transporter import events as plugin_events

PLUGIN_NAME = 'DOAJ Transporter'
DESCRIPTION = 'A plugin for exporting metadata to DOAJ via their API'
AUTHOR = 'Mauro Sanchez'
VERSION = '1.2'
SHORT_NAME = 'doaj_transporter'
DISPLAY_NAME = 'DOAJ Transporter'
MANAGER_URL = 'doaj_index'
JANEWAY_VERSION = '1.5.0'


PLUGIN_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_SETTINGS_PATH = os.path.join(PLUGIN_PATH, "install/settings.json")


def install():
    plugin, created = models.Plugin.objects.get_or_create(
        name=SHORT_NAME,
        defaults={
            "enabled": True,
            "version": VERSION,
            "display_name": DISPLAY_NAME,
        }
    )

    if created:
        print('Plugin {0} installed.'.format(PLUGIN_NAME))
        update_settings(
            file_path='plugins/doaj_transporter/install/settings.json'
        )
    elif plugin.version != VERSION:
        print('Plugin updated: {0} -> {1}'.format(VERSION, plugin.version))
        update_settings( file_path=JSON_SETTINGS_PATH)
        plugin.version = VERSION
        plugin.display_name = DISPLAY_NAME
        plugin.save()

    else:
        print('Plugin {0} is already installed.'.format(PLUGIN_NAME))


def register_for_events():
    return plugin_events.register_for_events()

def hook_registry():
    # On site load, the load function is run for each installed plugin to
    # generate a list of hooks.
    return {}
