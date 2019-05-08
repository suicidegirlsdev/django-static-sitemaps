from datetime import timedelta

from celery import Celery
from celery import shared_task

app = Celery()

from static_sitemaps import conf
from static_sitemaps.generator import SitemapGenerator

__author__ = 'xaralis'

# Register the task conditionally so the task can be bypassed when repetition
# is set to something which evaluates to False.
if conf.CELERY_TASK_REPETITION:
    @app.on_after_configure.connect
    def setup_periodic_tasks(sender, **kwargs):
        sender.add_periodic_task(
            timedelta(minutes=conf.CELERY_TASK_REPETITION),
            generate_sitemap.s(),
            expires=600, # If hasn't started in 10m, don't risk overlap
        )

@shared_task
def generate_sitemap():
    generator = SitemapGenerator(verbosity=1)
    generator.write()
