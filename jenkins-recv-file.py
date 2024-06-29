#!/usr/bin/python3 -t
# -*- coding:utf-8 -*-

import sys, os
import base64
import signal
import time
import queue
import jenkins
import threading

magic='1qaz2wsx@@'
ack=0
target_file=""
total=0
start=0
# TODO: 暂时用全局变量控制

jenkins_url = "http://192.168.120.30:8080/"
jenkins_job='commit_copy'

jenkins_queue = queue.Queue(1000)
data_queue = queue.Queue(100000)


# 开启jenkins线程
def remove_build():
		remove_server = jenkins.Jenkins(jenkins_url, username="kycd", password='Ksvd@2023')
		while True:
				if jenkins_queue.empty():
						time.sleep(0.1)
						continue
				while not jenkins_queue.empty():
						i = jenkins_queue.get()
						remove_server.delete_build(jenkins_job, i)


# 开启jenkins线程
def recv_build():
		jenkins_server = jenkins.Jenkins(jenkins_url, username="kycd", password='Ksvd@2023')
		number = start
		if number == 0:
			number = jenkins_server.get_job_info(jenkins_job)['nextBuildNumber']
		print("jenkins next number is " + str(number))
		while True:
				try:
						b64_data = jenkins_server.get_build_info(jenkins_job,number)['actions'][0]["parameters"][0]['value']
						data_queue.put(b64_data)
						jenkins_queue.put(number) # FIXME: 删除掉这个build
						number = number + 1 # 简单自增即可
				#except jenkins.NotFoundException as error:
				except Exception as error:
						time.sleep(0.1)
						continue


def recv_data(data): 
	# TODO: 日志加时间戳
	if None == data or not data.startswith(magic + ':data:'):
		print('wrong data %s' % data)
		# TODO: 处理异常?
		return

	head_pos = data.find('\n')
	param = data[:head_pos].split(':')
	seq = int(param[2])
	size = int(param[3])
	if seq == 0:
		global total
		total = int(param[4])
	#print 'recv data seq: ', seq, ', size: ', size
	print('recv data seq: %d, size: %d' % (seq, size))
	global ack
	ack = seq + size

	# save data
	file_data = base64.b64decode(data[head_pos:])
	open(target_file, 'ab').write(file_data)

	if ack >= total:
		print('recv ended!')
		sys.exit(0)

def usage():
	print('<bin> file [seq]')
	pass

def main():
	if len(sys.argv) <= 1:
		usage()
		sys.exit(1)
	global start
	global target_file
	target_file = sys.argv[1]
	open(target_file, 'wb').close()

	if len(sys.argv) > 2:
		start = int(sys.argv[2])

	# 开启线程
	recv_thread = threading.Thread(target=recv_build)
	# recv_thread.daemon = True
	recv_thread.start()

	# remove_thread = threading.Thread(target=remove_build)
	# remove_thread.daemon = True
	# remove_thread.start()

	while True:
		if data_queue.empty():
			time.sleep(0.1)
			continue
		while not data_queue.empty():
			data = data_queue.get()
			recv_data(data)


if __name__ == '__main__':
	main()
