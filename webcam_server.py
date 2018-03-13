'''
MIT License

Copyright (c) 2018 Forest Jacobsen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import cv2
import sys
import socket
import struct
import pickle
import threading
from time import sleep
from select import select
from hashlib import sha512
from getpass import getpass
from string import letters, digits
from random import SystemRandom as random


def depickle(obj):
    ''' Turns pickle stream into object.
        Returns False on failure, object on success'''
    try: return pickle.loads(obj)
    except: return False


def cryp_str(length, prefix='', return_hash=False):
    ''' Generates and/or hashes string with sha512.

        Usage
            Generate 512 bit string: cryp_str(64)
            Hash string: cryp_str(0, string, True)'''
    for _ in xrange(length): prefix += random().choice(letters+digits)
    return sha512(prefix).hexdigest() if return_hash else prefix


def read_ready(sock, timeout):
    ''' Determines if socket is ready to read from.

        Args:
            sock    socket object
            timeout time to wait before returning (in seconds)

        Returns:
            0       socket is ready to read from
            1       no errors, and no data
            2       socket encountered an error
    '''
    read, _, err = select([sock], [], [sock], timeout)
    if len(err) != 0: return 2
    if len(read) == 0: return 1
    return 0


class Socks:
    '''This class provides functions making socket operations easier and more effecient to develop.
    '''
    @staticmethod
    def connect(host, port, debug=False):
        ''' Attempts to connect to given endpoint.
            Returns:
                False   could not connect
                socket  connected'''
        try:
            sock = socket.socket()
            sock.connect((host, port))
            return sock
        except Exception as e:
            if debug: print e
            return False

    @staticmethod
    def recv(sock, timeout=30, debug=False):
        ''' Receives data from socket object.

            Returns:
                1       timeout
                2       socket error
                string  data received from socket'''
        data = ''

        try:
            ready = read_ready(sock, timeout)
            if ready != 0: return ready

            length = sock.recv(4)
            length = struct.unpack('>I', length)[0]

            while len(data) < length:
                ready = read_ready(sock, timeout)
                if ready != 0: return ready
                data += sock.recv(8192)

            return data
        except socket.error as e:
            if debug is True and 'Errno 10054' not in str(e) and 'Errno 10053' not in str(e): print "[ERROR] (Socks.recv)\n        socket error: " + str(e)
            return 2
        except struct.error as e:
            if debug: print "[ERROR] (Socks.recv)\n        struct error: " + str(e)
            return 2
        except Exception as e:
            if debug: print "[ERROR] (Socks.recv)\n        unexpected error: " + str(e)
            return 2

    @staticmethod
    def send(sock, data, debug=False):
        ''' Sends data to remote end of connected socket.

            Returns:
                False       could not send data
                True        data successfully sent'''
        try:
            sent = 0
            data = struct.pack('>I', len(data)) + data

            while sent < len(data): sent += sock.send(data)
            return True
        except struct.error as e:
            if debug: print "[ERROR] (Socks.send)\n        struct error: " + str(e)
            return False
        except socket.error as e:
            if debug is True and 'Errno 10054' not in str(e) and 'Errno 10053' not in str(e): print "[ERROR] (Socks.recv)\n        socket error: " + str(e)
            return False
        except Exception as e:
            if debug: print "[ERROR] (Socks.send)\n        unexpected error: " + str(e)
            return False

    @staticmethod
    def close(sock):
        '''Shuts down, and closes socket object.'''
        try: sock.shutdown(socket.SHUT_RDWR)
        except: pass
        finally:
            try: sock.close()
            except: pass


class Webcam:
    '''Loads webcam pictures into memory, and pulls them out when requested.'''
    def __init__(self):
        self.__cam = None
        self.__frame = None
        self.__running = False

    def __stream(self):
        '''Takes pictures from webcam, and loads into memory.'''
        while self.__running:
            ret, frame = self.__cam.read()
            if ret: self.__frame = pickle.dumps(frame)
            sleep(0.7)  # cv2 freezes if FPS goes above 1.5

    def start(self):
        ''' Starts the recording process.

            Returns:
                True        started successfully
                False       could not start
        '''
        if self.__running: return False

        self.__cam = cv2.VideoCapture(0)
        if self.__cam.isOpened() is False: return False
        self.__running = True

        t = threading.Thread(target=self.__stream)
        t.setDaemon(True)
        t.start()

        return True

    def stop(self):
        self.__running = False
        self.__cam = None

    def get_frame(self):
        return self.__frame


class Server:
    ''' Base class for other server classes to inherit from.

        Note: Child classes are required to have a function called "on_connect".
              This function will be called anytime a new connection is made to the server.
              It requires 1 argument, an array holding the connection socket and address info in that order.'''
    def __init__(self, port, debug=False, verbose=False):
        # double underscore functions and variables don't clash when the same name is used by child and parent classes
        self.__port = port
        self.__debug = debug
        self.__running = False
        self.__verbose = verbose
        self.__sock = socket.socket()

    def __listen(self):
        ''' Background thread class for listening for '''
        while self.__running:
            try:
                if read_ready(self.__sock, 1) != 0: continue  # wait 1 second for a client to accept. Allows enough time to exit when told to stop, and to accept incoming connections
                t = threading.Thread(target=self.on_connect, args=(self.__sock.accept(),))
                t.setDaemon(True)
                t.start()
            except socket.timeout: continue
            except Exception as e:
                # TODO: find more effecient and less ugly way to check for listen socket being closed
                if str(e).startswith('[Errno 9]'): return  # listening socket has been closed
                if self.__debug: print "[ERROR] Server.__listen(): " + str(e)

    def start(self):
        ''' Sets up the server and starts the listening thread.'''
        if self.__running: return

        self.__running = True
        self.__sock.bind(('0.0.0.0', self.__port))
        self.__sock.listen(5)

        if self.__verbose: print "[INFO] server started"

        t = threading.Thread(target=self.__listen)
        t.setDaemon(True)
        t.start()

    def stop(self):
        ''' Signals the running threads to stop, and closes the listening socket'''
        if self.__running is False: return
        self.__running = False
        Socks.close(self.__sock)
        self.__sock = socket.socket()

    def __del__(self):
        self.stop()


class WebcamServer(Server):
    ''' Server for sending webcam feed to connected clients.'''
    def __init__(self, password, verbose=True, debug=False):
        ''' Arguments:
                password    password for clients to use
                verbose     set to print basic information or not
                debug       set to print error and debugging information or not'''
        Server.__init__(self, 1895, verbose=verbose, debug=debug)
        self.__password = password
        self.__verbose = verbose
        self.__debug = debug

        self.__webcam = Webcam()
        self.__webcam.start()

    def __stream(self, conn):
        ''' Function for streaming webcam feed to client.'''
        frame = None

        while True:
            sleep(0.1)
            new_frame = self.__webcam.get_frame()
            if new_frame == frame: continue
            frame = new_frame
            if Socks.send(conn, frame) is False: break

        Socks.close(conn)

    def on_connect(self, info):
        ''' Function used by base Server class for new connections.
            Gives connected client CHAP challenge, then sends to stream function if passed.
        '''
        conn, addr = info
        chap = cryp_str(128)  # 128byte string for 1024 bit chap nonce
        chap_hash = cryp_str(0, self.__password+chap, True)

        Socks.send(conn, chap)
        if Socks.recv(conn) != chap_hash:
            Socks.send(conn, 'FAIL')
            Socks.close(conn)
            if self.__verbose: print "[INFO] failed login from " + addr[0]
            return

        Socks.send(conn, 'SUCC')
        if self.__verbose: print "[INFO] successfull login from " + addr[0]
        self.__stream(conn)

    def stop(self):
        Server.stop(self)
        self.__webcam.stop()

    def __del__(self):
        self.stop()


class Client:
    ''' Class for connecting to server to fetch stream.'''
    def __init__(self):
        self.sock = None
        self.connected = False

    def connect(self, host):
        ''' Connects to webcam server.

            Returns:
                False       could not connect
                True        connected
        '''
        sock = Socks.connect(host, 1895)
        if sock is False: return False

        self.sock = sock
        self.connected = True

        return True

    def login(self, password):
        ''' Solves CHAP challenge and attempts to login.

            Returns:
                False       incorrect password
                True        successfull login'''
        chap = Socks.recv(self.sock)
        if chap in [1, 2]:
            Socks.close(self.sock)
            self.connected = False
            return False

        Socks.send(self.sock, sha512(password+chap).hexdigest())
        if Socks.recv(self.sock) != 'SUCC':
            Socks.close(self.sock)
            self.connected = False
            return False

        return True

    def stream(self):
        ''' Starts stream after successfull login.'''
        errors = 0
        cv2.namedWindow("Remote-Webcam")

        while self.connected:
            if errors > 2: break

            frame = depickle(Socks.recv(self.sock))
            if frame is False:  # timeout, socket error, or data from server was malformed
                errors += 1
                continue

            errors = 0
            cv2.imshow("Remote-Webcam", frame)
            cv2.waitKey(1)  # needed for cv2.imshow to update

        self.disconnect()

    def disconnect(self):
        self.connected = False
        Socks.close(self.sock)

    def __del__(self):
        self.disconnect()


def main():
    ''' Usage
            Server:
                python webcam_server.py -s
            Client:
                python webcam_server.py
                python webcam_server.py -c
    '''
    if len(sys.argv) > 1 and sys.argv[1] == '-s':
        server = WebcamServer(getpass(), debug=True)
        server.start()

        try:
            while True: sleep(1)
        except KeyboardInterrupt: pass
        finally: server.stop()
    else:
        host = raw_input('Host: ')
        password = getpass('Password: ')
        client = Client()
        if client.connect(host):
            if client.login(password):
                print "Logged in!"
                client.stream()
            else: print "Could not login!"
        else: print "Could not connect!"


if __name__ == '__main__':
    main()
