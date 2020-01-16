import os
from django.http import Http404, HttpResponseRedirect, FileResponse

from . import conf
from .generator import SitemapGenerator


def _passthru(generator, file_path, allow_gzip=True):
    try:
        response = FileResponse(generator.storage.open(file_path), content_type='application/xml')
    except IOError:
        raise Http404("Sitemap not found")
    if conf.USE_GZIP and allow_gzip:
        response['Content-Encoding'] = 'gzip'
    return response


def index_view(request):
    generator = SitemapGenerator()
    if not conf.SERVE_VIA_PASSTHRU:
        return HttpResponseRedirect(generator.get_index_url())
    return _passthru(generator, generator.get_index_file_path(), allow_gzip=False)


def page_view(request, filename):
    generator = SitemapGenerator()
    file_path = os.path.join(generator.page_dir, filename)
    if not generator.is_valid_page(filename):
        generator.out("Sitemap file requested is not valid: %s" % file_path)
        raise Http404("Sitemap file requested is not valid: %s" % file_path)
    if not conf.SERVE_VIA_PASSTHRU:
        return HttpResponseRedirect(generator.storage.url(file_path))
    return _passthru(generator, file_path)

