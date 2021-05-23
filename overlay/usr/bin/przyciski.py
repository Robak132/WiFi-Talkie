#!/usr/bin/python
import gpiod
import time
chip = gpiod.Chip('gpiochip0')
buttons = []

def event_wait_bulk(buttons):
    ev_lines = []
    for button in buttons:
        ev_lines.append(button.event_wait())
    return ev_lines

def event_read_multiply(button):
    event = button.event_read()
    while(button.event_wait()):
        event = button.event_read()
    return event

buttons.append(chip.get_line(12))
buttons.append(chip.get_line(13))
buttons.append(chip.get_line(14))
buttons.append(chip.get_line(15))
buttons.append(chip.get_line(16))

for button in buttons:
    button.request(consumer="its_me", type=gpiod.LINE_REQ_EV_BOTH_EDGES)
while True:
   ev_lines = event_wait_bulk(buttons)
   time.sleep(1)
   for i in range(len(ev_lines)):
       if ev_lines[i]:
             event = event_read_multiply(buttons[i])
             print("Przycisk nr: %s" % (i))
       else:
             print(".")
     
