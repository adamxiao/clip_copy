#!/usr/bin/python3 -t
# -*- coding:utf-8 -*-

import socket
from gi.repository import Gtk, GLib, Gdk
import signal
import base64
import sys
import queue

IS_TCP_SERVER = True
HOST = '127.0.0.1'
PORT = 2022
send_clip = Gdk.SELECTION_PRIMARY
recv_clip = Gdk.SELECTION_CLIPBOARD

class TCPEchoServer():
    def __init__(self):
        self.server_socket = None
        self.client_socket = None
        if IS_TCP_SERVER:
            self.server_socket = self.init_tcp_server()

        self.can_send_clip = True # 能够发送数据
        self.retrans_data = False # 是否重传数据
        self.data_queue = queue.Queue(100000)
        self.last_send_data = None # 待重传的数据
        self.resend_ack = False # 是否需要发送ack, 收到包就要发ack, 只有异常包不需要发送ack?

        self.seq = 0
        self.ack = 0

    def init_tcp_server(self):
        """docstring for init_tcp_server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)
        print('tcp server listen %s:%d' % (HOST, PORT))
        return server_socket

    def start_client(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((HOST, PORT))
        self.client_socket.setblocking(False)
        print('connected %s:%d' % (HOST, PORT))

        GLib.io_add_watch(
            self.client_socket, GLib.IO_IN | GLib.IO_HUP, self.handle_client_data
        )

    def decode_data(self, data):
        """docstring for encode_data"""
        if not data:
            print('empty data')
            return None
            
        if '1qaz2wsx@@' != data[:10]:
            print('magic wrong data')
            return None

        ack = parse_hex_str(data[10:16])
        seq = parse_hex_str(data[16:22])]
        length = parse_hex_str(data[22:28])] # check length?
        # 处理ack, 以及seq
        if ack == self.seq:
            self.seq += 1
            self.can_send_clip = True
            self.retrans_data = False
        else:
            print('retrans data seq# ', self.seq)
            self.can_send_clip = True
            self.retrans_data = True
            # TODO: retrans data
            pass

        if 0 == length:
            # recv only ack, do nothing!
            return None

        self.resend_ack = True
        if seq == self.ack:
            # process data
            self.ack = seq
            # receive new data, send ack!
        else:
            # receive duplicate data, send ack!
            return None

        new_data = base64.b64decode(data[28:])
        return new_data

    def get_hex_str(self, num):
        desired_length = 6  # for example, you want the string to have 6 characters
        hex_string = format(num, f'0{desired_length}X')
        return hex_string

    def parse_hex_str(self, hex_string):
        hex_string = format(num, f'0{desired_length}X')
        decimal_number = int(hex_string, 16)
        return decimal_number

    def encode_data(self, data):
        """docstring for encode_data"""
        ack_str = self.get_hex_str(self.ack)
        seq_str = self.get_hex_str(self.seq)
        length = 0
        if data:
            length = len(data)
        len_str = self.get_hex_str(length)
        if data:
            enc_data = base64.b64encode(data).decode('utf-8')
            return '1qaz2wsx@@' + seq_str + ack_str + len_str + enc_data
        else
            # only send ack
            return '1qaz2wsx@@' + seq_str + ack_str + len_str

    def start(self):
        if IS_TCP_SERVER:
            self.start_server()
        self.start_clipboard()

    def start_clipboard(self):
        clip = Gtk.Clipboard.get(recv_clip) 
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
        if not IS_TCP_SERVER and not self.client_socket:
            self.start_client()

        clip = Gtk.Clipboard.get(recv_clip) 
        if self.client_socket:
            # FIXME: 验证b64_data? 空数据表示连接断开?
            print('7.recv clip resp')
            b64_data = clip.wait_for_text()
            # 异步处理?
            data = self.decode_data(b64_data)
            if data:
                print('8.<<<<<<  tcp forward resp# %d' % len(data))
                self.client_socket.sendall(data)
            # send ack, or retrans data
            if self.retrans_data:
                self.retrans_data = False
                self.resend_ack = False
                # 立即重传! FIXME: 不用考虑是否能写clip?
                self.forward_data_to_clip(self.last_send_data)
            elif self.resend_ack:
                self.resend_ack = False
                # 立即回ack! FIXME: 不用考虑是否能写clip?
                self.send_ack_to_clip()

    def start_server(self):
        GLib.idle_add(self.accept_connections)

    def accept_connections(self):
        self.client_socket, address = self.server_socket.accept()
        print("Connection from", address)
        self.client_socket.setblocking(False)

        GLib.io_add_watch(
            self.client_socket, GLib.IO_IN | GLib.IO_HUP, self.handle_client_data
        )

        return False

    def forward_data_queue_to_clip(self):
        """docstring for forward_tcp_to_clip"""
        # FIXME: merge multi data?
        if self.data_queue.empty():
            return
        self.last_send_data = self.data_queue.get()
        self.forward_data_to_clip(self.last_send_data)

    def forward_data_to_clip(self, data):
        """docstring for forward_tcp_to_clip"""
        b64_data = self.encode_data(data)
        print('1.recv tcp send req# %d >>>>>>' % (len(data)))
        clip = Gtk.Clipboard.get(send_clip) 
        clip.set_text(b64_data, len(b64_data))
        print('2.clip forward req')
        self.can_send_clip = False

    def send_ack_to_clip(self):
        """docstring for forward_tcp_to_clip"""
        send_ack = self.encode_data(None)
        clip = Gtk.Clipboard.get(send_clip) 
        clip.set_text(send_ack, -1)
        self.can_send_clip = False
        # GLib.timeout_add_seconds(1, self.timeout_reset_send_clip)

    def handle_client_data(self, source, condition):
        if condition & GLib.IO_IN:
            data = self.client_socket.recv(1600)
            if not data:
                self.client_socket.close()
                return False

            if self.can_send_clip:
                self.last_send_data = data
                self.forward_data_to_clip(data)
            else:
                print('1.enqueue data# %d >>>>>>' % (len(data)))
                self.data_queue.put(data)

        return True

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        if '--server' == sys.argv[1]:
            IS_TCP_SERVER = True
            send_clip = Gdk.SELECTION_CLIPBOARD
            recv_clip = Gdk.SELECTION_PRIMARY
        else:
            IS_TCP_SERVER = False
            send_clip = Gdk.SELECTION_PRIMARY
            recv_clip = Gdk.SELECTION_CLIPBOARD
        HOST = sys.argv[2]
        PORT = int(sys.argv[3])

    win = TCPEchoServer()
    win.start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()
