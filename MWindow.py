#!/usr/bin/env python
# -*- coding: utf-8
# -----------------------------------------------------------------------
# Main window for the corpus_rec application
# -----------------------------------------------------------------------
# Ivan Vladimir Meza-Ruiz/ ivanvladimir at turing.iimas.unam.mx
# Caleb Antonio Rascón Estebané/  caleb at turing.iimas.unam.mx
# 2011/IIMAS/UNAM
# -----------------------------------------------------------------------
# MWindow is free software: you can redistribute it and/or modify
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

import os
import os.path
import pygtk
pygtk.require('2.0')
import gtk
import re
import socket
from subprocess import PIPE, Popen

import pygst
import gst

import SWindow

re_utts=re.compile('(?P<id>[^\.]*)\. (?P<utt>.*)')

class MainWindow(gtk.Window):
    # Menu
    menu= """<ui>
                 <menubar name="Root">
                    <menu action="file">
                       <menuitem action="open" />
                       <menuitem action="save" />
                       <menuitem action="save_as" />
                       <separator />
                       <menuitem action="close" />
                       <separator />
                       <menuitem action="quit" />
                    </menu>
                    <menu action="play_">
                       <menuitem action="record"/>
                       <menuitem action="play"/>
                       <menuitem action="stop"/>
                       %s
                    </menu>
                    <menu action="help">
                       <menuitem action="about"/>
                    </menu>
                  </menubar>
                  <toolbar action="toolbar">
                    <placeholder name="FileOptions">
                       <separator/>
                       <toolitem name="Open" action="open"/>
                       <toolitem name="Directory" action="sel_dir"/>
                       <toolitem name="Save" action="save"/>
                       <toolitem name="Save as" action="save_as"/>
                       <separator/>
                    </placeholder>
                    <placeholder name="UttOptions">
                       <separator/>
                       <toolitem name="First" action="first"/>
                       <toolitem name="Previous" action="previous"/>
                       <toolitem name="Next" action="next"/>
                       <toolitem name="Last" action="last"/>
                       <separator/>
                    </placeholder>
                    <placeholder name="AudioOptions">
                       <separator/>
                       <toolitem name="Record" action="record"/>
                       <toolitem name="Play" action="play"/>
                       <separator/>
                       <toolitem name="Activate monitor" action="connect"/>
                    </placeholder>
                 </toolbar>
                </ui>"""
                
    def get_actions(self):
        '''Actions for interface'''
        return [
             # Basic
             ('open', gtk.STOCK_OPEN, '_Open...', '<Control>o', None, self.open_file),
             ('sel_dir', gtk.STOCK_HOME, '_Directory', '<Control>h', None, self.directory),
             ('save', gtk.STOCK_SAVE, '_Save', '<Control>s', None, self.save),
             ('save_as', gtk.STOCK_SAVE_AS, 'Save _as...', None, None, self.save_as),
             ('close', gtk.STOCK_CLOSE, '_Close', '<Control>W', None, self.close),
             ('quit', gtk.STOCK_QUIT, '_Quit', '<Control>Q', None, self.quit),
             ('go_utt', None, 'Go to _utterance...', '<Control>U', None, self.hello),
             ('about', None, '_About...', None, None, self.hello),
             ('file', None, '_File'),
             ('play_', None, '_Play'),
             ('help', None, '_Help'),
             #UttOptions
             ('first', gtk.STOCK_GOTO_FIRST, None, '<Control>Left', None, self.go_first),
             ('previous', gtk.STOCK_GO_BACK, None, 'Left', None, self.go_prev),
             ('next', gtk.STOCK_GO_FORWARD, None, 'Right', None, self.go_next),
             ('last', gtk.STOCK_GOTO_LAST, None, '<Controll>Right', None, self.go_last),
             #UttReccord
             ('record', gtk.STOCK_MEDIA_RECORD, None, '<Ctrl>r', None, self.record),
             ('play', gtk.STOCK_MEDIA_PLAY, None, '<Ctrl>p', None, self.play),
             ('stop', gtk.STOCK_MEDIA_STOP, None, '<Ctrl>s', None, self.stop),
             ('connect', gtk.STOCK_CONNECT, None, '<Ctrl>m', None, self.connected)
         ]+[
             ('playn%d'%(i+1), None, 'Play mic %d'%(i+1), None, None, self.playn) for i in range(self.nmics)
         ]
            

    def splitter_callback(self, demuxer, pad):
        '''It identifies the source microphone'''
        pad.link(self.queues[pad.get_name()].get_pad("sink"))

    def init_audio(self):
        '''Initialization audio'''
        self.player = gst.element_factory_make("playbin2", "player")
        fakesink = gst.element_factory_make("fakesink", "fakesink")
        self.player.set_property("video-sink", fakesink)
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.recorder = gst.Pipeline("recorder")
        source = gst.element_factory_make("alsasrc", "alsa-source")
        self.recorder.add(source)
        sourcecaps = gst.element_factory_make("capsfilter", "alsa-source-caps")
        sourcecaps.set_property('caps',gst.Caps('audio/x-raw-int,rate=44100,channels=%d,depth=16'%self.nmics))
        self.recorder.add(sourcecaps)
        splitter = gst.element_factory_make("deinterleave", "split")
        splitter.connect("pad-added", self.splitter_callback)
        self.recorder.add(splitter)

        gst.element_link_many(source,sourcecaps,splitter)
        # Traverse the number of microphones
        self.ofiles=[]
        self.queues={}
        for mic in range(self.nmics):
            converter = gst.element_factory_make("audioconvert","converter%d"%mic)
            self.recorder.add(converter)
            wav = gst.element_factory_make("wavenc", "wav%d"%mic)
            self.recorder.add(wav)
            fileout = gst.element_factory_make("filesink", "sink%d"%mic)
            self.recorder.add(fileout)
            queue = gst.element_factory_make("queue", "queue%d"%mic)
            self.queues['src%d'%mic]=queue
            self.recorder.add(queue)

            # Code for adding a monitor
            #if mic==self.monitor:
            # If this is the mic to be monitor
            #    tee = gst.element_factory_make("tee","tee")
            #    self.recorder.add(tee)
            #    alsasink = gst.element_factory_make("alsasink","alsa-sink")
            #    self.recorder.add(alsasink)
            #    extra_queue1 = gst.element_factory_make("queue", "soundcard")
            #    extra_queue2 = gst.element_factory_make("queue", "normal")
            #    gst.element_link_many(queue,tee)
            #    self.recorder.add(extra_queue1)
            #    self.recorder.add(extra_queue2)
            #    extra_queue1.link(alsasink)
            #    tee.link(extra_queue1)
            #    gst.element_link_many(extra_queue2, converter, wav, fileout)
            #    tee.link(extra_queue2)
            #else:
            #    gst.element_link_many(queue, converter, wav, fileout)
            gst.element_link_many(queue, converter, wav, fileout)
            self.ofiles.append(fileout)


        bus = self.recorder.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_rec_message)

    def verbose(self,MSG):
        if self.verb:
            print MSG

    def  __init__(self,outdir="audio",filename=None,nmics=4,verbose=False,monitor=0,client=False,bind=('127.0.0.1',5000),full=False):
        # Number of microphones
        self.nmics=nmics
        # Verbose mode
        self.verb=verbose
        # Client mode (not display sentence window)
        self.client=client
        # Microphone to monitor
        self.monitor=monitor
        # Output directory for the wavs
        self.outdir=outdir
        # Corpus filename
        self.filename=filename
        # Initalization of audio
        self.init_audio()
        # Utt to display
        self.numUtt=0
        # If stop button present
        self.stop_state=0
        # Rewriting files flag
        self.rewrite=False
        # Dir audio dir create flag
        self.audiodir=False
        # Checking if jack up
        self.jack=self.check_jack()
     
        # Variables
        gtk.Window.__init__(self)
        self.set_size_request(500, 400)
        self.set_title("Aduio Corpus Recorder")
        self.connect("delete_event", lambda w,e: gtk.main_quit())

        # Filters for text files
        filter_text = gtk.FileFilter()
        filter_text.add_mime_type('text/plain')
        filter_text.set_name('Text Corpus')

        filter_all = gtk.FileFilter()
        filter_all.add_pattern('*')
        filter_all.set_name('All files')
 
        # File selectors
        self.file_select = gtk.FileChooserDialog(title="Open",action=gtk.FILE_CHOOSER_ACTION_OPEN,
                buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        self.file_select.set_default_response(gtk.RESPONSE_OK)
        self.file_select.add_filter(filter_text)
        self.file_select.add_filter(filter_all)
        
        # Save as File 
        self.save_as_file_select = gtk.FileChooserDialog(title="Save as",action=gtk.FILE_CHOOSER_ACTION_SAVE,
                buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK))
        self.save_as_file_select.set_default_response(gtk.RESPONSE_OK)
        self.save_as_file_select.add_filter(filter_text)
        self.save_as_file_select.add_filter(filter_all)


        # Dir selector 
        self.open_dir_sel = gtk.FileChooserDialog(title="Choose dir",action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_NEW,gtk.RESPONSE_OK),backend=None)

        # Main window
       

        # XML Readers
        # |---------------------------------|
        # |     Utterance browser           |
        # |---------------------------------|
        # | UTT to record                   |
        # |_________________________________|
        # | Recording controls              |
        # |_________________________________|
        

        # Main container
        vbox = gtk.VBox(False, 0)
        self.add(vbox)
        vbox.show()

        self.create_UI()

        # -- Accel
        self.add_accel_group(self.ui.get_accel_group())

        # -- Menu bar
        vbox.pack_start(self.ui.get_widget('/Root'), False, False, 2)
        
        # -- Toolbar
        vbox.pack_start(self.ui.get_widget('/toolbar'), False, False, 2)
       
        ## Utts
        vboxUtts = gtk.VBox(False, 0)
        vbox.pack_start(vboxUtts,True, True, 2)
        vboxUtts.show()

        ## Utterance 
        ## Initializing the Utterance Model
        #self.utt=UtteranceModel()

        
        ## Utterances browser
        self.utts_list =gtk.ListStore(int,str,int)
        self.utts_browser = gtk.TreeView(self.utts_list)

        self.utts_browser.add_events(gtk.gdk.BUTTON_PRESS_MASK )
        self.utts_browser.connect_after("move-cursor",self.move_cursor)
        self.utts_browser.connect_after('cursor-changed', self.cursor_changed)
        self.utts_browser.connect('button-press-event', self.click)
        
        
        # Creation of the columns
        cell1 = gtk.CellRendererText()
        cell1.set_property('editable', True)
        cell1.connect('edited', self.edited_cell,0)
        cell1.set_property('xalign', 0.0)
        cell2 = gtk.CellRendererText()
        cell2.set_property('editable', True)
        cell2.connect('edited', self.edited_cell,1)
        cell2.set_property('xalign', 0.0)
        self.utts_browser.append_column(gtk.TreeViewColumn("Num",cell1,text=0))
        self.utts_browser.append_column(gtk.TreeViewColumn("Utt",cell2,text=1))

        #self.utts_sel = self.utts_browser.get_selection()
        #self.utts_sel.set_select_function(self.utt_sel, None)
 
         
        self.utts_win = gtk.ScrolledWindow()
        self.utts_browser.show()
        self.utts_win.add(self.utts_browser)
 
        vboxUtts.pack_end(self.utts_win, True, True, 0)

        # Utterance viewer
        frame = gtk.Frame("Utterance")
        self.utt_label = gtk.Label("")
        self.utt_label.set_justify(gtk.JUSTIFY_LEFT)
        self.utt_label.set_selectable(True)
        self.utt_label.show()
        frame.add(self.utt_label)
        vboxUtts.pack_end(frame, False, False, 0)
        frame.show()

                
        self.utts_win.show()
        self.show_all()

        self.status_0()

       
        if filename:
            self.file_select_ok(None)
            self.prefix=os.path.splitext(os.path.basename(self.filename))[0]
        if self.client:
            self.sckt=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sckt.connect(bind)
        else:
            # Ventana auxiliar
            self.sentence=SWindow.SentenceW(full)
            
    def status_0(self):
        '''Default status'''
        self.actiongroup.get_action("open").set_sensitive(True)
        self.actiongroup.get_action("sel_dir").set_sensitive(True)
        self.actiongroup.get_action("save").set_sensitive(False)
        self.actiongroup.get_action("save_as").set_sensitive(False)
        self.actiongroup.get_action("close").set_sensitive(False)
        self.actiongroup.get_action("quit").set_sensitive(True)
        self.actiongroup.get_action("go_utt").set_sensitive(False)
        self.actiongroup.get_action("about").set_sensitive(False)
        self.actiongroup.get_action("first").set_sensitive(False)
        self.actiongroup.get_action("previous").set_sensitive(False)
        self.actiongroup.get_action("next").set_sensitive(False)
        self.actiongroup.get_action("last").set_sensitive(False)
        self.actiongroup.get_action("record").set_sensitive(False)
        self.actiongroup.get_action("play").set_sensitive(False)
        self.actiongroup.get_action("stop").set_sensitive(False)
        self.actiongroup.get_action("connect").set_sensitive(False)
       
        self.status_jack()
        for i in range(self.nmics):
            self.actiongroup.get_action("playn%d"%(i+1)).set_sensitive(False)
            

    def status_open(self):
        '''Status for a open corpus'''
        if len(self.utts_list) > 0:
            self.actiongroup.get_action("open").set_sensitive(True)
            self.actiongroup.get_action("sel_dir").set_sensitive(True)
            self.actiongroup.get_action("save").set_sensitive(True)
            self.actiongroup.get_action("save_as").set_sensitive(True)
            self.actiongroup.get_action("close").set_sensitive(True)
            self.actiongroup.get_action("quit").set_sensitive(True)
            self.actiongroup.get_action("go_utt").set_sensitive(True)
            self.actiongroup.get_action("about").set_sensitive(False)
            self.actiongroup.get_action("first").set_sensitive(True)
            self.actiongroup.get_action("previous").set_sensitive(True)
            self.actiongroup.get_action("next").set_sensitive(True)
            self.actiongroup.get_action("last").set_sensitive(True)
            self.actiongroup.get_action("record").set_sensitive(True)
            self.actiongroup.get_action("play").set_sensitive(True)
            self.actiongroup.get_action("stop").set_sensitive(True)
            self.actiongroup.get_action("play").set_stock_id(gtk.STOCK_MEDIA_PLAY)
            self.actiongroup.get_action("record").set_stock_id(gtk.STOCK_MEDIA_RECORD)
            self.status_jack()
            for i in range(self.nmics):
                self.actiongroup.get_action("playn%d"%(i+1)).set_sensitive(True)
     
        else:
            self.status_0()

    def status_jack(self):
    	if self.jack:
                self.actiongroup.get_action("connect").set_sensitive(True)
                if self.connect:
                    self.actiongroup.get_action("connect").set_stock_id(gtk.STOCK_DISCONNECT)
                else:
                    self.actiongroup.get_action("connect").set_stock_id(gtk.STOCK_CONNECT)
        else:
                self.actiongroup.get_action("connect").set_sensitive(False)



    def status_pause(self):
            '''Status for recording'''
            self.actiongroup.get_action("open").set_sensitive(False)
            self.actiongroup.get_action("sel_dir").set_sensitive(False)
            self.actiongroup.get_action("save").set_sensitive(False)
            self.actiongroup.get_action("save_as").set_sensitive(False)
            self.actiongroup.get_action("close").set_sensitive(False)
            self.actiongroup.get_action("quit").set_sensitive(False)
            self.actiongroup.get_action("go_utt").set_sensitive(False)
            self.actiongroup.get_action("about").set_sensitive(False)
            self.actiongroup.get_action("first").set_sensitive(False)
            self.actiongroup.get_action("previous").set_sensitive(False)
            self.actiongroup.get_action("next").set_sensitive(False)
            self.actiongroup.get_action("last").set_sensitive(False)
            self.actiongroup.get_action("play").set_sensitive(False)
            self.actiongroup.get_action("stop").set_sensitive(False)
            self.actiongroup.get_action("record").set_stock_id(gtk.STOCK_MEDIA_RECORD)
            self.status_jack()
            for i in range(self.nmics):
                self.actiongroup.get_action("playn%d"%(i+1)).set_sensitive(False)
 

    def status_recording(self):
            '''Status for recording'''
            self.actiongroup.get_action("open").set_sensitive(False)
            self.actiongroup.get_action("sel_dir").set_sensitive(False)
            self.actiongroup.get_action("save").set_sensitive(False)
            self.actiongroup.get_action("save_as").set_sensitive(False)
            self.actiongroup.get_action("close").set_sensitive(False)
            self.actiongroup.get_action("quit").set_sensitive(False)
            self.actiongroup.get_action("go_utt").set_sensitive(False)
            self.actiongroup.get_action("about").set_sensitive(False)
            self.actiongroup.get_action("first").set_sensitive(False)
            self.actiongroup.get_action("previous").set_sensitive(False)
            self.actiongroup.get_action("next").set_sensitive(False)
            self.actiongroup.get_action("last").set_sensitive(False)
            self.actiongroup.get_action("play").set_sensitive(False)
            self.actiongroup.get_action("stop").set_sensitive(True)
            self.actiongroup.get_action("record").set_stock_id(gtk.STOCK_MEDIA_STOP)
            self.status_jack()
            for i in range(self.nmics):
                self.actiongroup.get_action("playn%d"%(i+1)).set_sensitive(False)
 

    def status_playing(self):
            '''Status for playing'''
            self.actiongroup.get_action("open").set_sensitive(False)
            self.actiongroup.get_action("sel_dir").set_sensitive(False)
            self.actiongroup.get_action("save").set_sensitive(False)
            self.actiongroup.get_action("save_as").set_sensitive(False)
            self.actiongroup.get_action("close").set_sensitive(False)
            self.actiongroup.get_action("quit").set_sensitive(False)
            self.actiongroup.get_action("go_utt").set_sensitive(False)
            self.actiongroup.get_action("about").set_sensitive(False)
            self.actiongroup.get_action("first").set_sensitive(False)
            self.actiongroup.get_action("previous").set_sensitive(False)
            self.actiongroup.get_action("next").set_sensitive(False)
            self.actiongroup.get_action("last").set_sensitive(False)
            self.actiongroup.get_action("record").set_sensitive(False)
            self.actiongroup.get_action("stop").set_sensitive(True)
            self.actiongroup.get_action("play").set_stock_id(gtk.STOCK_MEDIA_STOP)
            if self.connect:
		self.connected()
            self.actiongroup.get_action("connect").set_sensitive(False)
            for i in range(self.nmics):
                self.actiongroup.get_action("playn%d"%(i+1)).set_sensitive(True)
 

    def cursor_changed(self, widget, data=None):
        treeselection = self.utts_browser.get_selection()
        treeselection.set_mode(gtk.SELECTION_SINGLE)
        (model, iter) = treeselection.get_selected()
        self.numUtt = self.utts_list.get_value(iter, 2)
        self.update_view()

    def click(self, widget, event, data=None):
        if event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
            self.play(None)


    # Creates the UI using the accelerators
    def create_UI(self):
        '''Creates the men'u from the action group
        '''
        self.ui = gtk.UIManager()
        self.actiongroup=gtk.ActionGroup('')
        self.actiongroup.add_actions(self.get_actions())
        extra_menu="<separator />"
        for i in range(self.nmics):
            extra_menu+='<menuitem action="playn%d"/>'%(i+1)
        self.merge_id = self.ui.add_ui_from_string(MainWindow.menu%extra_menu)
        self.ui.insert_action_group(self.actiongroup, 0)
        self.actiongroup.set_sensitive(True)

    def main(self):
        gtk.gdk.threads_init()
        gtk.main()

    def save_file(self,filename):
        try:
            fs=open(filename,"w")
            for row in self.utts_list:
                fs.write(str(row[0]))
                fs.write('. ')
                fs.write(row[1])
                fs.write('\n')
            fs.close()
        except IOError:
            print "Error"


    def utt_sel(self,path, model):
        '''Controls the selection of utterances
        '''
        self.numUtt=path[0]+1
        self.utt_label.set_text(self.utts_list[self.numUtt][1])
        return True

    def edited_cell(self,cell, path, new_text, user_data):
        if user_data==0:
            self.utts_list[path[0]][user_data]=int(new_text)
        else:
            self.utts_list[path[0]][user_data]=new_text
        self.update_view()
        return True

    def move_cursor(self,widget,event,data=None):
       # There was a movement of one column (This is go next utterance)
        treeselection = self.utts_browser.get_selection()
        treeselection.set_mode(gtk.SELECTION_SINGLE)
        (model, iter) = treeselection.get_selected()
        self.numUtt = self.utts_list.get_value(iter, 2)
        self.utts_browser.set_cursor(self.numUtt)  
        self.update_view()


    def go_first(self, data):
        self.utts_browser.set_cursor(0)  
        self.update_view()

    def go_last(self, data):
        self.utts_browser.set_cursor(len(self.utts_list))  
        self.update_view()

    def go_prev(self, data):
        if self.numUtt == 0:
           return
        self.utts_browser.set_cursor(self.numUtt-1)  
        self.update_view()

    def go_next(self, data):
        if self.numUtt == len(self.utts_list)-1:
            return
        self.utts_browser.set_cursor(self.numUtt+1)  
        self.update_view()

    def update_view(self):
        self.utt_label.set_text(self.utts_list[self.numUtt][1])

    # Main actions
    def hello(self, event, data=None):
        print "hello"

    # record
    def record(self, event, data=None):
        if self.stop_state==0:
            self.stop_state=1
            self.status_pause()
            if len(self.utts_list) > 0:
               
                mic=1
                for fileout in self.ofiles:
                    if self.prefix:
                        location="%s_%02d_mic%02d.wav"%(self.prefix,self.utts_list[self.numUtt][0],mic)
                    else:
                        location="%s_%02d_mic%02d.wav"%(self.filename,self.utts_list[self.numUtt][0],mic)
            
                    if self.outdir:
                        location="%s/%s/%s"%(self.outdir,self.prefix,location)
                        if not os.path.exists(location) and not self.audiodir:
                            try:
                                os.mkdir("%s/%s"%(self.outdir,self.prefix))
                            except OSError:
                                pass
                        self.audiodir=True

                    if os.path.exists(location):
                        if not self.rewrite:
                            msg="You are trying to rewrite this file: "+location+"\n Are you sure you want to do this?"

                            md = gtk.MessageDialog(self, 
                                            gtk.DIALOG_DESTROY_WITH_PARENT,
                                            gtk.MESSAGE_QUESTION, 
                                            gtk.BUTTONS_OK_CANCEL, msg)
                            md.set_default_response(gtk.RESPONSE_OK)
                            response=md.run()
                            md.destroy()
                            if not int(response) == int(gtk.RESPONSE_OK):
                                self.status_open()
                                return False
                            self.verbose("Setting rewrite mode")
                            self.rewrite=True
                    self.verbose("Saving file: %s"%location)
                    fileout.set_property("location",location)
                    mic+=1

                sntc=self.utt_label.get_text()
                if not self.client:
                    self.sentence.show(sntc)
                else:
                    self.sckt.send(sntc)
 
            return 
        if self.stop_state==2:
            self.stop_state=0
            self.stop(None)
            return True


        if self.stop_state==1:
            self.status_recording()
            if not self.client:
                self.sentence.record()
            else:
                self.sckt.send(":record")
            self.stop_state=2
            self.recorder.set_state(gst.STATE_PLAYING)
        return True

    def on_dialog_key_press(dialog, event):
        if event.string == ' ':
                    dialog.response(gtk.RESPONSE_OK)
                    return True
        return False

    def playn(self, event, data=None):
        '''Play one of the mics recorded'''
        if self.stop_state:
            self.stop_state=False
            self.stop(None)
            return True
        mic=int(event.get_name()[5:])
        if len(self.utts_list) > 0:
            self.status_playing()
            if self.prefix:
                    location="%s_%02d_mic%02d.wav"%(self.prefix,self.utts_list[self.numUtt][0],mic)
            else:
                    location="%s_%02d_mic%02d.wav"%(self.filename,self.utts_list[self.numUtt][0],mic)

            if self.outdir:
                location="%s/%s/%s"%(self.outdir,self.prefix,location)
                location=os.path.abspath(location)
            else:
                location="%s/%s/%s"%(os.getcwd(),self.prefix,location)

            self.verbose('Playing file: %s'%location)

            if not os.path.exists(location):
                    msg="You are trying to play this file: "+location+" which does not exists"

                    md = gtk.MessageDialog(self, 
                                    gtk.DIALOG_DESTROY_WITH_PARENT,
                                    gtk.MESSAGE_INFO, 
                                    gtk.BUTTONS_OK, msg)
                    md.run()
                    md.destroy()
                    self.status_open()
                    return False

            self.stop_state=True
            self.player.set_property("uri", "file://" + location)
            self.player.set_state(gst.STATE_PLAYING)

           
        return True

    def check_jack(self):
        p=Popen(['jack_wait','--check'],stdout=PIPE,stderr=PIPE)
        out=p.communicate()[0]
        if out.startswith('running'):
            return True
        else:
            return False

    def connected(self, event, data=None):
        if self.jack:
            if self.connect:
                p=Popen(['jack_disconnect','system:capture_1','system:playback_1'],stdout=PIPE,stderr=PIPE)
                p.communicate()
                p=Popen(['jack_disconnect','system:capture_1','system:playback_2'],stdout=PIPE,stderr=PIPE)
                p.communicate()
		self.connect=False
            else:
                p=Popen(['jack_connect','system:capture_1','system:playback_1'],stdout=PIPE,stderr=PIPE)
                p.communicate()
                p=Popen(['jack_connect','system:capture_1','system:playback_2'],stdout=PIPE,stderr=PIPE)
                p.communicate()
		self.connect=True
	self.status_jack()

    def play(self, event, data=None):
        '''Start playing'''
        if self.stop_state:
            self.stop_state=False
            self.stop(None)
            return True 
        if len(self.utts_list) > 0:
            self.status_playing()
            if self.prefix:
                    location="%s_%02d_mic%02d.wav"%(self.prefix,self.utts_list[self.numUtt][0],self.monitor+1)
            else:
                    location="%s_%02d_mic%02d.wav"%(self.filename,self.utts_list[self.numUtt][0],self.monitor+1)

            if self.outdir:
                location="%s/%s/%s"%(self.outdir,self.prefix,location)
                location=os.path.abspath(location)
            else:
                location="%s/%s/%s"%(os.getcwd(),self.prefix,location)

            self.verbose('Playing file: %s'%location)

            if not os.path.exists(location):
                    msg="You are trying to play this file: "+location+" which does not exists"

                    md = gtk.MessageDialog(self, 
                                    gtk.DIALOG_DESTROY_WITH_PARENT,
                                    gtk.MESSAGE_INFO, 
                                    gtk.BUTTONS_OK, msg)
                    md.run()
                    md.destroy()
                    self.status_open()
                    return False
            self.stop_state=True           
            self.player.set_property("uri", "file://" + location)
            self.player.set_state(gst.STATE_PLAYING)

           
        return True

    
    def stop(self, event, data=None):
        '''Stop playing/recording'''
        if self.recorder:
            self.recorder.set_state(gst.STATE_NULL)
            if self.client:
                self.sckt.send(':hide')
            else:
                self.sentence.hide()
            self.go_next(None)
        if self.player:
            self.player.set_state(gst.STATE_NULL)
        self.status_open()
        return True
 
 
    # Close
    def close(self, event, data=None):
        self.utts_list.clear()
        self.filename=None
        return True
        
    # Finish the app
    def quit(self, event, data=None):
        if self.client:
            self.sckt.send(':quit')
        gtk.main_quit()
        return False
 

    # save a file
    def save(self, event, data=None):
        self.save_file(self.filename)
        return True


    # save as
    def save_as(self, event, data=None):
        """Saves as the current corpus"""
        self.save_as_file_select.show()
        response = self.save_as_file_select.run()
      
        if int(response) == int(gtk.RESPONSE_OK):
            self.save_as_file_select.hide()
            self.filename=self.save_as_file_select.get_filename()
            self.save_file(self.filename)
        else:
            self.file_select_cancel(None)    
            return False
        return True
 
    def directory(self, event, data=None):
        ''' Open the directory selection'''

        self.open_dir_sel.show()
        response = self.open_dir_sel.run()
        print response
        if int(response) == int(gtk.RESPONSE_OK):
            self.open_dir_sel.hide()
            self.outdir=self.open_dir_sel.get_filename()
            self.rewrite=False
            return True
        else:
            self.open_dir_sel.hide()
            return False
        return True
 
    # Open a file
    def open_file(self, event, data=None):
        ''' Open the file'''

        self.file_select.show()
        response = self.file_select.run()
        if int(response) == int(gtk.RESPONSE_OK):
            self.file_select.hide()
            self.filename=self.file_select.get_filename()
            self.prefix=os.path.splitext(os.path.basename(self.filename))[0]
            self.audiodir=False
            return self.file_select_ok(None)
        else:
            self.file_select.hide()
            return False
        return True
 
    def file_select_ok(self, event, data=None):
        ''' If one file is selected, update the tree corpus'''
        # Get the name of the corpus
        self.numUtt=0
        self.utts_list.clear()

        id=0
        for line in open(self.filename):
            line=line.strip()
            if len(line)>0:
                m=re_utts.match(line)
                if m:
                    self.utts_list.append([int(m.group('id')),m.group('utt'),id])
                id+=1

        if len(self.utts_list)>0:
            self.status_open()
            self.update_view()
        return True

    # Audio messages
    def on_message(self, bus, message):
        '''Message recieved for the playing'''
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.stop_state=False
            self.status_open()
        elif t == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            self.stop_state=False
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.status_open()


    def on_rec_message(self, bus, message):
        '''Message recieved for the recording'''
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.recorder.set_state(gst.STATE_NULL)
            self.status_open()
            self.stop_state=False
        elif t == gst.MESSAGE_ERROR:
            self.recorder.set_state(gst.STATE_NULL)
            self.stop_state=False
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.status_open()


