import socket
import pyaudio
# import tkinter
import threading
from tkinter import *

import selectors
from types import SimpleNamespace

pyAudio = pyaudio.PyAudio()
chunk_size = 1024
data = None  # chunk do przesłania
streaming_event = threading.Event()
audio_streamers = {}
audio_streamers_terminators = {}

serv_IP = '192.168.1.14' # '192.168.1.14'
serv_comm_port = 61237

class Communication:
    def __init__(self):
        self.host = serv_IP         # Standard loopback interface address (localhost)
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
                        new_speaker_port = setup_stream(data.addr[0], int(message[6:]))
                        data.outb += f'accept {new_speaker_port}'.encode('ascii')
                    elif message[1:7] == 'active':
                        data.outb += b'active'
                    elif message[1:6] == 'speak':
                        receiver_sock = speaker.create_receiver(data.addr[0])
                        receiver_setup = threading.Thread(name="Waiting for connection from the speaker", target=speaker.setup_audio_receiver, args=(receiver_sock,))
                        receiver_setup.start()
                        receiver_port = receiver_sock.getsockname()[1]
                        if receiver_port:
                            data.outb += f'speak {receiver_port}'.encode('ascii')
                        else:
                            data.outb += b'speak rejected'
                elif message == 'quit':
                    audio_streamers_terminators[data.addr[0]].set()
                    print('Terminated thread for sending stream to', data.addr, flush=True)
                else:
                    data.outb += b'unrecognized command: ' + recv_data
            else:
                print('closing connection to', data.addr, flush=True)
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
        self.priority_speaker = create_stream(is_microphone=True)
        print('Priority speaker created', flush=True)
        self.are_we_streaming.set()

    def stop_priority_speaking(self):
        if not self.speaker:
            self.are_we_streaming.clear()
        self.priority_speaker.close()
        self.priority_speaker = None
        print('Priority speaking ended', flush=True)

    def remove_speaker(self):
        if not self.priority_speaker:
            self.are_we_streaming.clear()
        self.speaker.close()
        self.speaker = None
        print('Speaker removed', flush=True)

    def create_receiver(self, speaker_IP):
        if self.priority_speaker is not None: return self.priority_speaker
        if self.speaker is not None: return self.speaker
        # Socket Initialization
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # For using same port again
        sock.bind((sock.gethostname(), 0))
        return sock

        # Mamy sock.bind, które ustaliło port na przyjmowanie transmisji, więc teraz trzeba napisać do hosta z portem
        # i jednocześnie stworzyć wątek do obsługi klienta kiedy zacznie nadawać

    def setup_audio_receiver(self, sock):
        sock.listen(5)
        self.speaker, address = sock.accept()
        print(f'Ready for receiving datastream from client at {address}', flush=True)
        self.are_we_streaming.set()

    def audio_forwarder(self):
        global data
        print('Speaker handler thread initialized', flush=True)
        while True:
            self.are_we_streaming.wait()
            try:
                speaker = self.get_speaker()
                if isinstance(speaker, socket.socket):
                    data = speaker.recv(chunk_size)  # Receive one chunk of binary data
                else:
                    data = speaker.read(chunk_size)  # Read binary data from audio stream (server mic)
                
                if data:
                    streaming_event.set()
                    print(data[:30])  # Print the beginning of the batch
                    if isinstance(speaker, socket.socket):
                        self.get_speaker().send(b'ACK')  # Send back Acknowledgement, has to be in binary form
                else:
                    print('A może tak?', flush=True)
            except ConnectionResetError:
                self.are_we_streaming.clear()
                print('Connection has been ended by the host. Closing receiver socket.', flush=True)
                speaker = self.get_speaker()
                if isinstance(speaker, socket.socket):
                    self.speaker.close()
                    self.speaker = None
                    print('self.speaker closed', flush=True)
                else:
                    self.priority_speaker.close() # priority speaker - nie wiem czy to jest dobrze
                    self.priority_speaker = None
                continue
            # except Exception as ex:
            #     print('Dosłownie każdy inny exception niż ConnectionResetError. Jeśli to się pojawia to trzeba zacząć się martwić.\n', ex, flush=True)
            #     continue


def create_stream(is_microphone = False):
#   Audio Stream (PyAudio) Initialization
    return pyAudio.open(format=pyaudio.paInt16, # pyaudio.paInt24
                   channels=1,
                   rate=48000, # alt. 44100
                   output=not is_microphone,
                   input=is_microphone,
                   frames_per_buffer=chunk_size)

def setup_stream(client_IP, client_port):
    # Socket Initialization
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((sock.gethostname(), 0))  # możliwe że tutaj trzeba będzie client_IP
    sock.connect_ex((client_IP, client_port))
    audio_streamers_terminators[client_IP] = threading.Event()
    audio_streamers[client_IP] = threading.Thread(name=f'Sender to {client_IP} on port {client_port}', target=audio_streamer, args=(sock, streaming_event, client_IP, client_port,))
    audio_streamers[client_IP].start()     # docelowo: audio_senders[(client_IP, client_port)]
    return sock.getsockname()[1]

def audio_streamer(sock, streaming_event, client_IP, client_port):
    global data
    end_condition = audio_streamers_terminators[client_IP]
    print(f'Thread for {client_IP} on port {client_port} configured', flush=True)
    while not end_condition.isSet():
        streaming_event.wait()
        if data is not None:
            sock.send(data)
            sock.recv(chunk_size)
        streaming_event.clear()

speaker = Speaker()
speaker_thread = threading.Thread(name=f'Audio receiver', target=speaker.audio_forwarder, daemon=True)
speaker_thread.start()

# GUI do symulacji
class VOIP_FRAME(Frame):
    def OnMouseDown(self, uselessArgument = None): # Leave uselessArgument there, it prevents some pointless errors
        speaker.start_priority_speaking()

    def muteSpeak(self, uselessArgument = None): # Leave uselessArgument there, it prevents some pointless errors
        speaker.stop_priority_speaking()

    def createWidgets(self):
        self.speakb = Button(self)
        self.speakb["text"] = "Priority speak"
        self.speakb.pack({"side": "left"})
        self.speakb.bind("<ButtonPress-1>", self.OnMouseDown)
        self.speakb.bind("<ButtonRelease-1>", self.muteSpeak)

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.mouse_pressed = False
        self.pack()
        self.createWidgets()

communicator = Communication()
communicator_thread = threading.Thread(name=f'Communicator thread', target=communicator.launch, daemon=True)
communicator_thread.start()

print('this is the Raspberry main server')

root = Tk()
app = VOIP_FRAME(master=root)
app.mainloop()
try: root.destroy()
except: pass
for event in audio_streamers_terminators.values():
    event.set()