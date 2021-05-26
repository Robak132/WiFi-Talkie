#!/usr/bin/env python
import pyaudio
import socket
import tkinter
import threading
import selectors
from types import SimpleNamespace

chunk_size = 1024
pa = pyaudio.PyAudio()
data = None  # byte stream to send to server while speaking
serv_IP = '192.168.1.14'
my_IP = '192.168.1.14'  # socket.gethostbyname(socket.gethostname())
serv_comm_port = 61237  # server port for communication
speaking_event = threading.Event()


class Communication:
    def __init__(self, serv_host=serv_IP, serv_port=serv_comm_port):
        self.serv_IP = serv_host
        self.serv_port = serv_port
        self.sel = selectors.DefaultSelector()
        self.sock = None  # socket for communication with server
        self.server_responded_for_speaking = threading.Event()
        self.speaker_port = None

    def connect(self, messages):
        print(f'attempting to start communication with server at {self.serv_IP}:{self.serv_port}', flush=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.connect_ex((self.serv_IP, self.serv_port))
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.pending_requests = len(messages)  # for counting messages that wasn't responded yet
        data = SimpleNamespace(messages=list(messages),
                               outb=b'')
        self.sel.register(self.sock, events, data=data)

    def service_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(chunk_size)  # Reading message received from server
            if recv_data:
                self.pending_requests -= 1  # received a response
                message = recv_data.decode('ascii')  # decode from bytes to actual characters
                print(f'received message: {message}\npending requests: {self.pending_requests}', flush=True)
                if message[:6] == 'active':  # response for '?active'
                    print('Communication with server is still working.', flush=True)
                elif message[:6] == 'accept':  # response for '?accept' (request for listening)
                    print("Server accepted listening request.", flush=True)
                elif message[:5] == 'speak':  # response for '?speak' (request for speaking)
                    if message[6:] == 'rejected':  # someone's already speaking
                        print("Server rejected speaking request.", flush=True)
                        self.speaker_port = False
                        self.server_responded_for_speaking.set()
                    elif message[6:].isdigit():  # received server's port for speaking to
                        print("Server accepted speaking request.", flush=True)
                        self.speaker_port = int(message[6:])
                        self.server_responded_for_speaking.set()
                    else:
                        print(f"Unknown port value: {message[6:]}", flush=True)
                else:
                    print('received unknown message', repr(recv_data), 'from server at', sock.getpeername(), flush=True)
            if not recv_data or self.pending_requests == 0:  # end of communication for now
                print('closing connection with server at ', sock.getpeername(), flush=True)
                self.sel.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            if not data.outb and data.messages:
                data.outb = data.messages.pop(0)  # sending message
            if data.outb:
                print('sending', repr(data.outb), 'to server at', sock.getpeername(), flush=True)
                sent = sock.send(data.outb)
                data.outb = data.outb[sent:]  # deleting sent message from message list

    def request_listening(self, listener_port):  # ask server to accept listening request
        if self.sock._closed is True:  # send message '?join' with listening port number to server
            communication_thread = threading.Thread(name=f'WiFi-Talkie communication handler', target=self.launch,
                                                    args=([f'?join {listener_port}'.encode('ascii')],), daemon=True)
            communication_thread.start()
            return True
        else:
            print('socket is busy at the moment, try again later', flush=True)
            return False

    def request_speaking(self):
        print('Asking server for permission to speak.', flush=True)
        if self.sock._closed is True:  # send message '?speak' to server
            communication_thread = threading.Thread(name=f'WiFi-Talkie communication handler', target=self.launch,
                                                    args=([b'?speak'],), daemon=True)
            communication_thread.start()
        else:
            print('socket is busy at the moment, try again later', flush=True)
            return False
        self.server_responded_for_speaking.clear()
        while not self.server_responded_for_speaking.wait(10):
            print('Connecting to server is taking longer than usual...', flush=True)
        self.server_responded_for_speaking.clear()
        return self.speaker_port

    def exit(self):  # telling server to stop sending audio
        if self.sock._closed is True:
            self.connect([b'quit'])
        else:
            self.sock.send(b'quit')
        self.sock.close()

    def launch(self, messages=[b'?active']):  # function for handling messages to and from server
        self.connect(messages)  # establish a connection with server
        while True:
            events = self.sel.select(timeout=None)
            if events:
                for key, mask in events:
                    self.service_connection(key, mask)
            if not self.sel.get_map():  # Check for a socket being monitored to continue.
                break
        print("Communication with Raspberry server has been ended.", flush=True)
        self.sock.close()


def listener_fun():  # thread function for listening for audio
    print('Listener thread initialized.', flush=True)
    stream = pa.open(format=pyaudio.paInt16,
                     channels=1,
                     rate=44100,  # alt. 48000
                     output=True,
                     frames_per_buffer=chunk_size)

    # Socket Initialization
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((my_IP, 0))
    while communication.request_listening(
            sock.getsockname()[1]) is False:  # wait for a possibility of request listening
        pass
    sock.listen(5)
    server, address = sock.accept()  # accept server willing to speak
    print('Ready for receiving datastream from server', flush=True)

    while True:
        data = server.recv(chunk_size)  # Receive one chunk of binary data
        if data:
            if not speaking_event.is_set():  # if not speaking
                stream.write(data)  # Play the received audio data
            print(data[:30], flush=True)  # Print the beginning of the batch
            server.send(b'ACK')  # Send back Acknowledgement, has to be in binary form


# GUI for convenient use on PCs
class VOIP_FRAME(tkinter.Frame):
    def OnMouseDown(self, arg=None):  # arg has to stay because of tkinter GUI specifics
        speaking_event.set()  # inform that speaking has started
        t = threading.Thread(name='Speaker to server', target=self.speak)
        t.start()

    def muteSpeak(self, arg=None):  # arg has to stay because of tkinter GUI specifics
        speaking_event.clear()  # inform that speaking has ended
        print("You are now muted", flush=True)

    def speak(self):  # try to speak to server
        global data  # global variable for passing chunks to sender threads
        serv_audio_port = communication.request_speaking()  # request server (returns port number or False if request denied)
        if serv_audio_port is False:
            print('Speaking unavailable.', flush=True)
            speaking_event.set()
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((serv_IP, serv_audio_port))  # connect to specific port sent by server
        print("You are now speaking", flush=True)
        self.stream.start_stream()

        while speaking_event.is_set():  # until the user decides to stop talking
            sock.send(self.stream.read(chunk_size))  # send data as bytes
            sock.recv(chunk_size)  # receive ACK
        self.stream.stop_stream()
        sock.close()
        print('Stopped speaking', flush=True)

    def createWidgets(self):  # used on __init__ of GUI window
        self.speakb = tkinter.Button(self)
        self.speakb["text"] = "Speak to server"
        self.speakb.pack({"side": "left"})
        self.speakb.bind("<ButtonPress-1>", self.OnMouseDown)  # bind buttons to corresponding methods
        self.speakb.bind("<ButtonRelease-1>", self.muteSpeak)

    def __init__(self, master=None):
        self.stream = pa.open(format=pyaudio.paInt16,
                              channels=1,
                              rate=44100,  # alt. 48000
                              input=True,
                              frames_per_buffer=chunk_size)
        tkinter.Frame.__init__(self, master)
        self.mouse_pressed = False
        self.pack()
        self.createWidgets()
        self.receiver = threading.Thread(name=f'WiFi-Talkie audio receiver', target=listener_fun, daemon=True)
        self.receiver.start()


if __name__ == '__main__':
    communication = Communication()  # first of all, create communicator object check if sesrver is responding
    communication_thread = threading.Thread(name=f'Communicator thread', target=communication.launch, daemon=True)
    communication_thread.start()

    root = tkinter.Tk()
    root.protocol("WM_DELETE_WINDOW", communication.exit)
    root.title("Push to talk")
    app = VOIP_FRAME(master=root)
    app.mainloop()
    try:
        root.destroy()
    except:  # depending on how the window is closed, sometimes root has to be manually destroyed
        pass  # (GUI caveats)
    app.stream.close()
    pa.terminate()
