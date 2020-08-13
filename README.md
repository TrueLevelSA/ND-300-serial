# About this repository

This repository contains a simple library written in pure python 3 aiming to
drive a ND-300CM/KM by [International Currency Technologies][ict] over a serial
interface. The current code was written by referring to
[this documentation][doc].

[ict]: http://www.ictgroup.com.tw/
[doc]: https://www.coinoperatorshop.com/media/products/ND-300CM.KM_Installation_Guide_gb.pdf

# Requirements

This should require python 3.6 or higher and work on any POSIX system but has
only been tested on python 3.8.5 on a Raspberry Pi.

The library requires [pyserial][pyserial].

[pyserial]: https://pythonhosted.org/pyserial/

# Installation

```shell
pip install -r requirements.txt
python setup.py install
```

# API

## Connection

The `Connection` class is the entry point to communicate with the machine.
It contains three high level methods to directly drive the machine and two
lower level ones to have finer control over the exchanges between the user
and the machine.

`__init__(self, serial_file_name='/dev/ttyUSB0', timeout=10)`
  * The constructor opens a serial connection respeting the protocol's
    baudrate and parity bit. By default, the connection is opened over
    `/dev/ttyUSB0` but this can be changed with the `serial_file_name`
    argument. Default timeout is 10 seconds but this can be changed with
    the `timeout` argument.

`close(self)`
  * Close the serial connection. Not needed if opening the connection with
    the `with` statement.

`payout(self, quantity) -> (Message, Message)`
  * Commands the machine to dispense `quantity` bills. Returns a tuple of
    [`message`](#Message)s. The first one is the payout message that was sent
    by the user.  The second one is the last message received from the machine.
    This method repeatedly calls a `REQUEST_MACHINE_STATUS` command until the
    machine has stopped responding with either `DISPENSING_BUSY` or
    `PAYOUT_SUCCESSFUL`.  This ensures the method will block until the whole
    payout is succesful or the machine returns an error.

`status(self) -> (Message, Message)`
  * Commands the machine to send its current status. Returns a tuple of
    [`message`](#Message)s. The first one is the command that was sent by the
    user. The second one is the machine's response.

`reset_dispenser(self) -> Message`
  * Commands the machine to reset itself. Returns the [`message`](#Message)
    that was sent by the user. The machine does not respond to this command.

`send_command(self, command, data=None) -> Message`
  * Sends a command to the machine over the serial connection. `command` is a
    value from the [`Command`](#Command) enumeration. The `data` argument must
    correspond to the command, i.e. if the command has associated data, it must
    be present and of the correct type. Returns the [`message`](#Message) that
    was sent to the machine.

`read_response(self) -> Message`
  * Reads the serial connection for a response from the machine. Returns a
    [`message`](#Message) containing the machine's status and associated data.

## Command

The `Command` enumeration represents the various commands that can be sent to
the machine. Its values are the values over the protocol.

Its values are:
- SINGLE_MACHINE_PAYOUT = 0x10
- REQUEST_MACHINE_STATUS = 0x11
- RESET_DISPENSER = 0x12
- MULTIPLE_MACHINES_PAYOUT = 0x13

## Status

The `Status` enumeration represents the various machine status that can be
received from the machine. Its values are the values over the protocol.

Its values are:
- PAYOUT_SUCCESSFUL = 0xAA
- PAYOUT_FAILS = 0xBB
- STATUS_FINE = 0x00
- EMPTY_NOTE = 0x01
- STOCK_LESS = 0x02
- NOTE_JAM = 0x03
- OVER_LENGTH = 0x04
- NOTE_NOT_EXIT = 0x05
- SENSOR_ERROR = 0x06
- DOUBLE_NOTE_ERROR = 0x07
- MOTOR_ERROR = 0x08
- DISPENSING_BUSY = 0x09
- SENSOR_ADJUSTING = 0x0A
- CHECKSUM_ERROR = 0x0B
- LOW_POWER_ERROR = 0x0C

## Message

The `Message` class represents exchanges over the serial connection. A
message contains the command or status of the message and its associated
data if any. This class will enforce data type correctness, compute and
enforce checksum correctness. `Message` overrides `__repr__` to be logged
with good readability.

`__init__(self, command_or_status, data=None)`
  * `command_or_status` can be a value from either the [`Command`](#Command) or
    [`Status`](#Status) enumerations. The `data` argument must correspond to
    the command or status, i.e. if the command has associated data, it must be
    present and of the correct type.

`to_bytes(self) -> bytes`
  * Returns the bytes string representing this message's command and data that
    can be sent over the serial connection.

`@staticmethod from_bytes(bytes_) -> Message`
  * Returns a message containing the command or status and the data contained
    in the `bytes_` argument.

# Example usage

This repository contains a file called `example_usage.py` showcasing how to
simply use this library.

# Unit tests

Unit tests can be ran by running the module, i.e. `python nd300.py`. They only
test the [`Message`](#Message) class so they can be ran without a machine.

# Known limitations

Multiple machine payout has been completetly ignored and nothing in this
implementation pays any attention to it so it might be broken.
