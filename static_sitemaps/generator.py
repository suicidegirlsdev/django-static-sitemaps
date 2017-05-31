from __future__ import print_function

import gzip, hashlib, os, re

from django.contrib.sitemaps import ping_google
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse, NoReverseMatch
from django.template import loader
from django.utils import translation
from django.utils.encoding import smart_bytes
from six import BytesIO
from static_sitemaps import conf
from static_sitemaps.util import _lazy_load
from django.core.cache import cache
from datetime import datetime

# More aptly "inspired" than authored, since had to heavily refactor almost all of it.
__author__ = 'xaralis'


class FormatToRegex(dict):
    '''
    Helper class to convert format string (using named placeholders) to regex.
    Adapted from: https://stackoverflow.com/questions/2654856/python-convert-format-string-to-regular-expression
    '''
    # Quick and dirty unique str
    _unique = "_UNIQ-%s_" % hash(object())
    def __getitem__(self, key):
        return self._unique + ('(?P<%s>.*?)' % key) + self._unique

    @classmethod
    def convert(cls, format):
        sane = 50
        while cls._unique in format and sane:
            cls._unique = "_UNIQ-%s_" % hash(object())
            sane += -1
        assert sane, "Failed to get unique token for converting regex from format: %s, last try: "  % (format, cls._unique)
        parts = (format % cls()).split(cls._unique)
        for i in range(0, len(parts), 2):
            parts[i] = re.escape(parts[i])
        return re.compile(''.join(parts))


class SitemapGenerator(object):
    cache_key = conf.CACHE_KEY
    # Get dir paths and bake into filepath templates, to avoid extra join calls
    root_dir = conf.ROOT_DIR
    index_filename_template = conf.INDEX_FILENAME_TEMPLATE
    index_path_template = os.path.join(root_dir, index_filename_template)
    # Default is relative to root dir
    page_dir = conf.PAGES_DIR
    page_filename_template = conf.FILENAME_TEMPLATE
    page_path_template = os.path.join(page_dir, page_filename_template)
    page_ttl = conf.PAGES_EXPIRE_AFTER

    # These are loaded lazily for cases where not needed, safety tests to verify files that will get deleted.
    page_filename_validation_re = None
    index_filename_validation_re = None
    dry_run = False

    def __init__(self, verbosity=1):
        self.verbosity = verbosity
        self.has_changes = False
        self.storage = _lazy_load(conf.STORAGE_CLASS)()
        self.sitemaps = _lazy_load(conf.ROOT_SITEMAP)

        if not isinstance(self.sitemaps, dict):
            self.sitemaps = dict(enumerate(self.sitemaps))

        self.unmodified_pages = set()

        self.out("Config: root=%s, page_dir=%s, page_template=%s, index_template=%s" % (self.root_dir, self.page_dir, self.page_path_template, self.index_path_template))

    @staticmethod
    def get_hash(bytestream):
        return hashlib.md5(bytestream).hexdigest()

    @classmethod
    def get_index_url(cls):
        '''
        Returns the relative path to the index file based on current config settings, caching results.
        '''
        url = cache.get(cls.cache_key)
        if url:
            return url

        # Fallback, shouldn't happen unless cache cleared
        self = cls()
        self.out("Sitemap URL cache miss: %s" % self.cache_key, 1)
        url = self.storage.url(self.get_index_file_path())
        cache.set(self.cache_key, url)
        return url

    @classmethod
    def is_valid_page(cls, filename):
        # NO PATH, just name
        if not filename:
            return False
        if not cls.page_filename_validation_re:
            cls.page_filename_validation_re = FormatToRegex.convert(cls.page_filename_template)
        return cls.page_filename_validation_re.match(filename) is not None

    @classmethod
    def is_valid_index(cls, filename):
        # NO PATH, just name
        if not filename:
            return False
        if not cls.index_filename_validation_re:
            cls.index_filename_validation_re = FormatToRegex.convert(cls.index_filename_template)
        return cls.index_filename_validation_re.match(filename) is not None

    def get_index_file_path(self, all_files=False):
        '''
        Returns path of index file.
        '''
        file_paths = [ os.path.join(self.root_dir, file) for file in self.storage.listdir(self.root_dir)[1] if self.is_valid_index(file) ]
        if all_files:
            return file_paths
        assert file_paths, "Expected to find sitemap index file(s) in %s" % self.root_dir

        if len(file_paths) == 1:
            return file_paths[0]

        self.out("Found more than one index file, will use try to use most recently modified")
        most_recent_mod = None
        most_recent_file_path = None
        for file_path in file_paths:
            mod = self.storage.modified_time(file_path)
            if not most_recent_mod or (mod and mod > most_recent_mod):
                most_recent_mod = mod
                most_recent_file_path = file_path
        assert most_recent_file_path, "Tried to find index file by most recently modified, but no modified times found"
        return most_recent_file_path

    def get_page_urls(self, site, page):
        #self.out('Writing sitemap %s.' % filename, 2)
        urls = []

        if conf.MOCK_SITE:
            if conf.MOCK_SITE_NAME is None:
                raise ImproperlyConfigured("STATICSITEMAPS_MOCK_SITE_NAME must not be None. Try setting to www.yoursite.com")
            from django.contrib.sites.requests import RequestSite
            from django.test.client import RequestFactory
            rs = RequestSite(RequestFactory().get('/', SERVER_NAME=conf.MOCK_SITE_NAME))

        try:
            if conf.MOCK_SITE:
                urls = site.get_urls(page, rs, protocol=conf.MOCK_SITE_PROTOCOL)
            else:
                urls = site.get_urls(page)
        except EmptyPage:
            self.out("Page %s empty" % page)
        except PageNotAnInteger:
            self.out("No page '%s'" % page)

        if conf.PER_SITEMAP_LIMIT:
            urls = urls[:conf.PER_SITEMAP_LIMIT]

        return urls

    def out(self, string, min_level=1):
        # TODO: use real logging
        if self.verbosity >= min_level:
            print(string)

    def load_current_files(self):
        '''
        Loads up dict of current pages with modified time.
        '''
        self.current_files = { file: self.storage.modified_time(file) for file in 
                              [os.path.join(self.page_dir, file) for file in self.storage.listdir(self.page_dir)[1] if self.is_valid_page(file)] }
        # Add in the index file(s), which can expire immediately so no expiry stored
        self.current_files.update({ file: None for file in self.get_index_file_path(all_files=True) })
        self.out("Loaded current files: %s" % self.current_files, 2)

    def write(self):
        self.out('Generating sitemaps.', 1)
        self.load_current_files()
        translation.activate(conf.LANGUAGE)
        self.write_all()
        self.cull_expired_files()
        translation.deactivate()
        self.out('Finished generating sitemaps.', 1)

    def cull_expired_files(self):
        culled_count = 0
        for file_path, mod in self.current_files.iteritems():
            # Don't cull files still in use
            # NOTE: because we don't update unmodified files, they can get past the ttl and not have any delay when next update occurs. 
            # But, presuming a safely high ttl, then the file should not be getting crawled by any relatively active crawler anyhow.
            if file_path in self.unmodified_pages:
                continue
            if mod is None or datetime.utcnow() - mod > self.page_ttl:
                self.out("CULLING expired file: %s, mod: %s" % (file_path, mod), 2)
                if not self.dry_run:
                    self.storage.delete(file_path)
                culled_count += 1
        return culled_count

    def write_all(self):
        parts = []

        # Collect all pages and write them.
        for section, site in self.sitemaps.items():
            if callable(site):
                site = site()
            pages = site.paginator.num_pages

            for page in range(1, pages + 1):
                file_path = self.write_page(site, page, section)
                # If it's an existing file (not changed), use our stored value, otherwise look it up.
                # Could probably just use "now", but this is safer for tz issues and such.
                lastmod = self.current_files.get(file_path, self.storage.modified_time(file_path))
                parts.append({
                    'location': self.storage.url(file_path),
                    'lastmod': lastmod
                })

        index_file_path = self.write_index(parts)
        self.ping_google()

    def write_index(self, parts):
        output = loader.render_to_string(conf.INDEX_TEMPLATE, {'sitemaps': parts})
        hash = self.get_hash(output)
        file_path = self.index_path_template % { 'hash': hash }
        if self.is_modified(file_path):
            self.out('Writing index file: %s' % file_path, 2)
            self.has_changes = True
            self.storage.save(file_path, ContentFile(output))
        else:
            self.out('Index file (and, as such, sitemap pages) not modified', 2)
        # Go ahead and update cache, even if not changed.
        url = self.storage.url(file_path)
        cache.set(self.cache_key, url)

    def write_page(self, site, page, section):
        '''
        Renders template and stores to file based on site/page/section and content hash, returning file path.
        '''
        template = getattr(site, 'sitemap_template', 'sitemap.xml')
        output = loader.render_to_string(template, {'urlset': self.get_page_urls(site, page)})
        # NOTE: hash based on raw content, BEFORE gzip. However, changing protocol will
        # change the default filename and thereby invalidate the stored file.
        hash = self.get_hash(output)
        file_path = self.page_path_template % {'section': section, 'page': page, 'hash': hash}

        if not self.is_modified(file_path):
            self.out('Page not modified: %s' % file_path , 2)
            return file_path
        self.out('Writing page: %s' % file_path , 2)

        if conf.USE_GZIP:
            try:
                self.out('Compressing...', 2)
                buf = BytesIO()
                with gzip.GzipFile(fileobj=buf, mode="w") as f:
                    # Encode to bytes for write
                    f.write(smart_bytes(output))
                output = buf.getvalue()
            except OSError:
                self.out("Compress %s file error" % file_path)

        self.storage.save(file_path, ContentFile(output))
        return file_path

    def is_modified(self, file_path):
        if file_path in self.current_files:
            # File not changed, same hash already exists. No need to save, and flag it as a keeper.
            self.unmodified_pages.add(file_path)
            return False
        return True

    def ping_google(self):
        if conf.PING_GOOGLE:
            try:
                sitemap_url = reverse('static_sitemaps_index')
            except NoReverseMatch:
                sitemap_url = self.get_index_url()

            self.out('Pinging google...', 2)
            ping_google(sitemap_url)

