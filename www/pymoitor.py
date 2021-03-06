import os, sys, time, subprocess
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


def log(s):
    print('【监控】: %s' % s)


class MyFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, fn):
        super(MyFileSystemEventHandler, self).__init__()
        self.restart = fn

    def on_any_event(self, event):
        if event.src_path.endswith('.py'):
            log('Python 源文件改动: %s' % event.src_path)
            self.restart()


command = ['echo', 'ok']
process = None


def kill_process():
    global process
    if process:
        log('杀死进程: [%s]' % process.pid)
        process.kill()
        process.wait()
        log('进程结束, code: %s' % process.returncode)
        process = None


def start_process():
    global process, command
    log('开启进程 %s ...' % ' '.join(command))
    process = subprocess.Popen(command, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)


def restart_process():
    kill_process()
    start_process()


def start_watch(path, callback):
    observer = Observer()
    observer.schedule(MyFileSystemEventHandler(restart_process), path, recursive=True)
    observer.start()
    log('监控目录 %s ...' % path)
    start_process()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    argv = sys.argv[1:]
    if not argv:
        print('使用: ./pymonitor 启动脚本')
        exit(0)
    if argv[0] != 'python':
        argv.insert(0, 'python')
    command = argv
    path = os.path.abspath('.')
    start_watch(path, None)