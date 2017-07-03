# Enigma2 IPTV m3u to bouquet

Latest release can be downloaded from [releases](https://github.com/su1s/e2m3u2bouquet/releases)

## Usage
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

## Pre Requisites
EPG-Importer plugin is required. This should be available in the plugin feed or already installed.

N.B. OpenPLi may need additional packaes installed. If you attempt to run the script and get an error about
missing modules please run
```
opkg update
opkg install python-image python-imaging python-argparse
```

## How to install
* FTP the e2m3u2bouquet.py to your engima2 box (i would suggest to /home/root)
* SSH to your enigma2 box (using putty or something similar)
* CD to the correct directory if you are not already there
```
cd /home/root
```
* Make script executable
```
chmod 755 e2m3u2bouquet.py
```
## Provider Based Setup
```
./e2m3u2bouquet.py -n FAB -u USERNAME -p PASSWORD
```
Supported providers are currently
FAB, EPIC, ULTIMATESPORTS, ACE, POSH

## URL Based Setup
Run the script passing the url for your m3u file and the url for your providers XML TV data feed (for FAB hosting the below works)
```
./e2m3u2bouquet.py -m "http://stream.fabiptv.com:25461/get.php?username=YOURUSERNAME&password=YOURPASSWORD&type=m3u_plus&output=ts" -e "http://stream.fabiptv.com:25461/xmltv.php?username=YOURUSERNAME&password=YOURPASSWORD"
```
**NB: you need to replace the username and password values X 2**

If you are with a different provider the script should work but you will obviously need the m3u url (1st parameter) and XML TV url (2nd parameter) for your own provider. Please note the m3u file needs to be the “extended” version if you have the option.

## For Picon Support
Add -P and optionally -q /path/to/picon/folder/ if you don’t store your picons in the default location. The default location
is `/usr/share/enigma2/picon/` (internal flash) other enigma2 picon search location are `/media/usb/picon/` & `/media/hdd/picon/`.

N.B. If you store the picons on HDD it was spin up whenever they are shown

```
./e2m3u2bouquet.py -n FAB -u USERNAME -p PASSWORD -P
```

## To Reorder Bouquets
Run the script once, it will create e2m3u2bouquet-sort-default.txt in the working directory, FTP this to your machine rename it to e2m3u2bouquet-sort-override.txt put the bouquets into the order you want and FTP it back to the box.

Run the script again and your bouquet order will be as specified.

## Specify all stream types to be IPTV
Default is DVB stream types for live channels and IPTV for VOD, all IPTV type streams may be required if you are unable to record channels.
```
./e2m3u2bouquet.py -n FAB -u USERNAME -p PASSWORD -i
```

## Keep VOD all in a single bouquet
./e2m3u2bouquet.py -n FAB -u USERNAME -p PASSWORD -s

## Uninstall
./e2m3u2bouquet.py -U

## Help!
```
./e2m3u2bouquet.py --help
```

## Importing EPG Data
* Open EPG-Importer plugin (download it if you haven’t already got it)
* Select sources (Blue button on OpenVix)
* Enable the source created by the script (e2m3u2bouquet / FAB / EPIC)
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
0 6,18 * * * cd /home/root && ./e2m3u2bouquet.py -n FAB -u USERNAME -p PASSWORD
```
or
```
0 6,18 * * * cd /home/root && ./e2m3u2bouquet.py -m "http://stream.fabiptv.com:25461/get.php?username=YOURUSERNAME&password=YOURPASSWORD&type=m3u_plus&output=ts" -e "http://stream.fabiptv.com:25461/xmltv.php?username=YOURUSERNAME&password=YOURPASSWORD"
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
0 6,18 * * * cd /home/root && ./e2m3u2bouquet.py -n FAB -u USERNAME -p PASSWORD
```
* Ensure that cron Autostart is active

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
#### v0.4.1
* Update service number to use numbers unlikely to be in use by existing sat services
* Leave service number gaps between categories to reduce the effect of playlist additions cause the epg to get out of sync

Visit https://www.suls.co.uk/enigma2-iptv-bouquets-with-epg/ for further information
