'''
Created on 24.10.2011

@author: xaralis
'''
import os
from django.http import Http404, HttpResponseRedirect, FileResponse

from static_sitemaps import conf
from static_sitemaps.generator import SitemapGenerator

try:
    from django.conf.urls import url
except ImportError:  # django < 1.4
    from django.conf.urls.defaults import patterns, url

# Sets the app name for these urls
app_name = "static_sitemaps"

def _passthru(generator, file_path, allow_gzip=True):
    try:
        response = FileResponse(generator.storage.open(file_path), content_type='application/xml')
    except IOError:
        raise Http404("Sitemap not found")
    if conf.USE_GZIP and allow_gzip:
        response['Content-Encoding'] = 'gzip'
    return response

def serve_index(request):
    generator = SitemapGenerator()
    if not conf.SERVE_VIA_PASSTHRU:
        return HttpResponseRedirect(generator.get_index_url())
    return _passthru(generator, generator.get_index_file_path(), allow_gzip=False)

def serve_page(request, filename):
    generator = SitemapGenerator()
    file_path = os.path.join(generator.page_dir, filename)
    if not generator.is_valid_page(filename):
        generator.out("Sitemap file requested is not valid: %s" % file_path)
        raise Http404("Sitemap file requested is not valid: %s" % file_path)
    if not conf.SERVE_VIA_PASSTHRU:
        return HttpResponseRedirect(generator.storage.url(file_path))
    return _passthru(generator, file_path)

urlpatterns = [
    url(r'^index.xml$', serve_index, name='static_sitemaps_index'),
    # This is mainly for testing, though could rewrite the above index file with links like below, if so inclined,
    # Using xml parser and loading the index from S3 (like with passthru setting).
    url(r'^pages/(?P<filename>.*)$', serve_page, name='static_sitemaps_page'),
]
