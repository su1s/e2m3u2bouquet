# Enigma2 IPTV m3u to bouquet

Visit https://www.suls.co.uk/enigma2-iptv-bouquets-with-epg/ for further information

## Change notes
### v0.1
Initial version (Dave Sully)
### v0.2
Updated to use providers epg, doesn't need reboot to take effect - so could be scheduled from cron job (Doug MacKay)
### v0.3
Complete restructure of the code base to some thing more usable going forward, incorporated Dougs changes to EPG data source  (Dave Sully)
tvg-id now included in the channels
better parsing of m3u data (Doug MacKay)
downloads m3u file from url
sets custom source to providers xml tv feed (as per Dougs v0.2)
fixed IPTV streams not playing / having incorrect stream type
option to make all streams IPTV type
option to split VOD bouquets by initial category
all parameters arg based so in theory works for other providers and can be croned
auto reloads bouquets (Doug MacKay)
debug \ testrun modes
### v0.4
Restructure (again) of code base to bring in some of dougs better structures
m3u file parsing updated
bouquet sort order now based on m3u file
create single channels and sources list for EPG-Importer. Only one source now needs to be enabled in the EPG-Importer plugin
Add Picon download option (thanks to Jose Sanchez for initial code and idea)
Better args layout and processing
Mutli VOD by default
Named provider support (= simplified command line)
Delimiter options for user defined parsing of the m3u file
