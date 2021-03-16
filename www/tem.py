import random
import time
from multiprocessing import Process, Queue
from time import sleep
from www.log import Log


def app(q):
    t = time.time()
    for i in range(100):
        print('进行中。。。：%s' % i)
        sleep(1)
        q.put(i)
    print(time.time() - t)


def logg(q):
    log = Log().get_logger()
    while True:
        value = q.get(True)

        log.info(value)
        sleep(random.random() * 2)


if __name__ == '__main__':

    q = Queue()

    # p1 = Process(target=app, args=(q,))
    p2 = Process(target=logg, args=(q,))

    # p1.start()
    p2.start()

    for i in range(100):
        print('进行中。。。：%s' % i)
        sleep(1)
        q.put(i)

    # p1.join()

    # p2.terminate()

