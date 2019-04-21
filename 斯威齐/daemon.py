#!/usr/bin/env python
#coding: utf-8
import sys, os

 
def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
     #重定向标准文件描述符（默认情况下定向到/dev/null）
    try: 
        pid = os.fork() 
          #父进程(会话组头领进程)退出，这意味着一个非会话组头领进程永远不能重新获得控制终端。
        if pid > 0:
            sys.exit(0)   #父进程退出
    except OSError as e: 
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror) )
        sys.exit(1)
 
     #从母体环境脱离
    os.chdir("/home/xiacong/pig_xiacong/internet_of_things_feeders/server/")  #chdir确认进程不保持任何目录于使用状态，否则不能umount一个文件系统。也可以改变到对于守护程序运行重要的文件所在目录
    os.setsid()    #setsid调用成功后，进程成为新的会话组长和新的进程组长，并与原来的登录会话和进程组脱离。
    os.umask(0)    #调用umask(0)以便拥有对于写的任何东西的完全控制，因为有时不知道继承了什么样的umask。
    
 
     #执行第二次fork
    try: 
        pid = os.fork() 
        if pid > 0:
            sys.exit(0)   #第二个父进程退出
    except OSError as e: 
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror) )
        sys.exit(1)
 
     #进程已经是守护进程了，重定向标准文件描述符
 
    for f in sys.stdout, sys.stderr: 
    	f.flush()
    si = open(stdin, 'r')
    so = open(stdout, 'a')
    se = open(stderr, 'ab', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())    #dup2函数原子化关闭和复制文件描述符
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
 
def check(server):
    import time
    sys.stdout.write('\n Daemon started with pid %d\n' % os.getpid())
    sys.stdout.write('Daemon stdout output\n')
    sys.stderr.write('\n Daemon stderr output\n')
    count = 0
    is_alive = "ps -ef | grep " + server + " | grep -v grep"

    sys.stdout.write(os.getcwd())

    restart = "nohup python " + server + "&"
    while True:
        if os.system(is_alive):
            os.system(restart)
            message = "server is restarting."
            
        else:
            message = "server is running."
        sys.stdout.write('%d: %s, %s\n' %(count, time.ctime(), message))
        sys.stdout.flush()
        count = count+1
        time.sleep(5)
 
if __name__ == "__main__":
      daemonize('/dev/null','/home/xiacong/daemon_stdout.log','/home/xiacong/daemon_error.log')
      check("server.py")

