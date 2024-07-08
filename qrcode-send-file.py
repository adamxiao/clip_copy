#!/usr/bin/python3 -t
# -*- coding:utf-8 -*-

# refer clip_server3.py

from gi.repository import Gtk, Gdk 
import sys, os
import signal
import struct
import qrcode

magic="qwer123#"
segment=2900
seq=0
target_file=""
total=0
# TODO: 暂时用全局变量控制

def gen_qrcode(data):
  # 生成二维码
  qr = qrcode.QRCode(
      version=1,
      error_correction=qrcode.constants.ERROR_CORRECT_L,
      box_size=10,
      border=4,
  )

  # 最多2953个字符
  qr.add_data(data)
  qr.make(fit=True)

  img = qr.make_image(fill='black', back_color='white')
  img_path = "/tmp/qrcode.png"
  img.save(img_path)

  # 使用GNOME图像查看器显示图像
  os.system(f'xdg-open {img_path}')

def test(*args): 
	clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD) 
	data = clip.wait_for_text()
	if None == data  or not data.startswith(magic + ':ack:'):
		return

	huck = data.split(':')
	ack = int(huck[2])
	print ('recv ack ', ack)
	global seq
	seq = ack

	# should send data again?
	if seq >= total:
		sys.exit(0)
	copy2clip()


def copy2clip():
	global target_file
	global seq
	size = get_send_size()
	fp = open(target_file, 'rb')
	fp.seek(seq)
	send_data = fp.read(size)
	fp.close()

	#data = magic + ':data:' + str(seq) + ':' + str(size) + ':' + str(total) + ':\n'
	# data = data.encode('utf-8') + send_data
	# magic, seq, size, total => bin_data
	data = struct.pack('8sLLL', magic.encode('utf-8'), seq, size, total)
	# data += struct.pack('2900s', send_data)
	gen_qrcode(data + send_data)
	print('gen qrcode seq %d, size %d end' % (seq, size))


def get_send_size():
	send_size = total - seq
	if send_size > segment:
		send_size = segment
	return send_size

def clip_server(src_file):
	global total
	total = os.path.getsize(src_file)

	copy2clip()


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
