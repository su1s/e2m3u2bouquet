#!/usr/bin/python
# Main Plugin file
#import enigma

#from Screens.Screen import Screen
#from Components.Label import Label
#from Components.ActionMap import ActionMap
#from Plugins.Plugin import PluginDescriptor
import e2m3u2bouquet


iptv = e2m3u2bouquet.IPTVSetup()

#iptv.download_providers(e2m3u2bouquet.PROVIDERSURL )
cunto = iptv.read_providers(iptv.download_providers(e2m3u2bouquet.PROVIDERSURL ))
names=[]
for provider in iptv.PROVIDERS:
    names.append(provider[0])
print names

# Setup Plugin Config

#config.plugins.E2m3u2bouquet = ConfigSubsection()
#config.plugins.E2m3u2bouquet.provider = ConfigSelection(default = "FAB",choices= names )



class gui(Screen):
    skin = """
    <screen position="center,center" size="500,400" title="IPTV-Bouquet Maker" >
    <widget name="lblProvider" position="30,20" size="200,40" font="Regular;20"/>
	<widget name="lblUsername" position="30,60" size="200,40" font="Regular;20"/>
	<widget name="lblPassword" position="30,100" size="200,40" font="Regular;20"/>
	<widget name="chkmultivod" position="220,140" size="32,32" alphatest="on" zPosition="1" pixmaps="skin_default/icons/lock_off.png,skin_default/icons/lock_on.png"/>
	<widget name="lblmultivod" position="30,140" size="200,40" font="Regular; 22" halign="left" zPosition="2" transparent="0" />
    </screen>"""

    def __init__(self, session, args=None):
        self.session = session
        Screen.__init__(self, session)
        self["lblProvider"] = Label("Provider")
        self["lblUsername"] = Label("Username")
        self["lblPassword"] = Label("Password")
        self["lblmultivod"] = Label("Multi VOD")
        #self['chkmultivod'] = MultiPixmap()
        self["myActionMap"] = ActionMap(["SetupActions"],
                                        {
                                            "ok": self.cancel,
                                            "cancel": self.close  # add the RC Command "cancel" to close your Screen
                                        }, -1)

    def cancel(self):
        self.close(None)


def main(session, **kwargs):
    session.open(gui)


def Plugins(**kwargs):
    return PluginDescriptor(
        name="E2m3u2bouquet",
        description="Usable IPTV for Enigma2",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        fnc=main)
