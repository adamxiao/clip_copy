#!/usr/bin/python -t
# -*- coding:utf-8 -*-

from gi.repository import Gtk, Gdk 
import pyperclip
import sys, os
import base64
import signal

magic="ksvd@copy"
# echo "$magic:data:$seq:$send_size:$checksum:"
# segment=50*1024*1024
segment=1024
seq=0
target_file=""
total=0
# TODO: 暂时用全局变量控制

# TODO: register signal SIGINT terminate
def test(*args): 
	# print "Clipboard changed: recv data?"
	data = pyperclip.paste()
	# TODO: 日志加时间戳
	print 'clip changed, data len ', len(data) # TODO: 计算clip.paste时间消耗
	if not data.startswith(magic + ':ack:'):
		# TODO: 处理异常?
		return

	fuck = data.split(':')
	ack = int(fuck[2])
	print 'recv ack ', ack
	global seq
	seq = ack

	# should send data again?
	if seq >= total:
		sys.exit(0)
	copy2clip()
	# copy2clip(src_file, seq, get_send_size())

# import pyperclip
# data = pyperclip.paste()
# data = data[7:12]
# pyperclip.copy(data)
# pyperclip.paste()

# clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD) 
# clip.connect('owner-change',test) 
# Gtk.main() 

# def copy2clip(src_file, seq, size):
def copy2clip():
	global target_file
	global seq
	size = get_send_size()
	fp = open(target_file, 'rb')
	fp.seek(seq)
	send_data = fp.read(size)
	fp.close()

	data = magic + ':data:' + str(seq) + ':' + str(size) + ':' + str(total) + ':\n'
	data = data + base64.b64encode(send_data)
	# TODO: 计算md5sum
	pyperclip.copy(data)

	pass

def get_send_size():
	send_size = total - seq
	if send_size > segment:
		send_size = segment
	return send_size

def clip_server(src_file):
	# TODO: 处理文件不存在异常情况
	global total
	total = os.path.getsize(src_file)
	# TODO: 计算md5sum

	copy2clip()
	# copy2clip(src_file, seq, get_send_size())
	# copy2clip(fp, seq, segment)

	pass

def usage():
	print('<bin> file')
	pass

def main():
	if len(sys.argv) <= 1:
		usage()
		sys.exit(1)
	global target_file
	target_file = sys.argv[1]
	clip_server(target_file)

	clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD) 
	clip.connect('owner-change',test) 
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	Gtk.main() 

	pass

if __name__ == '__main__':
	main()
