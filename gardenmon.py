#!/usr/bin/python3 -u

import adafruit_sht31d
import board
import csv
import datetime
import glob
import shutil
import smbus
import time
import os

from abc import ABC, abstractmethod

def c_to_f(c: float) -> float:
    """
    Celcius to Farenheit.
    """
    return (c * 1.8) + 32

def swap16(x: int) -> int:
    """
    Swap bytes in 16 bit integer.
    """
    return ((x & 0x00ff) << 8) | ((x & 0xff00) >> 8)

class sensor(ABC):
    """
    Base class for all sensors.
    """

    @abstractmethod
    def read(self):
        pass

class sht30(sensor):
    """
    Sensor class for the SHT30 temperature and humidity sensor. This sensor
    is connected via I2C.
    """

    def __init__(self):
        # Create sensor object, communicating over the board's default I2C bus.
        i2c = board.I2C()
        self.sensor = adafruit_sht31d.SHT31D(i2c)

    def read(self) -> dict:
        vals = dict();
        vals["temperature"] = c_to_f(self.sensor.temperature)
        vals["humidity"] = self.sensor.relative_humidity
        return vals

class ds18b20(sensor):
    """
    Sensor class for the DS18B20 temperature sensor. This sensor is connected
    via 1 wire.
    """

    def __init__(self):
        base_dir = '/sys/bus/w1/devices/'
        # Folder will appear as 28-xxxxxxxxxxxx.
        device_folder = glob.glob(base_dir + '28*')[0]
        self.device_file = device_folder + '/w1_slave'

    def read(self) -> float:
        lines = self.read_temp_raw()
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = self.read_temp_raw()
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            temp_f = c_to_f(temp_c)
            return temp_f

    def read_temp_raw(self):
        f = open(self.device_file, 'r')
        lines = f.readlines()
        f.close()
        return lines

class ads1115(sensor):
    """
    Sensor class for the ads1115 ADC, with soil moisture sensor analog input,
    connected via I2C.
    """

    def __init__(self):
        self.i2cbus = smbus.SMBus(1)
        # addr bit is pulled to ground.
        self.i2caddr = 0x48
        # Set the config register at 0x01. Set voltage range to +-4.096V and
        # enable continuous-conversion mode.
        self.i2cbus.write_word_data(self.i2caddr, 0x01, swap16(0x8283))
        # What to add to decimal value to read ~0V as ~0. Found via
        # empirical testing.
        self.trim = 4800

    def read(self) -> int:
        # Read 16-bit value from ADC.
        data = self.i2cbus.read_word_data(self.i2caddr, 0x00)

        # Data endianess needs to be swapped.
        data = swap16(data)

        # Convert 16-bit two's complement to decimal.
        if (data & (1 << (16 - 1))) != 0:
            data = data - (1 << 16)

        # Add trim offset to value.
        data += self.trim

        return data

def gardenmon_main():
    log_folder = '/var/log/gardenmon'
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    sht30_sensor = sht30()
    ds18b20_sensor = ds18b20()
    ads1115_sensor = ads1115()

    print("gardenmon starting...")

    while True:
        current_time = datetime.datetime.now()

        timestamp = current_time.strftime('%Y-%m-%d %H:%M:%S')
        row = [timestamp]

        sht30_vals = sht30_sensor.read()
        row.extend(["sht30_temperature", f"{sht30_vals['temperature']:0.1f}", "F"])
        row.extend(["sht30_humidity",    f"{sht30_vals['humidity']:0.1f}",    "%"])

        ds18b20_temperature = ds18b20_sensor.read()
        row.extend(["ds18b20_temperature", f"{ds18b20_temperature:0.1f}", "F"])

        ads1115_val = ads1115_sensor.read()
        row.extend(["ads1115_val", f"{ads1115_val}", "decimal_value"])

        with open(f"{log_folder}/main.csv", "a") as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            csvwriter.writerow(row)

        with open(f"{log_folder}/{current_time.date()}.csv", "a") as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            csvwriter.writerow(row)

        time.sleep(1)

if __name__ == "__main__":
    gardenmon_main()
