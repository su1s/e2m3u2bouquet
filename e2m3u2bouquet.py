#!/usr/bin/python 
# encoding: utf-8
# Change notes 
# v0.1 - Initial version (Dave Sully) 
# v0.2 - Updated to use providers epg, doesn't need reboot to take effect - so could be scheduled from cron job (Doug MacKay)
# v0.3 - Complete restructure of the code base to some thing more usable going forward, incorporated Dougs changes to EPG data source  (Dave Sully)
#      -  tvg-id now included in the channels
#      -  better parsing of m3u data (Doug MacKay)
#      -  downloads m3u file from url
#      -  sets custom source to providers xml tv feed (as per Dougs v0.2)
#      -  fixed IPTV streams not playing / having incorrect stream type 
#      -  option to make all streams IPTV type
#      -  option to split VOD bouquets by initial category
#      -  all paramters arg based so in theory works for other providers and can be croned
#      -  auto reloads bouquets (Doug MacKay) 
#      -  debug \ testrun modes  
        
'''
e2m3u2bouquet.e2m3u2bouquet -- Enigma2 IPTV m3u to bouquet parser  

@author:     Dave Sully Doug MacKay
@copyright:  2017 All rights reserved.
@license:    http://www.apache.org/licenses/LICENSE-2.0
@contact:    me@you.com
@deffield    updated: Updated
'''
import sys
import os

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
#from crontab import CronTab

__all__ = []
__version__ = 0.3
__date__ = '2017-06-04'
__updated__ = '2017-06-04'

DEBUG = 0
TESTRUN = 0

ENIGMAPATH = "/etc/enigma2/"
EPGIMPORTPATH = "/etc/epgimport/"

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg

# Clean up routine to remove any previously made changes
def uninstaller():
    print("----Running uninstall----")
    try:
        # m3u file 
        print("Removing old m3u files...")
        if os.path.isfile(os.getcwd()+"/e2m3u2bouquet.m3u"):
            os.remove(os.getcwd()+"/e2m3u2bouquet.m3u")
        # Bouquets
        print("Removing old IPTV bouquets...")
        for fname in os.listdir(ENIGMAPATH):
            if "userbouquet.suls_iptv_" in fname:
                os.remove(ENIGMAPATH+fname)
            elif "bouquets.tv.bak" in fname:
                os.remove(ENIGMAPATH+fname)
        # Custom Channels and sources 
        print("Removing IPTV custom channels...")
        for fname in os.listdir(EPGIMPORTPATH):
            if "suls_iptv_" in fname:
                os.remove(EPGIMPORTPATH+fname)    
        # bouquets.tv
        print("Removing IPTV bouquets from bouquets.tv...")
        os.rename(ENIGMAPATH + "bouquets.tv",ENIGMAPATH + "bouquets.tv.bak")
        tvfile = open(ENIGMAPATH + "bouquets.tv","w+")
        bakfile = open(ENIGMAPATH + "bouquets.tv.bak")
        for line in bakfile:
            if ".suls_iptv_" not in line:
                tvfile.write(line)
        bakfile.close()
        tvfile.close() 
    except Exception, e:
            raise(e)
    print("----Uninstall complete----")

# Download m3u file from url    
def download_m3u(url):
    import urllib
    print("\n----Downloading m3u file----")
    if DEBUG:
        print("m3uurl="+url)
    try:
        webFile = urllib.urlopen(url)
        localFile = open("e2m3u2bouquet.m3u", 'w')
        localFile.write(webFile.read())
        webFile.close()
    except Exception, e:
            raise(e)
    print("file saved as "+os.getcwd()+"/e2m3u2bouquet.m3u")
    return os.getcwd()+"/e2m3u2bouquet.m3u"

# core parsing routine 
def parsem3u(filename,all_iptv_stream_types,multivod):
    # Extract and generate the following items from the m3u
    #0 category 
    #1 title 
    #2 tvg-id
    #3 stream url    
    #4 stream type
    #5 channel ID 
    print("\n----Parsing m3u file----")
    listchannels=[]
    with open (filename, "r") as myfile:
        for line in myfile:
            if 'EXTM3U' in line: # First line we are not interested 
                continue    
            elif 'EXTINF:' in line: # Info line - work out group and output the line
                channels = [line.split('"')[7],(line.split('"')[8])[1:].strip(),line.split('"')[1]]
            elif 'http:' in line:  
                channels.append(line.strip())
                listchannels.append(channels)
    # Clean up VOD and create stream types  
    for x in listchannels:
        if x[3].endswith(('.mp4','mkv','.avi',"mpg")):
            if multivod:
                x[0] = "VOD - "+x[0]
            else:
                x[0] = "VOD"
            x.append("4097")
        elif all_iptv_stream_types:
            x.append("4097")
        else: 
            x.append("1")
    # Sort the list 
    listchannels.sort()
    # Add Service references 
    num =1 
    for x in listchannels:
        x.append(x[4]+":0:1:"+str(num)+":0:0:0:0:0:0")
        num += 1
    # Have a look at what we have      
    if DEBUG and TESTRUN:
        datafile = open("channels.debug","w+")
        for line in listchannels:
            datafile.write(":".join(line)+"\n")
        datafile.close()
    print("Completed parsing data...")
    return listchannels

def create_bouquets(listchannels):
    print("\n----Creating bouquets----")
    for x in listchannels:
        # Create file if does exits 
        if not os.path.isfile(ENIGMAPATH + "userbouquet.suls_iptv_"+x[0].replace(" ","_").replace("/","_")+".tv"):
            #create file 
            if DEBUG:
                print("Creating: "+ENIGMAPATH + "userbouquet.suls_iptv_"+x[0].replace(" ","_").replace("/","_")+".tv")
            bouquetfile = open(ENIGMAPATH + "userbouquet.suls_iptv_"+x[0].replace(" ","_").replace("/","_")+".tv","w+")
            bouquetfile.write("#NAME IPTV - "+x[0].replace("/"," ")+"\n")
            bouquetfile.write("#SERVICE "+x[5]+":"+x[3].replace(":","%3a")+":"+x[2]+"\n")
            bouquetfile.write("#DESCRIPTION "+x[1]+"\n")
            bouquetfile.close()
            # Add to main bouquets files 
            tvfile = open(ENIGMAPATH + "bouquets.tv","a")
            tvfile.write("#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"userbouquet.suls_iptv_"+x[0].replace(" ","_").replace("/","_")+".tv\" ORDER BY bouquet\n")
            tvfile.close()
        else: 
            #Append to file 
            bouquetfile = open(ENIGMAPATH + "userbouquet.suls_iptv_"+x[0].replace(" ","_").replace("/","_")+".tv","a")
            bouquetfile.write("#SERVICE "+x[5]+":"+x[3].replace(":","%3a")+":"+x[2]+"\n")
            bouquetfile.write("#DESCRIPTION "+x[1]+"\n")
            bouquetfile.close()
    print("bouquets created ...")      

def reloadBouquets():        
    if not TESTRUN:
        print("\n----Reloading bouquets----")
        os.system("wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 > /dev/null 2>&1 &")
        print("bouquets reloaded...")

def create_custom_channel(bouquet,listchannels):
    if DEBUG:
        print("creating custom channel - " + bouquet)
    #create channels file and opening tag
    channelfile = open(EPGIMPORTPATH + "suls_iptv_"+bouquet.replace(" ","_").replace("/","_")+".channels.xml","w+")
    channelfile.write("<channels>\n")
    # loop through list out putting matching stuff 
    for x in listchannels:
        if x[0] == bouquet:
            # now using tvg-id from the mm3u file rather than dodgy cleaning attempts 
            channelfile.write("<channel id=\""+x[2].replace("&","&amp;")+"\">"+x[5]+":http%3a//example.m3u8</channel> <!-- "+x[1]+" -->\n")
    # Write closing tag and close file 
    channelfile.write("</channels>\n")
    channelfile.close()

def create_custom_source(bouquet,epgurl):
    if DEBUG:
        print("creating custom source - " + bouquet)
    #create custom sources file 
    sourcefile = open(EPGIMPORTPATH + "suls_iptv_"+bouquet.replace(" ","_").replace("/","_")+".sources.xml","w+")
    sourcefile.write("<sources><source type=\"gen_xmltv\" channels=\"" + EPGIMPORTPATH +"suls_iptv_"+bouquet.replace(" ","_").replace("/","_")+".channels.xml\">\n")
    sourcefile.write("<description>IPTV - "+bouquet.replace("/"," ")+"</description>\n")
    sourcefile.write("<url>" + epgurl[0].replace("&","&amp;") + "</url>\n")
    sourcefile.write("</source></sources>\n")
    sourcefile.close()

# crontab not installed in enigma by default / pip also missing - not sure how to get this in at the moment  
#def create_cron():
    #if not TESTRUN:
        #print("\n----Creating cron job----")
        #cron = CronTab(user="root")
        #job = cron.new(command = 'python /home/root/e2m3u2bouquet.py "http://stream.fabiptv.com:25461/get.php?username=UN&password=PW&type=m3u_plus&output=ts" "http://stream.fabiptv.com:25461/xmltv.php?username=UN&password=PW"')
        #job.comment = "e2m3u2bouquet"
        #job.minute.every(2)
        #cron.write()
        #print("cron job created, bouquets will autoupdate...")
    
def main(argv=None): # IGNORE:C0111
    #Command line options.
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)
    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = '''%s

  Copyright 2017. All rights reserved.
  Created on %s.  
  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument(dest="m3uurl", help="URL to download m3u data from  ", metavar="m3uurl", nargs='+')
        parser.add_argument(dest="epgurl", help="URL source for XML TV epg data sources ", metavar="epgurl", nargs='+')
        parser.add_argument("-i", "--iptvtypes", dest="iptvtypes", action="store_true", help="Treat all stream references as IPTV stream type. (required for some enigma boxes)")
        parser.add_argument("-m", "--multivod", dest="multivod", action="store_true", help="Create multiple VOD bouquets based on category rather than 1 bouquet for all VOD content")
        parser.add_argument("-U", "--uninstall", dest="uninstall", action="store_true", help="Uninstall all changes made by this script")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)
        # Process arguments
        args = parser.parse_args()
        m3uurl = args.m3uurl[0]
        epgurl = args.epgurl
        iptvtypes = args.iptvtypes
        uninstall = args.uninstall
        multivod = args.multivod
    
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    
    except Exception, e:
        if DEBUG or TESTRUN:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2
    # welcome message 
    print("\n********************************")        
    print("Starting Engima2 IPTV bouquets")
    print("********************************\n") 
    # Clean up any existing files 
    uninstaller()
    if uninstall:
        print("Uninstall only, program exiting ...")
        sys.exit(1) # Quit here if we just want to uninstall
    # Download m3u 
    m3ufile = download_m3u(m3uurl)
    # Test m3u format 
    #### TO DO ####
    # parse m3u file
    listchannels = parsem3u(m3ufile,iptvtypes,multivod)
    # Create bouquet files 
    create_bouquets(listchannels)
    # Create list of bouquets 
    bouquets= []
    for x in listchannels:
        if x[0] not in bouquets:
            bouquets.append(x[0])
    # Now create custom channels for each bouquet
    print("\n----Creating custom channels----")
    for bouquet in bouquets:
        create_custom_channel(bouquet,listchannels)
    print("custom channels created...")    
    # Finally create custom sources for each bouquet
    print("\n----Creating custom sources----")
    for bouquet in bouquets:
        create_custom_source(bouquet,epgurl)
    print("custom sources created...")    
    # Now create a cron job 
    #create_cron()
    # *Borrow* dougs better ending message and reload bouquets code
    # reload bouquets
    reloadBouquets()
    print("\n********************************")        
    print("Engima2 IPTV bouquets created ! ")
    print("********************************")        
    print("\nTo enable EPG data")
    print("Please open EPGImport plugin.. ")
    print("Select sources and enable the new IPTV sources (these start IPTV - )")
    print("Save the selected sources, press yellow button to start manual import")
    print("You can then set EPGImport to automatically import the EPG every day")

if __name__ == "__main__":
    #if DEBUG:
    if TESTRUN:
        EPGIMPORTPATH="H:/Satelite Stuff/epgimport/"
        ENIGMAPATH="H:/Satelite Stuff/enigma2/"
    sys.exit(main())