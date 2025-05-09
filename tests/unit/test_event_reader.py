#!/usr/bin/env python3
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

import asyncio
import os
import unittest
from unittest.mock import MagicMock, patch

import evdev
from evdev.ecodes import (
    EV_KEY,
    EV_ABS,
    BTN_A,
    ABS_X,
    ABS_Y,
    ABS_RX,
    ABS_RY,
    EV_REL,
    REL_X,
    REL_Y,
    REL_HWHEEL_HI_RES,
    REL_WHEEL_HI_RES,
)

from inputremapper.configs.input_config import InputCombination, InputConfig
from inputremapper.configs.keyboard_layout import keyboard_layout
from inputremapper.configs.mapping import Mapping
from inputremapper.configs.preset import Preset
from inputremapper.injection.context import Context
from inputremapper.injection.event_reader import EventReader
from inputremapper.injection.global_uinputs import GlobalUInputs, UInput
from inputremapper.injection.mapping_handlers.mapping_parser import MappingParser
from inputremapper.input_event import InputEvent
from inputremapper.utils import get_device_hash
from tests.lib.fixtures import fixtures
from tests.lib.test_setup import test_setup


@test_setup
class TestEventReader(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.gamepad_source = evdev.InputDevice(fixtures.gamepad.path)
        self.source_hash = fixtures.gamepad.get_device_hash()
        self.global_uinputs = GlobalUInputs(UInput)
        self.mapping_parser = MappingParser(self.global_uinputs)
        self.stop_event = asyncio.Event()
        self.preset = Preset()
        self.forward_uinput = evdev.UInput(name="test-forward-uinput")

        self.global_uinputs.is_service = True
        self.global_uinputs.prepare_all()

    async def setup(self, mapping):
        """Set a EventReader up for the test and run it in the background."""
        context = Context(
            mapping,
            {},
            {self.source_hash: self.forward_uinput},
            self.mapping_parser,
        )
        context.uinput = evdev.UInput()
        event_reader = EventReader(
            context,
            self.gamepad_source,
            self.stop_event,
        )
        asyncio.ensure_future(event_reader.run())
        await asyncio.sleep(0.1)
        return context, event_reader

    async def test_if_single_joystick_then(self):
        # TODO: Move this somewhere more sensible
        # Integration test style for if_single.
        # won't care about the event, because the purpose is not set to BUTTON
        code_a = keyboard_layout.get("a")
        code_shift = keyboard_layout.get("KEY_LEFTSHIFT")
        trigger = evdev.ecodes.BTN_A

        self.preset.add(
            Mapping.from_combination(
                InputCombination(
                    [
                        InputConfig(
                            type=EV_KEY,
                            code=trigger,
                            origin_hash=fixtures.gamepad.get_device_hash(),
                        )
                    ]
                ),
                "keyboard",
                "if_single(key(a), key(KEY_LEFTSHIFT))",
            )
        )
        self.preset.add(
            Mapping.from_combination(
                InputCombination(
                    [
                        InputConfig(
                            type=EV_ABS,
                            code=ABS_Y,
                            analog_threshold=1,
                            origin_hash=fixtures.gamepad.get_device_hash(),
                        )
                    ]
                ),
                "keyboard",
                "b",
            ),
        )

        # left x to mouse x
        config = {
            "input_combination": [
                InputConfig(
                    type=EV_ABS,
                    code=ABS_X,
                    origin_hash=fixtures.gamepad.get_device_hash(),
                )
            ],
            "target_uinput": "mouse",
            "output_type": EV_REL,
            "output_code": REL_X,
        }
        self.preset.add(Mapping(**config))

        # left y to mouse y
        config["input_combination"] = [
            InputConfig(
                type=EV_ABS,
                code=ABS_Y,
                origin_hash=fixtures.gamepad.get_device_hash(),
            )
        ]
        config["output_code"] = REL_Y
        self.preset.add(Mapping(**config))

        # right x to wheel x
        config["input_combination"] = [
            InputConfig(
                type=EV_ABS,
                code=ABS_RX,
                origin_hash=fixtures.gamepad.get_device_hash(),
            )
        ]
        config["output_code"] = REL_HWHEEL_HI_RES
        self.preset.add(Mapping(**config))

        # right y to wheel y
        config["input_combination"] = [
            InputConfig(
                type=EV_ABS,
                code=ABS_RY,
                origin_hash=fixtures.gamepad.get_device_hash(),
            )
        ]
        config["output_code"] = REL_WHEEL_HI_RES
        self.preset.add(Mapping(**config))

        context, _ = await self.setup(self.preset)

        gamepad_hash = get_device_hash(self.gamepad_source)
        self.gamepad_source.push_events(
            [
                InputEvent.key(evdev.ecodes.BTN_Y, 0, gamepad_hash),  # start the macro
                InputEvent.key(trigger, 1, gamepad_hash),  # start the macro
                InputEvent.abs(ABS_Y, 10, gamepad_hash),  # ignored
                InputEvent.key(evdev.ecodes.BTN_B, 2, gamepad_hash),  # ignored
                InputEvent.key(evdev.ecodes.BTN_B, 0, gamepad_hash),  # ignored
                # release the trigger, which runs `then` of if_single
                InputEvent.key(trigger, 0, gamepad_hash),
            ]
        )

        await asyncio.sleep(0.1)
        self.stop_event.set()  # stop the reader

        history = self.global_uinputs.get_uinput("keyboard").write_history
        self.assertIn((EV_KEY, code_a, 1), history)
        self.assertIn((EV_KEY, code_a, 0), history)
        self.assertNotIn((EV_KEY, code_shift, 1), history)
        self.assertNotIn((EV_KEY, code_shift, 0), history)

        # after if_single takes an action, the listener should have been removed
        self.assertSetEqual(context.listeners, set())

    async def test_if_single_joystick_under_threshold(self):
        """Triggers then because the joystick events value is too low."""
        # TODO: Move this somewhere more sensible
        code_a = keyboard_layout.get("a")
        trigger = evdev.ecodes.BTN_A
        self.preset.add(
            Mapping.from_combination(
                InputCombination(
                    [
                        InputConfig(
                            type=EV_KEY,
                            code=trigger,
                            origin_hash=fixtures.gamepad.get_device_hash(),
                        )
                    ]
                ),
                "keyboard",
                "if_single(k(a), k(KEY_LEFTSHIFT))",
            )
        )
        self.preset.add(
            Mapping.from_combination(
                InputCombination(
                    [
                        InputConfig(
                            type=EV_ABS,
                            code=ABS_Y,
                            analog_threshold=1,
                            origin_hash=fixtures.gamepad.get_device_hash(),
                        )
                    ]
                ),
                "keyboard",
                "b",
            ),
        )

        # self.preset.set("gamepad.joystick.left_purpose", BUTTONS)
        # self.preset.set("gamepad.joystick.right_purpose", BUTTONS)
        context, _ = await self.setup(self.preset)

        self.gamepad_source.push_events(
            [
                InputEvent.key(trigger, 1),  # start the macro
                InputEvent.abs(ABS_Y, 1),  # ignored because value too low
                InputEvent.key(trigger, 0),  # stop, only way to trigger `then`
            ]
        )
        await asyncio.sleep(0.1)
        self.assertEqual(len(context.listeners), 0)
        history = self.global_uinputs.get_uinput("keyboard").write_history

        # the key that triggered if_single should be injected after
        # if_single had a chance to inject keys (if the macro is fast enough),
        # so that if_single can inject a modifier to e.g. capitalize the
        # triggering key. This is important for the space cadet shift
        self.assertListEqual(
            history,
            [
                (EV_KEY, code_a, 1),
                (EV_KEY, code_a, 0),
            ],
        )

    @patch.object(Context, "reset")
    async def test_reset_handlers_on_stop(self, reset_mock: MagicMock) -> None:
        await self.setup(self.preset)

        self.stop_event.set()
        await asyncio.sleep(0.1)

        reset_mock.assert_called_once()

    @patch.object(Context, "reset")
    @patch.object(os, "stat")
    async def test_reset_handlers_after_unplugging(
        self,
        stat_mock: MagicMock,
        reset_mock: MagicMock,
    ) -> None:
        await self.setup(self.preset)

        self.gamepad_source.push_events([InputEvent.key(BTN_A, 1)])
        await asyncio.sleep(0.1)
        reset_mock.assert_not_called()

        # unplug the device
        stat_mock().st_nlink = 0

        # It seems that once a device is unplugged, asyncio stops waiting for new input
        # from _source.fileno() or something. I didn't manage to replicate this
        # behavior in tests using the fd of pending_events[fixtures.gamepad][0].fileno()
        # and/or pending_events[fixtures.gamepad][1].fileno(). So instead, I push
        # another event, so that the EventReader makes another iteration.
        self.gamepad_source.push_events([InputEvent.key(BTN_A, 1)])
        await asyncio.sleep(0.1)

        reset_mock.assert_called_once()
