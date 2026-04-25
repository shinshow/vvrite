"""vvrite macOS app — entry point."""

import os
import sys
import time
import threading

os.environ["TOKENIZERS_PARALLELISM"] = "false"

import objc
from AppKit import (
    NSApplication,
    NSApp,
    NSObject,
    NSApplicationActivationPolicyAccessory,
    NSAlert,
    NSAlertFirstButtonReturn,
    NSWorkspace,
)
from AppKit import NSTimer
from Foundation import NSLog, NSURL
import ApplicationServices

from vvrite import __version__, APP_BUNDLE_IDENTIFIER
from vvrite.locales import t
from vvrite.preferences import Preferences
from vvrite.status_bar import StatusBarController
from vvrite.hotkey import HotkeyManager
from vvrite.overlay import OverlayController
from vvrite.onboarding import OnboardingWindowController
from vvrite import transcriber, sounds, updater
from vvrite.recorder import Recorder
from vvrite.clipboard import paste_and_restore, retract_text


class AppDelegate(NSObject):
    def init(self):
        self = objc.super(AppDelegate, self).init()
        if self is None:
            return None
        self._prefs = Preferences()
        self._recorder = Recorder()
        self._recording = False
        self._lock = threading.Lock()
        self._overlay = None
        self._status_bar = None
        self._hotkey = None
        self._settings_wc = None
        self._load_retries = 0
        self._onboarding_wc = None
        self._available_update = None  # (tag, release) tuple when update found
        self._last_dictation_text = None
        return self

    def applicationDidFinishLaunching_(self, notification):
        # Initialize locale before any UI construction
        from vvrite.locales import set_locale, resolve_system_locale
        ui_lang = self._prefs.ui_language
        if ui_lang is None:
            ui_lang = resolve_system_locale()
        set_locale(ui_lang)

        self._status_bar = StatusBarController.alloc().initWithDelegate_(self)
        self._overlay = OverlayController.alloc().init()

        if not self._prefs.onboarding_completed or not transcriber.is_model_cached(self._prefs.asr_model_key):
            self._prefs.onboarding_completed = False
            self._onboarding_wc = (
                OnboardingWindowController.alloc()
                .initWithPreferences_statusBar_onComplete_(
                    self._prefs,
                    self._status_bar,
                    self._onboarding_finished,
                )
            )
            self._onboarding_wc.show()
        else:
            self._check_permissions()

    def _onboarding_finished(self):
        """Called when onboarding wizard completes."""
        self._hotkey = HotkeyManager(self)
        self._status_bar.setStatus_("ready")
        NSLog("vvrite ready.")
        self._maybe_check_for_updates()

    def _check_permissions(self):
        """Check all permissions and prompt user step by step."""
        import AVFoundation

        ax_ok = ApplicationServices.AXIsProcessTrustedWithOptions(
            {ApplicationServices.kAXTrustedCheckOptionPrompt: False}
        )
        mic_status = AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(
            AVFoundation.AVMediaTypeAudio
        )
        mic_ok = mic_status == 3  # Authorized

        if ax_ok and mic_ok:
            self._all_permissions_granted()
            return

        # Build permission prompt
        missing = []
        if not ax_ok:
            missing.append(t("alerts.permissions_required.accessibility"))
        if not mic_ok:
            missing.append(t("alerts.permissions_required.microphone"))

        alert = NSAlert.alloc().init()
        alert.setMessageText_(t("alerts.permissions_required.title"))
        alert.setInformativeText_(
            t("alerts.permissions_required.message", permissions="\n".join(missing))
        )
        alert.addButtonWithTitle_(t("common.grant"))
        alert.runModal()

        # Request accessibility first if needed
        if not ax_ok:
            ApplicationServices.AXIsProcessTrustedWithOptions(
                {ApplicationServices.kAXTrustedCheckOptionPrompt: True}
            )

        # Request microphone if needed
        if not mic_ok and mic_status == 0:  # NotDetermined
            AVFoundation.AVCaptureDevice.requestAccessForMediaType_completionHandler_(
                AVFoundation.AVMediaTypeAudio, lambda granted: None
            )

        # Poll until all permissions granted
        self._status_bar.setStatus_("waiting_permissions")
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, self, "pollPermissions:", None, True
        )

    @objc.typedSelector(b"v@:@")
    def pollPermissions_(self, timer):
        import AVFoundation
        ax_ok = ApplicationServices.AXIsProcessTrustedWithOptions(
            {ApplicationServices.kAXTrustedCheckOptionPrompt: False}
        )
        mic_ok = AVFoundation.AVCaptureDevice.authorizationStatusForMediaType_(
            AVFoundation.AVMediaTypeAudio
        ) == 3
        if ax_ok and mic_ok:
            timer.invalidate()
            self._all_permissions_granted()

    def _all_permissions_granted(self):
        self._status_bar.setStatus_("loading_model")
        threading.Thread(target=self._load_model, daemon=True).start()

    def _load_model(self):
        try:
            transcriber.load(self._prefs)
        except Exception as e:
            NSLog(f"Model load failed: {e}")
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "showModelError:", str(e), True
            )
            return

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "modelDidLoad:", None, False
        )

    @objc.typedSelector(b"v@:@")
    def showModelError_(self, error_msg):
        self._load_retries += 1
        if self._load_retries > 3:
            self._status_bar.setStatus_("error_model")
            return
        alert = NSAlert.alloc().init()
        alert.setMessageText_(t("alerts.model_failed.title"))
        alert.setInformativeText_(str(error_msg))
        alert.addButtonWithTitle_(t("common.retry"))
        alert.addButtonWithTitle_(t("common.dismiss"))
        response = alert.runModal()
        if response == NSAlertFirstButtonReturn:
            threading.Thread(target=self._load_model, daemon=True).start()
        else:
            self._status_bar.setStatus_("error_model")

    @objc.typedSelector(b"v@:@")
    def modelDidLoad_(self, _):
        self._hotkey = HotkeyManager(self)
        self._status_bar.setStatus_("ready")
        NSLog("vvrite ready.")
        self._maybe_check_for_updates()

    def toggleRecording(self):
        with self._lock:
            if not self._recording:
                self._start_recording()
            else:
                self._stop_recording()

    def _start_recording(self):
        self._recording = True
        sounds.play(self._prefs.sound_start, self._prefs.start_volume)

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "showRecordingUI:", None, False
        )

        def level_cb(level):
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "updateRecordingLevel:", float(level), False
            )

        try:
            self._recorder.start(
                device=self._prefs.mic_device,
                level_callback=level_cb,
            )
        except RuntimeError as e:
            self._recording = False
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "showErrorUI:", str(e), False
            )

    def _stop_recording(self):
        self._recording = False
        sounds.play(self._prefs.sound_stop, self._prefs.stop_volume)

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "showTranscribingUI:", None, False
        )

        try:
            raw_path = self._recorder.stop()
        except RuntimeError as e:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "showErrorUI:", str(e), False
            )
            return

        if raw_path is None:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "transcriptionComplete:", None, False
            )
            return

        threading.Thread(
            target=self._transcribe_and_paste,
            args=(raw_path,),
            daemon=True,
        ).start()

    def _transcribe_and_paste(self, raw_path: str):
        try:
            text = transcriber.transcribe(raw_path, self._prefs)
            if text:
                paste_and_restore(text)
                self._last_dictation_text = text
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "transcriptionComplete:", text, False
                )
            else:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    "transcriptionComplete:", None, False
                )
        except Exception as e:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "showErrorUI:", str(e), False
            )

    # --- UI update selectors (must run on main thread) ---

    @objc.typedSelector(b"v@:@")
    def showRecordingUI_(self, _):
        self._overlay.showRecording()
        self._status_bar.setStatus_("recording")
        self._status_bar.setRecording_(True)

    @objc.typedSelector(b"v@:@")
    def updateRecordingLevel_(self, level):
        self._overlay._current_level = float(level)

    @objc.typedSelector(b"v@:@")
    def showTranscribingUI_(self, _):
        self._overlay.showTranscribing()
        self._status_bar.setStatus_("transcribing")
        self._status_bar.setRecording_(False)

    @objc.typedSelector(b"v@:@")
    def showErrorUI_(self, message):
        self._overlay.showError_(str(message))
        self._status_bar.setStatus_("ready")
        self._status_bar.setRecording_(False)

    @objc.typedSelector(b"v@:@")
    def transcriptionComplete_(self, text):
        self._overlay.dismiss()
        self._status_bar.setStatus_("ready")

    def cancelRecording(self):
        """Cancel recording: stop mic, discard audio, dismiss overlay."""
        with self._lock:
            if not self._recording:
                return
            self._recording = False

        try:
            raw_path = self._recorder.stop()
            if raw_path:
                try:
                    os.unlink(raw_path)
                except OSError:
                    pass
        except RuntimeError:
            pass

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "dismissAndResetUI:", None, False
        )

    @objc.typedSelector(b"v@:@")
    def dismissAndResetUI_(self, _):
        self._overlay.dismiss()
        self._status_bar.setStatus_("ready")
        self._status_bar.setRecording_(False)

    def retractLastDictation(self):
        text = self._last_dictation_text
        if (
            not self._prefs.retract_last_dictation_enabled
            or not text
            or self._recording
        ):
            return

        if retract_text(text):
            self._last_dictation_text = None

    # --- Update check ---

    def _maybe_check_for_updates(self):
        """Auto-check for updates if enabled and cooldown has passed."""
        if not self._prefs.auto_update_check:
            return
        if not updater.should_check(self._prefs.last_update_check):
            return
        threading.Thread(target=self._check_for_updates, daemon=True).start()

    def _check_for_updates(self):
        """Background: fetch latest release and compare versions."""
        self._prefs.last_update_check = time.time()
        release = updater.fetch_latest_release()
        if release is None:
            return
        tag = release.get("tag_name", "")
        if updater.is_newer(tag, __version__):
            self._available_update = (tag, release)
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "updateCheckComplete:", tag, False
            )

    def _check_for_updates_manual(self):
        """Background: manual check (no cooldown), shows 'up to date' if none."""
        self._prefs.last_update_check = time.time()
        release = updater.fetch_latest_release()
        if release and updater.is_newer(release.get("tag_name", ""), __version__):
            tag = release["tag_name"]
            self._available_update = (tag, release)
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "updateCheckComplete:", tag, False
            )
        else:
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "showUpToDate:", None, False
            )

    @objc.typedSelector(b"v@:@")
    def updateCheckComplete_(self, tag):
        """Main thread: update menu and show alert."""
        self._status_bar.setUpdateAvailable_(str(tag))
        self._show_update_alert()

    @objc.typedSelector(b"v@:@")
    def showUpToDate_(self, _):
        alert = NSAlert.alloc().init()
        alert.setMessageText_(t("alerts.no_updates.title"))
        alert.setInformativeText_(t("alerts.no_updates.message", version=__version__))
        alert.addButtonWithTitle_(t("common.ok"))
        alert.runModal()

    def checkForUpdates(self):
        """Called from menu bar item click."""
        if self._available_update:
            self._show_update_alert()
        else:
            threading.Thread(target=self._check_for_updates_manual, daemon=True).start()

    def _show_update_alert(self):
        if not self._available_update:
            return
        tag, release = self._available_update
        body = release.get("body", "") or ""
        # Truncate long release notes
        if len(body) > 500:
            body = body[:500] + "..."

        alert = NSAlert.alloc().init()
        alert.setMessageText_(t("alerts.update_available.title", version=tag))
        info = t("alerts.update_available.message", current_version=__version__)
        if body:
            info += f"\n\n{body}"
        alert.setInformativeText_(info)
        alert.addButtonWithTitle_(t("common.download"))
        alert.addButtonWithTitle_(t("common.later"))
        response = alert.runModal()
        if response == NSAlertFirstButtonReturn:
            self._open_external_url(updater.release_page_url(release))

    def _open_external_url(self, url: str) -> bool:
        if not url:
            return False
        ns_url = NSURL.URLWithString_(url)
        if ns_url is None:
            return False
        return bool(NSWorkspace.sharedWorkspace().openURL_(ns_url))

    @objc.typedSelector(b"v@:@")
    def openExternalURL_(self, url):
        self._open_external_url(str(url))

    def openSettings(self):
        from vvrite.settings import SettingsWindowController
        if self._settings_wc is None:
            self._settings_wc = SettingsWindowController.alloc().initWithPreferences_(self._prefs)
        self._settings_wc.showWindow_(None)
        self._settings_wc.window().makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

    def invalidateSettingsWindow(self):
        """Force settings window to be recreated (after language change)."""
        self._settings_wc = None


def main():
    # Single-instance check: exit immediately if already running
    from AppKit import NSRunningApplication
    running = NSRunningApplication.runningApplicationsWithBundleIdentifier_(
        APP_BUNDLE_IDENTIFIER
    )
    my_pid = os.getpid()
    for r in running:
        if r.processIdentifier() != my_pid:
            sys.exit(0)

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    main()
