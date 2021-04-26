import sys
import time

import socket
import pyaudio
import wave
from tkinter import *
import threading

pyAudio = pyaudio.PyAudio()
chunk_size = 1024
def createStream():
    # Audio Stream (PyAudio) Initialization
    FORMAT = pyaudio.paInt16 # Change to 8 if doesn't work
    CHANNELS = 1
    RATE = 48000
    return pyAudio.open(format = FORMAT,
                        channels = CHANNELS,
                        rate = RATE,
                        input = True,
                        frames_per_buffer = chunk_size)   

def sendStream(event, hostname = socket.gethostname()):
    # Socket Initialization
    print(f'New thread created for {hostname}', flush=True)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname ,51237))

    print(f'Thread with hostname {hostname} configured', flush=True)
    while True:
        event.wait()
        print('Event activated', flush=True)
        if data is not None:
            s.send(data)
            s.recv(chunk_size)
        event.clear()
        print('Event cleared', flush=True)

print('this is the Raspberry main server')
stream = createStream()
data = None # chunk do przesłania

#                Mateusz         Paulina        Bartek  
hostnames = ['192.168.1.12', '192.168.1.23'] # [socket.gethostname()] # ('192.168.1.12', '192.168.1.23', '192.168.1.15')
event = threading.Event()
threads = []
for hostname in hostnames:
    threads.append(threading.Thread(name = f'Sender to {hostname}', target=sendStream, args=(event, hostname,)))
    threads[-1].start()

# GUI do symulacji
class VOIP_FRAME(Frame):    
    def OnMouseDown(self, event):
        self.mute = False
        self.speakStart()        
    def muteSpeak(self,event):
        self.mute = True
        print("You are now muted")
    def speakStart(self):
        t = threading.Thread(target=self.speak)
        t.start()                
    def speak(self):
        global data     # global variable for passing chunks to sender threads
        print("You are now speaking")
        while self.mute is False:
            data = stream.read(chunk_size)  # record voice (one batch)
            print(data[:30])    # Print the beginning of the batch data
            event.set()         # Signal all the sender threads to start sending data to hosts
    def createWidgets(self):
        self.speakb = Button(self)
        self.speakb["text"] = "Speak"
        self.speakb.pack({"side": "left"})
        self.speakb.bind("<ButtonPress-1>", self.OnMouseDown)
        self.speakb.bind("<ButtonRelease-1>", self.muteSpeak)
    def __init__(self, master=None):
        self.mute = True
        Frame.__init__(self, master)
        self.mouse_pressed = False
        self.pack()
        self.createWidgets()

root = Tk()
app = VOIP_FRAME(master=root)
app.mainloop()
root.destroy()
s.close()
stream.close()
p.terminate()






'''
# Audio Stream (PyAudio) Initialization
CHUNK = 1024
FORMAT = pyaudio.paInt16 # Change to 8 if doesn't work
CHANNELS = 1
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "output.wav"
RATE = 48000
p = pyaudio.PyAudio()
stream = p.open(format = FORMAT,
                channels = CHANNELS,
                rate = RATE,
                input = True,
                frames_per_buffer = CHUNK)

# Socket Initialization
size = 1024
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((socket.gethostname(),52137)) # socket.gethostname()

# GUI Specifics
class VOIP_FRAME(Frame):    
    def OnMouseDown(self, event):
        self.mute = False
        self.speakStart()        
    def muteSpeak(self,event):
        self.mute = True
        print("You are now muted")
    def speakStart(self):
        t = threading.Thread(target=self.speak)
        t.start()                
    def speak(self):
        print("You are now speaking")
        while self.mute is False:
            data = stream.read(CHUNK)
            print(data)
            s.send(data)
            s.recv(size)
    def createWidgets(self):
        self.speakb = Button(self)
        self.speakb["text"] = "Speak"
        self.speakb.pack({"side": "left"})
        self.speakb.bind("<ButtonPress-1>", self.OnMouseDown)
        self.speakb.bind("<ButtonRelease-1>", self.muteSpeak)
    def __init__(self, master=None):
        self.mute = True
        Frame.__init__(self, master)
        self.mouse_pressed = False
        self.pack()
        self.createWidgets()

root = Tk()
app = VOIP_FRAME(master=root)
app.mainloop()
root.destroy()
s.close()
stream.close()
p.terminate()
'''