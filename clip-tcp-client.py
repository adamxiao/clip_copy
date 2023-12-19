#!/usr/bin/python3 -t
# -*- coding:utf-8 -*-

import socket
from gi.repository import Gtk, GLib, Gdk
import signal
import base64
import sys
import queue

HOST = '127.0.0.1'
PORT = 22

class TCPEchoClient():
    def __init__(self):
        self.client_socket = None
        self.can_send_clip = True
        self.data_queue = queue.Queue(100000)
        self.last_send_data = None
        self.resend_ack = False

        self.seq = 0
        self.ack = 0
        self.recv_seq = 0
        self.recv_ack = 0

    def decode_data(self, data):
        """docstring for encode_data"""
        if not data:
            print('empty data')
            return None
            
        if '1qaz2wsx@@' != data[:10]:
            print('magic wrong data')
            return None

        if 'ack' == data[10:]:
            print('recv ack')
            self.last_send_data = None
            self.can_send_clip = True
            self.forward_data_queue_to_clip()
            print('after recv ack, can_send_clip is ', self.can_send_clip)
            return None

        data = base64.b64decode(data[10:])
        return data

    def encode_data(self, data):
        """docstring for encode_data"""
        enc_data = base64.b64encode(data).decode('utf-8')
        return '1qaz2wsx@@' + enc_data

    def start(self):
        # self.start_client()
        self.start_clipboard()


    def start_clipboard(self):
        clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD) 
        clip.connect('owner-change', self.clip_change) 

    def timeout_send_ack(self):
        """docstring for timeout_send_ack"""
        print('HUCK: resend ack ======================')
        if self.resend_ack:
            self.send_ack_to_clip()
            self.resend_ack = False

    def timeout_reset_send_clip(self):
        """docstring for timeout_send_ack"""
        self.can_send_clip = True
        self.forward_data_queue_to_clip()
        print('timeout send ack, can_send_clip change to', self.can_send_clip)

    def clip_change(self, *args):
        if not self.client_socket:
            self.start_client()

        clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD) 
        if self.client_socket:
            print('3.recv clip req')
            b64_data = clip.wait_for_text()
            data = self.decode_data(b64_data)
            # data = base64.b64decode(b64_data)
            if data:
                print('4.tcp forward send req# %d >>>>>>' % len(data))
                self.client_socket.sendall(data)
                # send ack
                if self.can_send_clip:
                    self.send_ack_to_clip()
                else:
                    # TODO: first send ack, then resend data
                    print('TODO: 4.first send ack, then resend data')
                    # https://docs.gtk.org/glib/index.html#functions
                    self.resend_ack = True
                    GLib.timeout_add_seconds(3, self.timeout_send_ack)

    def start_client(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((HOST, PORT))
        self.client_socket.setblocking(False)
        print('connected %s:%d' % (HOST, PORT))

        GLib.io_add_watch(
            self.client_socket, GLib.IO_IN | GLib.IO_HUP, self.handle_client_data
        )

    def forward_data_queue_to_clip(self):
        """docstring for forward_tcp_to_clip"""
        # FIXME: merge multi data?
        if self.data_queue.empty():
            return
        data = self.data_queue.get()
        self.forward_data_to_clip(data)

    def forward_data_to_clip(self, data):
        """docstring for forward_tcp_to_clip"""
        b64_data = self.encode_data(data)
        self.last_send_data = b64_data
        print('5.<<<<<< recv tcp resp# %d' % (len(data)))
        send_clip = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY) 
        send_clip.set_text(b64_data, len(b64_data))
        print('6.clip forwad resp')
        self.can_send_clip = False
        print('6.can_send_clip change to ', self.can_send_clip)

    def send_ack_to_clip(self):
        """docstring for forward_tcp_to_clip"""
        ack = '1qaz2wsx@@ack'
        send_clip = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY) 
        send_clip.set_text(ack, -1)
        self.can_send_clip = False
        print('6.send ack, can_send_clip change to ', self.can_send_clip)
        GLib.timeout_add_seconds(1, self.timeout_reset_send_clip)


    def handle_client_data(self, source, condition):
        if condition & GLib.IO_IN:
            data = self.client_socket.recv(1600)
            if not data:
                self.client_socket.close()
                return False

            if self.can_send_clip:
                self.forward_data_to_clip(data)
            else:
                print('5.<<<<<< enqueue data# %d' % (len(data)))
                self.data_queue.put(data)

        return True

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        HOST = sys.argv[1]
        PORT = int(sys.argv[2])
    win = TCPEchoClient()
    win.start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()
