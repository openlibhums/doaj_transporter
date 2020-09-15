from utils import models

PLUGIN_NAME = 'doaj'
DESCRIPTION = 'A plugin for exporting metadata to DOAJ via their API'
AUTHOR = 'Mauro Sanchez Lopez'
VERSION = '1.0'
SHORT_NAME = 'DOAJ'
DISPLAY_NAME = 'DOAJ'
MANAGER_URL = 'doaj_index'

DOAJ_API_TOKEN = ""


def install():
    new_plugin, created = models.Plugin.objects.get_or_create(
        name=SHORT_NAME,
        display_name=DISPLAY_NAME,
        version=VERSION,
        enabled=True
    )

    if created:
        print('Plugin {0} installed.'.format(PLUGIN_NAME))
    else:
        print('Plugin {0} is already installed.'.format(PLUGIN_NAME))


def hook_registry():
    # On site load, the load function is run for each installed plugin to
    # generate a list of hooks.
    return {}
