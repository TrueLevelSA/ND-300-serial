'''This is an abstraction to easily communicate with a ND-300 CM/KM.
The multiple machine payout has been completetly ignored and is not
implemented.
'''

import serial
import io
import aenum
from collections import namedtuple


def _int_to_bytes(i):
    '''Returns a single byte representation of a integer.'''
    return int.to_bytes(i, 1, byteorder='big')


class Sender(aenum.Enum):
    '''Represents the two different parties that can communicate and
    their respective values on the protocol.
    '''
    user = 10
    machine = 1


class Command(aenum.Enum):
    '''Available commands for the NV 300CM/KM. These commands can
    either be sent by the user or the machine and can have associated
    data.
    '''
    SINGLE_MACHINE_PAYOUT = 0x10
    REQUEST_MACHINE_STATUS = 0x11
    RESET_DISPENSER = 0x12
    MULTIPLE_MACHINES_PAYOUT = 0x13
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


# _commands_metadata contains the valid sender and data type (if any)
# for each command of the protocol.
_CommandMetaData = namedtuple('_CommandMetaData', 'sender data_type')
_commands_metadata = {
    Command.SINGLE_MACHINE_PAYOUT: _CommandMetaData(Sender.user, int),
    Command.REQUEST_MACHINE_STATUS: _CommandMetaData(Sender.user, None),
    Command.RESET_DISPENSER: _CommandMetaData(Sender.user, None),
    Command.MULTIPLE_MACHINES_PAYOUT: _CommandMetaData(Sender.user, int),
    Command.PAYOUT_SUCCESSFUL: _CommandMetaData(Sender.machine, int),
    Command.PAYOUT_FAILS: _CommandMetaData(Sender.machine, int),
    Command.STATUS_FINE: _CommandMetaData(Sender.machine, int),
    Command.EMPTY_NOTE: _CommandMetaData(Sender.machine, int),
    Command.STOCK_LESS: _CommandMetaData(Sender.machine, int),
    Command.NOTE_JAM: _CommandMetaData(Sender.machine, int),
    Command.OVER_LENGTH: _CommandMetaData(Sender.machine, int),
    Command.NOTE_NOT_EXIT: _CommandMetaData(Sender.machine, int),
    Command.SENSOR_ERROR: _CommandMetaData(Sender.machine, int),
    Command.DOUBLE_NOTE_ERROR: _CommandMetaData(Sender.machine, int),
    Command.MOTOR_ERROR: _CommandMetaData(Sender.machine, int),
    Command.DISPENSING_BUSY: _CommandMetaData(Sender.machine, int),
    Command.SENSOR_ADJUSTING: _CommandMetaData(Sender.machine, int),
    Command.CHECKSUM_ERROR: _CommandMetaData(Sender.machine, int),
    Command.LOW_POWER_ERROR: _CommandMetaData(Sender.machine, int),
}


class Message:
    '''Represents exchanged commands with the associated data.
    Enforces the correct sender and checksum for its command.
    '''

    MESSAGE_LENGTH = 6

    def __init__(self, command, data=None):
        self.command = command
        self.data = data
        self._validate_and_fix_data()

    def __repr__(self):
        '''Pretty print for debug.'''
        meta = _commands_metadata[self.command]
        arrow = {Sender.user: '==>', Sender.machine: '<=='}[meta.sender]
        if meta.data_type is None:
            data = 'No data'
        else:
            data = self.data
        return f'{arrow} {self.command} {data}'

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

        hex_string = f'011000{self.command.value:02X}{data:02X}'
        bytes_ = bytes.fromhex(hex_string)
        return bytes_ + _int_to_bytes(Message._compute_checksum(bytes_))

    @staticmethod
    def from_bytes(bytes_):
        '''Returns a Message from a bytes string.'''
        if len(bytes_) != Message.MESSAGE_LENGTH:
            raise ValueError(f'Expected a length {Message.MESSAGE_LENGTH} byte string')
        if bytes_[0] != 1:
            raise ValueError(f'Bad starting byte: expected 0x01, got 0x{bytes_[0]}')
        sender = Sender(bytes_[1])
        command = Command(bytes_[3])
        meta = _commands_metadata[command]
        data = meta.data_type(bytes_[4])
        checksum = bytes_[5]
        computed_checksum = Message._compute_checksum(bytes_[:-1])
        if checksum != computed_checksum:
            raise ValueError(f'Bad checksum, received {checksum} but computed {computed_checksum}')
        if sender != meta.sender:
            raise ValueError(f'Bad message sender, received {sender} but expected {meta["sender"]}')
        return Message(command, data)

    def _validate_and_fix_data(self):
        meta = _commands_metadata[self.command]
        if not (self.data is None and meta.data_type is None
                or isinstance(self.data, meta.data_type)):
            raise TypeError(
                f'Command {self.command} expected data type {meta["data_type"]}, got {type(self.data)}',
            )


class Connection:
    '''Abstraction around a serial connection to easily send commands
    and get responses as messages. Can be used as a context manager.
    '''

    def __init__(self):
        self.serial = serial.Serial(
            '/dev/ttyUSB0',
            9600,
            timeout=2,
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
        if _commands_metadata[command].sender == Sender.machine:
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
