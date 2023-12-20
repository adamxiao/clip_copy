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
        self.retrans_count = 0

        self.tcp_seq = 1
        self.recv_seq = 0
        self.seq = 1
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

        seq = self.parse_hex_str(data[10:16])
        ack = self.parse_hex_str(data[16:22])
        length = self.parse_hex_str(data[22:28]) # check length?
        # 处理ack, 以及seq
        if ack == self.seq:
            print('recv ack is #%d == seq #%d, could send new data' % (ack, self.seq))
            # 收到数据包的ack, 可以发新数据包了
            self.seq += 1
            self.can_send_clip = True
            self.retrans_data = False
            self.retrans_count = 0
            self.last_send_data = None
        elif self.last_send_data:
            print('recv ack is old #%d != seq #%d, should retrans data' % (ack, self.seq))
            self.can_send_clip = True
            if self.retrans_count < 5:
                self.retrans_count += 1;
                self.retrans_data = True
                # 在外面重传数据
            else:
                print('ERROR: reach retrans data limit, seq #%d, ack #%d' % (self.seq, self.ack))
                # FIXME: 断开客户端连接, 失败了
        else:
            print('recv ack is #%d != seq #%d (new?), could send new data' % (ack, self.seq))
            # 没有需要重传的数据, 可以发新数据包了
            self.can_send_clip = True
            pass

        if 0 == length:
            # recv only ack, do nothing!
            return None

        self.resend_ack = True
        self.recv_seq = seq
        if seq == self.ack + 1:
            print('recv seq is %d, self.ack %d' % (seq, self.ack))
            # process data
            self.ack = seq
            # receive new data, send ack!
        else:
            has_last_send_data = 1 if self.last_send_data else 0
            print('recv duplicate seq is old #%d, self.ack #%d, resend ack, has_last_send_data %d, send queue len %d' % (seq, self.ack, has_last_send_data, self.data_queue.qsize()))
            # receive duplicate data, send ack!
            return None

        new_data = base64.b64decode(data[28:])
        return new_data

    def get_hex_str(self, num):
        desired_length = 6  # for example, you want the string to have 6 characters
        hex_string = format(num, f'0{desired_length}X')
        return hex_string

    def parse_hex_str(self, hex_string):
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
        else:
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
                print('8.<<<<<<  tcp forward resp seq #%d, len: %d' % (self.recv_seq, len(data)))
                self.client_socket.sendall(data)
            # send ack, or retrans data
            if self.retrans_data:
                self.retrans_data = False
                self.resend_ack = False
                # 立即重传! FIXME: 不用考虑是否能写clip?
                self.forward_data_to_clip(self.last_send_data)
            elif self.resend_ack:
                self.resend_ack = False
                if not self.data_queue.empty():
                    self.forward_data_queue_to_clip() # 再发新数据了, 带上ack!
                else:
                    # 立即回ack! FIXME: 不用考虑是否能写clip?
                    self.send_ack_to_clip()
            elif self.can_send_clip:
                # 可能永远不走到这里。。。
                self.forward_data_queue_to_clip() # 可以再发数据了!

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
        clip = Gtk.Clipboard.get(send_clip) 
        clip.set_text(b64_data, len(b64_data))
        print('2.clip forward req #%d, ack #%d, len: %d >>>>>>' % (self.seq, self.ack, len(data)))
        self.can_send_clip = False

    def send_ack_to_clip(self):
        """docstring for forward_tcp_to_clip"""
        send_ack = self.encode_data(None)
        clip = Gtk.Clipboard.get(send_clip) 
        clip.set_text(send_ack, -1)
        # FIXME: 单纯回ack，不需要考虑是否能发
        self.can_send_clip = True
        # GLib.timeout_add_seconds(1, self.timeout_reset_send_clip)

    def handle_client_data(self, source, condition):
        if condition & GLib.IO_IN:
            data = self.client_socket.recv(1600)
            if not data:
                self.client_socket.close()
                return False

            print('1.recv tcp send data seq #%d, len: %d >>>>>>' % (self.tcp_seq, len(data)))
            self.tcp_seq += 1

            if self.can_send_clip:
                self.last_send_data = data
                self.forward_data_to_clip(data)
            else:
                print('1.enqueue data# %d, cur seq: #%d, cur ack: #%d, last_send_data %d>>>>>>' % (len(data), self.seq, self.ack, 1 if self.last_send_data else 0))
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
