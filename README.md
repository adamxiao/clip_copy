# clip copy

通过剪切板通信，进行传输文件
server端发送文件数据, client接收文件数据，回复ack

## install

ubuntu
```bash
apt install xsel python-pyperclip
```

## usage

首先在接收文件端运行client脚本
```bash
python clip_client.py output.file
```

然后在发送文件端运行server脚本
```bash
python clip_server.py input.file
```
