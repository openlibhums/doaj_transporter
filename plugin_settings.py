from utils import models
from utils.install import update_settings

PLUGIN_NAME = 'doaj'
DESCRIPTION = 'A plugin for exporting metadata to DOAJ via their API'
AUTHOR = 'Mauro Sanchez Lopez'
VERSION = '1.0'
SHORT_NAME = 'DOAJ'
DISPLAY_NAME = 'DOAJ'
MANAGER_URL = 'doaj_index'


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
        update_settings(
            file_path='plugins/doaj_transporter/install/settings.json'
        )
    else:
        print('Plugin {0} is already installed.'.format(PLUGIN_NAME))


def hook_registry():
    # On site load, the load function is run for each installed plugin to
    # generate a list of hooks.
    return {}
