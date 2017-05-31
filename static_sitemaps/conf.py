import os
from django.conf import settings
from datetime import timedelta

# Base sitemap config dict as stated in Django docs.
ROOT_SITEMAP = settings.STATICSITEMAPS_ROOT_SITEMAP

# Path to root location WITHIN the STATIC_ROOT where the sitemap indexes and PAGES_DIR dir (if default) will be stored.
# This is requisite because this uses the Django Storage system and files cannot be outside STATIC_ROOT. 
ROOT_DIR = getattr(settings, 'STATICSITEMAPS_ROOT_DIR', 'sitemaps')

# Directory where sitemap pages stored, will be created as a subdir of ROOT_DIR if default. 
# DO NOT PUT ANYTHING ELSE IN THIS DIR, FILES WILL BE DELETED!
PAGES_DIR = getattr(settings, 'STATICSITEMAPS_PAGES_DIR', os.path.join(ROOT_DIR, 'pages'))
assert PAGES_DIR, "PAGES_DIR cannot be empty since it's contents get deleted"

# Compress the result?
USE_GZIP = getattr(settings, 'STATICSITEMAPS_USE_GZIP', True)

# How to compress it? Must be in ('python', 'system').
GZIP_METHOD = getattr(settings, 'STATICSITEMAPS_GZIP_METHOD', 'python')

# Path to system gzip binary if system method is selected.
SYSTEM_GZIP_PATH = getattr(settings, 'STATICSITEMAPS_SYSTEM_GZIP_PATH', '/usr/bin/gzip')

INDEX_FILENAME_TEMPLATE = getattr(settings, 'STATICSITEMAPS_INDEX_FILENAME_TEMPLATE', 'sitemap.%(hash)s.xml')

# Template how to name the resulting sitemap pages. 
# Will use *.xml.gz if gzipped and default template used. 
_default_filename_template = 'sitemap-%(section)s-%(page)s.%(hash)s.xml'
if USE_GZIP:
    _default_filename_template = '%s.gz' % _default_filename_template

FILENAME_TEMPLATE = getattr(settings,
                            'STATICSITEMAPS_FILENAME_TEMPLATE',
                            _default_filename_template)

# Only for backwards compatibility, same as URL.
DOMAIN = getattr(settings, 'STATICSITEMAPS_DOMAIN', None)

# Language of sitemaps.
LANGUAGE = getattr(settings, 'STATICSITEMAPS_LANGUAGE', settings.LANGUAGE_CODE)

# Ping google after something changed in sitemap?
PING_GOOGLE = getattr(settings, 'STATICSITEMAPS_PING_GOOGLE', True)

# Template for sitemap index.
INDEX_TEMPLATE = getattr(settings, 'STATICSITEMAPS_INDEX_TEMPLATE',
                         'static_sitemaps/sitemap_index.xml')

# Storage class to use.
STORAGE_CLASS = getattr(settings, 'STATICSITEMAPS_STORAGE', 'django.core.files.storage.FileSystemStorage')

# How often should the celery task be run.
CELERY_TASK_REPETITION = int(getattr(settings, 'STATICSITEMAPS_REFRESH_AFTER', 60))

# Mock django sites framework
MOCK_SITE = getattr(settings, 'STATICSITEMAPS_MOCK_SITE', False)

# Mock django sites framework with hostname string...for example www.yoursite.com
MOCK_SITE_NAME = getattr(settings, 'STATICSITEMAPS_MOCK_SITE_NAME', None)

# Mock django sites framework with https | https
MOCK_SITE_PROTOCOL = getattr(settings, 'STATICSITEMAPS_MOCK_SITE_PROTOCOL', 'http')

# Mainly for testing, will limit the results from get_urls() for each sitemap (using [:limit])
PER_SITEMAP_LIMIT = int(getattr(settings, 'STATICSITEMAPS_PER_SITEMAP_LIMIT', 0))

# Where the sitemap index file url is saved
CACHE_KEY = getattr(settings, 'STATICSITEMAPS_CACHE_KEY', 'sitemaps_url')

# Expire old files, deleting them from storage
# Leave this high or crawlers working off an old index may 404.
PAGES_EXPIRE_AFTER = getattr(settings, 'PAGES_EXPIRE_AFTER', timedelta(days=2))

SERVE_INDEX_VIA_PASSTHRU = getattr(settings, 'STATICSITEMAPS_SERVE_INDEX_VIA_PASSTHRU', True)
