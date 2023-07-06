#!/usr/bin/env python
# coding: utf-8

import ctypes

uint32_t = ctypes.c_uint32
uint64_t = ctypes.c_uint64

__all__ = ['BootloaderStatus', 'PositionerStatus']


class BootloaderFlagBits(ctypes.LittleEndianStructure):
    """bootloader status register flags"""
    _fields_ = [
                ('init', uint32_t, 1),                  # 0x00000001
                ('timeout', uint32_t, 1),               # 0x00000002
                ('reserve2', uint32_t, 1),              # 0x00000004
                ('reserve3', uint32_t, 1),              # 0x00000008
                ('reserve4', uint32_t, 1),              # 0x00000010
                ('reserve5', uint32_t, 1),              # 0x00000020
                ('reserve6', uint32_t, 1),              # 0x00000040
                ('reserve7', uint32_t, 1),              # 0x00000080
                ('config_changed', uint32_t, 1),        # 0x00000100
                ('bsettings_changed', uint32_t, 1),     # 0x00000200
                ('reserve10', uint32_t, 1),             # 0x00000400
                ('reserve11', uint32_t, 1),             # 0x00000800
                ('reserve12', uint32_t, 1),             # 0x00001000
                ('reserve13', uint32_t, 1),             # 0x00002000
                ('reserve14', uint32_t, 1),             # 0x00004000
                ('reserve15', uint32_t, 1),             # 0x00008000
                ('receiving_firmware', uint32_t, 1),    # 0x00010000
                ('reserve17', uint32_t, 1),             # 0x00020000
                ('reserve18', uint32_t, 1),             # 0x00040000
                ('reserve19', uint32_t, 1),             # 0x00080000
                ('reserve20', uint32_t, 1),             # 0x00100000
                ('reserve21', uint32_t, 1),             # 0x00200000
                ('reserve22', uint32_t, 1),             # 0x00400000
                ('reserve23', uint32_t, 1),             # 0x00800000
                ('firmware_received', uint32_t, 1),     # 0x01000000
                ('firmware_ok', uint32_t, 1),           # 0x02000000
                ('firmware_bad', uint32_t, 1),          # 0x04000000
                ('reserve27', uint32_t, 1),             # 0x08000000
                ('reserve28', uint32_t, 1),             # 0x10000000
                ('reserve29', uint32_t, 1),             # 0x20000000
                ('reserve30', uint32_t, 1),             # 0x40000000
                ('reserve31', uint32_t, 1)]             # 0x80000000


class BootloaderStatus(ctypes.Union):
    """"bootloader status"""
    _anonymous_ = ('bit',)
    _fields_ = [
                ('bit', BootloaderFlagBits),
                ('asInt', uint32_t)]


class PositionerFlagBits(ctypes.LittleEndianStructure):
    """positioner status register flags"""
    _fields_ = [
        ('init', uint64_t, 1),
        ('config_changed', uint64_t, 1),
        ('bsettings_changed', uint64_t, 1),
        ('data_streaming', uint64_t, 1),
        ('receiving_trajectory', uint64_t, 1),
        ('trajectory_alpha_received', uint64_t, 1),
        ('trajectory_beta_received', uint64_t, 1),
        ('low_power_after_move', uint64_t, 1),
        ('displacement_completed', uint64_t, 1),
        ('displacement_completed_alpha', uint64_t, 1),
        ('displacement_completed_beta', uint64_t, 1),
        ('collision_alpha', uint64_t, 1),
        ('collision_beta', uint64_t, 1),
        ('closed_loop_alpha', uint64_t, 1),
        ('closed_loop_beta', uint64_t, 1),
        ('precise_positioning_alpha', uint64_t, 1),
        ('precise_positioning_beta', uint64_t, 1),
        ('collision_detect_alpha_disable', uint64_t, 1),
        ('collision_detect_beta_disable', uint64_t, 1),
        ('motor_calibration', uint64_t, 1),
        ('motor_alpha_calibrated', uint64_t, 1),
        ('motor_beta_calibrated', uint64_t, 1),
        ('datum_calibration', uint64_t, 1),
        ('datum_alpha_calibrated', uint64_t, 1),
        ('datum_beta_calibrated', uint64_t, 1),
        ('datum_initialization', uint64_t, 1),
        ('datum_alpha_initialized', uint64_t, 1),
        ('datum_beta_initialized', uint64_t, 1),
        ('hall_alpha_disable', uint64_t, 1),
        ('hall_beta_disable', uint64_t, 1),
        ('cogging_calibration', uint64_t, 1),
		('cogging_alpha_calibrated', uint64_t, 1),
		('cogging_beta_calibrated', uint64_t, 1),
		('estimated_position', uint64_t, 1),
		('position_restored', uint64_t, 1),
		('switch_off_after_move', uint64_t, 1),
		('calibration_saved', uint64_t, 1),
		('precise_move_in_open_loop_alpha', uint64_t, 1),
		('precise_move_in_open_loop_beta', uint64_t, 1),
		('switch_off_hall_after_move', uint64_t, 1),
		('reserve41', uint64_t, 1),
		('reserve42', uint64_t, 1),
		('reserve43', uint64_t, 1),
		('reserve44', uint64_t, 1),
		('reserve45', uint64_t, 1),
		('reserve46', uint64_t, 1),
		('reserve47', uint64_t, 1),
		('reserve48', uint64_t, 1),
		('reserve49', uint64_t, 1),
		('reserve50', uint64_t, 1),
		('reserve51', uint64_t, 1),
		('reserve52', uint64_t, 1),
		('reserve53', uint64_t, 1),
		('reserve54', uint64_t, 1),
		('reserve55', uint64_t, 1),
		('reserve56', uint64_t, 1),
		('reserve57', uint64_t, 1),
		('reserve58', uint64_t, 1),
		('reserve59', uint64_t, 1),
		('reserve60', uint64_t, 1),
		('reserve61', uint64_t, 1),
		('reserve62', uint64_t, 1),
		('reserve63', uint64_t, 1),
        ('reserve64', uint64_t, 1)]


class PositionerStatus(ctypes.Union):
    """positioner status register"""
    _anonymous_ = ('bit',)
    _fields_ = [
        ('bit', PositionerFlagBits),
        ('asInt', uint64_t)]

