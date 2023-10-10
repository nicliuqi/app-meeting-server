"""
WSGI config for community_meetings project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

try:
    import armorrasp
    armorrasp.start()
except ImportError:
    pass
except Exception as e:
    print(e)

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app_meeting_server.settings.prod')

application = get_wsgi_application()
