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

## TODO

windows下也能使用剪切版拷贝文件?
https://gist.github.com/Garciat/1077310

https://www.one-tab.com/page/nsZ5o0-1S-6CmkhwRL24BQ


其他python使用clip的示例
https://python.hotexamples.com/examples/gtk/Clipboard/-/python-clipboard-class-examples.html

https://gist.github.com/Garciat/1077310

https://www.programcreek.com/python/example/8347/gtk.Clipboard

## FAQ

#### ubuntu系统clip最后一个ack没有发出来的问题

暂时使用xclip解决
```
def send_finish_ack(ack):
	data = magic + ':ack:' + str(ack) + ':\n'
	import subprocess
	p = subprocess.Popen(['xclip', '-selection', 'c'], stdin=subprocess.PIPE, close_fds=True)
	p.communicate(input=data.encode('utf-8'))
```

关键字《Gtk.Clipboard set_text not working》

https://askubuntu.com/questions/1365154/gtk-clipboard-owner-change-event-detecting-whether-the-changer-is-me

ubuntu 20.04 gtk clipboard.set_text not working的上游bug
https://gitlab.gnome.org/GNOME/pygobject/-/issues/405


