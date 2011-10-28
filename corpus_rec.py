#!/usr/bin/env python
# -*- coding: utf-8
# ----------------------------------------------------------------------
# Audio Corpus Recorder 
# Records a corpus by promting the user with the sentence to be read. It
# can capture up to four michophone sources.
# ----------------------------------------------------------------------
# Ivan Vladimir Meza-Ruiz/ ivanvladimir at turing.iimas.unam.mx
# Caleb Antonio Rascón Estebané/  caleb at turing.iimas.unam.mx
# 2011/IIMAS/UNAM
# ----------------------------------------------------------------------
# corpus_rec.py is free software: you can redistribute it and/or modify
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

import pygtk
pygtk.require('2.0')
import gtk
import optparse


if __name__ == "__main__":
    usage="""%prog [options] [data_file]

        Records an audio corpus from a transcription file

        """

    version="%prog 0.1"

    p = optparse.OptionParser(usage=usage,version=version)
    p.add_option("-o", "--outdir",
            action="store", dest="outdir", type="str",default="audio",
            help="Output dir [.]")
    p.add_option("", "--server",
            action="store_true", dest="server", default=False,
            help="Runs server mode")
    p.add_option("", "--client",
            action="store_true", dest="client", default=False,
            help="Runs client mode")
    p.add_option("-n", "--nmics",
            action="store", dest="nmics", type="int",default=4,
            help="Number of microphones to capture from [1]")
    p.add_option("-f", "--fullscreen",
            action="store_true", dest="full",default=False,
            help="Full screen for sentences")
    p.add_option("-i", "--ip",
            action="store", dest="ip", type="str",default='127.0.0.1',
            help="IP of server [127.0.0.1]")
    p.add_option("-p", "--port",
            action="store", dest="port", type="int",default=5000,
            help="Port number for server mode [5000]")
    p.add_option("-v", "--verbose",
            action="store_true", dest="verbose", default=True,
            help="Prints a lot of information [default]")


    opts, args = p.parse_args()

    if len(args)>1:
        p.error("Incorrect number of arguments")


    if len(args)==0:
        filename=None
    else:
        filename=args[0]

    bind=(opts.ip,opts.port)

    if not opts.server:
        from MWindow import MainWindow
        w = MainWindow(
                filename=filename,
                outdir=opts.outdir,
                nmics=opts.nmics,
                client=opts.client,
                bind=bind,
                full=opts.full,
                verbose=opts.verbose)
        w.main()
    else:
       import socket
       import threading
       import SWindow
       import gtk

       class SCKT(threading.Thread):
           def __init__(self,bind,sentence):
               threading.Thread.__init__(self)
               gtk.gdk.threads_init()
               self.bind=bind
               self.sentence=sentence

           def socketListen(self):
                try:
                     if opts.verbose:
                         print "Listening to %s:%d"%bind
                     s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                     s.bind(self.bind) #bound to 127.0.0.1 and port 7070
                     s.listen(1) #At this point only listening for one connection
                     self.clientConn, addrinfo=s.accept()
                     if opts.verbose:
                         print addrinfo
                except Exception as e:
                    print e
    
           def run(self):
               self.socketListen()
               try:
                running=True
                while(running):
                    MSG=self.clientConn.recv(1024)
                    if len(MSG)==0:
                        running=False
                        gtk.main_quit()
                        
                    if MSG.startswith(':quit'):
                        self.clientConn.close()
                        if opts.verbose:
                            print "Connection finishing"
                        self.sentence.hide()
                        gtk.main_quit()
                    elif MSG.startswith(':hide'):
                        self.sentence.hide()
                    elif MSG.startswith(':record'):
                        self.sentence.record()
                    else:
                        self.sentence.show(MSG)

                    if opts.verbose:
                        print "Displaying:",MSG

               except Exception as e:
                    print e
                    try:
                        clienConn.close()
                    except:
                        pass


       sentence=SWindow.SentenceW(opts.full)
       sckt=SCKT(bind,sentence)
       sckt.start()
       sentence.show("")
       sentence.hide()
       sentence.main()

 

