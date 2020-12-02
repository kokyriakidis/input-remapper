#!/usr/bin/python3
# -*- coding: utf-8 -*-
# key-mapper - GUI for device specific keyboard mappings
# Copyright (C) 2020 sezanzeb <proxima@hip70890b.de>
#
# This file is part of key-mapper.
#
# key-mapper is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# key-mapper is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with key-mapper.  If not, see <https://www.gnu.org/licenses/>.


import unittest

from keymapper.getdevices import _GetDevices, get_devices


class FakePipe:
    devices = None

    def send(self, devices):
        self.devices = devices


class TestGetDevices(unittest.TestCase):
    def test_get_devices(self):
        pipe = FakePipe()
        _GetDevices(pipe).run()
        self.assertDictEqual(pipe.devices, {
            'device 1': {
                'paths': [
                    '/dev/input/event11',
                    '/dev/input/event10',
                    '/dev/input/event13'
                ],
                'devices': [
                    'device 1 foo',
                    'device 1',
                    'device 1'
                ]
            },
            'device 2': {
               'paths': ['/dev/input/event20'],
               'devices': ['device 2']
            },
            'gamepad': {
                'paths': ['/dev/input/event30'],
                'devices': ['gamepad']
            },
            'key-mapper device 2': {
               'paths': ['/dev/input/event40'],
               'devices': ['key-mapper device 2']
            },
        })
        self.assertDictEqual(pipe.devices, get_devices(include_keymapper=True))

    def test_get_devices_2(self):
        self.assertDictEqual(get_devices(), {
            'device 1': {
                'paths': [
                    '/dev/input/event11',
                    '/dev/input/event10',
                    '/dev/input/event13'
                ],
                'devices': [
                    'device 1 foo',
                    'device 1',
                    'device 1'
                ]
            },
            'device 2': {
               'paths': ['/dev/input/event20'],
               'devices': ['device 2']
            },
            'gamepad': {
                'paths': ['/dev/input/event30'],
                'devices': ['gamepad']
            },
        })


if __name__ == "__main__":
    unittest.main()