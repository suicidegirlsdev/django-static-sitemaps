'''
Created on 24.10.2011

@author: xaralis
'''
from django.conf.urls import url

from .views import index_view, page_view

# Sets the app name for these urls
app_name = "static_sitemaps"

urlpatterns = [
    url(r'^sitemap_index.xml$', index_view, name='static_sitemaps_index'),
    # This is mainly for testing, though could rewrite the above index file with links like below, if so inclined,
    # Using xml parser and loading the index from S3 (like with passthru setting).
    url(r'^sitemap_(?P<filename>.*)$', page_view, name='static_sitemaps_page'),
]
