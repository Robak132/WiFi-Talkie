import socket
import pyaudio
import threading
import selectors
from types import SimpleNamespace

pyAudio = pyaudio.PyAudio()
chunk_size = 1024
data = None  # chunk do przesłania
streaming_event = threading.Event()
audio_senders = []

serv_IP = '192.168.0.150'
serv_comm_port = 61237


class Communication:
    def __init__(self):
        self.host = serv_IP  # Standard loopback interface address (localhost)
        self.port = serv_comm_port  # Port to listen on (non-privileged ports are > 1023)
        self.sel = selectors.DefaultSelector()

    def accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        print('accepted connection from ', addr, flush=True)
        conn.setblocking(False)
        data = SimpleNamespace(addr=addr, inb=b'', outb=b'')
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(conn, events, data=data)

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                message = recv_data.decode('ascii')
                print(f'received message {message}', flush=True)
                if message[0] == '?':
                    if message[1:5] == 'join' and message[6:].isdigit():
                        new_speaker_port = setupStream(data.addr[0], int(message[6:]))
                        data.outb += f'accept {new_speaker_port}'.encode('ascii')
                    elif message[1:7] == 'active':
                        data.outb += b'active'
                    elif message[1:6] == 'speak':
                        port = speaker.set_speaker(data.addr[0])
                        if port:
                            data.outb += f'speak {port}'.encode('ascii')
                        else:
                            data.outb += f'speak reject'.encode('ascii')
                else:
                    data.outb += b'unrecognized command: ' + recv_data
            else:
                self.sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            if data.outb:
                print("echoing", repr(data.outb), "to", data.addr, flush=True)
                sent = sock.send(data.outb)  # Should be ready to write
                data.outb = data.outb[sent:]

    def launch(self):
        lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lsock.bind((self.host, self.port))
        lsock.listen()
        print('listening for communiaction on', (self.host, self.port), flush=True)
        lsock.setblocking(False)
        self.sel.register(lsock, selectors.EVENT_READ, data=None)

        while True:
            events = self.sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    self.accept_wrapper(key.fileobj)
                else:
                    self.service_connection(key, mask)


class Speaker:
    def __init__(self):
        self.speaker = None
        self.priority_speaker = None
        self.are_we_streaming = threading.Event()

    def get_speaker(self):
        if self.priority_speaker is not None:
            return self.priority_speaker
        else:
            return self.speaker

    def start_priority_speaking(self):
        self.priority_speaker = createStream(is_microphone=True)
        print('Priority speaker created', flush=True)
        self.are_we_streaming.set()

    def stop_priority_speaking(self):
        self.priority_speaker.close()
        self.priority_speaker = None
        if not self.speaker:
            self.are_we_streaming.clear()
        print('Priority speaking ended', flush=True)

    def remove_speaker(self):
        self.speaker.close()
        self.speaker = None
        if not self.priority_speaker:
            self.are_we_streaming.clear()
        print('Speaker removed', flush=True)

    def set_speaker(self, speaker_IP):
        if self.is_speaker_free() is not True: return False
        # Socket Initialization
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # For using same port again
        sock.bind((speaker_IP, 0))
        yield sock.getsockname()[1]
        sock.listen(5)
        client, address = sock.accept()
        self.speaker = client
        self.speaker.read = self.speaker.recv
        self.are_we_streaming.set()
        print(f'Ready for receiving datastream from client at {client_IP}', flush=True)

    def speaker_handler(self):
        global data
        print('Speaker handler thread initialized', flush=True)
        while self.are_we_streaming.wait():
            data = self.get_speaker().read(chunk_size)  # Receive one chunk of binary data
            if data:
                streaming_event.set()
                # print(data[:30])  # Print the beginning of the batch
                # self.get_speaker().send(b'ACK')  # Send back Acknowledgement, has to be in binary form


def createStream(is_microphone=False):
    # Audio Stream (PyAudio) Initialization
    return pyAudio.open(format=pyaudio.paInt16,  # pyaudio.paInt24
                        channels=1,
                        rate=48000,  # alt. 44100
                        output=not is_microphone,
                        input=is_microphone,
                        frames_per_buffer=chunk_size)


def setupStream(client_IP, client_port):
    # Socket Initialization
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('192.168.0.150', 0))  # możliwe że tutaj trzeba będzie client_IP
    serv_port = sock.getsockname()[1]
    sock.connect_ex((client_IP, client_port))
    audio_senders.append(threading.Thread(name=f'Sender to {client_IP} on port {client_port}', target=sendStream,
                                          args=(sock, streaming_event, client_IP, client_port,)))
    audio_senders[-1].start()
    return client_port


def sendStream(sock, streaming_event, client_IP, client_port):
    global data
    print(f'Thread for {client_IP} on port {client_port} configured', flush=True)
    while True:
        streaming_event.wait()
        if data is not None:
            sock.send(data)
            sock.recv(chunk_size)
        else:
            break
        streaming_event.clear()
    sock.close()


if __name__ == '__main__':
    speaker = Speaker()
    speaker_thread = threading.Thread(target=speaker.speaker_handler, daemon=True)
    speaker_thread.start()

    communicator = Communication()
    communicator_thread = threading.Thread(name=f'Communicator thread', target=communicator.launch, daemon=True)
    communicator_thread.start()

    print('this is the Raspberry main server')
    while True:
        command = input()
        if command == 'speak':
            speaker.start_priority_speaking()
        elif command == 'stop':
            speaker.stop_priority_speaking()
        elif command == 'kill':
            break

    for thread in audio_senders:
        thread.terminate()
