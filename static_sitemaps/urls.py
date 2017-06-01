'''
Created on 24.10.2011

@author: xaralis
'''
from django.http import HttpResponse, Http404, HttpResponseRedirect

from static_sitemaps import conf
from static_sitemaps.generator import SitemapGenerator

try:
    from django.conf.urls import url
except ImportError:  # django < 1.4
    from django.conf.urls.defaults import patterns, url

def serve_index(request):
    generator = SitemapGenerator()
    if not conf.SERVE_INDEX_VIA_PASSTHRU:
        return HttpResponseRedirect(generator.get_index_url())

    try:
        with generator.storage.open(generator.get_index_file_path()) as f:
            content = f.readlines()
    except IOError:
        raise Http404("No sitemap file exists")

    return HttpResponse(content, content_type='application/xml')

urlpatterns = [
    url(r'^', serve_index, name='static_sitemaps_index'),
]
