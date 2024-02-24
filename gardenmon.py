#!/usr/bin/python3 -u

import csv
import datetime
import glob
import os
import smbus
import time

from abc import ABC, abstractmethod

def c_to_f(c: float) -> float:
    """
    Celcius to Farenheit.
    """
    return (c * 1.8) + 32

class sensor(ABC):
    """
    Base class for all sensors.
    """

    @abstractmethod
    def read(self):
        pass

class cpu_temp(sensor):
    """
    Sensor class for the temperature sensor for the RPi CPU.
    """

    def __init__(self):
        self.cpu_temp_file = "/sys/class/thermal/thermal_zone0/temp"

    def read(self) -> dict:
        with open(self.cpu_temp_file) as cpu_temp_file:
            val = c_to_f(int(cpu_temp_file.read()) / 1000.0)
        return val

class aths(sensor):
    """
    Ambient Temperature/Humidity Sensor. Underlying sensor is the SHT30
    temperature and humidity sensor. Connected via I2C.
    """

    def __init__(self):
        self.i2cbus = smbus.SMBus(1)

        # addr bit is pulled to ground.
        self.i2caddr = 0x44

        # Set the sensor for high repeatability and 10 measurements per
        # second. Kinda overkill, but we aren't on battery power.
        self.i2cbus.write_byte_data(self.i2caddr, 0x27, 0x37)

        # What to add to Fahrenheit temperature to measure "true".
        self.temperature_trim = 0.0

        # What to add to relative humidity to measure "true".
        self.humidity_trim = 0.0

    def read(self) -> dict:
        # Sensor readings are 6 bytes:
        #   0 : MSB of temp reading
        #   1 : LSB of temp reading
        #   2 : CRC of temp reading (ignored)
        #   3 : MSB of humidity reading
        #   4 : LSB of humidity reading
        #   5 : CRC of humidity reading (ignored)
        data = self.i2cbus.read_i2c_block_data(self.i2caddr, 0x00, 6)
        temperature_raw = data[0] << 8 | data[1]
        humidity_raw    = data[3] << 8 | data[4]

        # Apply conversion formulas to raw values.
        temperature_f    = ((temperature_raw * 315.0) / 0xFFFF) - 49 + self.temperature_trim
        humidity_percent = ((humidity_raw    * 100.0) / 0xFFFF) + self.humidity_trim

        vals = dict();
        vals["temperature"] = temperature_f
        vals["humidity"] = humidity_percent
        return vals

class sts(sensor):
    """
    Soil Temperature Sensor. Underlying sensor is the DS18B20 temperature
    sensor. Connected via 1 wire.
    """

    def __init__(self):
        base_dir = '/sys/bus/w1/devices/'
        # Folder will appear as 28-xxxxxxxxxxxx.
        device_folder = glob.glob(base_dir + '28*')[0]
        self.device_file = device_folder + '/w1_slave'
        
        # What to add to Fahrenheit temperature to measure "true".
        self.trim = -2.2

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
            return temp_f + self.trim

    def read_temp_raw(self):
        f = open(self.device_file, 'r')
        lines = f.readlines()
        f.close()
        return lines

class sms(sensor):
    """
    Soil Moisture Sensor. Underlying sensor is a soil moisture probe with
    the output fed into an ADS1115 ADC. Connected via I2C.
    """

    def __init__(self):
        self.i2cbus = smbus.SMBus(1)

        # addr bit is pulled to ground.
        self.i2caddr = 0x48

        # Set the config register at 0x01. Set voltage range to +-4.096V and
        # enable continuous-conversion mode.
        self.i2cbus.write_i2c_block_data(self.i2caddr, 0x01, [0x82, 0x83])

        # What to add to decimal value to read ~0V as ~0. Found via
        # empirical testing.
        self.trim = 4800

    def read(self) -> int:
        # From register 0x00, sensor readings are 2 bytes:
        #   0 : MSB of ADC reading
        #   1 : LSB of ADC reading
        data = self.i2cbus.read_i2c_block_data(self.i2caddr, 0x00)
        val = data[0] << 8 | data[1]

        # Convert 16-bit two's complement to decimal.
        if (val & (1 << (16 - 1))) != 0:
            val = val - (1 << 16)

        # Add trim offset to value.
        val += self.trim

        return val

class als(sensor):
    """
    Ambient Light Sensor. Underlying sensor is probably a BH1750. Connected
    via I2C.
    """

    def __init__(self):
        self.i2cbus = smbus.SMBus(1)
        self.i2caddr = 0x23

        # What to add to lux value to measure "true".
        self.trim = 0.0

    def read(self) -> float:
        # From register 0x10, sensor readings are 2 bytes:
        #   0 : MSB of lux reading
        #   1 : LSB of lux reading
        data = self.i2cbus.read_i2c_block_data(self.i2caddr, 0x10, 2)
        val = data[0] << 8 | data[1]
        lux = float(val)/1.2 + self.trim
        return lux

def gardenmon_main():
    log_folder = '/var/log/gardenmon'
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)

    cpu_temp_sensor = cpu_temp()
    aths_sensor = aths()
    sts_sensor = sts()
    sms_sensor = sms()
    als_sensor = als()

    time.sleep(1)

    print("gardenmon starting...")

    while True:
        current_time = datetime.datetime.now()

        timestamp = current_time.strftime('%Y-%m-%d %H:%M:%S')
        row = [timestamp]

        cpu_temp_val = cpu_temp_sensor.read()
        row.extend(["CPU Temperature", f"{cpu_temp_val:0.1f}", "F"])

        aths_vals = aths_sensor.read()
        row.extend(["Ambient Temperature", f"{aths_vals['temperature']:0.1f}", "F"])
        row.extend(["Ambient Humidity",    f"{aths_vals['humidity']:0.1f}",    "%"])

        sts_temperature = sts_sensor.read()
        row.extend(["Soil Temperature", f"{sts_temperature:0.1f}", "F"])

        sms_val = sms_sensor.read()
        row.extend(["Soil Moisture Value", f"{sms_val}", "decimal_value"])

        als_val = als_sensor.read()
        row.extend(["Ambient Light", f"{als_val:0.1f}", "lx"])

        with open(f"{log_folder}/main.csv", "a") as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            csvwriter.writerow(row)

        with open(f"{log_folder}/{current_time.date()}.csv", "a") as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            csvwriter.writerow(row)

        time.sleep(1)

if __name__ == "__main__":
    gardenmon_main()
