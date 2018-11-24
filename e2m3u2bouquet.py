#!/usr/bin/env python2
# encoding: utf-8

"""
e2m3u2bouquet.e2m3u2bouquet -- Enigma2 IPTV m3u to bouquet parser

@author:     Dave Sully, Doug Mackay
@copyright:  2017 All rights reserved.
@license:    GNU GENERAL PUBLIC LICENSE version 3
@deffield    updated: Updated
"""
import time
import sys
import os
import errno
import re
import unicodedata
import datetime
import urllib
import urlparse
import imghdr
import tempfile
import glob
import ssl
import hashlib
import base64
import socket
from PIL import Image
from collections import OrderedDict
from collections import deque
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
try:
    from enigma import eDVBDB
except ImportError:
    eDVBDB = None
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__all__ = []
__version__ = '0.8.0'
__date__ = '2017-06-04'
__updated__ = '2018-11-22'

DEBUG = 0
TESTRUN = 0

ENIGMAPATH = '/etc/enigma2/'
EPGIMPORTPATH = '/etc/epgimport/'
CFGPATH = os.path.join(ENIGMAPATH, 'e2m3u2bouquet/')
PICONSPATH = '/usr/share/enigma2/picon/'
IMPORTED = False
PLACEHOLDER_SERVICE = '#SERVICE 1:832:d:0:0:0:0:0:0:0:'


class CLIError(Exception):
    """Generic exception to raise and log different fatal errors."""
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg

    def __str__(self):
        return self.msg

    def __unicode__(self):
        return self.msg


class AppUrlOpener(urllib.FancyURLopener):
    """Set user agent for downloads
    """
    version = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'


def display_welcome():
    print('\n********************************')
    print('Starting Enigma2 IPTV bouquets v{}'.format(__version__))
    print(str(datetime.datetime.now()))
    print("********************************\n")

def make_config_folder():
    """create config folder if it doesn't exist
    """
    try:
        os.makedirs(CFGPATH)
    except OSError, e:  # race condition guard
        if e.errno != errno.EEXIST:
            raise


def uninstaller():
    """Clean up routine to remove any previously made changes
    """
    print('----Running uninstall----')
    try:
        # Bouquets
        print('Removing old IPTV bouquets...')
        for fname in os.listdir(ENIGMAPATH):
            if 'userbouquet.suls_iptv_' in fname:
                os.remove(os.path.join(ENIGMAPATH, fname))
            elif 'bouquets.tv.bak' in fname:
                os.remove(os.path.join(ENIGMAPATH, fname))
        # Custom Channels and sources
        print('Removing IPTV custom channels...')
        if os.path.isdir(EPGIMPORTPATH):
            for fname in os.listdir(EPGIMPORTPATH):
                if 'suls_iptv_' in fname:
                    os.remove(os.path.join(EPGIMPORTPATH, fname))
        # bouquets.tv
        print('Removing IPTV bouquets from bouquets.tv...')
        os.rename(os.path.join(ENIGMAPATH, 'bouquets.tv'), os.path.join(ENIGMAPATH, 'bouquets.tv.bak'))
        tvfile = open(os.path.join(ENIGMAPATH, 'bouquets.tv'), 'w+')
        bakfile = open(os.path.join(ENIGMAPATH, 'bouquets.tv.bak'))
        for line in bakfile:
            if '.suls_iptv_' not in line:
                tvfile.write(line)
        bakfile.close()
        tvfile.close()
    except Exception, e:
        print('Unable to uninstall')
        raise
    print('----Uninstall complete----')


def get_category_title(cat, category_options):
    """Return the title override if set else the title
    """
    if cat in category_options:
        return category_options[cat]['nameOverride'] if category_options[cat].get('nameOverride', False) else cat
    return cat


def get_service_title(channel):
    """Return the title override if set else the title
    """
    return channel['nameOverride'] if channel.get('nameOverride', False) else channel['stream-name']


def reload_bouquets():
    if not TESTRUN:
        print("\n----Reloading bouquets----")
        if eDVBDB:
            eDVBDB.getInstance().reloadBouquets()
            print("bouquets reloaded...")
        else:
            os.system("wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 > /dev/null 2>&1 &")
            print("bouquets reloaded...")


def xml_safe_comment(string):
    """Can't have -- in xml comments"""
    return string.replace('--', '- - ')


def xml_escape(string):
    return string.replace("&", "&amp;") \
        .replace("\"", "&quot;") \
        .replace("'", "&apos;") \
        .replace("<", "&lt;") \
        .replace(">", "&gt;")


def xml_unescape(string):
    return string.replace('&quot;', '"') \
        .replace() \
        .replace("&apos;", "'") \
        .replace("&lt;", "<") \
        .replace("&gt;", ">") \
        .replace("&amp;", "&")


def get_safe_filename(filename):
    """Convert filename to safe filename
    """
    name = filename.replace(" ", "_").replace("/", "_")
    if type(name) is unicode:
        name = name.encode('utf-8')
    name = unicodedata.normalize('NFKD', unicode(name, 'utf_8')).encode('ASCII', 'ignore')
    name = re.sub('[^a-z0-9-_]', '', name.lower())
    return name

def get_parser_args(program_license, program_version_message):
    parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
    # URL Based Setup
    urlgroup = parser.add_argument_group('URL Based Setup')
    urlgroup.add_argument('-m', '--m3uurl', dest='m3uurl', action='store',
                          help='URL to download m3u data from (required)')
    urlgroup.add_argument('-e', '--epgurl', dest='epgurl', action='store',
                          help='URL source for XML TV epg data sources')
    # Provider based setup
    providergroup = parser.add_argument_group('Provider Based Setup')
    providergroup.add_argument('-n', '--providername', dest='providername', action='store',
                               help='Host IPTV provider name (e.g. FAB/EPIC) (required)')
    providergroup.add_argument('-u', '--username', dest='username', action='store',
                               help='Your IPTV username (required)')
    providergroup.add_argument('-p', '--password', dest='password', action='store',
                               help='Your IPTV password (required)')
    # Options
    parser.add_argument('-i', '--iptvtypes', dest='iptvtypes', action='store_true',
                        help='Treat all stream references as IPTV stream type. (required for some enigma boxes)')
    parser.add_argument('-sttv', '--streamtype_tv', dest='sttv', action='store', type=int,
                        help='Stream type for TV (e.g. 1, 4097, 5001 or 5002) overrides iptvtypes')
    parser.add_argument('-stvod', '--streamtype_vod', dest='stvod', action='store', type=int,
                        help='Stream type for VOD (e.g. 4097, 5001 or 5002) overrides iptvtypes')
    parser.add_argument('-M', '--multivod', dest='multivod', action='store_true',
                        help='Create multiple VOD bouquets rather single VOD bouquet')
    parser.add_argument('-a', '--allbouquet', dest='allbouquet', action='store_true',
                        help='Create all channels bouquet')
    parser.add_argument('-P', '--picons', dest='picons', action='store_true',
                        help='Automatically download of Picons, this option will slow the execution')
    parser.add_argument('-q', '--iconpath', dest='iconpath', action='store',
                        help='Option path to store picons, if not supplied defaults to /usr/share/enigma2/picon/')
    parser.add_argument('-xs', '--xcludesref', dest='xcludesref', action='store_true',
                        help='Disable service ref overriding from override.xml file')
    parser.add_argument('-b', '--bouqueturl', dest='bouqueturl', action='store',
                        help='URL to download providers bouquet - to map custom service references')
    parser.add_argument('-bd', '--bouquetdownload', dest='bouquetdownload', action='store_true',
                        help='Download providers bouquet (use default url) - to map custom service references')
    parser.add_argument('-bt', '--bouquettop', dest='bouquettop', action='store_true',
                        help='Place IPTV bouquets at top')
    parser.add_argument('-U', '--uninstall', dest='uninstall', action='store_true',
                        help='Uninstall all changes made by this script')
    parser.add_argument('-V', '--version', action='version', version=program_version_message)
    return parser


class Provider:
    def __init__(self):
        self._panel_bouquet_file = ''
        self._panel_bouquet = None
        self._m3u_file = None
        self._category_order = []
        self._category_options = {}
        self._dictchannels = OrderedDict()
        self.xmltv_sources_list = None
        self.name = ''
        self.enabled = False
        self.settings_level = ''
        self.m3u_url = ''
        self.epg_url = ''
        self.username = ''
        self.password = ''
        self.provider_update_url = ''
        self.iptv_types = False
        self.streamtype_tv = ''
        self.streamtype_vod = ''
        self.multi_vod = False
        self.all_bouquet = False
        self.picons = False
        self.icon_path = ''
        self.sref_override = False
        self.bouquet_url = ''
        self.bouquet_download = False
        self.bouquet_top = False
        self.last_provider_update = 0


    def _download_picon_file(self, logo_url, title):
        if logo_url:
            if not logo_url.startswith('http'):
                logo_url = 'http://{}'.format(logo_url)
            piconname = self._get_picon_name(title)
            picon_file_path = os.path.join(self.icon_path, piconname)
            existingpicon = filter(os.path.isfile, glob.glob(picon_file_path + '*'))

            if not existingpicon:
                if DEBUG:
                    print("Picon file doesn't exist downloading")
                    print('PiconURL: {}'.format(logo_url))
                else:
                    # Output some kind of progress indicator
                    if not IMPORTED:
                        # don't output when called from the plugin
                        sys.stdout.write('.')
                        sys.stdout.flush()
                try:
                    response = urllib.urlopen(logo_url)
                    info = response.info()
                    response.close()
                    if info.maintype == 'image':
                        urllib.urlretrieve(logo_url, picon_file_path)
                    else:
                        if DEBUG:
                            print('Download Picon - not an image, skipping')
                        self._picon_create_empty(picon_file_path)
                        return
                except Exception, e:
                    if DEBUG:
                        print('Download picon urlopen error', e)
                    self._picon_create_empty(picon_file_path)
                    return
                self._picon_post_processing(picon_file_path)

    def _picon_create_empty(self, picon_file_path):
        """
        create an empty picon so that we don't retry this picon
        """
        open(picon_file_path + '.None', 'a').close()

    def _picon_post_processing(self, picon_file_path):
        """Check type of image received and convert to png
        if necessary
        """
        ext = ""
        # get image type
        try:
            ext = imghdr.what(picon_file_path)
        except Exception, e:
            if DEBUG:
                print('Picon post processing - not an image or no file', e, picon_file_path)
            self._picon_create_empty(picon_file_path)
            return
        # if image but not png convert to png
        if (ext is not None) and (ext is not 'png'):
            if DEBUG:
                print('Converting Picon to png')
            try:
                Image.open(picon_file_path).save("{}.{}".format(picon_file_path, 'png'))
            except Exception, e:
                if DEBUG:
                    print('Picon post processing - unable to convert image', e)
                self._picon_create_empty(picon_file_path)
                return
            try:
                # remove non png file
                os.remove(picon_file_path)
            except Exception, e:
                if DEBUG:
                    print('Picon post processing - unable to remove non png file', e)
                return
        else:
            # rename to correct extension
            try:
                os.rename(picon_file_path, "{}.{}".format(picon_file_path, ext))
            except Exception, e:
                if DEBUG:
                    print('Picon post processing - unable to rename file ', e)

    def _get_picon_name(self, service_name):
        """Convert the service name to a Picon Service Name
        """
        name = service_name
        if type(name) is unicode:
            name = name.encode('utf-8')
        name = unicodedata.normalize('NFKD', unicode(name, 'utf_8')).encode('ASCII', 'ignore')
        name = re.sub('[\W]', '', name.replace('&', 'and')
                      .replace('+', 'plus')
                      .replace('*', 'star')
                      .lower())
        return name

    def _parse_panel_bouquet(self):
        """Check providers bouquet for custom service references
        """
        self._panel_bouquet = {}

        if os.path.isfile(self._panel_bouquet_file):
            with open(self._panel_bouquet_file, "r") as f:
                for line in f:
                    if '#SERVICE' in line:
                        # get service ref values we need (dict value) and stream file (dict key)
                        service = line.strip().split(':')
                        if len(service) == 11:
                            pos = service[10].rfind('/')
                            if pos != -1 and (pos + 1 != len(service[10])):
                                key = service[10][pos + 1:]
                                value = ':'.join((service[1], service[2], service[3], service[4], service[5],
                                                  service[6], service[7], service[8], service[9]))
                                if value != '0:1:0:0:0:0:0:0:0':
                                    # only add to dict if a custom service id is present
                                    self._panel_bouquet[key] = value
            if not DEBUG:
                # remove panel bouquet file
                os.remove(self._panel_bouquet_file)

    def _set_streamtypes_vodcats(self, service_dict):
        """Set the stream types and VOD categories
        """
        parsed_stream_url = urlparse.urlparse(service_dict['stream-url'])
        root, ext = os.path.splitext(parsed_stream_url.path)

        # check for vod streams ending .*.m3u8 e.g. 2345.mp4.m3u8
        is_m3u8_vod = re.search('\..+\.m3u8$', parsed_stream_url.path)

        if (parsed_stream_url.path.endswith('.ts') or parsed_stream_url.path.endswith('.m3u8')) \
                or not ext \
                and not is_m3u8_vod \
                and not service_dict['group-title'].startswith('VOD'):
            service_dict['stream-type'] = '4097' if self.iptv_types else '1'
            if self.streamtype_tv:
                # Set custom TV stream type if supplied - this overrides all_iptv_stream_types
                service_dict['stream-type'] = str(self.streamtype_tv)
        else:
            service_dict['group-title'] = u"VOD - {}".format(service_dict['group-title'])
            service_dict['stream-type'] = '4097' if not self.streamtype_vod else str(self.streamtype_vod)

    def _parse_map_bouquet_xml(self):
        """Check for bouquets within mapping override file and applies if found
        """
        category_order = []
        mapping_file = self._get_mapping_file()
        if mapping_file:
            print("\n----Parsing custom bouquet order----")

            tree = ET.ElementTree(file=mapping_file)
            for node in tree.findall(".//category"):
                dictoption = {}

                category = node.attrib.get('name')
                if not type(category) is unicode:
                    category = category.decode("utf-8")
                cat_title_override = node.attrib.get('nameOverride', '')
                if not type(cat_title_override) is unicode:
                    cat_title_override = cat_title_override.decode("utf-8")
                dictoption['nameOverride'] = cat_title_override
                dictoption['idStart'] = int(node.attrib.get('idStart', '0')) \
                    if node.attrib.get('idStart', '0').isdigit() else 0
                if node.attrib.get('enabled') == 'false':
                    dictoption['enabled'] = False
                    # Remove category/bouquet
                    if category != "VOD":
                        if category in self._dictchannels:
                            self._dictchannels.pop(category, None)
                    else:
                        keys_to_remove = []
                        for k in self._dictchannels.iterkeys():
                            if k.startswith("VOD"):
                                keys_to_remove.append(k)
                        if keys_to_remove:
                            for k in keys_to_remove:
                                self._dictchannels.pop(k, None)
                else:
                    dictoption["enabled"] = True
                    category_order.append(category)

                    # If this category is marked as custom and doesn't exist in self._dictchannels then add
                    is_custom_category = node.attrib.get('customCategory', '')
                    if is_custom_category == 'true':
                        dictoption['customCategory'] = 'true'
                        if category not in self._dictchannels:
                            self._dictchannels[category] = []

                self._category_options[category] = dictoption

            print("custom bouquet order applied...")
        return category_order

    def _parse_map_channels_xml(self):
        """Check for channels within mapping override file and apply if found
        """
        mapping_file = self._get_mapping_file()
        if mapping_file:
            print("\n----Parsing custom channel order, please be patient----")

            tree = ET.ElementTree(file=mapping_file)
            i = 0
            for cat in self._dictchannels:
                if not cat.startswith("VOD"):
                    # We don't override any individual VOD streams
                    sortedchannels = []
                    listchannels = []

                    # find channels that are to be moved to this category (categoryOverride)
                    for node in tree.findall(u'.//channel[@categoryOverride="{}"]'.format(cat)):
                        node_name = node.attrib.get('name')
                        category = node.attrib.get('category')
                        channel_index = None

                        # get index of channel in the current category
                        try:
                            channel_index = next((self._dictchannels[category].index(item) for item in self._dictchannels[category]
                                                  if item['stream-name'] == node_name), None)
                        except KeyError:
                            pass

                        if channel_index is not None:
                            # remove from existing category and add to new
                            self._dictchannels[cat].append(self._dictchannels[category].pop(channel_index))

                    for x in self._dictchannels[cat]:
                        listchannels.append(x['stream-name'])

                    for node in tree.findall(u'.//channel[@category="{}"]'.format(cat)):
                        # Check for placeholders, give unique name, insert into sorted channels and dictchannels[cat]
                        node_name = node.attrib.get('name')

                        if node_name == 'placeholder':
                            node_name = 'placeholder_' + str(i)
                            listchannels.append(node_name)
                            self._dictchannels[cat].append({'stream-name': node_name})
                            i += 1
                        sortedchannels.append(node_name)

                    sortedchannels.extend(listchannels)
                    # remove duplicates, keep order
                    listchannels = OrderedDict((x, True) for x in sortedchannels).keys()

                    # sort the channels by new order
                    channel_order_dict = {channel: index for index, channel in enumerate(listchannels)}
                    self._dictchannels[cat].sort(key=lambda x: channel_order_dict[x['stream-name']])
            print('custom channel order applied...')

            # apply overrides
            channel_nodes = tree.iter('channel')
            for override_channel in channel_nodes:
                name = override_channel.attrib.get('name')
                category = override_channel.attrib.get('category')
                category_override = override_channel.attrib.get('categoryOverride')
                channel_index = None
                channels_list = None

                if category_override:
                    # check if the channel has been moved to the new category
                    try:
                        channel_index = next((self._dictchannels[category_override].index(item) for item in self._dictchannels[category_override]
                                          if item['stream-name'] == name), None)
                    except KeyError:
                        pass

                if category_override and channel_index is not None:
                    channels_list = self._dictchannels.get(category_override)
                else:
                    channels_list = self._dictchannels.get(category)

                if channels_list is not None and name != 'placeholder':
                    for x in channels_list:
                        if x['stream-name'] == name:
                            if override_channel.attrib.get('enabled') == 'false':
                                x['enabled'] = False
                            x['nameOverride'] = override_channel.attrib.get('nameOverride', '')
                            x['categoryOverride'] = override_channel.attrib.get('categoryOverride', '')
                            # default to current values if attribute doesn't exist
                            x['tvg-id'] = override_channel.attrib.get('tvg-id', x['tvg-id'])
                            if override_channel.attrib.get('serviceRef', None) and self.sref_override:
                                x['serviceRef'] = override_channel.attrib.get('serviceRef', x['serviceRef'])
                                x['serviceRefOverride'] = True
                            # streamUrl no longer output to xml file but we still check and process it
                            x['stream-url'] = override_channel.attrib.get('streamUrl', x['stream-url'])
                            clear_stream_url = override_channel.attrib.get('clearStreamUrl') == 'true'
                            if clear_stream_url:
                                x['stream-url'] = ''
                            break
            print('custom overrides applied...')

    def _get_mapping_file(self):
        mapping_file = None
        search_path = [os.path.join(CFGPATH, get_safe_filename(self.name) + '-sort-override.xml'),
                       os.path.join(os.getcwd(), get_safe_filename(self.name) + '-sort-override.xml')]
        for path in search_path:
            if os.path.isfile(path):
                mapping_file = path
                break;
        return mapping_file

    def _save_bouquet_entry(self, f, channel):
        """Add service to bouquet file
        """
        if not channel['stream-name'].startswith('placeholder_'):
            f.write("#SERVICE {}:{}:{}\n"
                    .format(channel['serviceRef'], urllib.quote(channel['stream-url']),
                            get_service_title(channel).encode("utf-8")))
            f.write("#DESCRIPTION {}\n".format(get_service_title(channel).encode("utf-8")))
        else:
            f.write('{}\n'.format(PLACEHOLDER_SERVICE))

    def _get_bouquet_index_name(self, cat_filename, provider_filename):
        return ('#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.suls_iptv_{}_{}.tv" ORDER BY bouquet\n'
                .format(provider_filename, cat_filename))

    def _save_bouquet_index_entries(self, iptv_bouquets):
        """Add to the main bouquets.tv file
        """
        # get current bouquets indexes
        current_bouquet_indexes = self._get_current_bouquet_indexes()

        if iptv_bouquets:
            with open(os.path.join(ENIGMAPATH, 'bouquets.tv'), 'w') as f:
                f.write('#NAME Bouquets (TV)\n')
                if self.bouquet_top:
                    for bouquet in iptv_bouquets:
                        f.write(bouquet)
                    for bouquet in current_bouquet_indexes:
                        f.write(bouquet)
                else:
                    for bouquet in current_bouquet_indexes:
                        f.write(bouquet)
                    for bouquet in iptv_bouquets:
                        f.write(bouquet)

    def _get_current_bouquet_indexes(self):
        """Get all the bouquet indexes except this provider
        """
        current_bouquets_indexes = []

        with open(os.path.join(ENIGMAPATH, 'bouquets.tv'), 'r') as f:
            for line in f:
                if line.startswith('#NAME'):
                    continue
                else:
                    if not '.suls_iptv_{}'.format(get_safe_filename(self.name)) in line:
                        current_bouquets_indexes.append(line)
        return current_bouquets_indexes

    def _create_all_channels_bouquet(self):
        """Create the Enigma2 all channels bouquet
        """
        print("\n----Creating all channels bouquet----")

        bouquet_indexes = []

        vod_categories = list(cat for cat in self._category_order if cat.startswith('VOD -'))
        bouquet_name = '{} All Channels'.format(self.name)
        cat_filename = get_safe_filename(bouquet_name)
        provider_filename = get_safe_filename(self.name)

        # create file
        bouquet_filepath = os.path.join(ENIGMAPATH, 'userbouquet.suls_iptv_{}_{}.tv'
                                        .format(provider_filename, cat_filename))
        if DEBUG:
            print("Creating: {}".format(bouquet_filepath))

        with open(bouquet_filepath, 'w+') as f:
            f.write('#NAME {} - {}\n'.format(self.name.encode('utf-8'), bouquet_name.encode('utf-8')))

            # write place holder channels (for channel numbering)
            for i in xrange(100):
                f.write('{}\n'.format(PLACEHOLDER_SERVICE))
            channel_num = 1

            for cat in self._category_order:
                if cat in self._dictchannels:
                    if cat not in vod_categories:
                        cat_title = get_category_title(cat, self._category_options)
                        # Insert group description placeholder in bouquet
                        f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
                        f.write("#DESCRIPTION {}\n".format(cat_title.encode('utf-8')))
                        for x in self._dictchannels[cat]:
                            if x.get('enabled') or x['stream-name'].startswith('placeholder_'):
                                self._save_bouquet_entry(f, x)
                            channel_num += 1

                        while (channel_num % 100) is not 0:
                            f.write('{}\n'.format(PLACEHOLDER_SERVICE))
                            channel_num += 1

        # Add to bouquet index list
        bouquet_indexes.append(self._get_bouquet_index_name(cat_filename, provider_filename))
        print("all channels bouquet created ...")
        return bouquet_indexes

    def _create_epgimport_source(self, sources, group=None):
        """Create epg-importer source file
        """
        indent = "  "
        source_name = '{} - {}'.format(self.name, group) if group else self.name

        channels_filename = os.path.join(EPGIMPORTPATH, 'suls_iptv_{}_channels.xml'.format(get_safe_filename(self.name)))

        # write providers epg feed
        source_filename = os.path.join(EPGIMPORTPATH, 'suls_iptv_{}.sources.xml'
                                       .format(get_safe_filename(source_name)))

        with open(os.path.join(EPGIMPORTPATH, source_filename), "w+") as f:
            f.write('<sources>\n')
            f.write('{}<sourcecat sourcecatname="IPTV Bouquet Maker - E2m3u2bouquet">\n'.format(indent))
            f.write('{}<source type="gen_xmltv" nocheck="1" channels="{}">\n'
                    .format(2 * indent, channels_filename))
            f.write('{}<description>{}</description>\n'.format(3 * indent, xml_escape(source_name)))
            for source in sources:
                f.write('{}<url><![CDATA[{}]]></url>\n'.format(3 * indent, source))
            f.write('{}</source>\n'.format(2 * indent))
            f.write('{}</sourcecat>\n'.format(indent))
            f.write('</sources>\n')

    def _get_category_id(self, cat):
        """Generate 32 bit category id to help make service refs unique"""
        return hashlib.md5(self.name + cat.encode('utf-8')).hexdigest()[:8]

    def _has_m3u_file(self):
        return self._m3u_file is not None

    def process_provider(self):
        # Set epg to rytec if nothing else provided
        if self.epg_url is None:
            self.epg_url = "http://www.vuplus-community.net/rytec/rytecxmltv-UK.gz"
        # Set picon path
        if self.icon_path is None or TESTRUN == 1:
            self.icon_path = PICONSPATH
        if self.name is None:
            self.name = "E2m3u2Bouquet"

        # If no username or password supplied extract them from m3u_url
        if (self.username is None) or (self.password is None):
            # username, password = e2m3u_setup.extract_user_details_from_url(provider)
            self.extract_user_details_from_url()

        # Replace USERNAME & PASSWORD placeholders in urls
        self.m3u_url = self.m3u_url.replace('USERNAME', urllib.quote_plus(self.username)).replace('PASSWORD', urllib.quote_plus(self.password))
        self.epg_url = self.epg_url.replace('USERNAME', urllib.quote_plus(self.username)).replace('PASSWORD', urllib.quote_plus(self.password))
        if self.bouquet_download and self.bouquet_url:
            self.bouquet_url = self.bouquet_url.replace('USERNAME', urllib.quote_plus(self.username)).replace('PASSWORD', urllib.quote_plus(self.password))

        # get default provider bouquet download url if bouquet download set and no bouquet url given
        if self.bouquet_download and not self.bouquet_url:
            # set bouquet_url to default url
            pos = self.m3u_url.find('get.php')
            if pos != -1:
                self.bouquet_url = self.m3u_url[
                                       0:pos + 7] + '?username={}&password={}&type=dreambox&output=ts'.format(
                    urllib.quote_plus(self.username), urllib.quote_plus(self.password))

        # Download panel bouquet
        if self.bouquet_url:
            self.download_panel_bouquet()

        # Download m3u
        self.download_m3u()

        if self._has_m3u_file():
            # parse m3u file
            self.parse_m3u()
            self.parse_map_xmltvsources_xml()
            # save xml mapping - should be after m3u parsing
            self.save_map_xml()

            # Download picons
            if self.picons:
                self.download_picons()
            # Create bouquet files
            self.create_bouquets()
            # Now create custom channels for each bouquet
            print("\n----Creating EPG-Importer config ----")
            self.create_epgimporter_config()
            print("EPG-Importer config created...")
            # reload bouquets
            reload_bouquets()
            print("\n********************************")
            print("Engima2 IPTV bouquets created ! ")
            print("********************************")
            print("\nTo enable EPG data")
            print("Please open EPG-Importer plugin.. ")
            print("Select sources and enable the new IPTV source")
            print("(will be listed as {} under 'IPTV Bouquet Maker - E2m3u2bouquet')".format(self.name))
            print("Save the selected sources, press yellow button to start manual import")
            print("You can then set EPG-Importer to automatically import the EPG every day")

    def extract_user_details_from_url(self):
        """Extract username & password from m3u_url """
        if self.m3u_url:
            parsed = urlparse.urlparse(self.m3u_url)
            username_param = urlparse.parse_qs(parsed.query).get('username')
            if username_param:
                self.username = username_param[0]
            password_param = urlparse.parse_qs(parsed.query).get('password')
            if password_param:
                self.password = password_param[0]

    def download_m3u(self):
        """Download m3u file from url"""
        path = tempfile.gettempdir()
        filename = os.path.join(path, 'e2m3u2bouquet.m3u')
        print("\n----Downloading m3u file----")
        if DEBUG:
            print("m3uurl = {}".format(self.m3u_url))
        try:
            urllib.urlretrieve(self.m3u_url, filename)
        except Exception, e:
            print('Unable to download m3u file from url for {}'.format(self.name))
            # raise
            filename = None
        self._m3u_file = filename

    def parse_m3u(self):
        """core parsing routine"""
        # Extract and generate the following items from the m3u
        # group-title
        # tvg-name
        # tvg-id
        # tvg-logo
        # stream-name
        # stream-url

        print("\n----Parsing m3u file----")
        try:
            if not os.path.getsize(self._m3u_file):
                raise Exception("M3U file is empty. Check username & password")
        except Exception, e:
            raise

        service_dict = {}

        with open(self._m3u_file, "r") as f:
            for line in f:
                if 'EXTM3U' in line:  # First line we are not interested
                    continue
                elif 'EXTINF:' in line:  # Info line - work out group and output the line
                    service_dict = {'tvg-id': '', 'tvg-name': '', 'tvg-logo': '', 'group-title': '', 'stream-name': '',
                                    'stream-url': '', 'enabled': True, 'nameOverride': '', 'categoryOverride': '',
                                    'serviceRef': '', 'serviceRefOverride': False
                                    }
                    if line.find('tvg-') == -1:
                        raise Exception("No extended playlist info found. Check m3u url should be 'type=m3u_plus'")
                    channel = line.split('"')
                    # strip unwanted info at start of line
                    pos = channel[0].find(' ')
                    channel[0] = channel[0][pos:]

                    # loop through params and build dict
                    for i in xrange(0, len(channel) - 2, 2):
                        service_dict[channel[i].lower().strip(' =')] = channel[i + 1].decode('utf-8')

                    # Get the stream name from end of line (after comma)
                    stream_name_pos = line.rfind(',')
                    if stream_name_pos != -1:
                        service_dict['stream-name'] = line[stream_name_pos + 1:].strip().decode('utf-8')

                    # Set default name for any blank groups
                    if service_dict['group-title'] == '':
                        service_dict['group-title'] = u'None'
                elif 'http:' in line or 'https:' in line or 'rtmp:' in line:
                    if 'tvg-id' not in service_dict:
                        # if this is true the playlist had a http line but not EXTINF
                        raise Exception("No extended playlist info found. Check m3u url should be 'type=m3u_plus'")
                    service_dict['stream-url'] = line.strip()
                    self._set_streamtypes_vodcats(service_dict)

                    if service_dict['group-title'] not in self._dictchannels:
                        self._dictchannels[service_dict['group-title']] = [service_dict]
                    else:
                        self._dictchannels[service_dict['group-title']].append(service_dict)

        # sort categories by custom order (if exists)
        sorted_categories = self._parse_map_bouquet_xml()
        self._category_order = self._dictchannels.keys()
        sorted_categories.extend(self._category_order)
        # remove duplicates, keep order
        self._category_order = OrderedDict((x, True) for x in sorted_categories).keys()

        # Check for and parse override map
        self._parse_map_channels_xml()

        # Add Service references
        # VOD won't have epg so use same service id for all VOD
        vod_service_id = 65535
        serviceid_start = 34000
        category_offset = 150
        catstartnum = serviceid_start

        for cat in self._category_order:
            num = catstartnum
            if cat in self._dictchannels:
                if not cat.startswith("VOD"):
                    if cat in self._category_options:
                        # check if we have cat idStart from override file
                        if self._category_options[cat]["idStart"] > 0:
                            num = self._category_options[cat]["idStart"]
                        else:
                            self._category_options[cat]["idStart"] = num
                    else:
                        self._category_options[cat] = {"idStart": num}

                    for x in self._dictchannels[cat]:
                        cat_id = self._get_category_id(cat)
                        service_ref = "{:x}:{}:{}:0".format(num, cat_id[:4], cat_id[4:])
                        if not x['stream-name'].startswith('placeholder_'):
                            if self._panel_bouquet and not x.get('serviceRefOverride'):
                                # check if we have the panels custom service ref
                                pos = x['stream-url'].rfind('/')
                                if pos != -1 and (pos + 1 != len(x['stream-url'])):
                                    m3u_stream_file = x['stream-url'][pos + 1:]
                                    if m3u_stream_file in self._panel_bouquet:
                                        # have a match use the panels custom service ref
                                        x['serviceRef'] = "{}:{}".format(x['stream-type'], self._panel_bouquet[m3u_stream_file])
                                        continue
                            if not x.get('serviceRefOverride'):
                                # if service ref is not overridden in xml update
                                x['serviceRef'] = "{}:0:1:{}:0:0:0".format(x['stream-type'], service_ref)
                            num += 1
                        else:
                            x['serviceRef'] = PLACEHOLDER_SERVICE
                else:
                    for x in self._dictchannels[cat]:
                        x['serviceRef'] = "{}:0:1:{:x}:0:0:0:0:0:0".format(x['stream-type'], vod_service_id)
            while catstartnum < num:
                catstartnum += category_offset

        vod_index = None
        if "VOD" in self._category_order:
            # if we have the vod category placeholder from the override use it otherwise
            # use the first found vod category position
            vod_index = self._category_order.index("VOD")
        else:
            for key in self._category_order:
                if key.startswith("VOD"):
                    vod_index = self._category_order.index(key)
                    break

        if vod_index is not None:
            # move all VOD categories to VOD placeholder position or group after first vod position
            vodcategories = list((cat for cat in self._category_order if cat.startswith('VOD -')))
            if len(vodcategories):
                # remove the vod category(s) from current position
                self._category_order = [x for x in self._category_order if x not in vodcategories]
                # insert the vod category(s) at the placeholder / first pos
                self._category_order[vod_index:vod_index] = vodcategories
                try:
                    self._category_order.remove("VOD")
                except ValueError:
                    pass    # ignore exception

        # Have a look at what we have
        if DEBUG and TESTRUN:
            datafile = open(os.path.join(CFGPATH, 'channels.debug'), "w+")
            for cat in self._category_order:
                if cat in self._dictchannels:
                    for line in self._dictchannels[cat]:
                        linevals = ""
                        for key, value in line.items():
                            if type(value) is bool:
                                linevals += str(value) + ":"
                            else:
                                linevals += (value).encode("utf-8") + ":"
                        datafile.write("{}\n".format(linevals))
            datafile.close()
        print("Completed parsing data...")

        if not DEBUG:
            # remove m3u file
            if os.path.isfile(self._m3u_file):
                os.remove(self._m3u_file)

    def download_panel_bouquet(self):
        """Download panel bouquet file from url
        """
        path = tempfile.gettempdir()
        filename = os.path.join(path, 'userbouquet.panel.tv')
        print("\n----Downloading providers bouquet file----")
        if DEBUG:
            print("bouqueturl = {}".format(self.bouquet_url))
        try:
            urllib.urlretrieve(self.bouquet_url, filename)
        except Exception, e:
            print('Unable to download providers panel bouquet file')
            raise
        self._panel_bouquet_file = filename
        self._parse_panel_bouquet()

    def download_picons(self):
        print('\n----Downloading Picon files, please be patient----')
        print('If no Picons exist this will take a few minutes')
        try:
            os.makedirs(self.icon_path)
        except OSError, e:  # race condition guard
            if e.errno != errno.EEXIST:
                raise

        for cat in self._dictchannels:
            if not cat.startswith('VOD'):
                # Download Picon if not VOD
                for x in self._dictchannels[cat]:
                    if not x['stream-name'].startswith('placeholder_'):
                        self._download_picon_file(x['tvg-logo'], get_service_title(x))
        print('\nPicons download completed...')
        print('Box will need restarted for Picons to show...')

    def parse_map_xmltvsources_xml(self):
        """Check for a mapping override file and parses it if found
        """
        self.xmltv_sources_list = {}
        mapping_file = self._get_mapping_file()
        if mapping_file:
            tree = ET.ElementTree(file=mapping_file)
            for group in tree.findall('.//xmltvextrasources/group'):
                group_name = group.attrib.get('id')
                urllist = []
                for url in group:
                    urllist.append(url.text)
                self.xmltv_sources_list[group_name] = urllist

    def save_map_xml(self):
        """Create mapping file"""
        mappingfile = os.path.join(CFGPATH, get_safe_filename(self.name) + '-sort-current.xml')
        indent = "  "
        vod_category_output = False

        if self._dictchannels:
            with open(mappingfile, "wb") as f:
                f.write('<!--\r\n')
                f.write('{} E2m3u2bouquet Custom mapping file\r\n'.format(indent))
                f.write('{} Rearrange bouquets or channels in the order you wish\r\n'.format(indent))
                f.write('{} Disable bouquets or channels by setting enabled to "false"\r\n'.format(indent))
                f.write('{} Map DVB EPG to IPTV by changing channel serviceRef attribute to match DVB service reference\r\n'.format(indent))
                f.write('{} Map XML EPG to different feed by changing channel tvg-id attribute\r\n'.format(indent))
                f.write('{} Rename this file as {}-sort-override.xml for changes to apply\r\n'.format(indent, get_safe_filename(self.name)))
                f.write('-->\r\n')

                f.write('<mapping>\r\n')

                f.write('{}<xmltvextrasources>\r\n'.format(indent))
                if not self.xmltv_sources_list:
                    # output example config
                    f.write('{}<!-- Example Config\r\n'.format((2 * indent)))
                    # UK - Freeview (xz)
                    f.write('{}<group id="{}">\r\n'.format(2 * indent, 'UK - Freeview (xz)'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://www.xmltvepg.nl/rytecUK_Basic.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://rytecepg.ipservers.eu/epg_data/rytecUK_Basic.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://rytecepg.wanwizard.eu/rytecUK_Basic.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://91.121.106.172/~rytecepg/epg_data/rytecUK_Basic.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://www.vuplus-community.net/rytec/rytecUK_Basic.xz'))
                    f.write('{}</group>\r\n'.format(2 * indent))
                    # UK - FTA (xz)
                    f.write('{}<group id="{}">\r\n'.format(2 * indent, 'UK - FTA (xz)'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://www.xmltvepg.nl/rytecUK_FTA.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://rytecepg.ipservers.eu/epg_data/rytecUK_FTA.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://rytecepg.wanwizard.eu/rytecUK_FTA.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://91.121.106.172/~rytecepg/epg_data/rytecUK_FTA.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://www.vuplus-community.net/rytec/rytecUK_FTA.xz'))
                    f.write('{}</group>\r\n'.format(2 * indent))
                    # UK - International (xz)
                    f.write('{}<group id="{}">\r\n'.format(2 * indent, 'UK - International (xz)'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://www.xmltvepg.nl/rytecUK_int.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent,
                                                         'http://rytecepg.ipservers.eu/epg_data/rytecUK_int.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://rytecepg.wanwizard.eu/rytecUK_int.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent,
                                                         'http://91.121.106.172/~rytecepg/epg_data/rytecUK_int.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent,
                                                         'http://www.vuplus-community.net/rytec/rytecUK_int.xz'))
                    f.write('{}</group>\r\n'.format(2 * indent))
                    # UK - Sky Live (xz)
                    f.write('{}<group id="{}">\r\n'.format(2 * indent, 'UK - Sky Live (xz)'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://www.xmltvepg.nl/rytecUK_SkyLive.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent,
                                                         'http://rytecepg.ipservers.eu/epg_data/rytecUK_SkyLive.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://rytecepg.wanwizard.eu/rytecUK_SkyLive.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent,
                                                         'http://91.121.106.172/~rytecepg/epg_data/rytecUK_SkyLive.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent,
                                                         'http://www.vuplus-community.net/rytec/rytecUK_SkyLive.xz'))
                    f.write('{}</group>\r\n'.format(2 * indent))
                    # UK - Sky Dead (xz)
                    f.write('{}<group id="{}">\r\n'.format(2 * indent, 'UK - Sky Dead (xz)'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://www.xmltvepg.nl/rytecUK_SkyDead.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent,
                                                         'http://rytecepg.ipservers.eu/epg_data/rytecUK_SkyDead.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://rytecepg.wanwizard.eu/rytecUK_SkyDead.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent,
                                                         'http://91.121.106.172/~rytecepg/epg_data/rytecUK_SkyDead.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent,
                                                         'http://www.vuplus-community.net/rytec/rytecUK_SkyDead.xz'))
                    f.write('{}</group>\r\n'.format(2 * indent))
                    # UK - Sports/Movies (xz)
                    f.write('{}<group id="{}">\r\n'.format(2 * indent, 'UK - Sports/Movies (xz)'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://www.xmltvepg.nl/rytecUK_SportMovies.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent,
                                                         'http://rytecepg.ipservers.eu/epg_data/rytecUK_SportMovies.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent, 'http://rytecepg.wanwizard.eu/rytecUK_SportMovies.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent,
                                                         'http://91.121.106.172/~rytecepg/epg_data/rytecUK_SportMovies.xz'))
                    f.write('{}<url>{}</url>\r\n'.format(3 * indent,
                                                         'http://www.vuplus-community.net/rytec/rytecUK_SportMovies.xz'))
                    f.write('{}</group>\r\n'.format(2 * indent))
                    f.write('{}-->\r\n'.format(2 * indent))

                else:
                    for group in self.xmltv_sources_list:
                        f.write('{}<group id="{}">\r\n'.format(2 * indent, xml_escape(group)))
                        for source in self.xmltv_sources_list[group]:
                            f.write('{}<url>{}</url>\r\n'.format(3 * indent, xml_escape(source)))
                        f.write('{}</group>\r\n'.format(2 * indent))
                f.write('{}</xmltvextrasources>\r\n'.format(indent))

                f.write('{}<categories>\r\n'.format(indent))
                for cat in self._category_order:
                    if cat in self._dictchannels:
                        if not cat.startswith('VOD -'):
                            cat_title_override = ''
                            idStart = ''
                            if cat in self._category_options:
                                cat_title_override = self._category_options[cat].get('nameOverride', '')
                                idStart = self._category_options[cat].get('idStart', '')
                            f.write('{}<category name="{}" nameOverride="{}" idStart="{}" enabled="true" customCategory="{}"/>\r\n'
                                    .format(2 * indent,
                                            xml_escape(cat).encode('utf-8'),
                                            xml_escape(cat_title_override).encode('utf-8'),
                                            idStart,
                                            self._category_options[cat].get('customCategory', 'false')
                                            ))
                        elif not vod_category_output:
                            # Replace multivod categories with single VOD placeholder
                            cat_title_override = ''
                            if 'VOD' in self._category_options:
                                cat_title_override = self._category_options['VOD'].get('nameOverride', '')
                            f.write('{}<category name="{}" nameOverride="{}" enabled="true" />\r\n'
                                    .format(2 * indent,
                                            'VOD',
                                            xml_escape(cat_title_override).encode('utf-8'),
                                            ))
                            vod_category_output = True
                for cat in self._category_options:
                    if 'enabled' in self._category_options[cat] and self._category_options[cat]['enabled'] is False:
                        f.write('{}<category name="{}" nameOverride="{}" enabled="false" />\r\n'
                                .format(2 * indent,
                                        xml_escape(cat).encode("utf-8"),
                                        xml_escape(cat_title_override).encode("utf-8")
                                        ))

                f.write('{}</categories>\r\n'.format(indent))

                f.write('{}<channels>\r\n'.format(indent))
                for cat in self._category_order:
                    if cat in self._dictchannels:
                        # Don't output any of the VOD channels
                        if not cat.startswith('VOD'):
                            f.write('{}<!-- {} -->\r\n'.format(2 * indent, xml_safe_comment(xml_escape(cat.encode('utf-8')))))
                            for x in self._dictchannels[cat]:
                                if not x['stream-name'].startswith('placeholder_'):
                                    f.write('{}<channel name="{}" nameOverride="{}" tvg-id="{}" enabled="{}" category="{}" categoryOverride="{}" serviceRef="{}" clearStreamUrl="{}" />\r\n'
                                            .format(2 * indent,
                                                    xml_escape(x['stream-name'].encode('utf-8')),
                                                    xml_escape(x.get('nameOverride', '').encode('utf-8')),
                                                    xml_escape(x['tvg-id'].encode('utf-8')),
                                                    str(x['enabled']).lower(),
                                                    xml_escape(x['group-title'].encode('utf-8')),
                                                    xml_escape(x.get('categoryOverride', '').encode('utf-8')),
                                                    xml_escape(x['serviceRef']),
                                                    'false' if x['stream-url'] else 'true'
                                                    ))
                                else:
                                    f.write(
                                        '{}<channel name="{}" category="{}" />\r\n'
                                        .format(2 * indent,
                                                'placeholder',
                                                xml_escape(cat.encode('utf-8')),
                                                ))

                f.write('{}</channels>\r\n'.format(indent))
                f.write('</mapping>')

    def create_bouquets(self):
        """Create the Enigma2 bouquets
        """
        print("\n----Creating bouquets----")
        # clean old bouquets before writing new
        if self._dictchannels:
            for fname in os.listdir(ENIGMAPATH):
                if 'userbouquet.suls_iptv_{}'.format(get_safe_filename(self.name)) in fname:
                    os.remove(os.path.join(ENIGMAPATH, fname))
        iptv_bouquet_list = []

        if self.all_bouquet:
            iptv_bouquet_list = self._create_all_channels_bouquet()

        vod_categories = list(cat for cat in self._category_order if cat.startswith('VOD -'))
        vod_category_output = False
        vod_bouquet_entry_output = False
        channel_number_start_offset_output = False

        for cat in self._category_order:
            if cat in self._dictchannels:
                cat_title = get_category_title(cat, self._category_options)
                # create file
                cat_filename = get_safe_filename(cat_title)
                provider_filename = get_safe_filename(self.name)

                if cat in vod_categories and not self.multi_vod:
                    cat_filename = "VOD"

                bouquet_filepath = os.path.join(ENIGMAPATH, 'userbouquet.suls_iptv_{}_{}.tv'
                                                .format(provider_filename, cat_filename))
                if DEBUG:
                    print("Creating: {}".format(bouquet_filepath))

                if cat not in vod_categories or self.multi_vod:
                    with open(bouquet_filepath, "w+") as f:
                        bouquet_name = '{} - {}'.format(self.name, cat_title.encode('utf-8')).decode("utf-8")
                        if not cat.startswith('VOD -'):
                            if cat in self._category_options and self._category_options[cat].get('nameOverride', False):
                                bouquet_name = self._category_options[cat]['nameOverride'].decode('utf-8')
                        else:
                            if 'VOD' in self._category_options and self._category_options['VOD'].get('nameOverride', False):
                                bouquet_name = '{} - {}'\
                                    .format(self._category_options['VOD']['nameOverride'].decode('utf-8'),
                                            cat_title.replace('VOD - ', '').decode("utf-8"))
                        channel_num = 0
                        f.write("#NAME {}\n".format(bouquet_name.encode("utf-8")))
                        if not channel_number_start_offset_output and not self.all_bouquet:
                            # write place holder services (for channel numbering)
                            for i in xrange(100):
                                f.write('{}\n'.format(PLACEHOLDER_SERVICE))
                            channel_number_start_offset_output = True
                            channel_num += 1

                        for x in self._dictchannels[cat]:
                            if x.get('enabled') or x['stream-name'].startswith('placeholder_'):
                                self._save_bouquet_entry(f, x)
                            channel_num += 1

                        while (channel_num % 100) is not 0:
                            f.write('{}\n'.format(PLACEHOLDER_SERVICE))
                            channel_num += 1
                elif not vod_category_output and not self.multi_vod:
                    # not multivod - output all the vod services in one file
                    with open(bouquet_filepath, "w+") as f:
                        bouquet_name = '{} - VOD'.format(self.name).decode("utf-8")
                        if 'VOD' in self._category_options and self._category_options['VOD'].get('nameOverride', False):
                            bouquet_name = self._category_options['VOD']['nameOverride'].decode('utf-8')

                        channel_num = 0
                        f.write("#NAME {}\n".format(bouquet_name.encode("utf-8")))
                        if not channel_number_start_offset_output and not self.all_bouquet:
                            # write place holder services (for channel numbering)
                            for i in xrange(100):
                                f.write('{}\n'.format(PLACEHOLDER_SERVICE))
                            channel_number_start_offset_output = True
                            channel_num += 1

                        for vodcat in vod_categories:
                            if vodcat in self._dictchannels:
                                # Insert group description placeholder in bouquet
                                f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0:\n")
                                f.write("#DESCRIPTION {}\n". format(vodcat.encode("utf-8")))
                                for x in self._dictchannels[vodcat]:
                                    self._save_bouquet_entry(f, x)
                                    channel_num += 1

                                while (channel_num % 100) is not 0:
                                    f.write('{}\n'.format(PLACEHOLDER_SERVICE))
                                    channel_num += 1
                        vod_category_output = True

                # Add to bouquet index list
                if cat not in vod_categories or (cat in vod_categories and not vod_bouquet_entry_output):
                    iptv_bouquet_list.append(self._get_bouquet_index_name(cat_filename, provider_filename))
                    if cat in vod_categories and not self.multi_vod:
                        vod_bouquet_entry_output = True

        # write the bouquets.tv indexes
        self._save_bouquet_index_entries(iptv_bouquet_list)

        print("bouquets created ...")

    def create_epgimporter_config(self):
        indent = "  "
        if DEBUG:
            print('creating EPGImporter config')
        # create channels file
        try:
            os.makedirs(EPGIMPORTPATH)
        except OSError, e:  # race condition guard
            if e.errno != errno.EEXIST:
                raise
        channels_filename = os.path.join(EPGIMPORTPATH, 'suls_iptv_{}_channels.xml'.format(get_safe_filename(self.name)))

        if self._dictchannels:
            with open(channels_filename, "w+") as f:
                f.write('<channels>\n')
                for cat in self._category_order:
                    if cat in self._dictchannels:
                        if not cat.startswith('VOD'):
                            cat_title = get_category_title(cat, self._category_options)

                            f.write('{}<!-- {} -->\n'.format(indent, xml_safe_comment(xml_escape(cat_title.encode('utf-8')))))
                            for x in self._dictchannels[cat]:
                                if not x['stream-name'].startswith('placeholder_'):
                                    tvg_id = x['tvg-id'] if x['tvg-id'] else get_service_title(x)
                                    if x['enabled']:
                                        # force the epg channels to stream type '1'
                                        epg_service_ref = x['serviceRef']
                                        pos = epg_service_ref.find(':')
                                        if pos != -1:
                                            epg_service_ref = '1{}'.format(epg_service_ref[pos:])
                                        f.write('{}<channel id="{}">{}:http%3a//example.m3u8</channel> <!-- {} -->\n'
                                                .format(indent, xml_escape(tvg_id.encode('utf-8')), epg_service_ref,
                                                        xml_safe_comment(xml_escape(get_service_title(x).encode('utf-8')))))
                f.write('</channels>\n')

            # create epg-importer sources file for providers feed
            self._create_epgimport_source([self.epg_url])

            # create epg-importer sources file for additional feeds
            for group in self.xmltv_sources_list:
                self._create_epgimport_source(self.xmltv_sources_list[group], group)

    def provider_update(self):
        if self.provider_update_url and self.username and self.password:
            return self._process_provider_update()
        return False

    def _process_provider_update(self):
        """Download provider update file from url"""
        downloaded = False
        updated = False

        path = tempfile.gettempdir()
        filename = os.path.join(path, 'provider-{}-update.txt'.format(self.name))
        print('\n----Downloading providers update file----')
        print('provider update url = ', self.provider_update_url)
        try:
            context = ssl._create_unverified_context()
            urllib.urlretrieve(self.provider_update_url, filename, context=context)
            downloaded = True
        except Exception:
            pass  # fallback to no ssl context

        if not downloaded:
            try:
                urllib.urlretrieve(self.provider_update_url, filename)
            except Exception, e:
                print('[e2m3u2b] process_provider_update error. Type:', type(e))
                print('[e2m3u2b] process_provider_update error: ', e)

        if os.path.isfile(filename):
            try:
                with open(filename, 'r') as f:
                    line = f.readline().strip()
                if line:
                    provider_tmp = {
                        'name': line.split(',')[0],
                        'm3u': line.split(',')[1],
                        'epg': line.split(',')[2],
                    }
                    # check we have name and m3u values
                    if provider_tmp.get('name') and provider_tmp.get('m3u'):
                        self.name = provider_tmp['name']
                        self.m3u_url = provider_tmp['m3u']
                        self.epg_url = provider_tmp.get('epg', self.epg_url)
                        self.last_provider_update = int(time.time())
                        updated = True
            except IndexError, e:
                print('[e2m3u2b] _process_provider_update error unable to read providers update file')

            if not DEBUG:
                os.remove(filename)
        return updated


class Config:
    def __init__(self):
        self.providers = OrderedDict()

    def make_default_config(self, configfile):
        print('Default configuration file created in {}\n'.format(os.path.join(CFGPATH, 'config.xml')))

        f = open(configfile, 'wb')
        f.write("""<!--\r
    E2m3u2bouquet supplier config file\r
    Add as many suppliers as required and run the script with no parameters\r
    this config file will be used and the relevant bouquets set up for all suppliers entered\r
    0 = No/false\r
    1 = Yes/true\r
    For elements with <![CDATA[]] enter value between brackets e.g. <![CDATA[mypassword]]>\r
-->\r
<config>\r
    <supplier>\r
        <name>Supplier Name 1</name><!-- Supplier Name -->\r
        <enabled>1</enabled><!-- Enable or disable the supplier (0 or 1) -->\r
        <m3uurl><![CDATA[http://address.yourprovider.com:80/get.php?username=USERNAME&password=PASSWORD&type=m3u_plus&output=ts]]></m3uurl><!-- Extended M3U url -->\r
        <epgurl><![CDATA[http://address.yourprovider.com:80/xmltv.php?username=USERNAME&password=PASSWORD]]></epgurl><!-- XMLTV EPG url -->\r
        <username><![CDATA[]]></username><!-- (Optional) will replace USERNAME placeholder in urls -->\r
        <password><![CDATA[]]></password><!-- (Optional) will replace PASSWORD placeholder in urls -->\r
        <iptvtypes>0</iptvtypes><!-- Change all streams to IPTV type (0 or 1) -->\r
        <streamtypetv></streamtypetv><!-- (Optional) Custom TV stream type (e.g. 1, 4097, 5001 or 5002) -->\r
        <streamtypevod></streamtypevod><!-- (Optional) Custom VOD stream type (e.g. 4097, 5001 or 5002) -->\r
        <multivod>0</multivod><!-- Split VOD into seperate categories (0 or 1) -->\r
        <allbouquet>1</allbouquet><!-- Create all channels bouquet -->\r
        <picons>0</picons><!-- Automatically download Picons (0 or 1) -->\r
        <iconpath>/usr/share/enigma2/picon/</iconpath><!-- Location to store picons -->\r
        <xcludesref>1</xcludesref><!-- Disable service ref overriding from override.xml file (0 or 1) -->\r
        <bouqueturl><![CDATA[]]></bouqueturl><!-- (Optional) url to download providers bouquet - to map custom service references -->\r
        <bouquetdownload>0</bouquetdownload><!-- Download providers bouquet (use default url) must have username and password set above - to map custom service references -->\r
        <bouquettop>0</bouquettop><!-- Place IPTV bouquets at top (0 or 1)-->\r
    </supplier>\r
    <supplier>\r
        <name>Supplier Name</name><!-- Supplier Name -->\r
        <enabled>0</enabled><!-- Enable or disable the supplier (0 or 1) -->\r
        <m3uurl><![CDATA[http://address.yourprovider.com:80/get.php?username=USERNAME&password=PASSWORD&type=m3u_plus&output=ts]]></m3uurl><!-- Extended M3U url -->\r
        <epgurl><![CDATA[http://address.yourprovider.com:80/xmltv.php?username=USERNAME&password=PASSWORD]]></epgurl><!-- XMLTV EPG url -->\r
        <username><![CDATA[]]></username><!-- (Optional) will replace USERNAME placeholder in urls -->\r
        <password><![CDATA[]]></password><!-- (Optional) will replace PASSWORD placeholder in urls -->\r
        <iptvtypes>0</iptvtypes><!-- Change all streams to IPTV type (0 or 1) -->\r
        <streamtypetv></streamtypetv><!-- (Optional) Custom TV service type (e.g. 1, 4097, 5001 or 5002) -->\r
        <streamtypevod></streamtypevod><!-- (Optional) Custom VOD service type (e.g. 4097, 5001 or 5002) -->\r
        <multivod>0</multivod><!-- Split VOD into seperate categories (0 or 1) -->\r
        <allbouquet>1</allbouquet><!-- Create all channels bouquet -->\r
        <picons>0</picons><!-- Automatically download Picons (0 or 1) -->\r
        <iconpath>/usr/share/enigma2/picon/</iconpath><!-- Location to store picons -->\r
        <xcludesref>1</xcludesref><!-- Disable service ref overriding from override.xml file (0 or 1) -->\r
        <bouqueturl><![CDATA[]]></bouqueturl><!-- (Optional) url to download providers bouquet - to map custom service references -->\r
        <bouquetdownload>0</bouquetdownload><!-- Download providers bouquet (use default url) must have username and password set above - to map custom service references -->\r
        <bouquettop>0</bouquettop><!-- Place IPTV bouquets at top (0 or 1)--> \r
    </supplier>\r
</config>""")

    def read_config(self, configfile):
        """ Read Config from file """
        self.providers = OrderedDict()

        tree = ET.ElementTree(file=configfile)
        for node in tree.findall('.//supplier'):
            provider = Provider()

            if node is not None:
                for child in node:
                    if child.tag == 'name':
                        provider.name = '' if child.text is None else child.text.strip()
                    if child.tag == 'enabled':
                        provider.enabled = True if child.text == '1' else False
                    if child.tag == 'settingslevel':
                        provider.settings_level = '' if child.text is None else child.text.strip()
                    if child.tag == 'm3uurl':
                        provider.m3u_url = '' if child.text is None else child.text.strip()
                    if child.tag == 'epgurl':
                        provider.epg_url = '' if child.text is None else child.text.strip()
                    if child.tag == 'username':
                        provider.username = '' if child.text is None else child.text.strip()
                    if child.tag == 'password':
                        provider.password = '' if child.text is None else child.text.strip()
                    if child.tag == 'providerupdate':
                        provider.provider_update_url = '' if child.text is None else child.text.strip()
                    if child.tag == 'iptvtypes':
                        provider.iptv_types = True if child.text == '1' else False
                    if child.tag == 'streamtypetv':
                        provider.streamtype_tv = '' if child.text is None else child.text.strip()
                    if child.tag == 'streamtypevod':
                        provider.streamtype_vod = '' if child.text is None else child.text.strip()
                    if child.tag == 'multivod':
                        provider.multi_vod = True if child.text == '1' else False
                    if child.tag == 'allbouquet':
                        provider.all_bouquet = True if child.text == '1' else False
                    if child.tag == 'picons':
                        provider.picons = True if child.text == '1' else False
                    if child.tag == 'iconpath':
                        provider.icon_path = '' if child.text is None else child.text.strip()
                    if child.tag == 'xcludesref':
                        provider.sref_override = True if child.text == '0' else False
                    if child.tag == 'bouqueturl':
                        provider.bouquet_url = '' if child.text is None else child.text.strip()
                    if child.tag == 'bouquetdownload':
                        provider.bouquet_download = True if child.text == '1' else False
                    if child.tag == 'bouquettop':
                        provider.bouquet_top = True if child.text == '1' else False
                    if child.tag == 'lastproviderupdate':
                        provider.last_provider_update = 0 if child.text is None else child.text.strip()

            if provider.name:
                self.providers[provider.name] = provider

    def write_config(self):
        """Write providers to config file
        Manually write instead of using ElementTree so that we can format the file for easy human editing
        (inc. Windows line endings)
        """

        config_file = os.path.join(os.path.join(CFGPATH, 'config.xml'))
        indent = "  "

        if self.providers:
            with open(config_file, 'wb') as f:
                f.write('<!--\r\n')
                f.write('{}E2m3u2bouquet supplier config file\r\n'.format(indent))
                f.write('{}Add as many suppliers as required\r\n'.format(indent))
                f.write('{}this config file will be used and the relevant bouquets set up for all suppliers entered\r\n'.format(indent))
                f.write('{}0 = No/False\r\n'.format(indent))
                f.write('{}1 = Yes/True\r\n'.format(indent))
                f.write('{}For elements with <![CDATA[]] enter value between empty brackets e.g. <![CDATA[mypassword]]>\r\n'.format(indent))
                f.write('-->\r\n')
                f.write('<config>\r\n')

                for key, provider in self.providers.iteritems():
                    f.write('{}<supplier>\r\n'.format(indent))
                    f.write('{}<name>{}</name><!-- Supplier Name -->\r\n'.format(2 * indent, xml_escape(provider.name)))
                    f.write('{}<enabled>{}</enabled><!-- Enable or disable the supplier (0 or 1) -->\r\n'.format(2 * indent, '1' if provider.enabled else '0'))
                    f.write('{}<settingslevel>{}</settingslevel>\r\n'.format(2 * indent, provider.settings_level))
                    f.write('{}<m3uurl><![CDATA[{}]]></m3uurl><!-- Extended M3U url --> \r\n'.format(2 * indent, provider.m3u_url))
                    f.write('{}<epgurl><![CDATA[{}]]></epgurl><!-- XMLTV EPG url -->\r\n'.format(2 * indent, provider.epg_url))
                    f.write('{}<username><![CDATA[{}]]></username><!-- (Optional) will replace USERNAME placeholder in urls -->\r\n'.format(2 * indent, provider.username))
                    f.write('{}<password><![CDATA[{}]]></password><!-- (Optional) will replace PASSWORD placeholder in urls -->\r\n'.format(2 * indent, provider.password))
                    f.write('{}<providerupdate><![CDATA[{}]]></providerupdate><!-- (Optional) Provider update url -->\r\n'.format(2 * indent, provider.provider_update_url))
                    f.write('{}<iptvtypes>{}</iptvtypes><!-- Change all TV streams to IPTV type (0 or 1) -->\r\n'.format(2 * indent, '1' if provider.iptv_types else '0'))
                    f.write('{}<streamtypetv>{}</streamtypetv><!-- (Optional) Custom TV stream type (e.g. 1, 4097, 5001 or 5002 -->\r\n'.format(2 * indent, provider.streamtype_tv))
                    f.write('{}<streamtypevod>{}</streamtypevod><!-- (Optional) Custom VOD stream type (e.g. 4097, 5001 or 5002 -->\r\n'.format(2 * indent, provider.streamtype_vod))
                    f.write('{}<multivod>{}</multivod><!-- Split VOD into seperate categories (0 or 1) -->\r\n'.format(2 * indent, '1' if provider.multi_vod else '0'))
                    f.write('{}<allbouquet>{}</allbouquet><!-- Create all channels bouquet (0 or 1) -->\r\n'.format(2 * indent, '1' if provider.all_bouquet else '0'))
                    f.write('{}<picons>{}</picons><!-- Automatically download Picons (0 or 1) -->\r\n'.format(2 * indent, '1' if provider.picons else '0'))
                    f.write('{}<iconpath>{}</iconpath><!-- Location to store picons) -->\r\n'.format(2 * indent, provider.icon_path if provider.icon_path else ''))
                    f.write('{}<xcludesref>{}</xcludesref><!-- Disable service ref overriding from override.xml file (0 or 1) -->\r\n'.format(2 * indent, '0' if provider.sref_override else '1'))
                    f.write('{}<bouqueturl><![CDATA[{}]]></bouqueturl><!-- (Optional) url to download providers bouquet - to map custom service references -->\r\n'.format(2 * indent, provider.bouquet_url))
                    f.write('{}<bouquetdownload>{}</bouquetdownload><!-- Download providers bouquet (uses default url) must have username and password set above - to map custom service references -->\r\n'.format(2 * indent, '1' if provider.bouquet_download else '0'))
                    f.write('{}<bouquettop>{}</bouquettop><!-- Place IPTV bouquets at top (0 or 1) -->\r\n'.format(2 * indent, '1' if provider.bouquet_top else '0'))
                    f.write('{}<lastproviderupdate>{}</lastproviderupdate><!-- Internal use -->\r\n'.format(2 * indent, provider.last_provider_update))
                    f.write('{}</supplier>\r\n'.format(indent))
                f.write('</config>\r\n')
        else:
            # no providers delete config file
            if os.path.isfile(os.path.join(CFGPATH, 'config.xml')):
                print('no providers remove config')
                os.remove(os.path.join(CFGPATH, 'config.xml'))


def main(argv=None):  # IGNORE:C0111
    # Command line options.
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)
    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%(prog)s {} ({})'.format(program_version, program_build_date)
    program_shortdesc = __doc__.split("\n")[1]
    program_license = """{}

  Copyright 2017. All rights reserved.
  Created on {}.
  Licensed under GNU GENERAL PUBLIC LICENSE version 3
  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
""".format(program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = get_parser_args(program_license, program_version_message)
        args = parser.parse_args()
        uninstall = args.uninstall

        # Core program logic starts here
        urllib._urlopener = AppUrlOpener()
        socket.setdefaulttimeout(30)
        display_welcome()
        if uninstall:
            # Clean up any existing files
            uninstaller()
            # reload bouquets
            reload_bouquets()
            print("Uninstall only, program exiting ...")
            sys.exit(1)  # Quit here if we just want to uninstall
        else:
            make_config_folder()

        # create provider from command line based setup (if passed)
        args_provider = Provider()
        args_provider.m3u_url = args.m3uurl
        args_provider.epg_url = args.epgurl
        args_provider.iptv_types = args.iptvtypes
        args_provider.multi_vod = args.multivod
        args_provider.all_bouquet = args.allbouquet
        args_provider.bouquet_url = args.bouqueturl
        args_provider.bouquet_download = args.bouquetdownload
        args_provider.picons = args.picons
        args_provider.icon_path = args.iconpath
        args_provider.sref_override = not args.xcludesref
        args_provider.bouquet_top = args.bouquettop
        args_provider.name = args.providername
        args_provider.username = args.username
        args_provider.password = args.password
        args_provider.streamtype_tv = args.sttv
        args_provider.streamtype_vod = args.stvod

        if args_provider.m3u_url:
            print('\n**************************************')
            print('E2m3u2bouquet - Command line based setup')
            print('**************************************\n')
            args_provider.process_provider()
        else:
            print('\n********************************')
            print('E2m3u2bouquet - Config based setup')
            print('********************************\n')
            e2m3u2b_config = Config()
            if os.path.isfile(os.path.join(CFGPATH, 'config.xml')):
                e2m3u2b_config.read_config(os.path.join(CFGPATH, 'config.xml'))
                providers_updated = False

                for key, provider in e2m3u2b_config.providers.iteritems():
                    if provider.enabled:
                        if provider.name.startswith('Supplier Name'):
                            print("Please enter your details in the config file in - {}".format(os.path.join(CFGPATH, 'config.xml')))
                            sys.exit(2)
                        else:
                            print('\n********************************')
                            print('Config based setup - {}'.format(provider.name))
                            print('********************************\n')

                            if int(time.time()) - int(provider.last_provider_update) > 21600:
                                # wait at least 6 hours (21600s) between update checks
                                providers_updated = provider.provider_update()
                            provider.process_provider()
                    else:
                        print('\nProvider: {} is disabled - skipping.........\n'.format(provider.name))

                if providers_updated:
                    e2m3u2b_config.write_config()

            else:
                e2m3u2b_config.make_default_config(os.path.join(CFGPATH, 'config.xml'))
                print('Please ensure correct command line options are passed to the program \n'
                      'or populate the config file in {} \n'
                      'for help use --help\n'.format(os.path.join(CFGPATH, 'config.xml')))
                parser.print_usage()
                sys.exit(1)


    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0

    except Exception, e:
        if DEBUG or TESTRUN:
            raise e
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

if __name__ == "__main__":
    if TESTRUN:
        EPGIMPORTPATH = "H:/Satelite Stuff/epgimport/"
        ENIGMAPATH = "H:/Satelite Stuff/enigma2/"
        PICONSPATH = "H:/Satelite Stuff/picons/"
        CFGPATH = os.path.join(ENIGMAPATH, 'e2m3u2bouquet/')
    sys.exit(main())
else:
    IMPORTED = True
