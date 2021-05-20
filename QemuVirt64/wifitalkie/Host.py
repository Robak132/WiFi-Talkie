#!/usr/bin/env python
import pyaudio
import socket

import threading
# for communicating with server
import selectors
from types import SimpleNamespace

chunk_size = 1024
pa = pyaudio.PyAudio()
data = None
serv_IP = '10.0.2.15'
my_IP = '10.0.2.15'  # for now, please manually specify your IP address in local network
serv_comm_port = 61237
serv_audio_port = None
streaming_event = threading.Event()

class Communication:
    def __init__(self, serv_host = serv_IP, serv_port = serv_comm_port):
        self.serv_IP = serv_host
        self.serv_port = serv_port
        self.sel = selectors.DefaultSelector()
        self.sock = None
        self.my_IP = None
        self.my_port = None
        self.messages = []

    def connect(self):
        server_addr = (self.serv_IP, self.serv_port)
        print('attempting to start communication with server at', server_addr, flush=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.connect_ex(server_addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.messages = [b'?active']
        data = SimpleNamespace( messages=list(self.messages),
                                outb=b'')
        self.sel.register(self.sock, events, data=data)

    def service_connection(self, key, mask):
        global serv_audio_port
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                message = recv_data.decode('ascii')
                print(f'received message {message}')
                if message[0] == '?':
                    if message[1:7] == 'active':
                        data.outb += b'active'
                elif message[:6] == 'active':
                    print('Communication with server is still working.', flush=True)
                elif message[:6] == 'accept':
                    print("Server accepted listening request.", flush=True)
                elif message[:5] == 'speak':
                    if message[6:] == 'rejected':
                        print("Server rejected speaking request.", flush=True)
                    elif message[6:].isdigit():
                        print("Server accepted speaking request.", flush=True)
                        serv_audio_port = int(message[6:])
                else:
                    print('received unknown message', repr(recv_data), 'from server at', sock.getpeername(), flush=True)
            if not recv_data:
                print('closing connection with server at ', sock.getpeername())
                self.sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            if not data.outb and data.messages:
                data.outb = data.messages.pop(0)
            if data.outb:
                print('sending', repr(data.outb), 'to server at', sock.getpeername(), flush=True)
                sent = sock.send(data.outb)  # Should be ready to write
                data.outb = data.outb[sent:]

    def connect_listener(self, listener_port):
        if self.sock is not None:
            self.sock.send(f'?join {listener_port}'.encode('ascii'))
        else:
            print("Connection with server hasn't been established yet. Socket doesn't exist yet.", flush=True)

    def send_message(self, message):    # not recommended for use in final product!
        if message == '?active':
            self.messages.append(message.encode('ascii'))
        elif message.startswith('?join') and  message[6:].isdigit():
            self.messages.append(message.encode('ascii'))

    def launch(self):
        self.connect()
        while True:
                events = self.sel.select(timeout=None)
                if events:
                    for key, mask in events:
                        self.service_connection(key, mask)
                # Check for a socket being monitored to continue.
                if not self.sel.get_map():
                    break
        print("Communication with Raspberry server has been lost.", flush=True)
        self.sock.close()




def listener_fun():
    print('Listener thread initialized.', flush=True)
    stream = pa.open(format=pyaudio.paInt16, # pyaudio.paInt24
                     channels=1,
                     rate=48000, # alt. 44100
                     output=True,
                     frames_per_buffer=chunk_size)

    # Socket Initialization
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # For using same port again
    sock.bind((my_IP, 0))
    communication.connect_listener(sock.getsockname()[1])
    sock.listen(5)
    client, address = sock.accept()
    print('Ready for receiving datastream from server', flush=True)

    while True:
        data = client.recv(chunk_size)  # Receive one chunk of binary data
        if data:
            stream.write(data)  # Play the received audio data
            print(data[:30], flush=True)  # Print the beginning of the batch
            client.send(b'ACK')  # Send back Acknowledgement, has to be in binary form


communication = Communication()
communication_thread = threading.Thread(name=f'WiFi-Talkie communication handler', target=communication.launch, daemon=True)
communication_thread.start()

while True:
	pass
