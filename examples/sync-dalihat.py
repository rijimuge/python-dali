#!/usr/bin/env python3

from dali.gear.general import DAPC, QueryControlGearPresent
from dali.driver.base import SyncDALIDriver
from dali.driver.atxled import SyncDaliHatDriver
from dali.address import GearShort

class DaliTest:
    def __init__(self, driver: SyncDALIDriver):
        self.driver = driver

    def scan_devices(self):
        # Assuming DALI addresses are from 0 to 63 for short addresses
        present_devices = []
        for address in range(0, 64):
            try:
                response = self.driver.send(QueryControlGearPresent(GearShort(address)))
                if response.value is True:
                    present_devices.append(address)
                    print(f"Device found at address: {address}")
            except Exception as e:
                print(f"Error while querying address {address}: {e}")
        
        return present_devices

    def set_device_level(self, address, level, fade_time=0):
        # Set device to a specific brightness level
        try:
            self.driver.send(DAPC(GearShort(address), level, fade_time))
            print(f"Set device at address {address} to level {level} with fade time {fade_time}")
        except Exception as e:
            print(f"Error while setting level for address {address}: {e}")

if __name__ == "__main__":
    serial_port = "/dev/ttyS0"  # Your specific serial port here

    # Initialize your DALI driver; make sure it is compatible with SyncDALIDriver interface
    dali_driver = SyncDaliHatDriver(port=serial_port)

    # Creating an instance of DaliTest with our driver
    dali_test = DaliTest(dali_driver)

    # Scanning for devices
    found_devices = dali_test.scan_devices()
    print(f"Scanned and found {len(found_devices)} devices.")

    # Example: Setting level of the first found device (if any) to 50% brightness for 0 fade time
    if found_devices:
        dali_test.set_device_level(found_devices[0], 128, 0)

    # Don't forget to close the driver connection
    dali_driver.close()