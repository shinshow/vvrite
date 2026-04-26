# Settings Sidebar Layout Design

## Goal

Make the vvrite settings window usable on smaller Mac screens, including a
14-inch MacBook Pro, without hiding controls below the visible display area.
The window should stay compact and predictable even as more settings are added.

## Current Problem

`SettingsWindowController` builds one fixed-height, single-column window:

- Window size is `400 x 1160`.
- Controls are manually positioned from top to bottom.
- Only the custom words and replacements text editors are scroll views.
- The overall settings window does not scroll.

On smaller displays, the bottom of the window can be unreachable, so controls
such as permissions, launch at login, or later sections can be hard to select.

## Recommended Layout

Use a two-pane settings window:

- Left sidebar: category list.
- Right pane: settings for the selected category.
- Right pane content is scrollable when needed.
- Window target size: about `640 x 660`, with a practical minimum size near
  `600 x 560`.

This follows the macOS settings pattern and prevents the window height from
growing whenever a new feature adds settings.

## Categories

The initial categories should be:

- General
  - UI language
  - Launch at login
  - Automatic update check
- Recording
  - Primary hotkey
  - Microphone
  - Accessibility and microphone permission status/actions
- Model
  - ASR model
  - Transcription vs English translation output mode
  - Download/delete model controls and download progress
- Output
  - Lightweight output mode
  - Custom words
  - Replacement rules
- Sound
  - Start sound
  - Stop sound
  - Start/stop volume
- Advanced
  - Delete-by-keystroke/retract shortcut controls

## Behavior

Opening settings selects `General` by default.

Selecting a sidebar item replaces the right pane content with that category's
controls. Existing control behavior should not change: actions such as
`uiLanguageChanged:`, `asrModelChanged:`, `modeChanged:`, custom word import,
sound selection, permission refresh, and model download should continue to use
the current preference and controller methods.

Each category panel should be built in a scrollable content view. Most panels
will fit without scrolling, but `Model` and `Output` can scroll if localized
strings or model status text make the content taller.

The settings window should not depend on a height larger than a laptop screen.
It should be centered and remain usable without resizing.

## Implementation Shape

Keep `SettingsWindowController` as the owner of the window and action methods,
but split UI construction into smaller helpers:

- `_build_window()`
  - Create the fixed-size window.
  - Create sidebar container.
  - Create right-side scroll view.
  - Select the default category.
- `_build_sidebar(content)`
  - Add category buttons or a table/list.
  - Store category keys and selected state.
- `_show_settings_category_(category_key)`
  - Clear the right pane.
  - Call the matching category builder.
- Category builders:
  - `_build_general_panel(content, y)`
  - `_build_recording_panel(content, y)`
  - `_build_model_panel(content, y)`
  - `_build_output_panel(content, y)`
  - `_build_sound_panel(content, y)`
  - `_build_advanced_panel(content, y)`

The existing manual frame style can remain initially. This keeps the change
focused and avoids introducing Auto Layout into a file that currently does not
use it.

## Data Flow

The sidebar only changes which controls are visible. Preferences remain stored
in `Preferences`, and all existing actions continue writing to the same
properties.

When a category is shown, its controls should be initialized from current
preferences. When the settings window is shown again, refresh behavior should
still run for model state, microphones, and sounds.

## Testing

Add focused tests for:

- Settings window height is small-screen friendly.
- Sidebar categories are present in the expected order.
- Selecting a category rebuilds the right pane without crashing.
- Existing action tests still pass.
- UI smoke still constructs `SettingsWindowController` and `OverlayController`.

Retain existing tests for model controls, sound controls, custom words,
replacement rules, locale completeness, and preferences.

Manual verification after implementation:

- Build settings UI smoke command.
- Open the app or local build on a small screen.
- Confirm every category is reachable without the window exceeding display
  height.

## Non-Goals

- Do not redesign app onboarding.
- Do not change preference keys or migration behavior.
- Do not change transcription, model download, or hotkey behavior.
- Do not add new settings in this layout pass.
- Do not introduce a new design framework.

## Risks

The main risk is breaking existing settings actions while moving controls into
category builders. Keep action methods unchanged and move only control creation
where possible.

Another risk is hiding controls that currently refresh when the window opens.
The implementation should refresh shared state before or during category
rendering, and category builders should tolerate controls being absent when a
different category is selected.
