'''This is an abstraction to easily communicate with a ND-300CM/KM.
The multiple machine payout has been completetly ignored and is not
implemented.
'''

__author__ = 'Quentin Jeanmonod <q@truelevel.ch>'
__version__ = '1.0.0'

import serial
from collections import namedtuple
from enum import Enum


def _int_to_bytes(i):
    '''Returns a single byte representation of a integer.'''
    return int.to_bytes(i, 1, byteorder='big')


class _Sender(Enum):
    '''Represents the two different parties that can communicate and
    their respective values on the protocol.
    '''
    user = 0x10
    machine = 0x01


class _CommandOrStatus(Enum):
    '''This class represents the byte occupying the cmd/status field
    over the protocol.
    '''

    @staticmethod
    def from_byte(value):
        try:
            return Command(value)
        except ValueError:
            return Status(value)

    def is_user_command(self):
        return self in Command


class Command(_CommandOrStatus):
    '''Available commands for the ND-300CM/KM. These commands can
    be sent by the user.
    '''
    SINGLE_MACHINE_PAYOUT = 0x10
    REQUEST_MACHINE_STATUS = 0x11
    RESET_DISPENSER = 0x12
    MULTIPLE_MACHINES_PAYOUT = 0x13

    def data_type(self):
        return _commands_data_types[self]

    @classmethod
    def sender(_cls):
        return _Sender.user

    @classmethod
    def pretty_arrow(_cls):
        return '==>'


class Status(_CommandOrStatus):
    '''Machine statuses the ND-300CM/KM can return after command calls.'''
    PAYOUT_SUCCESSFUL = 0xAA
    PAYOUT_FAILS = 0xBB
    STATUS_FINE = 0x00
    EMPTY_NOTE = 0x01
    STOCK_LESS = 0x02
    NOTE_JAM = 0x03
    OVER_LENGTH = 0x04
    NOTE_NOT_EXIT = 0x05
    SENSOR_ERROR = 0x06
    DOUBLE_NOTE_ERROR = 0x07
    MOTOR_ERROR = 0x08
    DISPENSING_BUSY = 0x09
    SENSOR_ADJUSTING = 0x0A
    CHECKSUM_ERROR = 0x0B
    LOW_POWER_ERROR = 0x0C

    def data_type(self):
        # All machine statuses have associated integer data.
        return int

    @classmethod
    def sender(_cls):
        return _Sender.machine

    @classmethod
    def pretty_arrow(_cls):
        return '<=='


_commands_data_types = {
    Command.SINGLE_MACHINE_PAYOUT: int,
    Command.REQUEST_MACHINE_STATUS: None,
    Command.RESET_DISPENSER: None,
    Command.MULTIPLE_MACHINES_PAYOUT: int,
}


class Message:
    '''Represents exchanged commands with the associated data.
    Enforces the correct sender and checksum for its command.
    '''

    MESSAGE_LENGTH = 6

    def __init__(self, command_or_status, data=None):
        '''command can represent a user command or a machine status.'''
        self.command = command_or_status
        self.data = data
        self._validate()

    def __eq__(self, other):
        return (
            self.command == other.command
            and self.data == other.data
        )

    def __repr__(self):
        '''Pretty print for debug.'''
        if self.command.data_type() is None:
            data = 'No data'
        else:
            data = self.data
        return f'{self.command.pretty_arrow()} {self.command} {data}'

    @staticmethod
    def _compute_checksum(bytes_):
        '''As the documentation does not specify how to handle any
        overflow, this function makes the assumption that it must be
        discarded.
        '''
        return sum(bytes_) % 256

    def to_bytes(self):
        '''Returns a bytes string that can be sent over the serial
        connection.
        '''
        data = self.data
        if data is None:
            # data is set to 0 since a data byte must still be
            # present on the protocol for commmands with no data.
            data = 0

        bytes_ = bytes.fromhex(
            f'01{self.command.sender().value:02X}00{self.command.value:02X}{data:02X}',
        )
        return bytes_ + _int_to_bytes(Message._compute_checksum(bytes_))

    @staticmethod
    def from_bytes(bytes_):
        '''Returns a Message from a bytes string.'''
        if len(bytes_) != Message.MESSAGE_LENGTH:
            raise ValueError(f'Expected a length {Message.MESSAGE_LENGTH} byte string')
        if bytes_[0] != 1:
            raise ValueError(f'Bad starting byte: expected 0x01, got {bytes_[0]}')
        sender = _Sender(bytes_[1])
        command = _CommandOrStatus.from_byte(bytes_[3])
        data = command.data_type()(bytes_[4])
        checksum = bytes_[5]
        computed_checksum = Message._compute_checksum(bytes_[:-1])
        if checksum != computed_checksum:
            raise ValueError(f'Bad checksum: received {checksum} but computed {computed_checksum}')
        if sender != command.sender():
            raise ValueError(f'Command {command} expected {command.sender()}, received {sender}')
        return Message(command, data)

    def _validate(self):
        expected_data_type =  self.command.data_type()
        if not (self.data is None and expected_data_type is None
                or isinstance(self.data, expected_data_type)):
            raise TypeError(
                f'Command {self.command} expected data type {expected_data_type}, got {type(self.data)}',
            )


class Connection:
    '''Abstraction around a serial connection to easily send commands
    and get responses as messages. Can be used as a context manager.
    '''

    def __init__(self, serial_file_name='/dev/ttyUSB0', timeout=10):
        self.serial = serial.Serial(
            serial_file_name,
            9600,
            timeout=timeout,
            parity=serial.PARITY_EVEN,
        )

    def close(self):
        self.serial.close()

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.serial.close()

    def send_command(self, command, data=None):
        '''Returns the message that was sent.'''
        if not command.is_user_command():
            raise ValueError(f'Expected an user command, got {command}')

        message = Message(command, data)
        bytes_to_send = message.to_bytes()
        self.serial.write(bytes_to_send)
        return message

    def read_response(self):
        '''Returns a message in the serial buffer.'''
        bytes_ = self.serial.read(Message.MESSAGE_LENGTH)
        if len(bytes_) == 0:
            raise ValueError('Empty buffer, no response at this time.')
        if len(bytes_) != Message.MESSAGE_LENGTH:
            raise ValueError(f'Bad response: {bytes_}')
        return Message.from_bytes(bytes_)

    def payout(self, quantity):
        command = self.send_command(Command.SINGLE_MACHINE_PAYOUT, quantity)
        response = self.read_response()
        while (response.command == Status.DISPENSING_BUSY
                or response.command == Status.PAYOUT_SUCCESSFUL):
            self.send_command(Command.REQUEST_MACHINE_STATUS)
            response = self.read_response()
        return command, response

    def status(self):
        command = self.send_command(Command.REQUEST_MACHINE_STATUS)
        response = self.read_response()
        return command, response

    def reset_dispenser(self):
        return self.send_command(Command.RESET_DISPENSER)


if __name__ == '__main__':
    import unittest

    class MessageTests(unittest.TestCase):
        def test_compute_checksum(self):
            def compare(bytes_, checksum):
                self.assertEqual(
                    _int_to_bytes(
                        Message._compute_checksum(bytes_),
                    ),
                    checksum,
                )
            compare(b'\x01\x01\x00\xBB\x0B', b'\xC8')
            compare(b'\xFF\xFF\xFF\xFF\xFF', b'\xFB')

        def test_to_bytes(self):
            def compare(message, bytes_):
                self.assertEqual(
                    message.to_bytes(),
                    bytes_,
                )
            compare(
                Message(Command.SINGLE_MACHINE_PAYOUT, 23),
                b'\x01\x10\x00\x10\x17\x38',
            )
            compare(
                Message(Command.RESET_DISPENSER),
                b'\x01\x10\x00\x12\x00\x23',
            )
            compare(
                Message(Status.PAYOUT_SUCCESSFUL, 3),
                b'\x01\x01\x00\xAA\x03\xAF',
            )

        def test_from_bytes(self):
            with self.assertRaises(ValueError):
                # Too short
                Message.from_bytes(b'\x01\x10\x00\x10\x17')
            with self.assertRaises(ValueError):
                # Too long
                Message.from_bytes(b'\x01\x10\x00\x10\x17\x38\x01')
            with self.assertRaises(ValueError):
                # Must start with 0x01
                Message.from_bytes(b'\x00\x10\x00\x10\x17\x38')
            with self.assertRaises(ValueError):
                # Bad checksum
                Message.from_bytes(b'\x01\x10\x00\x10\x17\x33')
            with self.assertRaises(ValueError):
                # Bad sender
                Message.from_bytes(b'\x01\x01\x00\x10\x17\x29')
            with self.assertRaises(ValueError):
                # Bad sender
                Message.from_bytes(b'\x01\x10\x00\xAA\x03\xBE')
            self.assertEqual(
                Message.from_bytes(b'\x01\x10\x00\x10\x17\x38'),
                Message(Command.SINGLE_MACHINE_PAYOUT, 23),
            )
            self.assertEqual(
                Message.from_bytes(b'\x01\x01\x00\xAA\x03\xAF'),
                Message(Status.PAYOUT_SUCCESSFUL, 3),
            )

        def test_validate(self):
            with self.assertRaises(TypeError):
                # Needs data
                _ = Message(Command.SINGLE_MACHINE_PAYOUT)
            with self.assertRaises(TypeError):
                # Needs no data
                _ = Message(Command.RESET_DISPENSER, 3)
            with self.assertRaises(TypeError):
                # Needs int data
                _ = Message(Command.SINGLE_MACHINE_PAYOUT, 'Hello, world')
            # This should not error out
            _ = Message(Command.SINGLE_MACHINE_PAYOUT, 231)

    unittest.main()
