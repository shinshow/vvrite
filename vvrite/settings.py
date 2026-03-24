"""Settings window for hotkey, microphone, permissions, and launch at login."""

import objc
import ApplicationServices
import os

from AppKit import (
    NSObject,
    NSMakeRect,
    NSWindow,
    NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable,
    NSBackingStoreBuffered,
    NSTextField,
    NSFont,
    NSButton,
    NSButtonTypeSwitch,
    NSPopUpButton,
    NSColor,
    NSApp,
    NSBezelStyleRounded,
    NSAlert,
    NSWorkspace,
    NSSlider,
    NSOpenPanel,
    NSMenuItem,
)
from Foundation import NSLog, NSURL, NSTimer

from vvrite import launch_at_login, sounds
from vvrite.audio_devices import (
    get_default_input_device,
    list_input_devices,
    resolve_input_device,
)
from vvrite.preferences import Preferences
from vvrite.widgets import ShortcutField


class SettingsWindowController(NSObject):
    def initWithPreferences_(self, prefs):
        self = objc.super(SettingsWindowController, self).init()
        if self is None:
            return None
        self._prefs = prefs
        self._window = None
        self._permission_timer = None
        self._acc_label = None
        self._mic_label = None
        self._shortcut_field = None
        self._retract_checkbox = None
        self._retract_shortcut_field = None
        self._retract_change_btn = None
        self._mic_popup = None
        self._mic_device_ids = [None]
        self._login_checkbox = None
        self._custom_words_field = None
        self._start_sound_popup = None
        self._stop_sound_popup = None
        self._start_volume_slider = None
        self._stop_volume_slider = None
        self._start_volume_label = None
        self._stop_volume_label = None
        self._build_window()
        return self

    def _build_window(self):
        frame = NSMakeRect(0, 0, 400, 706)
        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False,
        )
        self._window.setTitle_("Settings")
        self._window.setReleasedWhenClosed_(False)
        self._window.center()
        self._window.setDelegate_(self)

        content = self._window.contentView()
        y = 692

        # --- Shortcut ---
        y -= 30
        label = NSTextField.labelWithString_("Shortcut")
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 30
        self._shortcut_field = ShortcutField.alloc().initWithFrame_preferences_(
            NSMakeRect(20, y, 280, 24), self._prefs
        )
        content.addSubview_(self._shortcut_field)

        change_btn = NSButton.alloc().initWithFrame_(NSMakeRect(310, y, 80, 24))
        change_btn.setTitle_("Change")
        change_btn.setBezelStyle_(NSBezelStyleRounded)
        change_btn.setTarget_(self)
        change_btn.setAction_("changeShortcut:")
        content.addSubview_(change_btn)

        # --- Correction ---
        y -= 40
        label = NSTextField.labelWithString_("Correction")
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 30
        self._retract_checkbox = NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 360, 20))
        self._retract_checkbox.setButtonType_(NSButtonTypeSwitch)
        self._retract_checkbox.setTitle_("Enable retract last dictation shortcut")
        self._retract_checkbox.setState_(
            1 if self._prefs.retract_last_dictation_enabled else 0
        )
        self._retract_checkbox.setTarget_(self)
        self._retract_checkbox.setAction_("retractShortcutToggled:")
        content.addSubview_(self._retract_checkbox)

        y -= 30
        self._retract_shortcut_field = (
            ShortcutField.alloc().initWithFrame_preferences_keycodeKey_modifiersKey_(
                NSMakeRect(20, y, 280, 24),
                self._prefs,
                "retract_hotkey_keycode",
                "retract_hotkey_modifiers",
            )
        )
        content.addSubview_(self._retract_shortcut_field)

        self._retract_change_btn = NSButton.alloc().initWithFrame_(NSMakeRect(310, y, 80, 24))
        self._retract_change_btn.setTitle_("Change")
        self._retract_change_btn.setBezelStyle_(NSBezelStyleRounded)
        self._retract_change_btn.setTarget_(self)
        self._retract_change_btn.setAction_("changeRetractShortcut:")
        content.addSubview_(self._retract_change_btn)

        y -= 20
        hint = NSTextField.labelWithString_(
            "방금 붙여넣은 받아쓰기 결과를 Delete로 지웁니다"
        )
        hint.setFrame_(NSMakeRect(20, y, 360, 16))
        hint.setFont_(NSFont.systemFontOfSize_(11.0))
        hint.setTextColor_(NSColor.secondaryLabelColor())
        content.addSubview_(hint)

        # --- Microphone ---
        y -= 40
        label = NSTextField.labelWithString_("Microphone")
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 30
        self._mic_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(20, y, 360, 24), False
        )
        self._populate_mics()
        self._mic_popup.setTarget_(self)
        self._mic_popup.setAction_("micChanged:")
        content.addSubview_(self._mic_popup)

        # --- Model ---
        y -= 40
        label = NSTextField.labelWithString_("Model")
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 26
        model_label = NSTextField.labelWithString_(self._prefs.model_id)
        model_label.setFrame_(NSMakeRect(20, y, 360, 20))
        model_label.setTextColor_(NSColor.secondaryLabelColor())
        content.addSubview_(model_label)

        # --- Custom Words ---
        y -= 40
        label = NSTextField.labelWithString_("Custom Words")
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 26
        self._custom_words_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y, 360, 24)
        )
        self._custom_words_field.setStringValue_(self._prefs.custom_words)
        self._custom_words_field.setPlaceholderString_("MLX, Qwen, vvrite")
        self._custom_words_field.setDelegate_(self)
        content.addSubview_(self._custom_words_field)

        y -= 20
        hint = NSTextField.labelWithString_(
            "인식이 잘 안 되는 단어를 쉼표로 구분해서 입력하세요"
        )
        hint.setFrame_(NSMakeRect(20, y, 360, 16))
        hint.setFont_(NSFont.systemFontOfSize_(11.0))
        hint.setTextColor_(NSColor.secondaryLabelColor())
        content.addSubview_(hint)

        # --- Sound ---
        y -= 40
        label = NSTextField.labelWithString_("Sound")
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        # Start sound row
        y -= 30
        start_label = NSTextField.labelWithString_("Start")
        start_label.setFrame_(NSMakeRect(20, y, 50, 20))
        start_label.setAlignment_(2)  # NSTextAlignmentRight
        start_label.setTextColor_(NSColor.secondaryLabelColor())
        start_label.setFont_(NSFont.systemFontOfSize_(12.0))
        content.addSubview_(start_label)

        self._start_sound_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(76, y, 140, 24), False
        )
        self._start_sound_popup.setTarget_(self)
        self._start_sound_popup.setAction_("startSoundChanged:")
        content.addSubview_(self._start_sound_popup)

        self._start_volume_slider = NSSlider.alloc().initWithFrame_(
            NSMakeRect(222, y, 120, 24)
        )
        self._start_volume_slider.setMinValue_(0)
        self._start_volume_slider.setMaxValue_(100)
        self._start_volume_slider.setIntValue_(int(self._prefs.start_volume * 100))
        self._start_volume_slider.setContinuous_(True)
        self._start_volume_slider.setTarget_(self)
        self._start_volume_slider.setAction_("startVolumeChanged:")
        content.addSubview_(self._start_volume_slider)

        self._start_volume_label = NSTextField.labelWithString_(
            f"{int(self._prefs.start_volume * 100)}%"
        )
        self._start_volume_label.setFrame_(NSMakeRect(348, y, 40, 20))
        self._start_volume_label.setTextColor_(NSColor.secondaryLabelColor())
        self._start_volume_label.setFont_(NSFont.systemFontOfSize_(11.0))
        content.addSubview_(self._start_volume_label)

        # Stop sound row
        y -= 30
        stop_label = NSTextField.labelWithString_("Stop")
        stop_label.setFrame_(NSMakeRect(20, y, 50, 20))
        stop_label.setAlignment_(2)  # NSTextAlignmentRight
        stop_label.setTextColor_(NSColor.secondaryLabelColor())
        stop_label.setFont_(NSFont.systemFontOfSize_(12.0))
        content.addSubview_(stop_label)

        self._stop_sound_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(76, y, 140, 24), False
        )
        self._stop_sound_popup.setTarget_(self)
        self._stop_sound_popup.setAction_("stopSoundChanged:")
        content.addSubview_(self._stop_sound_popup)

        self._stop_volume_slider = NSSlider.alloc().initWithFrame_(
            NSMakeRect(222, y, 120, 24)
        )
        self._stop_volume_slider.setMinValue_(0)
        self._stop_volume_slider.setMaxValue_(100)
        self._stop_volume_slider.setIntValue_(int(self._prefs.stop_volume * 100))
        self._stop_volume_slider.setContinuous_(True)
        self._stop_volume_slider.setTarget_(self)
        self._stop_volume_slider.setAction_("stopVolumeChanged:")
        content.addSubview_(self._stop_volume_slider)

        self._stop_volume_label = NSTextField.labelWithString_(
            f"{int(self._prefs.stop_volume * 100)}%"
        )
        self._stop_volume_label.setFrame_(NSMakeRect(348, y, 40, 20))
        self._stop_volume_label.setTextColor_(NSColor.secondaryLabelColor())
        self._stop_volume_label.setFont_(NSFont.systemFontOfSize_(11.0))
        content.addSubview_(self._stop_volume_label)

        y -= 20
        hint = NSTextField.labelWithString_(
            "슬라이더를 조절하면 선택된 소리가 자동으로 재생됩니다"
        )
        hint.setFrame_(NSMakeRect(76, y, 310, 16))
        hint.setFont_(NSFont.systemFontOfSize_(11.0))
        hint.setTextColor_(NSColor.secondaryLabelColor())
        content.addSubview_(hint)

        self._populate_sounds()

        # --- Permissions ---
        y -= 40
        label = NSTextField.labelWithString_("Permissions")
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 26
        self._acc_label = NSTextField.labelWithString_("Accessibility: checking...")
        self._acc_label.setFrame_(NSMakeRect(20, y, 250, 20))
        content.addSubview_(self._acc_label)

        acc_btn = NSButton.alloc().initWithFrame_(NSMakeRect(310, y, 70, 24))
        acc_btn.setTitle_("Open")
        acc_btn.setBezelStyle_(NSBezelStyleRounded)
        acc_btn.setTarget_(self)
        acc_btn.setAction_("openAccessibility:")
        content.addSubview_(acc_btn)

        y -= 26
        self._mic_label = NSTextField.labelWithString_("Microphone: checking...")
        self._mic_label.setFrame_(NSMakeRect(20, y, 250, 20))
        content.addSubview_(self._mic_label)

        mic_perm_btn = NSButton.alloc().initWithFrame_(NSMakeRect(310, y, 70, 24))
        mic_perm_btn.setTitle_("Open")
        mic_perm_btn.setBezelStyle_(NSBezelStyleRounded)
        mic_perm_btn.setTarget_(self)
        mic_perm_btn.setAction_("openMicrophonePrivacy:")
        content.addSubview_(mic_perm_btn)

        # --- Launch at Login ---
        y -= 40
        self._login_checkbox = NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 360, 20))
        self._login_checkbox.setButtonType_(NSButtonTypeSwitch)
        self._login_checkbox.setTitle_("Launch at login")
        self._login_checkbox.setState_(1 if self._prefs.launch_at_login else 0)
        self._login_checkbox.setTarget_(self)
        self._login_checkbox.setAction_("loginToggled:")
        content.addSubview_(self._login_checkbox)

        # --- Automatically check for updates ---
        y -= 34
        self._update_checkbox = NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 360, 20))
        self._update_checkbox.setButtonType_(NSButtonTypeSwitch)
        self._update_checkbox.setTitle_("Automatically check for updates")
        self._update_checkbox.setState_(1 if self._prefs.auto_update_check else 0)
        self._update_checkbox.setTarget_(self)
        self._update_checkbox.setAction_("updateCheckToggled:")
        content.addSubview_(self._update_checkbox)

        self._update_permissions()
        self._refresh_login_checkbox()
        self._refresh_retract_controls()

    def _populate_sounds(self):
        """Populate both sound dropdowns with system sounds + Custom option."""
        system_sounds = sounds.list_system_sounds()
        for popup, pref_value in [
            (self._start_sound_popup, self._prefs.sound_start),
            (self._stop_sound_popup, self._prefs.sound_stop),
        ]:
            popup.removeAllItems()
            for name in system_sounds:
                popup.addItemWithTitle_(name)
            popup.menu().addItem_(NSMenuItem.separatorItem())
            popup.addItemWithTitle_("Custom...")

            # Select current value
            if sounds.is_custom_path(pref_value):
                filename = os.path.basename(pref_value)
                if filename:  # guard against empty/malformed paths
                    popup.insertItemWithTitle_atIndex_(filename, len(system_sounds))
                    popup.selectItemAtIndex_(len(system_sounds))
            else:
                idx = popup.indexOfItemWithTitle_(pref_value)
                if idx >= 0:
                    popup.selectItemAtIndex_(idx)

    def _populate_mics(self):
        self._mic_popup.removeAllItems()
        devices = list_input_devices()
        default_device = get_default_input_device(devices)
        default_label = "System Default"
        if default_device is not None:
            default_label = f"System Default ({default_device.name})"
        self._mic_popup.addItemWithTitle_(default_label)

        self._mic_device_ids = [None]
        current = self._prefs.mic_device
        selected_idx = 0
        selected_device = resolve_input_device(current, devices)

        for device in devices:
            self._mic_popup.addItemWithTitle_(device.display_name)
            self._mic_device_ids.append(device.device_id)
            if selected_device is not None and selected_device.device_id == device.device_id:
                selected_idx = self._mic_popup.numberOfItems() - 1

        self._mic_popup.selectItemAtIndex_(selected_idx)

    def _update_permissions(self):
        trusted = ApplicationServices.AXIsProcessTrusted()
        self._acc_label.setStringValue_(
            f"Accessibility: {'✅ Granted' if trusted else '❌ Not Granted'}"
        )
        self._mic_label.setStringValue_("Microphone: ✅ Granted")

    def showWindow_(self, sender):
        self._populate_mics()
        self._populate_sounds()
        self._window.makeKeyAndOrderFront_(sender)
        self._permission_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, self, "pollPermissions:", None, True
        )

    def window(self):
        return self._window

    def windowWillClose_(self, notification):
        self._save_custom_words()
        if self._permission_timer:
            self._permission_timer.invalidate()
            self._permission_timer = None

    def _save_custom_words(self):
        if self._custom_words_field is None:
            return
        self._prefs.custom_words = self._custom_words_field.stringValue()

    @objc.typedSelector(b"v@:@")
    def pollPermissions_(self, timer):
        self._update_permissions()

    @objc.typedSelector(b"v@:@")
    def changeShortcut_(self, sender):
        self._shortcut_field.startCapture()

    @objc.typedSelector(b"v@:@")
    def changeRetractShortcut_(self, sender):
        self._retract_shortcut_field.startCapture()

    @objc.typedSelector(b"v@:@")
    def retractShortcutToggled_(self, sender):
        self._prefs.retract_last_dictation_enabled = sender.state() == 1
        self._refresh_retract_controls()

    @objc.typedSelector(b"v@:@")
    def micChanged_(self, sender):
        index = sender.indexOfSelectedItem()
        if index <= 0:
            self._prefs.mic_device = None
        else:
            self._prefs.mic_device = self._mic_device_ids[index]

    @objc.typedSelector(b"v@:@")
    def loginToggled_(self, sender):
        enabled = sender.state() == 1
        try:
            actual_state = launch_at_login.set_enabled(enabled)
            self._prefs.launch_at_login = actual_state
        except launch_at_login.LaunchAtLoginError as e:
            NSLog(f"Launch at login toggle failed: {e}")
            self._show_launch_at_login_error(str(e))
        finally:
            self._refresh_login_checkbox()

    @objc.typedSelector(b"v@:@")
    def updateCheckToggled_(self, sender):
        self._prefs.auto_update_check = sender.state() == 1

    def controlTextDidEndEditing_(self, notification):
        field = notification.object()
        if field == self._custom_words_field:
            self._save_custom_words()

    @objc.typedSelector(b"v@:@")
    def openAccessibility_(self, sender):
        url = NSURL.URLWithString_(
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
        )
        NSWorkspace.sharedWorkspace().openURL_(url)

    @objc.typedSelector(b"v@:@")
    def openMicrophonePrivacy_(self, sender):
        url = NSURL.URLWithString_(
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
        )
        NSWorkspace.sharedWorkspace().openURL_(url)

    def _refresh_login_checkbox(self):
        if self._login_checkbox is None:
            return

        support_error = launch_at_login.support_error()
        if support_error:
            self._login_checkbox.setEnabled_(False)
            self._login_checkbox.setState_(1 if self._prefs.launch_at_login else 0)
            return

        self._login_checkbox.setEnabled_(True)
        actual_state = launch_at_login.is_registered()
        self._prefs.launch_at_login = actual_state
        self._login_checkbox.setState_(1 if actual_state else 0)

    def _refresh_retract_controls(self):
        enabled = bool(self._prefs.retract_last_dictation_enabled)
        if self._retract_checkbox is not None:
            self._retract_checkbox.setState_(1 if enabled else 0)
        if self._retract_shortcut_field is not None:
            self._retract_shortcut_field.setEnabled_(enabled)
        if self._retract_change_btn is not None:
            self._retract_change_btn.setEnabled_(enabled)

    @objc.typedSelector(b"v@:@")
    def startSoundChanged_(self, sender):
        title = sender.titleOfSelectedItem()
        if title == "Custom...":
            self._open_custom_sound_panel(for_start=True)
            return
        self._prefs.sound_start = title
        sounds.play(title, self._prefs.start_volume)

    @objc.typedSelector(b"v@:@")
    def stopSoundChanged_(self, sender):
        title = sender.titleOfSelectedItem()
        if title == "Custom...":
            self._open_custom_sound_panel(for_start=False)
            return
        self._prefs.sound_stop = title
        sounds.play(title, self._prefs.stop_volume)

    @objc.typedSelector(b"v@:@")
    def startVolumeChanged_(self, sender):
        vol = sender.intValue() / 100.0
        self._prefs.start_volume = vol
        self._start_volume_label.setStringValue_(f"{sender.intValue()}%")
        # Play preview only on mouse-up (NSEventTypeLeftMouseUp == 2)
        event = NSApp.currentEvent()
        if event and event.type() == 2:
            sounds.play(self._prefs.sound_start, vol)

    @objc.typedSelector(b"v@:@")
    def stopVolumeChanged_(self, sender):
        vol = sender.intValue() / 100.0
        self._prefs.stop_volume = vol
        self._stop_volume_label.setStringValue_(f"{sender.intValue()}%")
        # Play preview only on mouse-up (NSEventTypeLeftMouseUp == 2)
        event = NSApp.currentEvent()
        if event and event.type() == 2:
            sounds.play(self._prefs.sound_stop, vol)

    def _open_custom_sound_panel(self, for_start: bool):
        import UniformTypeIdentifiers
        panel = NSOpenPanel.openPanel()
        allowed_types = [
            UniformTypeIdentifiers.UTType.typeWithFilenameExtension_(ext)
            for ext in ["aiff", "wav", "mp3", "m4a", "caf"]
        ]
        panel.setAllowedContentTypes_(allowed_types)
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setTitle_("Choose a sound file")

        if panel.runModal() == 1:  # NSModalResponseOK
            path = str(panel.URL().path())
            if for_start:
                self._prefs.sound_start = path
                sounds.play(path, self._prefs.start_volume)
            else:
                self._prefs.sound_stop = path
                sounds.play(path, self._prefs.stop_volume)
            self._populate_sounds()
        else:
            # User cancelled — revert dropdown to current selection
            self._populate_sounds()

    def _show_launch_at_login_error(self, message):
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Launch at login could not be updated")
        alert.setInformativeText_(message)
        alert.runModal()
