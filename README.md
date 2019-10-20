# Enigma2 IPTV m3u to bouquet

Latest release can be downloaded from [releases](https://github.com/su1s/e2m3u2bouquet/releases/latest)

## Usage
```
usage: e2m3u2bouquet.py [-h] [-m M3UURL] [-e EPGURL] [-n PROVIDERNAME]
                        [-u USERNAME] [-p PASSWORD] [-i] [-sttv STTV]
                        [-stvod STVOD] [-M] [-a] [-P] [-q ICONPATH] [-xs]
                        [-b BOUQUETURL] [-bd] [-bt] [-U] [-V]

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
  -sttv STTV, --streamtype_tv STTV
                        Stream type for TV (e.g. 1, 4097, 5001 or 5002)
                        overrides iptvtypes
  -stvod STVOD, --streamtype_vod STVOD
                        Stream type for VOD (e.g. 4097, 5001 or 5002)
						overrides iptvtypes
  -M, --multivod        Create multiple VOD bouquets rather than single VOD
                        bouquet
  -a, --allbouquet      Create all channels bouquet
  -P, --picons          Automatically download of Picons, this option will
                        slow the execution
  -q ICONPATH, --iconpath ICONPATH
                        Option path to store picons, if not supplied defaults
                        to /usr/share/enigma2/picon/
  -xs, --xcludesref     Disable service ref overriding from override.xml file
  -b BOUQUET_URL, --bouqueturl BOUQUET_URL
                        URL to download providers bouquet - to map custom
                        service references
  -bd, --bouquetdownload
                        Download providers bouquet (use default url) - to map
                        custom service references
  -bt, --bouquettop     Place IPTV bouquets at top
  -U, --uninstall       Uninstall all changes made by this script
  -V, --version         show program's version number and exit

URL Based Setup:
  -m M3UURL, --m3uurl M3UURL
                        URL to download m3u data from (required)
                        or local file to download (file:///home/iptv/playlist.m3u)
  -e EPGURL, --epgurl EPGURL
                        URL source for XML TV epg data sources

  -n PROVIDERNAME, --providername PROVIDERNAME
                        Host IPTV provider name

Config file based setup
                        No parameters required
                        The script will create a default config file
                        first time it is run, IPTV providers details
                        need to be entered into this file before
                        running the script again
```

## Prerequisites
EPG-Importer plugin is required. This should be available in the plugin feed or already installed.

N.B. OpenPLi may need additional packages installed. If you attempt to run the script and get an error about
missing modules please run
```
opkg update
opkg install python-image python-imaging python-argparse
```

## How to install
* FTP the e2m3u2bouquet.py to your enigma2 box (I would suggest to /etc/enigma2/e2m3u2bouquet)
* SSH to your enigma2 box (using putty or something similar)
* CD to the correct directory if you are not already there
```
cd /etc/enigma2/e2m3u2bouquet
```
* Make script executable
```
chmod 755 e2m3u2bouquet.py
```

## URL Based Setup
Run the script passing the url for your m3u file and the url for your providers XML TV data feed
```
./e2m3u2bouquet.py -m "http://provider_url/get.php?username=YOURUSERNAME&password=YOURPASSWORD&type=m3u_plus&output=ts" -e "http://provider_url/xmltv.php?username=YOURUSERNAME&password=YOURPASSWORD"
```
**NB: you need to replace the username and password values X 2**

If you are with a different provider the script should work but you will obviously need the m3u url (1st parameter) and XML TV url (2nd parameter) for your own provider. Please note the m3u file needs to be the "extended" version if you have the option.

## Config File Setup
No parameters required, just run the script
```
./e2m3u2bouquet.py
```
The script will create a default config.xml file in /etc/enigma2/e2m3u2bouquet the first time it is run
IPTV providers details need to be entered into this file before running the script again

Note: Multiple IPTV providers can be supported via the config.xml

## For Picon Download Support
Add -P and optionally -q /path/to/picon/folder/ if you don't store your picons in the default location. The default location
is `/usr/share/enigma2/picon/` (internal flash) other enigma2 picon search location are `/media/usb/picon/` & `/media/hdd/picon/`.

N.B. If you store the picons on HDD it was spin up whenever they are shown

```
./e2m3u2bouquet.py "http://provider_url/get.php?username=YOURUSERNAME&password=YOURPASSWORD&type=m3u_plus&output=ts" -e "http://provider_url/xmltv.php?username=YOURUSERNAME&password=YOURPASSWORD" -P
```

## Specify all stream types to be IPTV
Default is DVB stream types for live channels and IPTV for VOD, all IPTV type streams may be required if you are unable to record channels.
```
./e2m3u2bouquet.py "http://provider_url/get.php?username=YOURUSERNAME&password=YOURPASSWORD&type=m3u_plus&output=ts" -e "http://provider_url/xmltv.php?username=YOURUSERNAME&password=YOURPASSWORD" -i
```

## Keep VOD all in a single bouquet
./e2m3u2bouquet.py "http://provider_url/get.php?username=YOURUSERNAME&password=YOURPASSWORD&type=m3u_plus&output=ts" -e "http://provider_url/xmltv.php?username=YOURUSERNAME&password=YOURPASSWORD" -s

## Uninstall
./e2m3u2bouquet.py -U

## Help!
```
./e2m3u2bouquet.py --help
```

## Importing EPG Data
* Open EPG-Importer plugin (download it if you haven't already got it)
* Select sources (Blue button on OpenVix)
* Enable the source created by the script (listed under IPTV Bouquet Maker - E2m3u2bouquet)
* Kick off a manual EPG import

## Updating Channels
To update the channels simply run this script again. A scheduled script can
be set up to automate this process (see below)

## Automate channel updates (set up from SSH)
* If your box doesn't already have cron then install it
```
opkg install busybox-cron
```
* open crontab for editing
```
crontab -e
```
Once open press i to switch to INSERT mode enter the following (retype or ctrl-v to paste)
This will automatically run the script at 06:00 & 18:00 every day
```
0 6,18 * * * /etc/enigma2/e2m3u2bouquet/e2m3u2bouquet.py -m "http://provider_url/get.php?username=YOURUSERNAME&password=YOURPASSWORD&type=m3u_plus&output=ts" -e "http://provider_url/xmltv.php?username=YOURUSERNAME&password=YOURPASSWORD"
```
or
```
0 6,18 * * * /etc/enigma2/e2m3u2bouquet/e2m3u2bouquet.py
```
Press ESC follwed by :wq to exit the cron editor and save the entry
You can check the entry with the command below
```
crontab -l
```

(Depending on your box image installing nano `opkg install nano` may set it as the default editor
which makes editing the crontab easier)

## Automate Channel Updates (set up from box GUI)
* Go to 'Menu -> Timers -> CronTimers
* Select the required update frequency
* For the command to run enter i.e. to run at 06:00 & 18:00 enter
```
0 6,18 * * * cd /home/root && ./e2m3u2bouquet.py
```
* Ensure that cron Autostart is active

## Custom Mapping
* Run the script once. It will create `provider_name-sort-current.xml`
* FTP `provider_name-sort-current.xml` to your machine and rename it `provider_name-sort-override.xml`
* For custom bouquet order move the `<category` lines within `<mapping> -> <categories>`
* To disable a bouquet change `enabled="true"` to `enabled="false"`
* For custom channel ordering within a bouquet move the `<channel` lines within `<mapping> -> <channels>`
* To disable a channel change `enabled="true"` to `enabled="false"`
* To change the id used for XML EPG mapping update the `tvg-id` attribute
* To change the service ref (e.g. to map to an existing satellite EPG feed) change the `serviceRef` attribute
  * For example to use the Channel 4 HD DVB-S EPG you would set the serviceRef to "1:0:1:**52D0:814:2:11A0000**:0:0:0" (part in bold SID:TID:NID:Namespace needs to match). If you match a DVB service and also set the streamUrl to blank the DVB service will replace the IPTV service
* FTP `provider_name-sort-override.xml` to your box
* Run the script again and the changes made will be applied

## Change notes
#### v0.1
* Initial version
#### v0.2
* Updated to use providers epg, doesn't need reboot to take effect - so could be scheduled from cron job
#### v0.3
* Complete restructure of the code base to some thing more usable going forward, incorporated Dougs changes to EPG data source
* tvg-id now included in the channels
* better parsing of m3u data
* downloads m3u file from url
* sets custom source to providers xml tv feed (as per Dougs v0.2)
* fixed IPTV streams not playing / having incorrect stream type
* option to make all streams IPTV type
* option to split VOD bouquets by initial category
* all parameters arg based so in theory works for other providers and can be croned
* auto reloads bouquets
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
#### v0.4.1
* Update service number to use numbers unlikely to be in use by existing sat services
* Leave service number gaps between categories to reduce the effect of playlist additions cause the epg to get out of sync
#### v0.4.2
* Fixed error for ACE and FLAWLESS users where ":" in category put the box into an infinite loop
#### v0.5
* Custom mapping feature
  * Reorder bouquets
  * Reorder channels within bouquets
  * Disable entire bouquet or individual channels
  * Ability to change service reference (so that EPG from existing satellite service can be used)
  * Change tvg-id to match other xml epg feeds
  * Support unicode characters in playlist
  * Xml override file can set-up EPG-Importer config for different xmltv feeds
  * Single VOD bouquet now default (use -M for multiple VOD bouquets)
  * Option for all channels bouquet (-a)
#### v0.5.1
* Stream Url no longer output to xml (replaced by clearStreamUrl). This means that custom override
  maps can be shared as they no longer contain username and passwords

#### v0.5.2
* Fix bug where delimiter arguments weren't getting converted to ints

#### v0.5.3
* Minor fixes

#### v0.5.4
* Add nameOverride attribute to xml files to allow channel name or category name to be changed
* Add option to use service references from providers bouquet file. See -b argument
* Add SSL fix for some boxes (unconfirmed if working)
* Improved service ref id generation logic to reduce (hopefully eliminate) id conflicts especially if override file is used
* Add option -xs to stop service refs from override.xml file being used

#### v0.5.5
* Minor fixes

#### v0.5.6
* Minor fixes

#### v0.6
* Better m3u parsing
* Plugin integration

#### v0.6.1
* Dedicated config directory '/etc/enigma2/e2m3u2bouquet'
* Pre Python 2.7.9 SSL context workaround
* Remove delimiter options
* No longer uninstall on each run
* Option to place IPTV bouquets at top or bottom '-bt'
* Consistent channel numbering (best results when IPTV bouquets are set to top). Each new IPTV category
  will start numbering +100 from start of last category
* [plugin] Add /picon option for download path
* [plugin] Show last playlist update
* [plugin] Add override service service refs' option
* [plugin] Add IPTV bouquet position option
* [plugin] Add option download providers bouquet (for custom service refs)

#### v0.6.2
* Put epg-importer source in source cat for new epg-importer version

#### v0.6.3
* Set user agent for downloads

#### v0.7
* Added Config file based setup support
* Support for multiple service providers

#### v0.7.1
* Make sure comments are xml safe
* Extract username and password from m3u url if they are not passed in
* Set services to stream type '1' in epg config so that the epg can be imported if
  serviceapp is overriding stream type '4097' to exteplayer3
* Minor fixes & tidy
* Option for custom stream type for TV and VOD
* Allow https & rtmp services
* Unicode fixes
* Url encoding fixes

### v0.7.3
* Fix issue where main screen showing no text on some skins
* Add option to reset bouquets

### v0.7.4
* Extra checking to ensure that logos are actually images
* Keep provider order from config file

### v0.7.5
* Additional stream url type checking (e.g. live or VOD)

### v0.7.6
* Add nocheck attribute for EpgImporter sources (fix for new EpgImporter version)
* Add m3u8 VOD stream matching

### v0.7.7
* Set extensionless streams as live TV

### v0.8
* When providers bouquet is downloaded (-b or -bd option) now uses full service references
  instead of just the epg relevant part in case it's used for picon naming
* Better multi provider handler e.g. if there is an issue with one provider it
  won't stop the script processing others
* If vod categories are out of order in the playlist group together
* Fix file naming issues with non alphanumeric characters
* Much faster when using an override file :)
* Don't retry failed picon downloads
* Option to add placeholder channel in override file (to control channel numbering)
* Allow channels to be moved between categories, use categoryOverride in the override file
* All custom categories, use customCategory="true" in the override file
* Add provider managed update support

Visit https://www.suls.co.uk/enigma2-iptv-bouquets-with-epg/ for further information on the script
