# Enigma2 IPTV m3u to bouquet

```
usage: e2m3u2bouquet.py [-h] [-m M3UURL] [-e EPGURL] [-d1 DELIMITER_CATEGORY]
                        [-d2 DELIMITER_TITLE] [-d3 DELIMITER_TVGID]
                        [-d4 DELIMITER_LOGOURL] [-n PROVIDERNAME]
                        [-u USERNAME] [-p PASSWORD] [-i] [-s] [-P]
                        [-q ICONPATH] [-U] [-V]

e2m3u2bouquet.e2m3u2bouquet -- Enigma2 IPTV m3u to bouquet parser

  Copyright 2017. All rights reserved.
  Created on 2017-06-04.
  Licensed under GNU GENERAL PUBLIC LICENSE version 3
  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE

optional arguments:
  -h, --help            show this help message and exit
  -i, --iptvtypes       Treat all stream references as IPTV stream type.
                        (required for some enigma boxes)
  -s, --singlevod       Create single VOD bouquets rather multiple VOD
                        bouquets
  -P, --picons          Automatically download of Picons, this option will
                        slow the execution
  -q ICONPATH, --iconpath ICONPATH
                        Option path to store picons, if not supplied defaults
                        to /usr/share/enigma2/picon/
  -U, --uninstall       Uninstall all changes made by this script
  -V, --version         show program's version number and exit

URL Based Setup:
  -m M3UURL, --m3uurl M3UURL
                        URL to download m3u data from (required)
  -e EPGURL, --epgurl EPGURL
                        URL source for XML TV epg data sources
  -d1 DELIMITER_CATEGORY, --delimiter_category DELIMITER_CATEGORY
                        Delimiter (") count for category - default = 7
  -d2 DELIMITER_TITLE, --delimiter_title DELIMITER_TITLE
                        Delimiter (") count for title - default = 8
  -d3 DELIMITER_TVGID, --delimiter_tvgid DELIMITER_TVGID
                        Delimiter (") count for tvg_id - default = 1
  -d4 DELIMITER_LOGOURL, --delimiter_logourl DELIMITER_LOGOURL
                        Delimiter (") count for logourl - default = 5

Provider Based Setup:
  -n PROVIDERNAME, --providername PROVIDERNAME
                        Host IPTV provider name (FAB/EPIC) (required)
  -u USERNAME, --username USERNAME
                        Your IPTV username (required)
  -p PASSWORD, --password PASSWORD
                        Your IPTV password (required)
```
Visit https://www.suls.co.uk/enigma2-iptv-bouquets-with-epg/ for further information

## Change notes
#### v0.1
* Initial version (Dave Sully)
#### v0.2
* Updated to use providers epg, doesn't need reboot to take effect - so could be scheduled from cron job (Doug MacKay)
#### v0.3
* Complete restructure of the code base to some thing more usable going forward, incorporated Dougs changes to EPG data source  (Dave Sully)
* tvg-id now included in the channels
* better parsing of m3u data (Doug MacKay)
* downloads m3u file from url
* sets custom source to providers xml tv feed (as per Dougs v0.2)
* fixed IPTV streams not playing / having incorrect stream type
* option to make all streams IPTV type
* option to split VOD bouquets by initial category
* all parameters arg based so in theory works for other providers and can be croned
* auto reloads bouquets (Doug MacKay)
* debug \ testrun modes
#### v0.4
* Restructure (again) of code base to bring in some of dougs better structures
* m3u file parsing updated
* channel ordering based on m3u file, bouquet ordering alphabetically or custom.
* create single channels and sources list for EPG-Importer. Only one source now needs to be enabled in the EPG-Importer plugin
* Add Picon download option (thanks to Jose Sanchez for initial code and idea)
* Better args layout and processing
* Mutli VOD by default
* Named provider support (= simplified command line)
* Delimiter options for user defined parsing of the m3u file
* Ability to chose own bouquet sort order
