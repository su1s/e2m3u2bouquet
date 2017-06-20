#!/usr/bin/env python 
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
# v0.3.1 - Restructure (again) of code base to bring in some of dougs better structures
#        - m3u file parsing updated ..
#        - create single channels and sources list for EPG-Importer. Only one source now needs to be enabled in the EPG-Importer plugin
#        - Add Picon download option (thanks to Jose Sanchez for initial code and idea)
#        - Added custom bouquet ordering

        
'''
e2m3u2bouquet.e2m3u2bouquet -- Enigma2 IPTV m3u to bouquet parser  

@author:     Dave Sully, Doug MacKay
@copyright:  2017 All rights reserved.
@license:    GNU GENERAL PUBLIC LICENSE version 3
@deffield    updated: Updated
'''
import sys
import os, re, unicodedata
import datetime
import urllib
import imghdr
from PIL import Image
from collections import OrderedDict
import glob
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
#from crontab import CronTab

__all__ = []
__version__ = 0.31
__date__ = '2017-06-04'
__updated__ = '2017-06-20'

DEBUG = 1
TESTRUN = 1

ENIGMAPATH = "/etc/enigma2/"
EPGIMPORTPATH = "/etc/epgimport/"
PICONSPATH = "/usr/share/enigma2/picon/"
PROVIDER = "FabIPTV"

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg

class IPTVSetup:
    def __init__(self):
        # welcome message 
        print("\n********************************")        
        print("Starting Engima2 IPTV bouquets")
        print(str(datetime.datetime.now()))
        print("********************************\n") 
        
    # Clean up routine to remove any previously made changes
    def uninstaller(self):
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
    def download_m3u(self, url):
        filename = os.path.join(os.getcwd(), 'e2m3u2bouquet.m3u')
        print("\n----Downloading m3u file----")
        if DEBUG:
            print("m3uurl="+url)
        try:
            urllib.urlretrieve(url, filename)
        except Exception, e:
            raise(e)                    
        return filename

    # core parsing routine 
    def parsem3u(self, filename,all_iptv_stream_types,multivod,picons):
        # Extract and generate the following items from the m3u
        #0 category 
        #1 title 
        #2 tvg-id
        #3 logo url        
        #4 stream url    
        #5 stream type
        #6 service Ref 
        
        print("\n----Parsing m3u file----")        
        try:
            if not os.path.getsize(filename):
                raise Exception, "File is empty"
        except Exception, e:
            raise(e)
            
        listcategories=[]
        listchannels=[]
        with open (filename, "r") as myfile:
            for line in myfile:
                if 'EXTM3U' in line: # First line we are not interested 
                    continue    
                elif 'EXTINF:' in line: # Info line - work out group and output the line
                    channel = [line.split('"')[7],(line.split('"')[8])[1:].strip(),line.split('"')[1],line.split('"')[5]]
                elif 'http:' in line:  
                    channel.append(line.strip())
                    channeldict = {'category':channel[0],'title':channel[1],'tvgId':channel[2],'logoUrl':channel[3],'streamUrl':channel[4]}
                    listchannels.append(channeldict)
					
        # Clean up VOD to single or multi bouquet and create stream types  
        for x in listchannels:
            if x['streamUrl'].endswith(('.mp4','mkv','.avi',"mpg")):
                if multivod:
                    x['category'] = "VOD - "+x['category']
                else:
                    x['category'] = "VOD"
                x['streamType'] = "4097"                
            elif all_iptv_stream_types:
                x['streamType'] = "4097"
            else: 
                x['streamType'] = "1"
        
        # get category list (keep order from m3u file)
        for x in listchannels:
            if x['category'] not in listcategories:
                listcategories.append(x['category'])
        #sort categories by name
        listcategories.sort()
        #sort categories by custom order (if exists)
        sortedcategories = self.parse_bouquet_map()
        sortedcategories.extend(listcategories)
        #remove duplicates, keep order
        listcategories = OrderedDict((x, True) for x in sortedcategories).keys()
        
        #Sort the channels by category
        #listchannels.sort(key=lambda x: x['category'])
        #listchannels.sort(key=lambda x: listcategories.index(x['category']))        
        category_order_dict = {category: index for index, category in enumerate(listcategories)}
        listchannels.sort(key=lambda x: category_order_dict[x['category']])

        # Add Service references
        num =1 
        for x in listchannels:
            x['serviceRef'] = x['streamType']+":0:1:"+str(num)+":0:0:0:0:0:0"            
            num += 1
        # Have a look at what we have      
        if DEBUG and TESTRUN:
            datafile = open(EPGIMPORTPATH + "channels.debug","w+")
            for line in listchannels:                
                linevals = ""
                for key, value in line.items():
                    linevals += value + ":"
                datafile.write(linevals+"\n")
            datafile.close()
        print("Completed parsing data...")
        
        if picons:
            print("\n----Downloading Picon files please be patient----")
            print("If no Picons exist this will take a few minutes")
            for x in listchannels:
                #Download Picon if not VOD
                if not x['category'].startswith('VOD'):
                    self.download_picon(x['logoUrl'],x['title'])
            print("Picons downloads completed...")
            print("Box will need restarted for Picons to show...")
        return (listcategories, listchannels)
    
    def parse_bouquet_map(self):
        category_order=[]
        mappingfile=os.getcwd()+"/e2m3u2bouquet-sort-override.txt"
        if os.path.isfile(mappingfile):
            with open (mappingfile, "r") as myfile:
                for line in myfile:
                    if not line.startswith('#'):
                        category_order.append(line.rstrip("\n\r"))
        return category_order
    
    def download_picon(self, logourl, title):        
        if logourl:            
            if not logourl.startswith("http"):
                logourl = "http://{}".format(logourl)            
            piconname = self.get_picon_name(title)
            piconfilepath = os.path.join(PICONSPATH,piconname)           
            existingpicon = filter(os.path.isfile, glob.glob(piconfilepath+'*'))

            if not existingpicon:
                if DEBUG:
                    print("Picon file doesn't exist downloading")
                    print('PiconURL: ' + logourl) 
                try:                
                    urllib.urlretrieve(logourl, piconfilepath)                    
                except Exception, e:
                    if DEBUG:                        
                        print(e)
                    return                
                self.picon_post_processing(piconfilepath)

    def picon_post_processing(self, piconfilepath):
        ext = ""        
        #get image type
        try:                
            ext = imghdr.what(piconfilepath)
        except Exception, e:
            if DEBUG:                        
                print(e)
            return 
        #if image but not png convert to png
        if (ext is not None) and (ext is not 'png'):                            
            if DEBUG:
                print("Converting Picon to png")
            try:                
                Image.open(piconfilepath).save(piconfilepath+".{}".format('png'))
            except Exception, e:
                if DEBUG:
                    print(e)
                return
            try:
                #remove non png file
                os.remove(piconfilepath)
            except Exception, e:
                if DEBUG:                        
                    print(e)
                return
        else:
            #rename to correct extension
            try:
                os.rename(piconfilepath, piconfilepath+".{}".format(ext))
            except Exception, e:
                if DEBUG:                        
                    print(e)
            pass
            
    def get_picon_name(self, serviceName):
        name = unicodedata.normalize('NFKD', unicode(serviceName, 'utf_8')).encode('ASCII', 'ignore')
        excludeChars = ['/', '\\', '\'', '"', '`', '?', ' ', '(', ')', ':', '<', '>', '|', '.', '\n', '!']
        name = re.sub('[%s]' % ''.join(excludeChars), '', name)
        name = name.replace('&', 'and')
        name = name.replace('+', 'plus')
        name = name.replace('*', 'star')
        name = name.lower()
        return name

    def create_bouquets(self, listcategories, listchannels):
        print("\n----Creating bouquets----")
        for cat in listcategories:
            if any(x['category'] == cat for x in listchannels):       
                #create file
                if DEBUG:
                    print("Creating: "+ENIGMAPATH + "userbouquet.suls_iptv_"+cat.replace(" ","_").replace("/","_")+".tv")
                bouquetfile = open(ENIGMAPATH + "userbouquet.suls_iptv_"+cat.replace(" ","_").replace("/","_")+".tv","w+")			
                bouquetfile.write("#NAME IPTV - "+cat+"\n")
                for x in listchannels:
                    if x['category'] == cat:
                        bouquetfile.write("#SERVICE "+x['serviceRef']+":"+x['streamUrl'].replace(":","%3a")+":"+x['title']+"\n")
                        bouquetfile.write("#DESCRIPTION "+x['title']+"\n")
                bouquetfile.close()

                # Add to main bouquets.tv file
                tvfile = open(ENIGMAPATH + "bouquets.tv","a")
                tvfile.write("#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"userbouquet.suls_iptv_"+cat.replace(" ","_").replace("/","_")+".tv\" ORDER BY bouquet\n")
                tvfile.close()        
        print("bouquets created ...")      
    
    def reloadBouquets(self):        
        if not TESTRUN:
            print("\n----Reloading bouquets----")
            os.system("wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 > /dev/null 2>&1 &")
            print("bouquets reloaded...")
    
    def create_epgimporter_config(self, listcategories, listchannels, epgurl):
        if DEBUG:
            print("creating EPGImporter config")
        #create channels file        
        channelfile = open(EPGIMPORTPATH + "suls_iptv_channels.channels.xml","w+")		
        nonvodcatgories = (cat for cat in listcategories if not cat.startswith('VOD'))
        channelfile.write("<channels>\n")
        for cat in nonvodcatgories:
            if any(x['category'] == cat for x in listchannels):
                channelfile.write("<!-- "+cat.replace("&","&amp;")+" -->\n")            
                for x in listchannels:
                    if x['category'] == cat:					
                        channelfile.write("<channel id=\""+x['tvgId'].replace("&","&amp;")+"\">"+x['serviceRef']+":http%3a//example.m3u8</channel> <!-- "+x['title'].replace("&","&amp;")+" -->\n")						
        channelfile.write("</channels>\n")
        channelfile.close()
        
        #create custom sources file
        sourcefile  = open(EPGIMPORTPATH + "suls_iptv_sources.sources.xml","w+")
        sourcefile.write("<sources><source type=\"gen_xmltv\" channels=\"/etc/epgimport/suls_iptv_channels.channels.xml\">\n")
        sourcefile.write("<description>"+PROVIDER.replace("&","&amp;")+"</description>\n")
        sourcefile.write("<url>"+epgurl.replace("&","&amp;")+"</url>\n")		
        sourcefile.write("</source></sources>\n")
        sourcefile.close()

    # crontab not installed in enigma by default / pip also missing - not sure how to get this in at the moment  
    #def create_cron(self):
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
  Licensed under GNU GENERAL PUBLIC LICENSE version 3
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
        parser.add_argument("-p", "--picons", dest="picons", action="store_true", help="Automatically download of PIcons, this option will slow the execution")
        parser.add_argument("-U", "--uninstall", dest="uninstall", action="store_true", help="Uninstall all changes made by this script")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)
        # Process arguments
        args = parser.parse_args()
        m3uurl = args.m3uurl[0]
        epgurl = args.epgurl[0]
        iptvtypes = args.iptvtypes
        uninstall = args.uninstall
        multivod = args.multivod
        picons = args.picons
    
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
    
    
    ## Core program logic starts here     
    e2m3uSetup = IPTVSetup()
    if uninstall:
        # Clean up any existing files
        e2m3uSetup.uninstaller()
        # reload bouquets
        e2m3uSetup.reloadBouquets()
        print("Uninstall only, program exiting ...")
        sys.exit(1) # Quit here if we just want to uninstall
    else:
        # Clean up any existing files
        e2m3uSetup.uninstaller()
        # Download m3u         
        m3ufile = e2m3uSetup.download_m3u(m3uurl)
        # parse m3u file
        listcategories, listchannels = e2m3uSetup.parsem3u(m3ufile,iptvtypes,multivod,picons)        
        # Create bouquet files 
        e2m3uSetup.create_bouquets(listcategories,listchannels)        
        # Now create custom channels for each bouquet
        print("\n----Creating EPG-Importer config ----")        
        e2m3uSetup.create_epgimporter_config(listcategories,listchannels,epgurl)
        print("EPG-Importer config created...")            
        # reload bouquets
        e2m3uSetup.reloadBouquets()
        # Now create a cron job 
        #create_cron()
        print("\n********************************")        
        print("Engima2 IPTV bouquets created ! ")
        print("********************************")        
        print("\nTo enable EPG data")
        print("Please open EPG-Importer plugin.. ")
        print("Select sources and enable the new IPTV sources (will be listed as {})".format(PROVIDER))
        print("Save the selected sources, press yellow button to start manual import")
        print("You can then set EPG-Importer to automatically import the EPG every day")

if __name__ == "__main__":
    #if DEBUG:
    if TESTRUN:
        EPGIMPORTPATH="H:/Satelite Stuff/epgimport/"
        ENIGMAPATH="H:/Satelite Stuff/enigma2/"
        PICONSPATH="H:/Satelite Stuff/picons/"
    sys.exit(main())