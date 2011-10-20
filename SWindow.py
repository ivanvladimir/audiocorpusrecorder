#!/usr/bin/env python
# -*- coding: utf-8
# ----------------------------------------------------------------------
# Sentence window to be read
# ----------------------------------------------------------------------
# Ivan Vladimir Meza-Ruiz/ ivanvladimir at turing.iimas.unam.mx
# Caleb Antonio Rascón Estebané/  caleb at turing.iimas.unam.mx
# 2011/IIMAS/UNAM
# ----------------------------------------------------------------------
# SWindow.py is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------------------------------
# Based on example from 
#     Siegfried-Angel Gevatter Pujals <siegfried@gevatter.com>
# Buttons obtain from:
# http://www.openclipart.org/people/Anonymous/Anonymous_Button_Green.svg
# http://www.openclipart.org/people/Anonymous/Anonymous_Button_Red.svg
#
# Under CC0 PD Dedication License 
# http://creativecommons.org/publicdomain/zero/1.0/
#
# Thank you to the anonymous contributor

import gtk
import pango

class DesktopWindow(gtk.Window):
    """ A transparent and borderless window, fixed on the desktop."""
    
    # Based upon the composited window example from:
    # http://www.pygtk.org/docs/pygtk/class-gdkwindow.html
    
    def __init__(self, full,*args):
        
        gtk.Window.__init__(self, *args)
       
        if not full:
            self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)
        self.set_keep_above(True)
        self.set_decorated(False)
        self.stick()
        
        self.screen = self.get_screen()
        rgba = self.screen.get_rgba_colormap()
        self.set_colormap(rgba)
        self.set_app_paintable(True)


    def get_screen_width(self):
        return self.screen.get_width()

    def get_screen_height(self):
        return self.screen.get_height()


class SentenceW:
    """ An example widget, which shows a quote embedded into your desktop."""
    
    def __init__(self,full):
        
        self.window = DesktopWindow(full)

        if full:
            self.window.fullscreen()
        
        self.box = gtk.VBox()
                
        self.window.add(self.box)
       
        self.image = gtk.Image()
        self.image.set_from_file("imgs/green.png")
        self.image.show()
        self.box.pack_start(self.image,expand=False)

        self.label = gtk.Label()
        self.label.modify_font(pango.FontDescription("ubuntu 32"))
        self.box.pack_start(self.label, expand=True)

               
    def main(self):
        gtk.gdk.threads_init()
        gtk.main()

    def hide(self):
        self.image.hide()
        self.label.set_text("")
        self.label.show()        

    def record(self):
        self.image.set_from_file("imgs/red.png")
        self.image.show()

    def show(self,str):
        self.image.set_from_file("imgs/green.png")
        self.label.set_text(str)
        h2=self.window.get_screen_height()
        w2=self.window.get_screen_width()
        (w,h)=self.window.get_size()
        self.window.move((w2-w)/2, (h2-h)/2-(h/2))
        self.window.show_all()        
        

if __name__ == "__main__":
    ints = SentenceW(False)
    sntc=raw_input('>')
    ints.show("This is a test")
    ints.record()
    ints.main()

