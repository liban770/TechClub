"""
WSGI config for techclub_core project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techclub_core.settings')

# Auto-initialize preview SQLite database on Vercel when DATABASE_URL is not configured
if 'VERCEL' in os.environ and 'DATABASE_URL' not in os.environ:
    try:
        flag_file = '/tmp/.db_migrated'
        if not os.path.exists(flag_file):
            import django
            django.setup()
            from django.core.management import call_command
            call_command('migrate', interactive=False)
            try:
                import seed_data
                seed_data.run_seed()
            except Exception as se:
                print(f"Seed notice: {se}")
            with open(flag_file, 'w') as f:
                f.write('ready')
    except Exception as e:
        print(f"Vercel auto-setup notice: {e}")

application = get_wsgi_application()
app = application
