#!/usr/bin/env python3

from enum import Enum

import qwiic_i2c
from smbus2 import SMBus, i2c_msg
# _i2c_msg = i2c_msg

from struct import Struct
import json
import time
import math
import socket

class PressureUnits(Enum):
    PSI = 1
    CMH2O = 2
    INH20 = 3
    PA = 4
    KPA = 5


NS_TO_S = 0.000000001
NS_TO_MS = 0.000001


# // ABPDANT030PG0D3
# // Last 8 translation:
# // Source: https://sensing.honeywell.com/honeywell-sensing-basic-board-mount-pressure-abp-series-datasheet-32305128.pdf
# //   030PG -> 0-30 PSI Gauge
# //   0 -> I2C, Address 0x08
# //   D -> 10% to 90% of 2^14 counts (digital only) temperature output enabled, sleep mode enabled
# //   3 -> 3.3V version
PRESSURE_SENSOR_INFO = {
    "address": 0x08,
    "min_output":  1638,  # 10% of 2^14
    "max_output": 14745,  # 90% of 2^14
    "min_value": 0.0,     # 0psi
    "max_value": 30.0,    # 15psi
    "units": PressureUnits.PSI,
    "zero": -0.046849
}

# // HSCMRRV001PD2A3
# // Last 8 translation:
# // Source: https://sensing.honeywell.com/honeywell-sensing-trustability-hsc-series-high-accuracy-board-mount-pressure-sensors-50099148-a-en.pdf
# //   001PD -> ±1 PSI Differential
# //   2 -> I2C, Address 0x28
# //   A -> 10% to 90% of 2^14 counts (digital)
# //   3 -> 3.3V version
FLOW_PRESSURE_SENSOR_INFO = {
    "address": 0x28,
    "min_output":  1638,  # 10% of 2^14
    "max_output": 14745,  # 90% of 2^14
    "min_value": -1.0,    # -1psi
    "max_value": 1.0,     # 1psi
    "units": PressureUnits.PSI,
    # "k": 0.0516,   # K factor for flow
    "k": 0.05291351624874463,   # K factor for flow
    "zero": -0.000951
}


class HoneywellTruStabilitySensor(object):
    """HoneywellTruStabilitySensor

    :param address: The I2C address to use for the device. If not provided, the default address is used.
    :param i2c_driver: An existing i2c driver object. If not provided a driver object is created.

    :return: The HoneywellTruStabilitySensor device object.
    :rtype: Object
    """

    def __init__(self, min_value, max_value, i2c_driver=None, address=0x28, min_output=1638, max_output=14745, units=PressureUnits.PSI, k=None, zero=0):
        self.address = address
        self.min_output = min_output
        self.max_output = max_output
        self.min_value = min_value
        self.max_value = max_value
        self.units = units
        self.k = k

        self._data = []
        self._data_to_keep = 40
        self._data_insert_position = 0

        self._flow_data = []
        self._flow_data_to_keep = 40
        self._flow_data_insert_position = 0

        if self.units == PressureUnits.PSI:
            self.to_pascal = 6894.7572932
            self.to_cmh20 = 70.30696
        # TODO: Add more from and to conversions

        self._pressure = 0
        self._raw_pressure = 0
        self._raw_pressure_avg = 0

        self._temperature = 0

        self._flow = 0
        self._raw_flow_avg = 0

        self._noise_min = ((self.max_value - self.min_value) /
                           (self.max_output - self.min_output))
        self._zero_offset = zero
        self._zero_measurements_to_take = 300
        self._zero_offset_set_samples_left = self._zero_measurements_to_take
        self._zero_offset_rate = (2 / self._zero_measurements_to_take)
        self._zero_offset_slow_rate = self._zero_offset_rate / 20

        if i2c_driver is None:
            self._i2c = qwiic_i2c.getI2CDriver()
            if self._i2c is None:
                print("Unable to load I2C driver for this platform.")
                return
        else:
            self._i2c = i2c_driver

    @property
    def is_connected(self):
        """
            Determine if a device is conntected to the system..
            :return: True if the device is connected, otherwise False.
            :rtype: bool
        """
        return qwiic_i2c.isDeviceConnected(self.address)

    @property
    def pressure(self):
        return self._pressure

    @property
    def pressure_as_cmh2o(self):
        return self._pressure * self.to_cmh20

    @property
    def temperature(self):
        return self._temperature

    @property
    def flow(self):
        return self._flow

    def _read_value(self):
        with SMBus(1) as bus:
            msg = i2c_msg.read(self.address, 4)
            bus.i2c_rdwr(msg)

            val = [int.from_bytes(msg.buf[0:2], byteorder='big'), int.from_bytes(
                msg.buf[2:4], byteorder='big')]

            status = val[0] >> 14
            pressure_raw = val[0] & 0b0011111111111111
            temparature_raw = val[1] >> 5

            # read the raw pressure
            pressure = ((pressure_raw - self.min_output) * (self.max_value -
                                                            self.min_value)) / (self.max_output - self.min_output) + self.min_value
            self._raw_pressure = pressure

            # read the raw temperature temperature
            self._temperature = (temparature_raw / 2047) * 200 - 50

            # average pressure over the last self._data_to_keep samples
            if (len(self._data) < self._data_to_keep):
                self._data.append(pressure)
                self._raw_pressure_avg = self._raw_pressure_avg + pressure/self._data_to_keep
            else:
                old_pressure = self._data[self._data_insert_position]
                self._raw_pressure_avg = self._raw_pressure_avg + \
                    (pressure - old_pressure)/self._data_to_keep
                self._data[self._data_insert_position] = pressure
                self._data_insert_position = (
                    self._data_insert_position + 1) % self._data_to_keep

            # adjust the zero compensation
            if self._zero_offset_set_samples_left > 0:
                self._zero_offset = (self._zero_offset * (1 - self._zero_offset_rate)) + (
                    self._raw_pressure_avg * self._zero_offset_rate)
                self._zero_offset_set_samples_left -= 1
            elif abs(self._raw_pressure_avg - self._zero_offset) < self._noise_min:
                self._zero_offset = (self._zero_offset * (1 - self._zero_offset_slow_rate)) + (
                    self._raw_pressure_avg * self._zero_offset_slow_rate)

            # store the zero-compensate average pressure for external retrieval
            self._pressure = self._raw_pressure_avg - self._zero_offset

            # compute flow if we have a k value
            if self.k == None:
                return

            # note: flow is in sml, and pressure is in self.units implicitly per second
            flow = self.k * \
                math.copysign(
                    math.sqrt(math.fabs(self._pressure * self.to_pascal)), self._pressure) * 60.0

            if (len(self._flow_data) < self._flow_data_to_keep):
                self._flow_data.append(flow)
                self._raw_flow_avg = self._raw_flow_avg + flow/self._flow_data_to_keep
            else:
                old_flow = self._flow_data[self._flow_data_insert_position]
                self._raw_flow_avg = self._raw_flow_avg + \
                    (flow - old_flow)/self._flow_data_to_keep
                self._flow_data[self._flow_data_insert_position] = flow
                self._flow_data_insert_position = (
                    self._flow_data_insert_position + 1) % self._flow_data_to_keep

            self._flow = self._raw_flow_avg

    def read_value(self):
        """Reads the value from i2c"""
        try:
            return self._read_value()
        except:
            # should maybe log somethning here...
            pass


class CSVOutput(object):
    """CSVOutput

    Output csv data when output() is called.
    """

    def __init__(self, start_time, output_every):
        print(f"ms\tflow\tflow_pressure\ttemperature\tflow_zero\tflow_raw\tflow_raw_avg\tpressure\tpressure_zero\tpressure_raw\tpressure_cmh2o")
        self.start_time = start_time
        self.output_every = output_every
        self.output_count = 0

    def output(self, flow_sensor, pressure_sensor, read_time):
        self.output_count += 1
        if (self.output_count == self.output_every):
            print(
                  f"{(read_time-self.start_time)*0.000000001:.9f}\t"
                  f"{flow_sensor.flow: 3.6f}\t"
                  f"{flow_sensor.pressure: 3.9f}\t"
                  f"{flow_sensor.temperature: 3.6f}\t"
                  f"{flow_sensor._zero_offset: 3.6f}\t"
                  f"{flow_sensor._raw_pressure: 3.6f}\t"
                  f"{flow_sensor._raw_pressure_avg: 3.6f}\t"
                  f"{pressure_sensor.pressure: 3.9f}\t"
                  f"{pressure_sensor._zero_offset: 3.6f}\t"
                  f"{pressure_sensor._raw_pressure: 3.6f}\t"
                  f"{pressure_sensor.pressure_as_cmh2o: 3.9f}"
                )
            self.output_count = 0


class PIRDSOutput(object):
    """PIRDSOutput

    Output PIRDS data when output() is called.
    """

    def __init__(self, start_time, output_every, sock, sock_address, sock_port, full_report_every=200):
        self.start_time = start_time
        self.output_every = output_every
        self.output_countdown = output_every
        self.full_report_every = full_report_every
        self.full_report_countdown = full_report_every

        self.sock = sock
        self.sock_address = sock_address
        self.sock_port = sock_port

        # Measurement structure, based on
        # https://github.com/PubInv/PIRDS-respiration-data-standard/blob/master/pirds_library/PIRDS.h#L63-L71
        self.pirds_event_struct = Struct(">cccbLl")

        # Message structure, based on
        # https://github.com/PubInv/PIRDS-respiration-data-standard/blob/master/pirds_library/PIRDS.h#L75-L82
        self.pirds_message_struct = Struct(">ccL64p")

    def outputMeasurement(self, event, event_type, loc, num, ms, value):
        # See https://github.com/PubInv/PIRDS-respiration-data-standard/blob/master/pirds_library/PIRDS.cpp#L78-L87
        json_event = json.dumps(
            {"event": event, "type": event_type, "ms": ms, "loc": loc, "num": num, "val": value})

        # See https://github.com/PubInv/PIRDS-respiration-data-standard/blob/master/pirds_library/PIRDS.cpp#L57-L65
        binary_event = self.pirds_event_struct.pack(event.encode(
            'utf-8'), event_type.encode('utf-8'), loc.encode('utf-8'), num, ms, value)

        if sock is not None:
            sock.sendto(binary_event, (self.sock_address, self.sock_port))

        return {'json': json_event, 'binary': binary_event}

    def outputMesssage(self, event, event_type, ms, message):
        # See https://github.com/PubInv/PIRDS-respiration-data-standard/blob/master/pirds_library/PIRDS.cpp#L205-L222
        json_event = json.dumps(
            {"event": event, "type": event_type, "ms": ms, "b_size": len(message), "buff": message})

        # See https://github.com/PubInv/PIRDS-respiration-data-standard/blob/master/pirds_library/PIRDS.cpp#L191-L202
        binary_event = self.pirds_message_struct.pack(event.encode(
            'utf-8'), event_type.encode('utf-8'), ms, len(message), message)

        return {'json': json_event, 'binary': binary_event}

    def output(self, flow_sensor, pressure_sensor, read_time):
        self.output_countdown -= 1

        if (self.output_countdown == 0):
            ret = []
            ms = round((read_time - self.start_time)*NS_TO_MS)  # ns to ms
            self.output_countdown = self.output_every

            self.full_report_countdown -= 1
            if (self.full_report_countdown == 0):
                self.full_report_countdown = self.full_report_every
                ret.append(self.outputMeasurement('M', 'T', 'A', 0,
                                                  ms, round(flow_sensor.temperature * 100)))
                # self.outputMeasurement('M', 'T', 'A', 0, ms, round(pressure_sensor.temperature * 100))

            ret.append(self.outputMeasurement('M', 'D', 'A', 0, ms,
                                              round(pressure_sensor.pressure_as_cmh2o * 10)))
            ret.append(self.outputMeasurement('M', 'F', 'A',
                                              0, ms, round(flow_sensor.flow * 1000)))

            # Available to send:
            #   flow_sensor.pressure
            #   flow_sensor.temperature
            #   flow_sensor.flow
            #   pressure_sensor.pressure_as_cmh2o

            return ret
        else:
            return None


class NeopixelOutput(object):
    """NeopixelOutput

    Output to update a neopixel display when output() is called.
    """

    def __init__(self, pixels, min_flow=-80, max_flow=80, min_pressure=-5, max_pressure=20, output_every=20, max_brightness=20):
        self.pixels = pixels
        self.output_every = output_every
        self.output_count = 0

        self.min_flow = min_flow
        self.max_flow = max_flow

        self.min_pressure = min_pressure
        self.max_pressure = max_pressure

        self.pixel_count = len(pixels)
        self.pixel_zero_offset = (self.pixel_count - 1) / ((max_flow - min_flow) / max_flow)

        self.max_brightness = max_brightness


    def output(self, flow_sensor, pressure_sensor, read_time):
        self.output_count += 1
        if (self.output_count == self.output_every):
            flow_value = (flow_sensor.flow / (self.max_flow - self.min_flow)) * self.pixel_count
            pressure_value = (pressure_sensor.pressure_as_cmh2o / (self.max_pressure - self.min_pressure)) * self.pixel_count

            for n in range(self.pixel_count):
                offset_pixel = n-self.pixel_zero_offset
                value = [0,0,0]
                if flow_value != 0 and (offset_pixel / flow_value) > 0:
                    value[0] = min(1.0, max(0.0, 0.5 + abs(flow_value) - abs(offset_pixel)))
                if pressure_value != 0 and (offset_pixel / pressure_value) > 0:
                    value[1] = min(1.0, max(0.0, 0.5 + abs(pressure_value) - abs(offset_pixel)))
                # if flow_value != 0 and (offset_pixel / flow_value) > 0:
                #     value[0] = min(1.0, max(0.0, 0.5 + abs(flow_value) - abs(offset_pixel)))
                self.pixels[n] = [value[0]*self.max_brightness, value[1]*self.max_brightness, value[2]*self.max_brightness]
                # print(f"N: {n} -> Flow value: {flow_value:1.4f} -> Offset: {offset_pixel} -> Pixel value: {value*self.max_brightness:3.0f}")
            self.pixels.show()

            self.output_count = 0

# class RollingStatistic(object):

#     def __init__(self, window_size, average, variance):
#         self.N = window_size
#         self.average = average
#         self.variance = variance
#         self.stddev = sqrt(variance)

#     def update(new, old):
#         oldavg = self.average
#         newavg = oldavg + (new - old)/self.N
#         self.average = newavg
#         self.variance += (new-old)*(new-newavg+old-oldavg)/(self.N-1)
#         self.stddev = sqrt(variance)

pressure_sensor = HoneywellTruStabilitySensor(**PRESSURE_SENSOR_INFO)
if not pressure_sensor.is_connected:
    print("missing the pressure sensor\n")
    exit()

flow_sensor = HoneywellTruStabilitySensor(**FLOW_PRESSURE_SENSOR_INFO)
if not flow_sensor.is_connected:
    print("missing the flow pressure sensor\n")
    exit()

start_time = time.clock_gettime_ns(time.CLOCK_REALTIME)

### THREE OUTPUT OPTIONS - uncomment ONE and comment the other two!!

## OPTION 1 - plain CSV output, suitable for sending to a file and analyzing

output_sinks = [CSVOutput(start_time, output_every=20)]


## OPTION 2 - CSV + NeoPixels (requires the script to be run with `sudo`)

# import board
# import neopixel
# pixels = neopixel.NeoPixel(board.D12, 6, auto_write=False)
# output_sinks = [CSVOutput(start_time, output_every=20), NeopixelOutput(pixels)]


## OPTION 3 - VentMon-compatible output to the Public Invention data lake

# PARAMHOST="ventmon.coslabs.com"
# PARAMPORT=6111
# sock = socket.socket(socket.AF_INET,  # Internet
#                      socket.SOCK_DGRAM)  # UDP
# sock_address = socket.gethostbyname(PARAMHOST)
# output_sinks = [CSVOutput(start_time, output_every=20), PIRDSOutput(start_time, output_every=20, sock=sock, sock_address=sock_address, sock_port=PARAMPORT)]



pre_read_time = time.clock_gettime_ns(time.CLOCK_REALTIME)
seconds_per_read = 0.002

# for x in range(10000):
while (1):
    last_read_time = pre_read_time
    pre_read_time = time.clock_gettime_ns(time.CLOCK_REALTIME)
    slippage = max(0, (pre_read_time - last_read_time) - seconds_per_read)
    pressure_sensor.read_value()
    flow_sensor.read_value()
    for sink in output_sinks:
        ret = sink.output(flow_sensor, pressure_sensor,
                          read_time=pre_read_time)
        # if ret is not None:
        #     for r in ret:
        #         print(r['json'])

    post_read_time = time.clock_gettime_ns(time.CLOCK_REALTIME)
    time_to_sleep = max(0.0001, min(seconds_per_read, seconds_per_read -
                                    ((post_read_time - pre_read_time - slippage) * NS_TO_S)))
    last_read_time = pre_read_time
    time.sleep(time_to_sleep)
