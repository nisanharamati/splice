import socket

HOST = ''
PORT = 9009
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
print dir(s)
print s.fileno()
data = s.recv(1024)
s.close()
print 'Received', data
