#!/usr/bin/python -t
# -*- coding:utf-8 -*-

from gi.repository import Gtk, Gdk 
import pyperclip
import sys, os
import base64
import signal

magic="ksvd@copy"
ack=0
target_file=""
total=0
# TODO: 暂时用全局变量控制

def test(*args): 
	# print "Clipboard changed: recv data?"
	data = pyperclip.paste()
	# TODO: 日志加时间戳
	print 'clip changed, data len ', len(data) # TODO: 计算clip.paste时间消耗
	if not data.startswith(magic + ':data:'):
		# TODO: 处理异常?
		return

	head_pos = data.find('\n')
	fuck = data[:head_pos].split(':')
	seq = int(fuck[2])
	size = int(fuck[3])
	if seq == 0:
		global total
		total = int(fuck[4])
	print 'recv data seq: ', seq, ', size: ', size
	global ack
	ack = seq + size
	send_ack(ack)

	# save data
	file_data = base64.b64decode(data[head_pos:])
	open(target_file, 'ab').write(file_data)

	if ack >= total:
		print 'recv ended!'
		sys.exit(0)

def send_ack(ack):
	data = magic + ':ack:' + str(ack) + ':'
	pyperclip.copy(data)
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
	open(target_file, 'wb').close()

	clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD) 
	clip.connect('owner-change',test) 
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	Gtk.main() 

	pass

if __name__ == '__main__':
	main()
