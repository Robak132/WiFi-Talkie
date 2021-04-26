#!/usr/bin/env python
import pyaudio
import socket

print('this is receiver')

# Pyaudio Initialization
chunk_size = 1024
pa = pyaudio.PyAudio()

# Opening of the audio stream
stream = pa.open(format = 8,
                channels = 1,
                rate = 48000,
                output = True)

# Socket Initialization
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)     # For using same port again
s.bind((socket.gethostname(), 51237))
s.listen(5)
client, address = s.accept()

print('Host connected to Raspberry server...')
while True:
    data = client.recv(chunk_size)  # Receive one chunk of binary data
    if data:
        stream.write(data)  # Play the received audio data
        print(data[:30])    # Print the beginning of the batch
        client.send(b'ACK') # Send back Acknowledgement, has to be in binary form

client.close()
stream.close()
pa.terminate()
print("Connection with Raspberry server has been lost")