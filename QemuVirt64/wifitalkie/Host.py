#!/usr/bin/env python
import pyaudio
import socket
import tkinter  # for GUI, will be deleted on Raspberry version
import threading
import selectors
from types import SimpleNamespace

chunk_size = 1024
pa = pyaudio.PyAudio()
data = None
serv_IP = '192.168.0.150'
my_IP = socket.gethostbyname(socket.gethostname())
serv_comm_port = 61237
streaming_event = threading.Event()


class Communication:
    def __init__(self, serv_host = serv_IP, serv_port = serv_comm_port):
        self.serv_IP = serv_host
        self.serv_port = serv_port
        self.sel = selectors.DefaultSelector()
        self.sock = None
        self.messages = list([])
        self.is_speaker_accepted = threading.Event()
        # self.its_late = threading.Event()
        self.speaker_port = None
        
    def connect(self, messages):
        print(f'attempting to start communication with server at {self.serv_IP}:{self.serv_port}', flush=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.connect_ex((self.serv_IP, self.serv_port))
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.pending_requests = len(messages)
        data = SimpleNamespace( messages=list(messages),
                                outb=b'')
        self.sel.register(self.sock, events, data=data)

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                self.pending_requests -= 1
                message = recv_data.decode('ascii')
                print(f'received message: {message}\npending requests: {self.pending_requests}', flush=True)
                if message[:6] == 'active':
                    print('Communication with server is still working.', flush=True)
                elif message[:6] == 'accept':
                    print("Server accepted listening request.", flush=True)
                elif message[:5] == 'speak':
                    if message[6:] == 'rejected':
                        print("Server rejected speaking request.", flush=True)
                    elif message[6:].isdigit():
                        print("Server accepted speaking request.", flush=True)
                        self.speaker_port = int(message[6:])
                        self.is_speaker_accepted.set()
                    else:
                        print("Coś poszło bardzo bardzo nie tak.", flush=True)
                else:
                    print('received unknown message', repr(recv_data), 'from server at', sock.getpeername(), flush=True)
                # print('Closing socket after successful communication', flush=True)
                # self.sel.unregister(sock)
                # sock.close()
                # self.sock = None
            if not recv_data or self.pending_requests == 0:
                print('closing connection with server at ', sock.getpeername(), flush=True)
                self.sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            if not data.outb and data.messages:
                data.outb = data.messages.pop(0)
            if data.outb:
                print('sending', repr(data.outb), 'to server at', sock.getpeername(), flush=True)
                sent = sock.send(data.outb)  # Should be ready to write
                data.outb = data.outb[sent:]

    def request_listening(self, listener_port):
        if self.sock._closed is True:
            # self.connect([f'?join {listener_port}'.encode('ascii')])
            communication_thread = threading.Thread(name=f'WiFi-Talkie communication handler', target=self.launch, args=([f'?join {listener_port}'.encode('ascii')],), daemon=True)
            communication_thread.start()
            # self.its_late.set()
            return True
        else:
            print('socket is busy at the moment, try again later', flush=True)
            return False

    def request_speaking(self):
        print('Asking server for permission to speak.', flush=True)
        if self.sock._closed is True:
            # self.connect([b'?speak'])
            communication_thread = threading.Thread(name=f'WiFi-Talkie communication handler', target=self.launch, args=([b'?speak'],), daemon=True)
            communication_thread.start()
            # self.its_late.set()
        else:
            print('socket is busy at the moment, try again later', flush=True)
            return False
        self.is_speaker_accepted.clear()
        while not self.is_speaker_accepted.wait(10):
            print('Connecting to server is taking longer than usual...', flush=True)
        self.is_speaker_accepted.clear()
        return self.speaker_port

    # def request_listening(self, listener_port):
    #     if self.sock._closed is True:
    #         self.connect([f'?join {listener_port}'.encode('ascii')])
    #         self.its_late.set()
    #     else:
    #         self.pending_requests += 1
    #         self.sock.send(f'?join {listener_port}'.encode('ascii'))

    # def request_speaking(self):
    #     print('Asking server for permission to speak.', flush=True)
    #     if self.sock._closed is True:
    #         self.connect([b'?speak'])
    #         self.its_late.set()
    #     else:
    #         self.pending_requests += 1
    #         self.sock.send(b'?speak')
    #     self.is_speaker_accepted.clear()
    #     while not self.is_speaker_accepted.wait(10):
    #         print('Connecting to server is taking longer than usual...', flush=True)
    #     self.is_speaker_accepted.clear()
    #     return self.speaker_port

    def exit(self):
        if self.sock._closed is True:
            self.connect([b'quit'])
            # self.its_late.set()
        else:
            self.sock.send(b'quit')
        self.sock.close()


    def launch(self, messages = [b'?active']):
        self.connect(messages)
        while True:
                events = self.sel.select(timeout=None)
                if events:
                    for key, mask in events:
                        self.service_connection(key, mask)
                # Check for a socket being monitored to continue.
                if not self.sel.get_map():
                    break
        print("Communication with Raspberry server has been ended / lost.", flush=True)
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
    while communication.request_listening(sock.getsockname()[1]) is False:
        pass
    sock.listen(5)
    server, address = sock.accept()
    print('Ready for receiving datastream from server', flush=True)

    while True:
        data = server.recv(chunk_size)  # Receive one chunk of binary data
        if data:
            stream.write(data)  # Play the received audio data
            print(data[:30], flush=True)  # Print the beginning of the batch
            server.send(b'ACK')  # Send back Acknowledgement, has to be in binary form


communication = Communication()
communication_thread = threading.Thread(name=f'WiFi-Talkie communication handler', target=communication.launch, daemon=True)
communication_thread.start()



# Nadawca
# GUI do symulacji
class VOIP_FRAME(tkinter.Frame):
    def OnMouseDown(self, uselessArgument = None): # Leave uselessArgument there, it prevents some pointless errors
        self.mute = False
        self.speakStart()

    def muteSpeak(self, uselessArgument = None): # Leave uselessArgument there, it prevents some pointless errors
        self.mute = True
        print("You are now muted", flush=True)

    def speakStart(self):
        t = threading.Thread(target=self.speak)
        t.start()

    def speak(self):
        global data  # global variable for passing chunks to sender threads
        global serv_IP
        serv_audio_port = communication.request_speaking()
        if serv_audio_port is False:
            print('Speaking unavailable.', flush=True)
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # need to wait for serv_audio_port to come, gotta wait for message from server
        sock.connect((serv_IP, serv_audio_port))
        print("You are now speaking", flush=True)
        self.stream.start_stream()
        while self.mute is False:
            sock.send(self.stream.read(chunk_size))
            sock.recv(chunk_size)
        self.stream.stop_stream()
        sock.close() # ewentualnie to: sock.shutdown(socket.SHUT_RDWR)
        print('Stopped speaking', flush=True)

    def createWidgets(self):
        self.speakb = tkinter.Button(self)
        self.speakb["text"] = "Speak to server"
        self.speakb.pack({"side": "left"})
        # self.speakb["state"] = tkinter.DISABLED   # because speaking is not implemented yet
        self.speakb.bind("<ButtonPress-1>", self.OnMouseDown) # comment to prevent from speaking
        self.speakb.bind("<ButtonRelease-1>", self.muteSpeak) # comment to prevent from speaking

    def __init__(self, master=None):
        self.stream = pa.open(format=pyaudio.paInt16,
                              channels=1,
                              rate=48000, # alt. 44100
                              input=True,
                              frames_per_buffer=chunk_size)
        self.mute = True
        tkinter.Frame.__init__(self, master)
        self.mouse_pressed = False
        self.pack()
        self.createWidgets()
        self.receiver = threading.Thread(name=f'WiFi-Talkie audio receiver', target=listener_fun, daemon=True)
        self.receiver.start()

# Speaking not implemented yet
root = tkinter.Tk()
root.protocol("WM_DELETE_WINDOW", communication.exit)
root.title("Push to talk")
app = VOIP_FRAME(master=root)
app.mainloop()
try: root.destroy()
except: pass
app.stream.close()
pa.terminate()
print('End of the program. Receiver daemon will be terminated.')