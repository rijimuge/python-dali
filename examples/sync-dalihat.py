#!/usr/bin/env python3

from dali.gear.general import (
    DAPC, QueryControlGearPresent, QueryGroupsZeroToSeven, 
    QueryGroupsEightToFifteen, QueryActualLevel, Off, QueryMinLevel, QueryMaxLevel, QueryPhysicalMinimum
)
from dali.driver.base import SyncDALIDriver
from dali.driver.atxled import SyncDaliHatDriver
from dali.address import GearShort
from dali.frame import BackwardFrame
from dali.command import YesNoResponse

class DaliHatTest:
    def __init__(self, driver: SyncDALIDriver):
        self.driver = driver

    def scan_devices(self):
        present_devices = []
        for address in range(0, 64):
            try:
                response = YesNoResponse(self.driver.send(QueryControlGearPresent(GearShort(address))))
                if response.value is True:
                    present_devices.append(address)
                    print(f"Device found at address: {address}")
                else:
                    print(f"Response from address {address}: {response.value}")

            except Exception as e:
                print(f"Error while querying address {address}: {e}")

        return present_devices

    def set_device_level(self, address, level, fade_time=0):
        # Set device to a specific brightness level
        try:
            self.driver.send(DAPC(GearShort(address), level))
            print(f"Set device at address {address} to level {level} with fade time {fade_time}")
        except Exception as e:
            print(f"Error while setting level for address {address}: {e}")

    def query_device_info(self, address):
        # Query additional device information
        try:
            # Query group memberships
            groups_0_7 = self.driver.send(QueryGroupsZeroToSeven(GearShort(address)))
            print(f"Device {address} groups 0-7: {groups_0_7}")

            groups_8_15 = self.driver.send(QueryGroupsEightToFifteen(GearShort(address)))
            print(f"Device {address} groups 8-15: {groups_8_15}")

            # Query brightness levels
            min_level = self.driver.send(QueryMinLevel(GearShort(address)))
            print(f"Device {address} minimum level: {min_level}")

            max_level = self.driver.send(QueryMaxLevel(GearShort(address)))
            print(f"Device {address} maximum level: {max_level}")

            physical_minimum = self.driver.send(QueryPhysicalMinimum(GearShort(address)))
            print(f"Device {address} physical minimum: {physical_minimum}")

            actual_level = self.driver.send(QueryActualLevel(GearShort(address)))
            print(f"Device {address} actual level: {actual_level}")

        except Exception as e:
            print(f"Error while querying device {address}: {e}")

    def turn_off_device(self, address):
        # Turn off a specific device
        try:
            self.driver.send(Off(GearShort(address)))
            print(f"Turned off device at address {address}")
        except Exception as e:
            print(f"Error while turning off device {address}: {e}")

if __name__ == "__main__":
    serial_port = "/dev/ttyS0"  # Your specific serial port here

    # Initialize your DALI driver; make sure it is compatible with SyncDALIDriver interface
    dali_driver = SyncDaliHatDriver(port=serial_port)

    # Creating an instance of DaliTest with our driver
    dali_test = DaliHatTest(dali_driver)
    found_devices = []

    # Scanning for devices
    found_devices = dali_test.scan_devices()
    print(f"Scanned and found {len(found_devices)} devices.")

    # Query and display additional device information
    for device in found_devices:
        dali_test.query_device_info(device)
        dali_test.set_device_level(device, 128)  # Example: Set level to 50% brightness
        dali_test.turn_off_device(device)  # Turn off the device

    # Don't forget to close the driver connection
    dali_driver.close()
