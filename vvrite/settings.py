"""Settings window for hotkey, microphone, permissions, and launch at login."""

import objc
import ApplicationServices
import os
import re
import threading
import traceback

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
    NSAlertFirstButtonReturn,
    NSWorkspace,
    NSSlider,
    NSOpenPanel,
    NSSavePanel,
    NSScrollView,
    NSTextView,
    NSMenuItem,
    NSProgressIndicator,
    NSProgressIndicatorStyleBar,
)
from Foundation import NSLog, NSURL, NSTimer

from vvrite import launch_at_login, sounds, transcriber
from vvrite.asr_models import (
    ASR_MODELS,
    OUTPUT_MODE_TRANSCRIBE,
    OUTPUT_MODE_TRANSLATE_TO_ENGLISH,
    get_model,
    is_output_mode_supported,
)
from vvrite.audio_devices import (
    get_default_input_device,
    list_input_devices,
    resolve_input_device,
)
from vvrite.download_progress import format_progress
from vvrite.locales import t, SUPPORTED_LANGUAGES
from vvrite.preferences import Preferences
from vvrite.text_replacements import format_replacements_text
from vvrite.widgets import ShortcutField, format_shortcut

SETTINGS_WINDOW_HEIGHT = 1060
SETTINGS_START_Y = SETTINGS_WINDOW_HEIGHT - 14


def normalize_custom_words_text(text: str) -> str:
    """Return comma-separated custom words from comma or line separated input."""
    words = []
    seen = set()
    for raw_word in re.split(r"[,;\r\n]+", str(text or "")):
        word = raw_word.strip()
        if not word or word in seen:
            continue
        seen.add(word)
        words.append(word)
    return ", ".join(words)


def format_custom_words_for_editor(text: str) -> str:
    """Return one custom word per line for the multiline editor."""
    normalized = normalize_custom_words_text(text)
    if not normalized:
        return ""
    return "\n".join(normalized.split(", "))


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
        self._custom_words_text_view = None
        self._replacement_rules_text_view = None
        self._start_sound_popup = None
        self._stop_sound_popup = None
        self._start_volume_slider = None
        self._stop_volume_slider = None
        self._start_volume_label = None
        self._stop_volume_label = None
        self._ui_lang_popup = None
        self._asr_lang_popup = None
        self._model_popup = None
        self._output_mode_popup = None
        self._model_status_label = None
        self._model_capability_label = None
        self._model_mode_notice = None
        self._download_model_btn = None
        self._delete_model_btn = None
        self._download_progress_bar = None
        self._download_progress_label = None
        self._model_downloading = False
        self._mic_device_signature = ()
        self._build_window()
        return self

    def _build_window(self):
        frame = NSMakeRect(0, 0, 400, SETTINGS_WINDOW_HEIGHT)
        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False,
        )
        self._window.setTitle_(t("settings.title"))
        self._window.setReleasedWhenClosed_(False)
        self._window.center()
        self._window.setDelegate_(self)

        content = self._window.contentView()
        y = SETTINGS_START_Y

        # --- Language ---
        y -= 30
        label = NSTextField.labelWithString_(t("settings.language.title"))
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 30
        ui_lang_label = NSTextField.labelWithString_(t("settings.language.ui_language"))
        ui_lang_label.setFrame_(NSMakeRect(20, y, 130, 20))
        ui_lang_label.setAlignment_(2)  # NSTextAlignmentRight
        ui_lang_label.setTextColor_(NSColor.secondaryLabelColor())
        ui_lang_label.setFont_(NSFont.systemFontOfSize_(12.0))
        content.addSubview_(ui_lang_label)

        self._ui_lang_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(156, y, 224, 24), False
        )
        self._ui_lang_popup.addItemWithTitle_(t("common.system_default"))
        for code, native_name in SUPPORTED_LANGUAGES:
            self._ui_lang_popup.addItemWithTitle_(native_name)
        # Select current value
        current_ui = self._prefs.ui_language
        if current_ui is None:
            self._ui_lang_popup.selectItemAtIndex_(0)
        else:
            selected = 0
            for i, (code, _) in enumerate(SUPPORTED_LANGUAGES):
                if code == current_ui:
                    selected = i + 1
                    break
            self._ui_lang_popup.selectItemAtIndex_(selected)
        self._ui_lang_popup.setTarget_(self)
        self._ui_lang_popup.setAction_("uiLanguageChanged:")
        content.addSubview_(self._ui_lang_popup)

        y -= 30
        asr_lang_label = NSTextField.labelWithString_(t("settings.language.asr_language"))
        asr_lang_label.setFrame_(NSMakeRect(20, y, 130, 20))
        asr_lang_label.setAlignment_(2)  # NSTextAlignmentRight
        asr_lang_label.setTextColor_(NSColor.secondaryLabelColor())
        asr_lang_label.setFont_(NSFont.systemFontOfSize_(12.0))
        content.addSubview_(asr_lang_label)

        self._asr_lang_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(156, y, 224, 24), False
        )
        self._asr_lang_popup.addItemWithTitle_(t("common.automatic"))
        for code, native_name in SUPPORTED_LANGUAGES:
            self._asr_lang_popup.addItemWithTitle_(native_name)
        # Select current value
        current_asr = self._prefs.asr_language
        if current_asr == "auto":
            self._asr_lang_popup.selectItemAtIndex_(0)
        else:
            selected = 0
            for i, (code, _) in enumerate(SUPPORTED_LANGUAGES):
                if code == current_asr:
                    selected = i + 1
                    break
            self._asr_lang_popup.selectItemAtIndex_(selected)
        self._asr_lang_popup.setTarget_(self)
        self._asr_lang_popup.setAction_("asrLanguageChanged:")
        content.addSubview_(self._asr_lang_popup)

        # --- Shortcut ---
        y -= 40
        label = NSTextField.labelWithString_(t("settings.shortcut.title"))
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 30
        self._shortcut_field = ShortcutField.alloc().initWithFrame_preferences_(
            NSMakeRect(20, y, 280, 24), self._prefs
        )
        self._shortcut_field._on_change = self._update_hotkey_display
        content.addSubview_(self._shortcut_field)

        change_btn = NSButton.alloc().initWithFrame_(NSMakeRect(310, y, 80, 24))
        change_btn.setTitle_(t("common.change"))
        change_btn.setBezelStyle_(NSBezelStyleRounded)
        change_btn.setTarget_(self)
        change_btn.setAction_("changeShortcut:")
        content.addSubview_(change_btn)

        # --- Correction ---
        y -= 40
        label = NSTextField.labelWithString_(t("settings.correction.title"))
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 30
        self._retract_checkbox = NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 360, 20))
        self._retract_checkbox.setButtonType_(NSButtonTypeSwitch)
        self._retract_checkbox.setTitle_(t("settings.correction.enable"))
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
        self._retract_change_btn.setTitle_(t("common.change"))
        self._retract_change_btn.setBezelStyle_(NSBezelStyleRounded)
        self._retract_change_btn.setTarget_(self)
        self._retract_change_btn.setAction_("changeRetractShortcut:")
        content.addSubview_(self._retract_change_btn)

        y -= 20
        hint = NSTextField.labelWithString_(
            t("settings.correction.hint")
        )
        hint.setFrame_(NSMakeRect(20, y, 360, 16))
        hint.setFont_(NSFont.systemFontOfSize_(11.0))
        hint.setTextColor_(NSColor.secondaryLabelColor())
        content.addSubview_(hint)

        # --- Microphone ---
        y -= 40
        label = NSTextField.labelWithString_(t("settings.microphone.title"))
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 30
        self._mic_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(20, y, 360, 24), False
        )
        self._populate_mics(refresh=True)
        self._mic_popup.setTarget_(self)
        self._mic_popup.setAction_("micChanged:")
        content.addSubview_(self._mic_popup)

        # --- Model ---
        y -= 40
        label = NSTextField.labelWithString_(t("settings.model.title"))
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 30
        model_label = NSTextField.labelWithString_(t("settings.model.selected_model"))
        model_label.setFrame_(NSMakeRect(20, y, 130, 20))
        model_label.setAlignment_(2)
        model_label.setTextColor_(NSColor.secondaryLabelColor())
        model_label.setFont_(NSFont.systemFontOfSize_(12.0))
        content.addSubview_(model_label)

        self._model_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(156, y, 224, 24), False
        )
        for model in ASR_MODELS.values():
            self._model_popup.addItemWithTitle_(model.display_name)
        current_model = get_model(self._prefs.asr_model_key)
        for i, model in enumerate(ASR_MODELS.values()):
            if model.key == current_model.key:
                self._model_popup.selectItemAtIndex_(i)
                break
        self._model_popup.setTarget_(self)
        self._model_popup.setAction_("asrModelChanged:")
        content.addSubview_(self._model_popup)

        y -= 30
        output_label = NSTextField.labelWithString_(t("settings.model.output_mode"))
        output_label.setFrame_(NSMakeRect(20, y, 130, 20))
        output_label.setAlignment_(2)
        output_label.setTextColor_(NSColor.secondaryLabelColor())
        output_label.setFont_(NSFont.systemFontOfSize_(12.0))
        content.addSubview_(output_label)

        self._output_mode_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(156, y, 224, 24), False
        )
        self._output_mode_popup.addItemWithTitle_(t("settings.model.mode_transcribe"))
        self._output_mode_popup.addItemWithTitle_(
            t("settings.model.mode_translate_to_english")
        )
        self._output_mode_popup.selectItemAtIndex_(
            1 if self._prefs.output_mode == OUTPUT_MODE_TRANSLATE_TO_ENGLISH else 0
        )
        self._output_mode_popup.setTarget_(self)
        self._output_mode_popup.setAction_("outputModeChanged:")
        content.addSubview_(self._output_mode_popup)

        y -= 22
        self._model_capability_label = NSTextField.labelWithString_("")
        self._model_capability_label.setFrame_(NSMakeRect(20, y, 360, 18))
        self._model_capability_label.setTextColor_(NSColor.systemOrangeColor())
        self._model_capability_label.setFont_(NSFont.systemFontOfSize_(11.0))
        content.addSubview_(self._model_capability_label)

        y -= 30
        self._model_status_label = NSTextField.labelWithString_("")
        self._model_status_label.setFrame_(NSMakeRect(20, y, 170, 20))
        self._model_status_label.setTextColor_(NSColor.secondaryLabelColor())
        self._model_status_label.setFont_(NSFont.systemFontOfSize_(11.0))
        content.addSubview_(self._model_status_label)

        self._download_model_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(200, y - 2, 82, 24)
        )
        self._download_model_btn.setTitle_(t("common.download"))
        self._download_model_btn.setBezelStyle_(NSBezelStyleRounded)
        self._download_model_btn.setTarget_(self)
        self._download_model_btn.setAction_("downloadSelectedModel:")
        content.addSubview_(self._download_model_btn)

        self._delete_model_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(292, y - 2, 88, 24)
        )
        self._delete_model_btn.setTitle_(t("settings.model.delete"))
        self._delete_model_btn.setBezelStyle_(NSBezelStyleRounded)
        self._delete_model_btn.setTarget_(self)
        self._delete_model_btn.setAction_("deleteSelectedModel:")
        content.addSubview_(self._delete_model_btn)

        y -= 24
        self._download_progress_bar = NSProgressIndicator.alloc().initWithFrame_(
            NSMakeRect(20, y, 360, 8)
        )
        self._download_progress_bar.setStyle_(NSProgressIndicatorStyleBar)
        self._download_progress_bar.setMinValue_(0.0)
        self._download_progress_bar.setMaxValue_(100.0)
        self._download_progress_bar.setHidden_(True)
        content.addSubview_(self._download_progress_bar)

        y -= 18
        self._download_progress_label = NSTextField.labelWithString_("")
        self._download_progress_label.setFrame_(NSMakeRect(20, y, 360, 16))
        self._download_progress_label.setTextColor_(NSColor.secondaryLabelColor())
        self._download_progress_label.setFont_(NSFont.systemFontOfSize_(11.0))
        content.addSubview_(self._download_progress_label)

        self._refresh_model_controls()

        # --- Custom Words ---
        y -= 40
        label = NSTextField.labelWithString_(t("settings.custom_words.title"))
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 86
        scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(20, y, 360, 78)
        )
        scroll.setHasVerticalScroller_(True)
        scroll.setAutohidesScrollers_(True)
        scroll.setBorderType_(1)

        self._custom_words_text_view = NSTextView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 360, 78)
        )
        self._custom_words_text_view.setString_(
            format_custom_words_for_editor(self._prefs.custom_words)
        )
        self._custom_words_text_view.setFont_(NSFont.systemFontOfSize_(12.0))
        self._custom_words_text_view.setDelegate_(self)
        scroll.setDocumentView_(self._custom_words_text_view)
        content.addSubview_(scroll)

        y -= 30
        import_btn = NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 90, 24))
        import_btn.setTitle_(t("settings.custom_words.import"))
        import_btn.setBezelStyle_(NSBezelStyleRounded)
        import_btn.setTarget_(self)
        import_btn.setAction_("importCustomWords:")
        content.addSubview_(import_btn)

        export_btn = NSButton.alloc().initWithFrame_(NSMakeRect(120, y, 90, 24))
        export_btn.setTitle_(t("settings.custom_words.export"))
        export_btn.setBezelStyle_(NSBezelStyleRounded)
        export_btn.setTarget_(self)
        export_btn.setAction_("exportCustomWords:")
        content.addSubview_(export_btn)

        y -= 20
        hint = NSTextField.labelWithString_(
            t("settings.custom_words.hint")
        )
        hint.setFrame_(NSMakeRect(20, y, 360, 16))
        hint.setFont_(NSFont.systemFontOfSize_(11.0))
        hint.setTextColor_(NSColor.secondaryLabelColor())
        content.addSubview_(hint)

        # --- Replacements ---
        y -= 40
        label = NSTextField.labelWithString_(t("settings.replacements.title"))
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 86
        replacement_scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(20, y, 360, 78)
        )
        replacement_scroll.setHasVerticalScroller_(True)
        replacement_scroll.setAutohidesScrollers_(True)
        replacement_scroll.setBorderType_(1)
        self._replacement_rules_text_view = NSTextView.alloc().initWithFrame_(
            NSMakeRect(0, 0, 360, 78)
        )
        self._replacement_rules_text_view.setString_(
            format_replacements_text(self._prefs.replacement_rules)
        )
        self._replacement_rules_text_view.setFont_(NSFont.systemFontOfSize_(12.0))
        self._replacement_rules_text_view.setDelegate_(self)
        replacement_scroll.setDocumentView_(self._replacement_rules_text_view)
        content.addSubview_(replacement_scroll)

        y -= 20
        hint = NSTextField.labelWithString_(t("settings.replacements.hint"))
        hint.setFrame_(NSMakeRect(20, y, 360, 16))
        hint.setFont_(NSFont.systemFontOfSize_(11.0))
        hint.setTextColor_(NSColor.secondaryLabelColor())
        content.addSubview_(hint)

        # --- Sound ---
        y -= 40
        label = NSTextField.labelWithString_(t("settings.sound.title"))
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        # Start sound row
        y -= 30
        start_label = NSTextField.labelWithString_(t("settings.sound.start"))
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
        stop_label = NSTextField.labelWithString_(t("settings.sound.stop"))
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
            t("settings.sound.hint")
        )
        hint.setFrame_(NSMakeRect(76, y, 310, 16))
        hint.setFont_(NSFont.systemFontOfSize_(11.0))
        hint.setTextColor_(NSColor.secondaryLabelColor())
        content.addSubview_(hint)

        self._populate_sounds()

        # --- Permissions ---
        y -= 40
        label = NSTextField.labelWithString_(t("settings.permissions.title"))
        label.setFrame_(NSMakeRect(20, y, 360, 20))
        label.setFont_(NSFont.boldSystemFontOfSize_(13.0))
        content.addSubview_(label)

        y -= 26
        self._acc_label = NSTextField.labelWithString_(t("settings.permissions.accessibility_checking"))
        self._acc_label.setFrame_(NSMakeRect(20, y, 250, 20))
        content.addSubview_(self._acc_label)

        acc_btn = NSButton.alloc().initWithFrame_(NSMakeRect(310, y, 70, 24))
        acc_btn.setTitle_(t("common.open"))
        acc_btn.setBezelStyle_(NSBezelStyleRounded)
        acc_btn.setTarget_(self)
        acc_btn.setAction_("openAccessibility:")
        content.addSubview_(acc_btn)

        y -= 26
        self._mic_label = NSTextField.labelWithString_(t("settings.permissions.microphone_checking"))
        self._mic_label.setFrame_(NSMakeRect(20, y, 250, 20))
        content.addSubview_(self._mic_label)

        mic_perm_btn = NSButton.alloc().initWithFrame_(NSMakeRect(310, y, 70, 24))
        mic_perm_btn.setTitle_(t("common.open"))
        mic_perm_btn.setBezelStyle_(NSBezelStyleRounded)
        mic_perm_btn.setTarget_(self)
        mic_perm_btn.setAction_("openMicrophonePrivacy:")
        content.addSubview_(mic_perm_btn)

        # --- Launch at Login ---
        y -= 40
        self._login_checkbox = NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 360, 20))
        self._login_checkbox.setButtonType_(NSButtonTypeSwitch)
        self._login_checkbox.setTitle_(t("settings.login.title"))
        self._login_checkbox.setState_(1 if self._prefs.launch_at_login else 0)
        self._login_checkbox.setTarget_(self)
        self._login_checkbox.setAction_("loginToggled:")
        content.addSubview_(self._login_checkbox)

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
            popup.addItemWithTitle_(t("settings.sound.custom"))

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

    def _mic_signature(self, devices):
        return tuple(
            (
                device.device_id,
                device.display_name,
                device.index,
                device.default_samplerate,
            )
            for device in devices
        )

    def _populate_mics(self, refresh: bool = False, devices=None):
        self._mic_popup.removeAllItems()
        if devices is None:
            devices = list_input_devices(refresh=refresh)
        self._mic_device_signature = self._mic_signature(devices)
        default_device = get_default_input_device(devices)
        default_label = t("common.system_default")
        if default_device is not None:
            default_label = f"{t('common.system_default')} ({default_device.name})"
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

    def _refresh_mics_if_changed(self):
        if self._mic_popup is None:
            return
        try:
            delegate = NSApp.delegate()
        except AttributeError:
            delegate = None
        if getattr(delegate, "_recording", False):
            return
        devices = list_input_devices(refresh=False)
        signature = self._mic_signature(devices)
        if signature != self._mic_device_signature:
            self._populate_mics(devices=devices)

    def _update_permissions(self):
        trusted = ApplicationServices.AXIsProcessTrusted()
        if trusted:
            self._acc_label.setStringValue_(t("settings.permissions.accessibility_granted"))
        else:
            self._acc_label.setStringValue_(t("settings.permissions.accessibility_not_granted"))
        self._mic_label.setStringValue_(t("settings.permissions.microphone_granted"))

    def showWindow_(self, sender):
        self._adopt_single_downloaded_model_if_unset()
        self._sync_model_controls_from_preferences()
        self._populate_mics(refresh=True)
        self._populate_sounds()
        self._window.makeKeyAndOrderFront_(sender)
        NSApp.activateIgnoringOtherApps_(True)
        self._permission_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, self, "pollPermissions:", None, True
        )

    def window(self):
        return self._window

    def windowWillClose_(self, notification):
        self._save_custom_words()
        self._save_replacement_rules()
        if self._permission_timer:
            self._permission_timer.invalidate()
            self._permission_timer = None

    def _save_custom_words(self):
        value = normalize_custom_words_text(self._custom_words_text())
        self._prefs.custom_words = value
        self._set_custom_words_text(value)

    def _custom_words_text(self) -> str:
        if self._custom_words_text_view is not None:
            return str(self._custom_words_text_view.string())
        if self._custom_words_field is not None:
            return str(self._custom_words_field.stringValue())
        return str(getattr(self._prefs, "custom_words", ""))

    def _set_custom_words_text(self, value: str):
        if self._custom_words_text_view is not None:
            self._custom_words_text_view.setString_(
                format_custom_words_for_editor(value)
            )
        elif self._custom_words_field is not None:
            self._custom_words_field.setStringValue_(value)

    def _save_replacement_rules(self):
        if self._replacement_rules_text_view is None:
            return
        value = format_replacements_text(
            str(self._replacement_rules_text_view.string())
        )
        self._prefs.replacement_rules = value
        self._replacement_rules_text_view.setString_(value)

    @objc.typedSelector(b"v@:@")
    def pollPermissions_(self, timer):
        self._update_permissions()
        self._refresh_mics_if_changed()

    def _update_hotkey_display(self):
        delegate = NSApp.delegate()
        if delegate and delegate._status_bar:
            hotkey_str = format_shortcut(
                self._prefs.hotkey_keycode, self._prefs.hotkey_modifiers
            )
            delegate._status_bar.setHotkeyDisplay_(hotkey_str)

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
    def uiLanguageChanged_(self, sender):
        index = sender.indexOfSelectedItem()
        if index == 0:
            self._prefs.ui_language = None
        else:
            code = SUPPORTED_LANGUAGES[index - 1][0]
            self._prefs.ui_language = code

        # Show restart dialog
        alert = NSAlert.alloc().init()
        alert.setMessageText_(t("settings.language.restart_message"))
        alert.addButtonWithTitle_(t("settings.language.restart_now"))
        alert.addButtonWithTitle_(t("common.later"))
        response = alert.runModal()

        # Close this window and invalidate cached settings window
        self._window.close()
        from AppKit import NSApp
        delegate = NSApp.delegate()
        if hasattr(delegate, 'invalidateSettingsWindow'):
            delegate.invalidateSettingsWindow()

        if response == NSAlertFirstButtonReturn:
            # Restart the app
            import subprocess
            from Foundation import NSBundle
            bundle = NSBundle.mainBundle().bundlePath()
            subprocess.Popen(["/usr/bin/open", "-n", bundle])
            NSApp.terminate_(None)

    @objc.typedSelector(b"v@:@")
    def asrLanguageChanged_(self, sender):
        index = sender.indexOfSelectedItem()
        if index == 0:
            self._prefs.asr_language = "auto"
        else:
            code = SUPPORTED_LANGUAGES[index - 1][0]
            self._prefs.asr_language = code

    @objc.typedSelector(b"v@:@")
    def asrModelChanged_(self, sender):
        selected_index = sender.indexOfSelectedItem()
        model = list(ASR_MODELS.values())[selected_index]
        old_key = self._prefs.asr_model_key
        self._prefs.asr_model_key = model.key
        if not is_output_mode_supported(model.key, self._prefs.output_mode):
            self._prefs.output_mode = OUTPUT_MODE_TRANSCRIBE
            self._model_mode_notice = "settings.model.translation_switched_to_transcribe"
            if self._output_mode_popup is not None:
                self._output_mode_popup.selectItemAtIndex_(0)
        else:
            self._model_mode_notice = None
        if old_key != model.key:
            self._begin_model_prepare(model.key)
        else:
            self._refresh_model_controls()

    @objc.typedSelector(b"v@:@")
    def outputModeChanged_(self, sender):
        selected_index = sender.indexOfSelectedItem()
        requested = (
            OUTPUT_MODE_TRANSLATE_TO_ENGLISH
            if selected_index == 1
            else OUTPUT_MODE_TRANSCRIBE
        )
        if is_output_mode_supported(self._prefs.asr_model_key, requested):
            self._prefs.output_mode = requested
            self._model_mode_notice = None
        else:
            self._prefs.output_mode = OUTPUT_MODE_TRANSCRIBE
            self._model_mode_notice = "settings.model.translation_switched_to_transcribe"
            sender.selectItemAtIndex_(0)
        self._refresh_model_controls()

    def _refresh_model_controls(self):
        model = get_model(self._prefs.asr_model_key)
        translation_supported = is_output_mode_supported(
            model.key, OUTPUT_MODE_TRANSLATE_TO_ENGLISH
        )
        downloaded = transcriber.is_model_cached(model.key)

        output_mode_popup = getattr(self, "_output_mode_popup", None)
        model_popup = getattr(self, "_model_popup", None)
        model_status_label = getattr(self, "_model_status_label", None)
        model_capability_label = getattr(self, "_model_capability_label", None)
        download_model_btn = getattr(self, "_download_model_btn", None)
        delete_model_btn = getattr(self, "_delete_model_btn", None)
        model_downloading = getattr(self, "_model_downloading", False)

        if output_mode_popup is not None:
            output_mode_popup.itemAtIndex_(1).setEnabled_(translation_supported)
        if model_capability_label is not None:
            capability_key = (
                self._model_mode_notice
                or (
                    "settings.model.translation_supported"
                    if translation_supported
                    else "settings.model.translation_unavailable"
                )
            )
            model_capability_label.setStringValue_(t(capability_key))
            capability_color = (
                NSColor.systemBlueColor()
                if translation_supported and self._model_mode_notice is None
                else NSColor.systemOrangeColor()
            )
            model_capability_label.setTextColor_(capability_color)
        if model_status_label is not None:
            status = (
                t("settings.model.downloaded")
                if downloaded
                else t("settings.model.not_downloaded")
            )
            model_status_label.setStringValue_(f"{status} ({model.size_hint})")
        if model_popup is not None:
            model_popup.setEnabled_(not model_downloading)
        if output_mode_popup is not None:
            output_mode_popup.setEnabled_(not model_downloading)
        if download_model_btn is not None:
            download_model_btn.setEnabled_(
                (not downloaded) and (not model_downloading)
            )
        if delete_model_btn is not None:
            delete_model_btn.setEnabled_(downloaded and (not model_downloading))

    def _model_index(self, model_key: str) -> int:
        current_model = get_model(model_key)
        for index, model in enumerate(ASR_MODELS.values()):
            if model.key == current_model.key:
                return index
        return 0

    def _sync_model_controls_from_preferences(self):
        model_popup = getattr(self, "_model_popup", None)
        output_mode_popup = getattr(self, "_output_mode_popup", None)
        if model_popup is not None:
            model_popup.selectItemAtIndex_(self._model_index(self._prefs.asr_model_key))
        if output_mode_popup is not None:
            output_mode_popup.selectItemAtIndex_(
                1
                if self._prefs.output_mode == OUTPUT_MODE_TRANSLATE_TO_ENGLISH
                else 0
            )
        self._model_mode_notice = None
        self._refresh_model_controls()

    def _adopt_single_downloaded_model_if_unset(self):
        has_saved_selection = getattr(
            self._prefs,
            "has_saved_asr_model_selection",
            None,
        )
        if has_saved_selection is None or has_saved_selection():
            return

        downloaded_models = [
            model
            for model in ASR_MODELS.values()
            if transcriber.is_model_cached(model.key)
        ]
        if len(downloaded_models) == 1:
            self._prefs.asr_model_key = downloaded_models[0].key

    @objc.typedSelector(b"v@:@")
    def downloadSelectedModel_(self, sender):
        self._begin_model_prepare(self._prefs.asr_model_key)

    def _begin_model_prepare(self, model_key: str):
        if self._model_downloading:
            return
        self._model_downloading = True
        self._set_model_download_progress(0, 0)
        self._refresh_model_controls()
        threading.Thread(
            target=self._prepare_selected_model,
            args=(model_key,),
            daemon=True,
        ).start()

    def _download_selected_model(self, model_key: str):
        self._prepare_selected_model(model_key)

    def _prepare_selected_model(self, model_key: str):
        try:
            def progress(downloaded: int, total: int):
                payload = f"{downloaded}:{total}"
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "modelDownloadProgress:",
                    payload,
                    False,
                )

            transcriber.prepare_model(model_key, progress_callback=progress)
        except Exception as e:
            details = "".join(
                traceback.format_exception(type(e), e, e.__traceback__)
            ).strip()
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "modelDownloadFailed:",
                details or str(e),
                False,
            )
            return
        finally:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "modelDownloadStateChanged:", None, False
            )

    @objc.typedSelector(b"v@:@")
    def deleteSelectedModel_(self, sender):
        alert = NSAlert.alloc().init()
        alert.setMessageText_(t("settings.model.delete_confirm_title"))
        alert.setInformativeText_(t("settings.model.delete_confirm_message"))
        alert.addButtonWithTitle_(t("settings.model.delete"))
        alert.addButtonWithTitle_(t("common.dismiss"))
        response = alert.runModal()
        if response != NSAlertFirstButtonReturn:
            return
        threading.Thread(target=self._delete_selected_model, daemon=True).start()

    def _delete_selected_model(self):
        try:
            transcriber.delete_model(self._prefs.asr_model_key)
        finally:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "modelDownloadStateChanged:", None, False
            )

    @objc.typedSelector(b"v@:@")
    def modelDownloadStateChanged_(self, _):
        self._model_downloading = False
        self._set_model_download_idle()
        self._refresh_model_controls()

    @objc.typedSelector(b"v@:@")
    def modelDownloadProgress_(self, payload):
        downloaded_str, total_str = str(payload).split(":", 1)
        self._set_model_download_progress(
            int(downloaded_str),
            int(total_str),
        )

    @objc.typedSelector(b"v@:@")
    def modelDownloadFailed_(self, error_msg):
        self._show_model_download_error(str(error_msg))

    def _set_model_download_progress(self, downloaded: int, total: int):
        if self._download_progress_bar is None or self._download_progress_label is None:
            return
        self._download_progress_bar.setHidden_(False)
        self._download_progress_label.setHidden_(False)
        self._download_progress_label.setStringValue_(
            t(
                "settings.model.downloading_progress",
                progress=format_progress(downloaded, total),
            )
        )
        if total > 0:
            self._download_progress_bar.setIndeterminate_(False)
            self._download_progress_bar.stopAnimation_(None)
            self._download_progress_bar.setDoubleValue_(
                min(100.0, (downloaded / total) * 100.0)
            )
        else:
            self._download_progress_bar.setIndeterminate_(True)
            self._download_progress_bar.startAnimation_(None)

    def _set_model_download_idle(self):
        if self._download_progress_bar is not None:
            self._download_progress_bar.stopAnimation_(None)
            self._download_progress_bar.setHidden_(True)
            self._download_progress_bar.setDoubleValue_(0.0)
        if self._download_progress_label is not None:
            self._download_progress_label.setStringValue_("")
            self._download_progress_label.setHidden_(True)

    def _show_model_download_error(self, message: str):
        alert = NSAlert.alloc().init()
        alert.setMessageText_(t("settings.model.download_failed"))
        alert.setInformativeText_(message)
        alert.addButtonWithTitle_(t("common.ok"))
        NSApp.activateIgnoringOtherApps_(True)
        alert.runModal()

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

    def controlTextDidEndEditing_(self, notification):
        field = notification.object()
        if field == self._custom_words_field:
            self._save_custom_words()

    def textDidEndEditing_(self, notification):
        if notification.object() == self._custom_words_text_view:
            self._save_custom_words()
        if notification.object() == self._replacement_rules_text_view:
            self._save_replacement_rules()

    @objc.typedSelector(b"v@:@")
    def importCustomWords_(self, sender):
        self._open_custom_words_import_panel()

    @objc.typedSelector(b"v@:@")
    def exportCustomWords_(self, sender):
        self._open_custom_words_export_panel()

    def _open_custom_words_import_panel(self):
        NSApp.activateIgnoringOtherApps_(True)
        if self._window is not None:
            self._window.makeKeyAndOrderFront_(None)

        panel = NSOpenPanel.openPanel()
        panel.setAllowedFileTypes_(["txt", "csv"])
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setTitle_(t("settings.custom_words.import_title"))

        if self._window is not None:
            panel.beginSheetModalForWindow_completionHandler_(
                self._window,
                lambda response: self._handle_custom_words_import_result(
                    response, panel
                ),
            )
            return

        self._handle_custom_words_import_result(panel.runModal(), panel)

    def _handle_custom_words_import_result(self, response, panel):
        if response != 1:  # NSModalResponseOK
            return
        path = str(panel.URL().path())
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            value = normalize_custom_words_text(f.read())
        self._prefs.custom_words = value
        self._set_custom_words_text(value)

    def _open_custom_words_export_panel(self):
        self._save_custom_words()
        NSApp.activateIgnoringOtherApps_(True)
        if self._window is not None:
            self._window.makeKeyAndOrderFront_(None)

        panel = NSSavePanel.savePanel()
        panel.setAllowedFileTypes_(["txt", "csv"])
        panel.setNameFieldStringValue_("vvrite-custom-words.txt")
        panel.setTitle_(t("settings.custom_words.export_title"))

        if self._window is not None:
            panel.beginSheetModalForWindow_completionHandler_(
                self._window,
                lambda response: self._handle_custom_words_export_result(
                    response, panel
                ),
            )
            return

        self._handle_custom_words_export_result(panel.runModal(), panel)

    def _handle_custom_words_export_result(self, response, panel):
        if response != 1:  # NSModalResponseOK
            return
        value = normalize_custom_words_text(self._custom_words_text())
        self._prefs.custom_words = value
        self._set_custom_words_text(value)
        path = str(panel.URL().path())
        with open(path, "w", encoding="utf-8") as f:
            f.write(value)
            f.write("\n")

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
        if title == t("settings.sound.custom"):
            self.performSelector_withObject_afterDelay_(
                "openStartCustomSoundPanel:", None, 0.0
            )
            return
        # If re-selecting the custom file entry, keep the full path
        current = self._prefs.sound_start
        if sounds.is_custom_path(current) and os.path.basename(current) == title:
            sounds.play(current, self._prefs.start_volume)
            return
        self._prefs.sound_start = title
        sounds.play(title, self._prefs.start_volume)

    @objc.typedSelector(b"v@:@")
    def stopSoundChanged_(self, sender):
        title = sender.titleOfSelectedItem()
        if title == t("settings.sound.custom"):
            self.performSelector_withObject_afterDelay_(
                "openStopCustomSoundPanel:", None, 0.0
            )
            return
        # If re-selecting the custom file entry, keep the full path
        current = self._prefs.sound_stop
        if sounds.is_custom_path(current) and os.path.basename(current) == title:
            sounds.play(current, self._prefs.stop_volume)
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
        NSApp.activateIgnoringOtherApps_(True)
        if self._window is not None:
            self._window.makeKeyAndOrderFront_(None)

        panel = NSOpenPanel.openPanel()
        panel.setAllowedFileTypes_(["aiff", "wav", "mp3", "m4a", "caf"])
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setTitle_(t("settings.sound.choose_file"))

        if self._window is not None:
            panel.beginSheetModalForWindow_completionHandler_(
                self._window,
                lambda response: self._handle_custom_sound_panel_result(
                    response, panel, for_start
                ),
            )
            return

        self._handle_custom_sound_panel_result(panel.runModal(), panel, for_start)

    def _handle_custom_sound_panel_result(self, response, panel, for_start: bool):
        if response == 1:  # NSModalResponseOK
            path = str(panel.URL().path())
            if for_start:
                self._prefs.sound_start = path
                sounds.play(path, self._prefs.start_volume)
            else:
                self._prefs.sound_stop = path
                sounds.play(path, self._prefs.stop_volume)

        # Rebuild the popup in both the success and cancel paths so it reflects
        # the persisted selection rather than the transient "Custom..." item.
        self._populate_sounds()

    @objc.typedSelector(b"v@:@")
    def openStartCustomSoundPanel_(self, _sender):
        self._open_custom_sound_panel(True)

    @objc.typedSelector(b"v@:@")
    def openStopCustomSoundPanel_(self, _sender):
        self._open_custom_sound_panel(False)

    def _show_launch_at_login_error(self, message):
        alert = NSAlert.alloc().init()
        alert.setMessageText_(t("settings.login.error"))
        alert.setInformativeText_(message)
        alert.runModal()
