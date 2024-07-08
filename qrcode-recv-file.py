#!/usr/bin/python3 -t
# -*- coding:utf-8 -*-

# refer clip_client3.py
# refer jenkins-recv-file.py

from gi.repository import Gtk, GLib, Gdk
import sys, os
import signal
import queue
import time
import threading
import struct
import binascii
# 解析二维码
import cv2
from pyzbar.pyzbar import decode

magic="qwer123#"
ack=0
target_file=""
total=0
window_id=123
recv_seq=0
sended_ack=0
sended_ack_ts=0
recv_finished=False
# TODO: 暂时用全局变量控制

# 标志变量，用于通知线程停止
stop_threads = threading.Event()

data_queue = queue.Queue(100000)

def get_screenshot():
	# global window_id
	# # 确保窗口在最前, FIXME: 手动用鼠标键盘切换确保窗口在最前面即可
	# os.system(f"xdotool windowactivate {window_id}")

	# 截取指定窗口的截图
	screenshot_path = "/tmp/qrcode.png"
	os.system(f"gnome-screenshot -w -B -f {screenshot_path}")

def parse_qrcode():
	# 加载图像
	image_path = '/tmp/qrcode.png'  # 替换为你的二维码图像路径
	image = cv2.imread(image_path)

	# 解码二维码
	decoded_objects = decode(image)

	# 打印解码信息
	for obj in decoded_objects:
		return obj.data.decode("utf-8").encode('latin1')
	return None

def parse_data(data): 
	if None == data:
		# print('null data')
		return None
	try:
		unpack_info = struct.unpack('8sLLL', data[:32])
	except Exception as error:
		print('unpack failed %s' % error)
		return None
	if magic.encode('utf-8') != unpack_info[0]:
		print('wrong magic')
		return None

	seq = unpack_info[1]
	size = unpack_info[2]
	if seq == 0:
		global total
		total = int(unpack_info[3])
	file_data = data[32:]
	print('recv data seq: %d, size: %d, data len %d' % (seq, size, len(file_data)))

	global ack
	ack = seq + size

	global recv_seq
	if recv_seq >= ack:
		# data_queue.put(ack)
		# print('recv dup data')
		# sys.exit(0)
		# already recv the data, do nothing
		return None
	elif recv_seq == seq:
		data_queue.put(ack)
		recv_seq = ack # update recv_seq
		return file_data
	else:
		print("recv wrong seq: %d" % seq)
		sys.exit(0)


# 开启监控qrcode进程
def recv_qrcode():
	while not stop_threads.is_set():
		get_screenshot()
		data = parse_qrcode()
		bin_data = parse_data(data)
		if not bin_data:
			time.sleep(1)
			continue
		print('save data len %d' % (len(bin_data)))
		open(target_file, 'ab').write(bin_data)
		# FIXME: 是否需要sleep?


def recv_data(data): 
	if None == data:
		print('wrong data len %d' % len(data))
		# TODO: 处理异常?
		return
	try:
		unpack_info = struct.unpack('8sLLL', data[:32])
	except Exception as error:
		print('unpack failed %s' % error)
		return
	if magic.encode('utf-8') != unpack_info[0]:
		print('wrong magic')
		return

	seq = unpack_info[1]
	size = unpack_info[2]
	if seq == 0:
		global total
		total = int(unpack_info[3])
	file_data = data.decode("utf-8")[32:]
	print('recv data seq: %d, size: %d, data len %d' % (seq, size, len(file_data)))

	global ack
	ack = seq + size
	send_ack(ack)

	global recv_seq
	if recv_seq >= ack:
		# print('recv dup data')
		# sys.exit(0)
		# already recv the data, do nothing
		return
	elif recv_seq == seq:
		recv_seq = ack # update recv_seq
	else:
		print("recv wrong seq: %d" % seq)
		sys.exit(0)

	# save data
	print('save seq data seq %d, len %d' % (seq, len(file_data)))
	open(target_file, 'ab').write(file_data.encode('latin1'))

	if ack >= total:
		print('recv ended!')
		send_finish_ack(ack)
		clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD) 
		clip.store()
		sys.exit(0)


def send_ack(ack):
	data = magic + ':ack:' + str(ack) + ':\n'
	# pyperclip.copy(data)
	clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD) 
	clip.set_text(data, len(data))
	clip.store()
	pass

def send_finish_ack(ack):
	data = magic + ':ack:' + str(ack) + ':\n'
	import subprocess
	p = subprocess.Popen(['xclip', '-selection', 'c'], stdin=subprocess.PIPE, close_fds=True)
	p.communicate(input=data.encode('utf-8'))
	pass

def usage():
	print('<bin> file')
	pass


# 发送数据到clip中
def consume_recv_data():
	while not data_queue.empty():
		ack = data_queue.get()
		send_ack(ack)
		global total
		if ack >= total:
			print('recv ended!')
			stop_threads.set()
			send_finish_ack(ack)
			sys.exit(0)
			return False
	return True

# 信号处理函数
def handle_signal(signum, frame):
	stop_threads.set()
	sys.exit(1)

# 注册信号处理函数


def main():
	if len(sys.argv) <= 1:
		usage()
		sys.exit(1)
	global target_file
	target_file = sys.argv[1]
	global window_id
	if len(sys.argv) > 2:
		window_id = int(sys.argv[2])
	open(target_file, 'wb').close()

	# 开启线程
	recv_thread = threading.Thread(target=recv_qrcode)
	# recv_thread.daemon = True
	recv_thread.start()

	GLib.timeout_add(100, consume_recv_data)  # Check the queue every 100 ms
	signal.signal(signal.SIGINT, handle_signal)
	Gtk.main()


if __name__ == '__main__':
	main()
