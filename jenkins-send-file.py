#!/usr/bin/python3 -t
# -*- coding:utf-8 -*-

import sys, os
import base64
import signal
import jenkins

magic='1qaz2wsx@@'
# echo "$magic:data:$seq:$send_size:$checksum:"
segment=4096
seq=0
target_file=""
total=0
# TODO: 暂时用全局变量控制

#jenkins_url = "http://192.168.120.30:8080/"
jenkins_url = "http://192.5.1.30:8080/"
jenkins_job='commit_copy'
jenkins_server = jenkins.Jenkins(jenkins_url, username="kycd", password='Ksvd@2023')


# FIXME: 开启线程处理，加速
def send_data_to_jenkins(enc_data):
	# send_data = self.jenkins_queue.get()
	adam = jenkins_server.build_job(jenkins_job, {'commit': enc_data})
	

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
	data = data + base64.b64encode(send_data).decode('utf-8')
	send_data_to_jenkins(data)


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

	seq = 0
	while seq < total:
		copy2clip()
		seq += segment


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


if __name__ == '__main__':
	main()
