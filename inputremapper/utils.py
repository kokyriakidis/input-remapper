# -*- coding: utf-8 -*-
# input-remapper - GUI for device specific keyboard mappings
# Copyright (C) 2025 sezanzeb <b8x45ygc9@mozmail.com>
#
# This file is part of input-remapper.
#
# input-remapper is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# input-remapper is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with input-remapper.  If not, see <https://www.gnu.org/licenses/>.


"""Utility functions."""

import sys
from hashlib import md5
from typing import Optional, NewType

import evdev

DeviceHash = NewType("DeviceHash", str)


def is_service() -> bool:
    return sys.argv[0].endswith("input-remapper-service")


def get_device_hash(device: evdev.InputDevice) -> DeviceHash:
    """get a unique hash for the given device."""
    # The builtin hash() function can not be used because it is randomly
    # seeded at python startup.
    # A non-cryptographic hash would be faster but there is none in the standard lib
    # This hash needs to stay the same across reboots, and even stay the same when
    # moving the config to a new computer.
    s = str(device.capabilities(absinfo=False)) + device.name
    return DeviceHash(md5(s.encode()).hexdigest().lower())


def get_evdev_constant_name(type_: Optional[int], code: Optional[int], *_) -> str:
    """Handy function to get the evdev constant name for display purposes.

    Returns "unknown" for unknown events.
    """
    # using this function is more readable than
    #   type_, code = event.type_and_code
    #   name = evdev.ecodes.bytype[type_][code]
    name = evdev.ecodes.bytype.get(type_, {}).get(code)

    if type(name) in [list, tuple]:
        # python-evdev >= 1.8.0 uses tuples
        name = name[0]

    if name is None:
        return "unknown"

    return name
