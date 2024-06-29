#!/usr/bin/python3 -t
# -*- coding:utf-8 -*-

import socket
from gi.repository import Gtk, GLib, Gdk
import signal
import base64
import sys
import queue
import logging
import jenkins
import time
#Gdk.threads_init()
import threading

# 1. 新增重传间隔, 至少1s?
# 2. 收到数据后，需要发送纯ack? (是否需要间隔重传数据?)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

exception = logger.exception
error = logger.error
info = logger.info
warning = logger.warning
debug = logger.debug

IS_TCP_SERVER = True # 外部
# jenkins能不能wait 到一个commit? => 貌似不行
HOST = '127.0.0.1'
PORT = 2022
send_clip = Gdk.SELECTION_PRIMARY
recv_clip = Gdk.SELECTION_CLIPBOARD
jenkins_url = "http://192.168.120.30:8080/"
jenkins_job='commit_copy'

class TCPEchoServer():
    def __init__(self):
        self.jenkins_queue = queue.Queue(1000)
        self.server_socket = None
        self.client_socket = None
        if IS_TCP_SERVER:
            self.server_socket = self.init_tcp_server()
            self.send_clip = Gdk.SELECTION_CLIPBOARD
            self.recv_clip = Gdk.SELECTION_PRIMARY
        else:
            self.send_clip = Gdk.SELECTION_PRIMARY
            self.recv_clip = Gdk.SELECTION_CLIPBOARD

        self.can_send_clip = True # 能够发送数据
        self.retrans_data = False # 是否重传数据
        self.data_queue = queue.Queue(100000)
        self.clip_queue = queue.Queue(1000)
        self.last_send_data = None # 待重传的数据
        self.last_send_data_ts = 0 # 上次发送数据的时间戳
        self.retrans_count = 0

        # 收到, 待转发的seq
        self.tcp_seq = 1

        # 发送, 待转发的seq
        self.recv_seq = 0

        # 待转发的逻辑seq,ack等
        self.seq = 1
        self.ack = 0
        self.recv_ack = 0

        # 开启jenkins线程
        self.thread = threading.Thread(target=self.jenkin_run)
        self.thread.daemon = True  # Ensure thread exits when the main thread does
        self.thread.start()
        if IS_TCP_SERVER: # 从jenkins中收数据
            GLib.timeout_add(100, self.consume_jenkin_queue)  # Check the queue every 100 ms
            GLib.timeout_add(100, self.consume_clip_queue)  # Check the queue every 100 ms

        # 开启发送线程, 发送数据到clip中, 或者jenkins中
        self.send_thread = threading.Thread(target=self.send_proxy_run)
        self.send_thread.daemon = True
        self.send_thread.start()

    # 参考clip_change的实现啦
    def consume_jenkin_queue(self):
        while not self.jenkins_queue.empty():
            if not self.client_socket:
                error("client socket not exist, exit")
                system.exit(1)
            b64_data = self.jenkins_queue.get()
            if b64_data is None:
                error("get wrong data")
                return False  # Stop the timeout_add callback
            if self.client_socket:
                if b64_data and len(b64_data) >= 28:
                    seq = self.parse_hex_str(b64_data[10:16])
                    ack = self.parse_hex_str(b64_data[16:22])
                    length = self.parse_hex_str(b64_data[22:28])
                    info('3.recv proxy data seq %d, len %d <<< ack: %d <<<' % (seq, length, ack))
                # 异步处理?
                (seq, data) = self.decode_data(b64_data)
                if data:
                    info('4.recv proxy data seq %d, len: %d <<<<<<' % (seq, len(data)))
                    self.client_socket.sendall(data)
                if seq > 0: # send ack
                    self.data_queue.put((seq, None))
                # FIXME: retrans data!
        return True  # Keep the timeout_add callback active

    # 开启jenkins线程
    def jenkin_run(self):
        server = jenkins.Jenkins(jenkins_url, username="kycd", password='Ksvd@2023')
        if IS_TCP_SERVER: # 从jenkins中收数据
            # job = server.get_job_info(jenkins_job)['lastSuccessfulBuild']
            number = server.get_job_info(jenkins_job)['nextBuildNumber']
            logging.info("jenkins next number is " + str(number))
            while True:
                try:
                    b64_data = server.get_build_info(jenkins_job,number)['actions'][0]["parameters"][0]['value']
                    self.jenkins_queue.put(b64_data)
                    # FIXME: 删除掉这个build
                    number = number + 1 # 简单自增即可
                #except jenkins.NotFoundException as error:
                except Exception as error:
                    time.sleep(0.1)
                    continue
        else:
            while True:
                if self.jenkins_queue.empty():
                    time.sleep(0.1)
                    continue
                while not self.jenkins_queue.empty():
                    send_data = self.jenkins_queue.get()
                    adam = server.build_job(jenkins_job, {'commit': send_data})

    # 发送数据到clip中
    def consume_clip_queue(self):
        while not self.clip_queue.empty():
            b64_data = self.clip_queue.get()
            if b64_data is None:
                error("get wrong send clip data")
                return False  # Stop the timeout_add callback
            clip = Gtk.Clipboard.get(send_clip) 
            clip.set_text(b64_data, len(b64_data))
        return True # Keep the timeout_add callback active


    # 开启发送线程, 发送数据
    def send_proxy_run(self):
        send_ack = 0
        while True:
            if self.data_queue.empty():
                time.sleep(0.1)
                continue
            while not self.data_queue.empty():
                (seq, data) = self.data_queue.get()
                for i in range(50):
                    if not data:
                        if send_ack >= self.ack:
                            # ack没必要重复发!
                            break
                    elif self.recv_ack >= seq:
                        break
                    send_ack = self.ack
                    send_data = self.encode_data(data, seq)
                    length = 0
                    if data:
                        length = len(data)
                    if i == 0:
                        info('2.send proxy data seq %s, len: %d, ack: %d >>> seq: %d >>>' % (seq, length, self.ack, seq))
                    else:
                        info('timeout 2.send proxy data seq %s, len: %d, ack: %d, retran: %d >>> seq: %d >>>' % (seq, length, self.ack, i, seq))
                    # 发送数据
                    if IS_TCP_SERVER:
                        self.clip_queue.put(send_data)
                    else:
                        self.jenkins_queue.put(send_data)
                        break # 不等ack
                    # TODO: 通过jenkins发送的, 等ack等久一点!
                    for j in range(100): # 等5s收到ack则
                        if self.recv_ack >= seq:
                            break
                        time.sleep(0.1)


    def init_tcp_server(self):
        """docstring for init_tcp_server"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)
        info('tcp server listen %s:%d' % (HOST, PORT))
        return server_socket

    def start_client(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((HOST, PORT))
        self.client_socket.setblocking(False)
        info('connected %s:%d' % (HOST, PORT))

        GLib.io_add_watch(
            self.client_socket, GLib.IO_IN | GLib.IO_HUP, self.handle_client_data
        )

    def decode_data(self, data):
        if not data:
            debug('empty data')
            return (0, None)
            
        if '1qaz2wsx@@' != data[:10]:
            debug('magic wrong data')
            return (0, None)

        seq = self.parse_hex_str(data[10:16])
        ack = self.parse_hex_str(data[16:22])
        length = self.parse_hex_str(data[22:28]) # check length?

        # 处理ack
        if ack > self.recv_ack: # 收到新的数据包的ack
            info('recv ack for seq %d, prev is %d' % (ack, self.recv_ack))
            self.recv_ack = ack

        if 0 == length:
            # recv only ack, do nothing!
            return (0, None)

        # 处理seq: 更新一下self.ack
        if seq == self.ack + 1:
            debug('recv seq is %d, self.ack %d' % (seq, self.ack))
            # process data
            self.ack = seq
            # receive new data, send ack!
        elif seq <= self.ack:
            debug('recv duplicate old seq old %d, len %d' % (seq, length))
            return (0, None)
        else:
            # 退出程序!
            error('recv wrong seq %d, expect %d' % (seq, self.ack + 1))
            system.exit(1)
            return (0, None)

        new_data = base64.b64decode(data[28:])
        return (seq, new_data)

    def get_hex_str(self, num):
        desired_length = 6  # for example, you want the string to have 6 characters
        hex_string = format(num, f'0{desired_length}X')
        return hex_string

    def parse_hex_str(self, hex_string):
        decimal_number = int(hex_string, 16)
        return decimal_number

    def encode_data(self, data, seq):
        ack_str = self.get_hex_str(self.ack)
        seq_str = self.get_hex_str(seq)
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

    def clip_change(self, *args):
        if not IS_TCP_SERVER and not self.client_socket:
            self.start_client()

        clip = Gtk.Clipboard.get(recv_clip) 
        # FIXME: client socket 断开则退出
        if self.client_socket:
            # FIXME: 验证b64_data? 空数据表示连接断开?
            b64_data = clip.wait_for_text()
            if b64_data and len(b64_data) >= 28:
                seq = self.parse_hex_str(b64_data[10:16])
                ack = self.parse_hex_str(b64_data[16:22])
                length = self.parse_hex_str(b64_data[22:28])
                info('3.recv proxy data seq %d, len %d <<< ack:%d <<<' % (seq, length, ack))
            # 异步处理?
            (seq, data) = self.decode_data(b64_data)
            if data:
                info('4.recv proxy data seq %d, len: %d' % (seq, len(data)))
                self.client_socket.sendall(data)
            if seq > 0: # send ack
                self.data_queue.put((seq, None))
            # FIXME: retrans data!

    def start_server(self):
        GLib.idle_add(self.accept_connections)

    def accept_connections(self):
        self.client_socket, address = self.server_socket.accept()
        debug("Connection from %s" % str(address))
        self.client_socket.setblocking(False)

        GLib.io_add_watch(
            self.client_socket, GLib.IO_IN | GLib.IO_HUP, self.handle_client_data
        )

        return False

    def handle_client_data(self, source, condition):
        if condition & GLib.IO_IN:
            data = self.client_socket.recv(4000)
            if not data:
                error("recv failed ====================================================")
                self.client_socket.close()
                return False

            info('1.send proxy data seq %d, len: %d' % (self.tcp_seq, len(data)))
            self.data_queue.put((self.tcp_seq, data))
            self.tcp_seq += 1

        return True

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        if '--server' == sys.argv[1]:
            IS_TCP_SERVER = True
            send_clip = Gdk.SELECTION_CLIPBOARD
            recv_clip = Gdk.SELECTION_PRIMARY
            jenkins_url = "http://192.168.120.30:8080/"
        else:
            IS_TCP_SERVER = False
            send_clip = Gdk.SELECTION_PRIMARY
            recv_clip = Gdk.SELECTION_CLIPBOARD
            jenkins_url = "http://192.5.1.30:8080/"
        HOST = sys.argv[2]
        PORT = int(sys.argv[3])

    win = TCPEchoServer()
    win.start()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()
