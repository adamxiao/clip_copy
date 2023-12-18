#!/usr/bin/python3 -t
# -*- coding:utf-8 -*-

import socket
from gi.repository import Gtk, GLib, Gdk
import signal
import base64
import sys

HOST = '127.0.0.1'
PORT = 8888

class TCPEchoServer():
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(1)
        print('listen %s:%d' % (HOST, PORT))

        self.client_socket = None

    def start(self):
        self.start_server()
        self.start_clipboard()


    def start_clipboard(self):
        clip = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY) 
        clip.connect('owner-change', self.clip_change) 

    def clip_change(self, *args):
        clip = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY) 
        if self.client_socket:
            # TODO: 验证b64_data? 空数据表示连接断开?
            b64_data = clip.wait_for_text()
            print('7.recv clip resp %s' % b64_data[:7])
            # 异步处理?
            data = base64.b64decode(b64_data)
            self.client_socket.sendall(data)
            print('8.tcp forward resp')

    def start_server(self):
        GLib.idle_add(self.accept_connections)

    def accept_connections(self):
        self.client_socket, address = self.server_socket.accept()
        print("Connection from", address)

        GLib.io_add_watch(
            self.client_socket, GLib.IO_IN | GLib.IO_HUP, self.handle_client_data
        )

        return False

    def handle_client_data(self, source, condition):
        if condition & GLib.IO_IN:
            data = self.client_socket.recv(1024)
            if not data:
                self.client_socket.close()
                return False

            # Echo the received data back to the client
            #self.client_socket.sendall(data)

            # TODO: 验证对端收包速度过慢的问题
            b64_data = base64.b64encode(data).decode('utf-8')
            print('1.recv tcp req: %s' % b64_data[:7])
            # 多线程问题，会随机出现错误!!!
            send_clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD) 
            send_clip.set_text(b64_data, len(b64_data))
            print('2.clip forward req')
            #ksend_clip.store()

        return True

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        HOST = sys.argv[1]
        PORT = int(sys.argv[2])
    win = TCPEchoServer()
    win.start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()
