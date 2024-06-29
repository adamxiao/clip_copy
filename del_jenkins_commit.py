#!/usr/bin/python3
#-*-coding:UTF-8 -*-

import jenkins
import json
import base64
import datetime
import logging
import logging.config
import os
import threading
import time

url="http://192.168.120.30:8080/"
first_build="commit"
next_build='commit_copy'
developer="kycd_dev"
username="kycd"
password="Ksvd@2023"
config_file="/usr/lib/update-KSVD-tool/config.properties"
version="8.1.7-server"
exe_time="08:00:00"
logging.basicConfig(level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(funcName)s: %(filename)s, %(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
            filemode='a')

def run_task():
    logging.info("will run task...")
    logging.info("start requesting "+ url)
    server = jenkins.Jenkins(url,username="kycd",password='Ksvd@2023')
    number = server.get_job_info(next_build)['nextBuildNumber']
    logging.info("the next number is " + str(number))

    # 获取内容 => ok
    while True:
      try:
          build = server.get_build_info(next_build,number)
          logging.info(build)
          # FIXME: 如果是rebuild的化, 获取方式不一样。。。这里就会报错...
          param = build['actions'][0]["parameters"][0]['value']
          logging.info(param)
          number = number + 1 # 简单自增即可
      except jenkins.NotFoundException as error:
          time.sleep(0.9)
          logging.info("not found build")
    return

    # 新建 commit内容
    adam = server.build_job(next_build, {'commit': 'aaabbb'})
    print(adam)

    # TODO: 删除job
    # python3的jenkins没有这个delete_build接口?

    return

def add_commits():
    server = jenkins.Jenkins(url,username="kycd",password='Ksvd@2023')
    number = server.get_job_info(next_build)['nextBuildNumber']
    logging.info("the next number is " + str(number))

    for i in range(10):
        try:
            adam = server.build_job(next_build, {'commit': 'aaabbb' + str(i)})
            print(adam)
            number += 1
        except jenkins.NotFoundException as error:
            pass
            logging.info("not found build")

def del_commits():
    logging.info("will run task...")
    logging.info("start requesting "+ url)
    server = jenkins.Jenkins(url,username="kycd",password='Ksvd@2023')
    number = server.get_job_info(next_build)['nextBuildNumber']
    logging.info("the next number is " + str(number))

    init = 13302

    for i in range(init, number):
        try:
            # FIXME: 优化: 直接获取所有的build, 然后开始删除...
            build = server.get_build_info(next_build, i)
            logging.info("delete build %d" % i)
            server.delete_build(next_build, i)
        #except jenkins.NotFoundException as error:
        except Exception as error:
            # do nothing
            continue

if __name__=='__main__':
    logging.info("start running.....")
    # run_task()
    del_commits()
    # add_commits()
