#!/usr/bin/env python3

"""
PyAudio example: Record a few seconds of audio and save to a WAVE
file.
"""

import pyaudio
import wave
import sys
import os.path
import gpiod
import time

from os import walk
from os import system

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "output.wav"

chip = gpiod.Chip('gpiochip0')

def event_read_multiply(button):
    event = button.event_read()
    while(button.event_wait(nsec=100000000)):
        event = button.event_read()
    return event

    

buttons = chip.get_lines([12,13,14,15,16])
recorddiod = chip.get_line(24)
recorddiod.request(consumer="its_me", type=gpiod.LINE_REQ_DIR_OUT)
playdiod = chip.get_line(25)
playdiod.request(consumer="its_me", type=gpiod.LINE_REQ_DIR_OUT)
recorddiod.set_value(0)
playdiod.set_value(0)

buttons.request(consumer='its_me', type=gpiod.LINE_REQ_EV_BOTH_EDGES)

run = True
files = []

def record(disactive_button):
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    recorddiod.set_value(1)
    print("* recording")

    frames = []

    run_record = True

    while run_record:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        ev_line = disactive_button.event_wait()
        if ev_line:
            run_record = False

    print("* done recording")
    recorddiod.set_value(0)
    stream.stop_stream()
    stream.close()
    p.terminate()

    filename = input("Enter your file name: ")
    filename += ".wav"

    wf = wave.open("/usr/bin/static/" + filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    time.sleep(0.5)
    event_read_multiply(disactive_button)

def play(file_name):
    wf = wave.open("/usr/bin/static/" + file_name, 'rb')

    # instantiate PyAudio (1)
    p = pyaudio.PyAudio()

    # open stream (2)
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)

    # read data
    data = wf.readframes(CHUNK)
    playdiod.set_value(1)
    # play stream (3)
    while len(data) > 0:
        stream.write(data)
        data = wf.readframes(CHUNK)
    playdiod.set_value(0)
    # stop stream (4)
    stream.stop_stream()
    stream.close()

    # close PyAudio (5)
    p.terminate()

    

def init_files():
    for f in os.listdir('/usr/bin/static/'):
            files.append(f)
    
def show_files(seleced_file):
    for i in range(len(files)):
        if i == seleced_file:
            print(files[i] + "<--")
        else:
            print(files[i])

def next_file(seleced_file):
    seleced_file = seleced_file + 1
    seleced_file = seleced_file % len(files) 
    return seleced_file

def prev_file(seleced_file):
    seleced_file = seleced_file - 1
    if(seleced_file < 0):
        seleced_file = len(files)-1
    return seleced_file

if sys.platform == 'darwin':
    CHANNELS = 1

init_files()

seleced_f = 0

while(run):
    system('clear')
    show_files(seleced_f)
    ev_lines = buttons.event_wait(sec=1)

    if ev_lines:
         i = 0
         time.sleep(0.5)
         for button in buttons:
             if button.event_wait():         
                    event_read_multiply(button)                                     
                    if(i == 0):
                        record(button)
                        files.clear()
                        init_files()
                    elif(i == 1):
                        play(files[seleced_f]) 
                    elif(i == 2):
                        seleced_f = prev_file(seleced_f)  
                    elif(i == 3):
                        seleced_f = next_file(seleced_f) 
                    else:
                        run = False
             i = i + 1 

            

    
    
    