#!/usr/bin/env python3

import time
import board
import adafruit_sht31d

# Create sensor object, communicating over the board's default I2C bus
i2c = board.I2C()  # uses board.SCL and board.SDA
sensor = adafruit_sht31d.SHT31D(i2c)

def c_to_f(c: float):
    return (c * 1.8) + 32

while True:
    tmp = c_to_f(sensor.temperature) 
    hmd = sensor.relative_humidity
    print(f"Temperature: {tmp:0.1f} F, Humidity: {hmd:0.1f} %")
    time.sleep(1)
