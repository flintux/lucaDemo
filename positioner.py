#!/usr/bin/env python
# coding: utf-8

import serial
import can
from commands import COMMANDS, RESPONSE_CODE_NUMBER
from status import *
import struct
import zlib
import os
import logging
import time

log_positioner = logging.getLogger(__name__)
log_positioner.setLevel(logging.INFO)

# create console handler and set level to debug
log_handler = logging.StreamHandler()
log_handler.setLevel(logging.INFO)

# create formatter
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')

# add formatter to ch
log_handler.setFormatter(log_formatter)

# add ch to logger
log_positioner.addHandler(log_handler)


class Positioner(object):
    """Positioner main object

    Provides status about positioner and communication interface to it

    :param bus: bus on which packet should be sent (bus should already be open)
    :param canid: identifier for the positioner

    """

    _CAN_ID_BIT_SHIFT = 18          # bits to shift for the ID on the can protocol
    _COMMAND_BIT_SHIFT = 10          # bits to shift for the command on the can protocol
    _POSITION_RESOLUTION = 2**30    # resolution for a position for a complete rotation
    _TIME_RESOLUTION = 2000         # steps of time per second for timestamps

    def __init__(self, bus, canid):
        self._bus = bus
        self._canid = canid
        self.alpha_position = 0
        self.beta_position = 0
        self.bootloader_status = BootloaderStatus()
        self.status = PositionerStatus()

    def _build_frame_id(self, command):
        """Builds ID for CAN frame by merging ID and command.

        :param command: command to be sent, based on list of commands
        :return: return the merged id with command inside
        """
        return (self._canid << self._CAN_ID_BIT_SHIFT) + (COMMANDS[command] << self._COMMAND_BIT_SHIFT)

    @classmethod
    def _get_response_code(cls, busid):
        """returns the response code from an id received from the communication bus

        :param busid: the id received from the can bus containing all information
        :return: the string corresponding to the response code
        """
        return RESPONSE_CODE_NUMBER[busid & (2**cls._COMMAND_BIT_SHIFT-1)]

    @classmethod
    def _angle_to_position(cls, angle: float):
        """converts angle in degrees to position encoding format

        :param angle: angle in degrees to convert
        :return: angle converted into counts
        """
        return round(angle / 360 * cls._POSITION_RESOLUTION)

    @classmethod
    def _position_to_angle(cls, position: int):
        """converts a position to an angle

        :param position in integer encoding
        :return: angle in degrees
        """
        return position / cls._POSITION_RESOLUTION * 360

    @classmethod
    def _seconds_to_timestamp(cls, seconds: float):
        """converts a time in seconds to timestamp for positioner

        :param seconds: as a float
        :return: timestamp as int
        """
        return round(seconds * cls._TIME_RESOLUTION)

    @classmethod
    def _timestamp_to_seconds(cls, timestamp: int):
        """converts a timestamp to seconds

        :param timestamp: timestamp given by positioner
        :return: time in seconds as float
        """
        return timestamp / cls._TIME_RESOLUTION

    @staticmethod
    def _crc(filename):
        """calculates the CRC32 checksum of a file

        :param filename: path to the filename to be used
        :return: CRC32 checksum as integer
        """
        result = 0
        for eachLine in open(filename, 'rb'):
            result = zlib.crc32(eachLine, result)
        return result

    def _send_command(self, command, extra_data=None):
        """sends a command to the positioner

        :param command: command to be send
        :param extra_data: data if any to be sent
        """

        if extra_data is None:
            extra_data = []
        canid = self._build_frame_id(command)
        msg = can.Message(arbitration_id=canid,
                          data=extra_data,
                          timestamp=time.time(),
                          is_extended_id=True)
        try:
            self._bus.send(msg)
            log_positioner.debug(msg)
        except Exception as e:
            log_positioner.error('Error sending message')
            log_positioner.error(e)

    def _get_answer(self):
        """gets a reply on the communication bus"""
        try:
            for i in range(5):
                answer = self._bus.recv(1)
                if answer is not None:
                    # log_positioner.debug(answer)
                    return answer
            return None
        except Exception as e:
            log_positioner.error('Error getting message')
            log_positioner.error(e)
            return None

    def get_status(self):
        """requests positioner status flags"""
        self._send_command('GET_STATUS')

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
            self.status.asInt = struct.unpack('<Q', answer.data)[0]
        else:
            log_positioner.error('Error with command get_status')

    def get_id(self):
        """requests id from positioner

        return: positioner id
        """
        self._send_command('GET_ID')

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)

            positioner_id = struct.unpack('<I', answer.data)[0]
            log_positioner.debug('positioner ID : {0}'.format(positioner_id))
            return positioner_id
        else:
            log_positioner.error('Error with command get_id')
            return None

    def get_fw_version(self):
        """request firmware version from positioner"""
        self._send_command('GET_FIRMWARE_VERSION')

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
            version = struct.unpack('BBBB', answer.data)
            log_positioner.debug('running firmware: V{:02}.{:02}.{:02}'.format(version[2], version[1], version[0]))
            return version
        else:
            log_positioner.error('Error with command get_fw_version')
            return None

    def get_position(self):
        """requests actual position of actuators

        :return alpha_angle, beta_angle: position in degrees
        """
        self._send_command('GET_ACTUAL_POSITION')

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
            alpha_position, beta_position = struct.unpack('<ii', answer.data)
            alpha_angle = self._position_to_angle(alpha_position)
            beta_angle = self._position_to_angle(beta_position)
            log_positioner.debug(f'alpha position: {alpha_angle:.3f} [°]')
            log_positioner.debug(f'beta position: {beta_angle:.3f} [°]')
            return alpha_angle, beta_angle
        else:
            log_positioner.error('Error with command get_position')
            return None

    def set_position(self, alpha, beta):
        """sets the actual position of the actuactors

        :param alpha: alpha angle in degrees
        :param beta: beta angle in degrees
        """
        alpha_position = self._angle_to_position(alpha)
        beta_position = self._angle_to_position(beta)
        packetdata = bytes(struct.pack('<ii', alpha_position, beta_position))

        self._send_command('SET_ACTUAL_POSITION', packetdata)
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command set_position')

    def firmware_upgrade(self, filename):
        """sends a new firmware to the positioner

        :param filename: location of the binary file to be uploaded
        """
        filesize = os.path.getsize(filename)
        checksum = self._crc(filename)
        packetdata = bytes(struct.pack('<II', filesize, checksum))
        self._send_command('SEND_NEW_FIRMWARE', packetdata)

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)

            with open(filename, 'rb') as f:
                transfered_data = 0
                while True:
                    data = f.read(8)
                    packetdata = bytearray(data)
                    # packetdata.reverse()
                    self._send_command('FIRMWARE_DATA', packetdata)
                    transfered_data += len(data)
                    answer = self._get_answer()
                    log_positioner.debug(answer)
                    if transfered_data == filesize:
                        log_positioner.debug('EOF found')
                        break
            log_positioner.info('firmware upgrade done')
        else:
            log_positioner.error('Error with firmware upgrade command')

    def goto_absolute(self, alpha, beta):
        """moves the positioner to an absolute position

        care must be taken to set speed before using this command

        :param alpha: alpha angle in degrees
        :param beta: beta angle in degrees
        :return alpha_time, beta_time: time in seconds for completion of motion
        """
        alpha_angle = self._angle_to_position(alpha)
        beta_angle = self._angle_to_position(beta)
        packetdata = bytes(struct.pack("<ii", alpha_angle, beta_angle))

        self._send_command('GOTO_POSITION_ABSOLUTE', packetdata)

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)

            alpha_timestamp, beta_timestamp = struct.unpack('<II', answer.data)
            alpha_time = self._timestamp_to_seconds(alpha_timestamp)
            beta_time = self._timestamp_to_seconds(beta_timestamp)
            log_positioner.debug(f'alpha ETA: {alpha_time} [s]')
            log_positioner.debug(f'beta ETA: {beta_time} [s]')
            return alpha_time, beta_time
        else:
            log_positioner.error('Error with command goto absolute')

    def goto_relative(self, delta_alpha, delta_beta):
        """moves the positioner to an relative position

        care must be taken to set speed before using this command

        :param delta_alpha: alpha angle in degrees
        :param delta_beta: beta angle in degrees
        :return alpha_time, beta_time: time in seconds for completion of motion
        """
        alpha_angle = self._angle_to_position(delta_alpha)
        beta_angle = self._angle_to_position(delta_beta)
        packetdata = bytes(struct.pack('<ii', alpha_angle, beta_angle))

        self._send_command('GOTO_POSITION_RELATIVE', packetdata)

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)

            alpha_timestamp, beta_timestamp = struct.unpack('<II', answer.data)
            alpha_time = self._timestamp_to_seconds(alpha_timestamp)
            beta_time = self._timestamp_to_seconds(beta_timestamp)
            log_positioner.debug(f'alpha ETA: {alpha_time} [s]')
            log_positioner.debug(f'beta ETA: {beta_time} [s]')
            return alpha_time, beta_time
        else:
            log_positioner.error('Error with command goto position relative')

    def set_speed(self, alpha_speed, beta_speed):
        """sets the speed of both actuators

        :param alpha_speed: alpha speed in RPM (at mtor, not output)
        :param beta_speed: beta speed in RPM (at motor, not output)
        """
        packetdata = bytes(struct.pack('<II', alpha_speed, beta_speed))
        self._send_command('SET_SPEED', packetdata)

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command set speed')

    def set_current(self, alpha_current, beta_current):
        """sets the current in percentage used to drive the actuators

        actually alpha current wiill curretnly be used for both actuators

        :param alpha_current: alpha current in percentage
        :param beta_current: beta current in percentage
        """
        packetdata = bytes(struct.pack('<II', alpha_current, beta_current))
        self._send_command('SET_CURRENT', packetdata)

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command set current')

    def set_low_current(self, alpha_current, beta_current):
        """sets the current in percentage used to drive the actuators

        actually alpha current wiill curretnly be used for both actuators

        :param alpha_current: alpha current in percentage
        :param beta_current: beta current in percentage
        """
        packetdata = bytes(struct.pack('<II', alpha_current, beta_current))
        self._send_command('SET_LOW_POWER_CURRENT', packetdata)

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command set low current')

    def set_low_power_mode(self, enable):
        """sets or disables low power mode

        low power mode is simply doisablign hall sensors

        :param enable: true to enbale, false to disable
        """

        if enable is True:
            command = 'SWITCH_OFF_HALL_AFTER_MOVE_CMD'
        else:
            command = 'SWITCH_ON_HALL_AFTER_MOVE_CMD'

        self._send_command(command)

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command set low power mode')

    def initialize_datums(self):
        """initialize positioner datums"""
        self._send_command('INITIALIZE_DATUMS')

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command initialize datums')

    def initialize_datum_alpha(self):
        """initialize positioner alpha datum"""
        self._send_command('GOTO_DATUM_ALPHA')

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command initialize datum alpha')

    def initialize_datum_beta(self):
        """initialize positioner beta datum"""
        self._send_command('GOTO_DATUM_BETA')

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command initialize datum beta')

    def send_trajectory(self, alpha, beta):
        """send a trajectory to the positioner

        :param alpha: list of tupples with alpha coordinate in angles and seconds
        :param beta: list of tupples with beta coordinates in angles and seconds
        """

        alpha_nb_points = len(alpha)
        beta_nb_points = len(beta)
        packetdata = bytes(struct.pack('<ii', alpha_nb_points, beta_nb_points))
        self._send_command('SEND_TRAJECTORY_NEW', packetdata)

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with send_trajectory')
            return

        for coordinate in alpha:
            position = self._angle_to_position(coordinate[0])
            timestamp = self._seconds_to_timestamp(coordinate[1])
            packetdata = bytes(struct.pack('<ii', position, timestamp))
            self._send_command('SEND_TRAJECTORY_DATA', packetdata)
            answer = self._get_answer()
            if answer is not None:
                result = self._get_response_code(answer.arbitration_id)
                log_positioner.debug(result)
                log_positioner.debug(f'alpha coordinate: {coordinate[0]}, timestamp: {coordinate[1]}')
        for coordinate in beta:
            position = self._angle_to_position(coordinate[0])
            timestamp = self._seconds_to_timestamp(coordinate[1])
            packetdata = bytes(struct.pack('<ii', position, timestamp))
            self._send_command('SEND_TRAJECTORY_DATA', packetdata)
            answer = self._get_answer()
            if answer is not None:
                result = self._get_response_code(answer.arbitration_id)
                log_positioner.debug(result)
                log_positioner.debug(f'beta coordinate: {coordinate[0]}, timestamp: {coordinate[1]}')

        self._send_command('SEND_TRAJECTORY_DATA_END')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)

    def start_trajectory(self):
        """start a previously loaded trajectory"""
        self._send_command('START_TRAJECTORY')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)

    def stop_trajectory(self):
        """stops a trajectory"""
        self._send_command('STOP_TRAJECTORY')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)

    def get_v_main(self):
        """gets v_main"""
        self._send_command('GET_ADC_ONE')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)

            positioner_v_main = struct.unpack('<I', answer.data)[0]
            log_positioner.debug('positioner ID : {0}'.format(positioner_v_main))
            return positioner_v_main
        else:
            log_positioner.error('Error with command get_v_main')
            return None

    def get_power(self):
        """requests actual actuators power usage

        :return alpha_power, beta_power: current in mA
        """
        self._send_command('GET_MOTOR_POWER')

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
            alpha_power, beta_power = struct.unpack('<ii', answer.data)
            log_positioner.debug(f'alpha power current: {alpha_power} [mA]')
            log_positioner.debug(f'beta power current: {beta_power} [mA]')
            return alpha_power, beta_power
        else:
            log_positioner.error('Error with command get_power')
            return None

    def get_hall(self):
        """requests actual actuators hall position

        :return alpha_pos, beta_pos: position in °
        """
        self._send_command('GET_HALL_POS')

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
            alpha_pos, beta_pos = struct.unpack('<ff', answer.data)
            log_positioner.debug(f'alpha hall position: {alpha_pos} [°]')
            log_positioner.debug(f'beta hall position: {beta_pos} [°]')
            return alpha_pos, beta_pos
        else:
            log_positioner.error('Error with command get_power')
            return None

    def get_hall_output(self):
        """requests actual output position based on  hall position

        :return alpha_pos, beta_pos: position in coordinates
        """
        self._send_command('GET_HALL_OUTPUT')

        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
            alpha_pos, beta_pos = struct.unpack('<ii', answer.data)
            alpha_angle = self._position_to_angle(alpha_pos)
            beta_angle = self._position_to_angle(beta_pos)
            log_positioner.debug(f'alpha hall position: {alpha_angle:.3f} [°]')
            log_positioner.debug(f'beta hall position: {beta_angle:.3f} [°]')
            return alpha_angle, beta_angle
        else:
            log_positioner.error('Error with command get_power')
            return None

    def erase_flash(self):
        """ erases the external flash"""
        self._send_command('ERASE_EXT_FLASH')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)

    def read_flash(self, address):
        """ reads an address of the external flash

        :param address: address to be read
        :return value: uint32_t value at the given address
        """
        packetdata = bytes(struct.pack('<I', address))

        self._send_command('READ_EXT_FLASH', packetdata)
        answer = self._get_answer()
        if answer is not None:
            value = struct.unpack('<I', answer.data)[0]
            log_positioner.debug(f'content of ext flash at address : {address:02X} is {value:02X}')
            return value
        else:
            log_positioner.error('Error with command read_flash')
            return None

    def write_flash(self, address, value):
        """ writes something to  an address of the external flash

        :param address: address to be read
        :param value: value to be written
        """
        packetdata = bytes(struct.pack('<II', address, value))

        self._send_command('WRITE_EXT_FLASH', packetdata)
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command write_flash')
            return None

    def request_reboot(self):
        """ request reboot of positioner"""

        self._send_command('REQUEST_REBOOT')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command request reboot')
            return None

    def get_hall_calibration(self):
        """ reads the calibration values of hall sensors

        :return value: uint32_t value at the given address
        """

        self._send_command('GET_ALPHA_HALL_CALIB')
        answer = self._get_answer()
        if answer is not None:
            max_aa, max_ab, min_aa, min_ab = struct.unpack('<HHHH', answer.data)
            log_positioner.debug(f'hall alpha: max aa: {max_aa}, max ab: {max_ab}, minaa: {min_aa}, minab : {min_ab}')
        else:
            log_positioner.error('Error with command get hall calibration')
            return None

        self._send_command('GET_BETA_HALL_CALIB')
        answer = self._get_answer()
        if answer is not None:
            max_ba, max_bb, min_ba, min_bb = struct.unpack('<HHHH', answer.data)
            log_positioner.debug(f'hall beta: max ba: {max_ba}, max bb: {max_bb}, minba: {min_ba}, minbb : {min_bb}')
            return max_aa, max_ab, min_aa, min_ab, max_ba, max_bb, min_ba, min_bb
        else:
            log_positioner.error('Error with command get hall calibration')
            return None

    def calib_motors(self):
        """ calibrations motors"""

        self._send_command('CALIB_MOTORS')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command CALIB_MOTORS')
            return None

    def set_mode_open_loop(self):
        self._send_command('SET_ALPHA_OPEN_LOOP_NO_COLL_DETECT')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command SET_ALPHA_OPEN_LOOP_NO_COLL_DETECT')
            return None

        self._send_command('SET_BETA_OPEN_LOOP_NO_COLL_DETECT')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command SET_BETA_OPEN_LOOP_NO_COLL_DETECT')
            return None
        return None

    def set_mode_closed_loop(self):
        self._send_command('SET_ALPHA_CLOSED_LOOP')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command SET_ALPHA_CLOSED_LOOP')
            return None

        self._send_command('SET_BETA_CLOSED_LOOP')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command SET_BETA_CLOSED_LOOP')
            return None
        return None

    def set_mode_closed_loop_no_colision(self):
        self._send_command('SET_ALPHA_CLOSED_LOOP_NO_COLL_DETECT')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command SET_ALPHA_CLOSED_LOOP_NO_COLL_DETECT')
            return None

        self._send_command('SET_BETA_CLOSED_LOOP_NO_COLL_DETECT')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command SET_BETA_CLOSED_LOOP_NO_COLL_DETECT')
            return None
        return None

    def set_precision_mode_off(self):
        self._send_command('SWITCH_OFF_PRECISE_ALPHA')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command SWITCH_OFF_PRECISE_ALPHA')
            return None

        self._send_command('SWITCH_OFF_PRECISE_BETA')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command SWITCH_OFF_PRECISE_BETA')
            return None
        return None

    def set_precision_mode_on(self):
        self._send_command('SWITCH_ON_PRECISE_ALPHA')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command SWITCH_ON_PRECISE_ALPHA')
            return None

        self._send_command('SWITCH_ON_PRECISE_BETA')
        answer = self._get_answer()
        if answer is not None:
            result = self._get_response_code(answer.arbitration_id)
            log_positioner.debug(result)
        else:
            log_positioner.error('Error with command SWITCH_ON_PRECISE_BETA')
            return None
        return None

    def wait_move(self):
        self.get_status()
        while self.status.displacement_completed != 1:
            self.get_status()
            time.sleep(0.5)
        return None
    
