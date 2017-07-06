#!/usr/bin/python
# Main Plugin file
from Screens.Screen import Screen
from Components.Label import Label
from Components.ActionMap import ActionMap
from Plugins.Plugin import PluginDescriptor


class gui(Screen):
    skin = """
    <screen position="center,center" size="600,500" title="Stem = Knobhead, E23mu2bouquet" >
    <widget name="lblProvider" position="10,60" size="200,40" font="Regular;20"/>
    </screen>"""

    def __init__(self, session, args=None):
        self.session = session
        Screen.__init__(self, session)
        self["lblProvider"] = Label("Provider")
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
