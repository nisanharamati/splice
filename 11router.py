"""A router using system.splice(2) to connect two sockets.

The router takes two ports as its arguments and listens on
localhost. Data transport is bidirectional.
"""
import errno
import fcntl
import os
import os.path
import socket
import select
import threading
import time

import splice


def set_nonblock(fd): #pylint: disable-msg=C0103
    '''Set a file descriptor in non-blocking mode'''
 
    flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
    flags |= os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)


class EndPoint(threading.Thread):
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.event = threading.Event()

    def run(self):
        self.sock.connect((self.host, self.port))
        self.event.set()
    
    def close(self):
        self.sock.close()
 

def main(port1, port2):
    # connect to both endpoints
    HOST = ''
    ep1 = EndPoint(HOST, port1)
    ep2 = EndPoint(HOST, port2)
    # start both
    ep1.start()
    ep2.start()
    # wait for both to connect
    while not (ep1.event.is_set() and ep2.event.is_set()):
        time.sleep(0.1)
    # we're connected on both ends. Start splicing!
    ep1_fd = ep1.sock.fileno()
    set_nonblock(ep1_fd)
    ep2_fd = ep2.sock.fileno()
    set_nonblock(ep2_fd)
    # get splicing
    chunksize = 1024
    flags = \ 
        splice.SPLICE_F_MOVE | splice.SPLICE_F_MORE | splice.SPLICE_F_NONBLOCK
    # run the transfer
    while True:
        # 2->1 direction
        f1_read, f2_write, _ = select.select([ep1_fd], [ep2_fd], [])
        if f1_read and f2_write: 
            # splice!
            try:
                d21 = splice.splice(ep2_fd, None, ep1_fd, None, chunksize, flags)
            except IOError, exc:
                if exc.errno in [errno.EAGAIN, errno.EWOULDBLOCK]:
                    # one of the fds blocked... retry!
                    pass
                else:
                    raise
        # 1->2 direction
        f2_read, f1_write, _ = select.select([ep2_fd], [ep1_fd], [])
        if f2_read and f1_write:
            # splice!
            try:
                d12 = splice.splice(ep1_fd, None, ep2_fd, None, chunksize, flags)
            except IOError, exc:
                if exc.errno in [errno.EAGAIN, errno.EWOULDBLOCK]:
                    # one of the fds blocked... retry!
                    pass
                else:
                    raise
        # we might have transffered some data in either or both directions
        # so say so!
        if d12:
            print '1->2: {} bytes'.format(len(d12))
        if d21:
            print '1<-2: {} bytse'.format(len(d21))
        # take a short break
        time.sleep(0.0001)
    # clean up both ends
    ep1.close()
    ep2.close()


if __name__ == '__main__':
    import sys
    main(sys.argv[1], sys.argv[2])

