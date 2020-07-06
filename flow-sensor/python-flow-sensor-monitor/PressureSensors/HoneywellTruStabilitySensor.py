import qwiic_i2c
from smbus2 import SMBus, i2c_msg

import math

from PressureSensors.PressureUnits import PressureUnits

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
