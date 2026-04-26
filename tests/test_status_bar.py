"""Tests for menu bar controller wiring."""

import unittest
from unittest.mock import MagicMock, patch

from vvrite.status_bar import StatusBarController


class _FakeButton:
    def __init__(self):
        self.image = None
        self.title = None
        self.needs_display = False
        self.displayed = False

    def setImage_(self, image):
        self.image = image

    def setTitle_(self, title):
        self.title = title

    def setNeedsDisplay_(self, needs_display):
        self.needs_display = needs_display

    def displayIfNeeded(self):
        self.displayed = True


class _FakeStatusItem:
    def __init__(self):
        self._button = _FakeButton()
        self.menu = None
        self.visible = None
        self.length = None

    def button(self):
        return self._button

    def setMenu_(self, menu):
        self.menu = menu

    def setVisible_(self, visible):
        self.visible = visible

    def setLength_(self, length):
        self.length = length


class _FakeStatusBar:
    _instance = None

    def __init__(self):
        self.item = _FakeStatusItem()
        self.requested_length = None

    @classmethod
    def systemStatusBar(cls):
        return cls._instance

    def statusItemWithLength_(self, _length):
        self.requested_length = _length
        return self.item


class _FakeImage:
    @classmethod
    def imageWithSystemSymbolName_accessibilityDescription_(cls, _name, _description):
        return object()


class _FakeMenu:
    @classmethod
    def alloc(cls):
        return cls()

    def init(self):
        self.items = []
        return self

    def addItem_(self, item):
        self.items.append(item)


class _FakeMenuItem:
    @classmethod
    def alloc(cls):
        return cls()

    @classmethod
    def separatorItem(cls):
        item = cls()
        item.title = "separator"
        return item

    def initWithTitle_action_keyEquivalent_(self, title, action, key):
        self.title = title
        self.action = action
        self.key = key
        self.target = None
        self.enabled = True
        return self

    def setTarget_(self, target):
        self.target = target

    def setEnabled_(self, enabled):
        self.enabled = enabled

    def setTitle_(self, title):
        self.title = title


class TestStatusBarMenuActions(unittest.TestCase):
    def test_settings_and_about_actions_target_app_delegate(self):
        status_bar = _FakeStatusBar()
        _FakeStatusBar._instance = status_bar
        delegate = MagicMock()
        delegate._prefs.hotkey_keycode = 49
        delegate._prefs.hotkey_modifiers = 0

        with patch("vvrite.status_bar.NSStatusBar", _FakeStatusBar), patch(
            "vvrite.status_bar.NSMenu", _FakeMenu
        ), patch("vvrite.status_bar.NSMenuItem", _FakeMenuItem), patch(
            "vvrite.status_bar.NSImage", _FakeImage
        ):
            controller = StatusBarController.alloc().initWithDelegate_(delegate)

        items_by_action = {
            item.action: item
            for item in controller._menu.items
            if getattr(item, "action", None)
        }

        self.assertIs(items_by_action["openSettings:"].target, delegate)
        self.assertIs(items_by_action["showAbout:"].target, delegate)

    def test_status_item_uses_fixed_visible_icon_slot_on_launch(self):
        status_bar = _FakeStatusBar()
        _FakeStatusBar._instance = status_bar
        delegate = MagicMock()
        delegate._prefs.hotkey_keycode = 49
        delegate._prefs.hotkey_modifiers = 0

        with patch("vvrite.status_bar.NSStatusBar", _FakeStatusBar), patch(
            "vvrite.status_bar.NSMenu", _FakeMenu
        ), patch("vvrite.status_bar.NSMenuItem", _FakeMenuItem), patch(
            "vvrite.status_bar.NSImage", _FakeImage
        ), patch("vvrite.status_bar.NSSquareStatusItemLength", "square", create=True):
            StatusBarController.alloc().initWithDelegate_(delegate)

        self.assertEqual(status_bar.requested_length, "square")
        self.assertTrue(status_bar.item.visible)
        self.assertTrue(status_bar.item.button().needs_display)
        self.assertTrue(status_bar.item.button().displayed)

    def test_download_progress_uses_variable_width_then_restores_icon_slot(self):
        status_bar = _FakeStatusBar()
        _FakeStatusBar._instance = status_bar
        delegate = MagicMock()
        delegate._prefs.hotkey_keycode = 49
        delegate._prefs.hotkey_modifiers = 0

        with patch("vvrite.status_bar.NSStatusBar", _FakeStatusBar), patch(
            "vvrite.status_bar.NSMenu", _FakeMenu
        ), patch("vvrite.status_bar.NSMenuItem", _FakeMenuItem), patch(
            "vvrite.status_bar.NSImage", _FakeImage
        ), patch("vvrite.status_bar.NSSquareStatusItemLength", "square", create=True), patch(
            "vvrite.status_bar.NSVariableStatusItemLength", "variable", create=True
        ):
            controller = StatusBarController.alloc().initWithDelegate_(delegate)
            controller.setDownloadProgress_(42)
            self.assertEqual(status_bar.item.length, "variable")
            self.assertEqual(status_bar.item.button().title, "42%")

            controller.setDownloadProgress_(-1)

        self.assertEqual(status_bar.item.length, "square")
        self.assertEqual(status_bar.item.button().title, "")


if __name__ == "__main__":
    unittest.main()
