from dali.command import Command
from dali.driver.base import SyncDALIDriver, DALIDriver
from dali.frame import ForwardFrame, BackwardFrame
import logging
import serial
import threading
import time


# The dictionary to define DALI packet sizes corresponds to command prefixes.
DALI_PACKET_SIZE = {"j": 8, "h": 16, "l": 24, "m": 25}
DALI_PACKET_PREFIX = {v: k for k, v in DALI_PACKET_SIZE.items()}


class DaliHatSerialDriver(DALIDriver):
    def __init__(self, port="/dev/ttyS0"):
        self.port = port
        self.lock = threading.RLock()
        self.buffer = []
        self.LOG = logging.getLogger('AtxLedDaliDriver')
        try:
            self.conn = serial.Serial(
                port=self.port,
                baudrate=19200,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=1,
            )
            print("Serial connection opened")
        except Exception as e:
            logging.exception("Could not open serial connection: %s", e)
            # Handle non-connectivity appropriately in your environment
            self.conn = None

    def reset_input_buffer(self):
        if self.conn:
            self.conn.reset_input_buffer()
            self.buffer = []

    def enqueue_buffer(self, line):
        with self.lock:
            self.buffer.append(line)

    def _read_line(self):
        with self.lock:
            line = ""
            byte = self.conn.read(1).decode("ascii")
            #if allow_blank and byte == "":
            #    return ""
            ct = 0
            while byte != "\n":
                # Sanity checks: make sure we're not getting a crazy long line,
                # or waiting forever for the end of a partial packet
                if byte:
                    self.LOG.info("read byte: %s", byte)
                    ct = 0
                    line += byte
                    if len(line) > 30:
                        raise RuntimeError("GOT CRAZY LINE: %s" % repr(line))
                else:
                    ct += 1
                    if ct > 10:
                        raise RuntimeError("GOT INCOMPLETE PACKET: %s" % repr(line))
                byte = self.conn.read(1).decode("ascii")
            return line

    def read_line(self):
        with self.lock:
            while not self.buffer:
                line = self._read_line()
                if not line:
                    return ""
                self.buffer.append(line)
            return self.buffer.pop(0)

    def construct(self, command):
        """Construct a DALI command."""
        assert isinstance(command, Command)
        f = command.frame
        packet_size = len(f)
        prefix = DALI_PACKET_PREFIX[packet_size]

        if command.sendtwice and packet_size == 16:
            prefix = "t"

        data = "".join(["{:02X}".format(byte) for byte in f.pack])
        command_str = (f"{prefix}{data}\n").encode("ascii")
        return command_str

    def extract(self, data):
        """Parse the response from the serial device and return."""
        if data.startswith("J"):
            try:
                data = int(data[1:], 16)
                return Command(BackwardFrame(data))
            except ValueError as e:
                self.LOG.error(f"Failed to parse response: {e}")
        return data

    def close(self):
        if self.conn:
            self.conn.close()


class SyncDaliHatDriver(DaliHatSerialDriver, SyncDALIDriver):
    def send(self, command):
        with self.lock:
            # Keep a buffer of unmatched input to queue up
            lines = []
            last_resp = None
            send_twice = command.sendtwice
            self.LOG.info("sending %r", command)
            print("sending %r", command)
            cmd = self.construct(command)
            self.LOG.info("sending %r", cmd)
            print("sending %r", cmd)
            self.conn.write((cmd))
            REPS = 5
            i = 0
            already_resent = False
            resent_times = 0
            while i < REPS:
                i += 1
                # Read a response line. We always allow blank lines here, because
                # otherwise we might deadlock if the hat is misbehaving. This hasn't
                # been seen to my knowledge, but defensive programming y'know.
                resp = self.read_line()
                self.LOG.info("got response: %r", resp)
                print("got response: %r", resp)
                resend = False
                # Got a normal response
                if cmd[:3] not in ["hB1", "hB3", "hB5"]:
                    if resp and resp[0] in {"N", "J"}:
                        # Check if we're sending twice, and check responses if so
                        if send_twice:
                            if last_resp:
                                if last_resp == resp:
                                    return self.extract(resp)
                                resend = True
                                last_resp = None
                            else:
                                last_resp = resp
                        else:
                            return self.extract(resp)
                    # Check for send/receive collision, and resend if so
                    elif resp and resp[0] in {"X", "Z", ""}:

                        # Some APIs want to see conflicts, so break in that case.
                        # We only return receive conflicts (as in, we got more than
                        # one response), but always retry on send conflicts (as in,
                        # somebody else was sending when we tried to)
                        time.sleep(0.1)
                        collision_bytes = None
                        while collision_bytes != "":
                            collision_bytes = self.read_line()
                        if resp[0] == "X":
                            break
                        self.LOG.info(
                            "got conflict (%s) sending %r, sending again", resp, cmd
                        )
                        last_resp = None
                        resend = True
                    elif resp:
                        lines.append(resp)

                    resp = None
                    if resend and not already_resent:
                        self.conn.write((cmd).encode("ascii"))
                        REPS += 1 + send_twice
                        already_resent = True
                else:
                    if resp and resp[0] == "N":
                        return self.extract(resp)
                        break
                    # For set compare: B1, B3, B5, only acceptable response is N, otherwise resend
                    elif resp and resp[0] in {"X", "Z", ""}:
                        # Some APIs want to see conflicts, so break in that case.
                        # We only return receive conflicts (as in, we got more than
                        # one response), but always retry on send conflicts (as in,
                        # somebody else was sending when we tried to)
                        time.sleep(0.1)
                        collision_bytes = None
                        while collision_bytes != "":
                            collision_bytes = self.read_line()
                    elif resp:
                        last_resp = None
                        resend = True

                    resp = None
                    if resend and resent_times < 5:
                        self.conn.write((cmd).encode("ascii"))
                        REPS += 1 + send_twice
                        resent_times += 1


# Usage example
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    serial_port = "/dev/ttyS0"  # Example serial port
    dali_driver = SyncDaliHatDriver(serial_port)

    # Example DALI command: address 0 (broadcast), turn off command
    command = Command(ForwardFrame(16, 0xFF00))  # Broadcast turn off
    response = dali_driver.send(command)

    print("DALI response:", response)
    dali_driver.close()
