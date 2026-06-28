---
title: Extending the CLI (TUI Hooks)
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [architecture, development, cli, hermes, tui]
sources: [https://hermes-agent.nousresearch.com/docs/developer-guide/extending-the-cli]
confidence: high
---

# Extending the CLI (TUI Hooks)

Hermes exposes protected extension hooks on `HermesCLI` so wrapper CLIs can add widgets, keybindings, and layout customizations without overriding the 1000+ line `run()` method.

## Extension Points (5 Hooks)

| Hook | Purpose | Override when… |
|------|---------|----------------|
| `_get_extra_tui_widgets()` | Inject widgets into layout | You need a persistent UI element (panel, status line, mini-player) |
| `_register_extra_tui_keybindings(kb, *, input_area)` | Add keyboard shortcuts | You need hotkeys (toggle panels, transport controls, modal shortcuts) |
| `_build_tui_layout_children(**widgets)` | Full control over widget ordering | You need to reorder or wrap existing widgets (rare) |
| `process_command()` | Add custom slash commands | You need `/mycommand` handling |
| `_build_tui_style_dict()` | Custom prompt_toolkit styles | Custom colors or styling |

## Quick Start: A Wrapper CLI

```python
#!/usr/bin/env python3
"""my_cli.py — Example wrapper CLI that extends Hermes."""

from cli import HermesCLI
from prompt_toolkit.layout import FormattedTextControl, Window
from prompt_toolkit.filters import Condition


class MyCLI(HermesCLI):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._panel_visible = False

    def _get_extra_tui_widgets(self):
        """Add a toggleable info panel above the status bar."""
        cli_ref = self
        return [
            Window(
                FormattedTextControl(lambda: "📊 My custom panel content"),
                height=1,
                filter=Condition(lambda: cli_ref._panel_visible),
            ),
        ]

    def _register_extra_tui_keybindings(self, kb, *, input_area):
        """F2 toggles the custom panel."""
        cli_ref = self

        @kb.add("f2")
        def _toggle_panel(event):
            cli_ref._panel_visible = not cli_ref._panel_visible

    def process_command(self, cmd: str) -> bool:
        """Add a /panel slash command."""
        if cmd.strip().lower() == "/panel":
            self._panel_visible = not self._panel_visible
            state = "visible" if self._panel_visible else "hidden"
            print(f"Panel is now {state}")
            return True
        return super().process_command(cmd)


if __name__ == "__main__":
    cli = MyCLI()
    cli.run()
```

## Hook Reference

### `_get_extra_tui_widgets()`

Returns a list of prompt_toolkit widgets inserted between the spacer and status bar.

Use `ConditionalContainer` or `filter=Condition(...)` for toggleable widgets:

```python
def _get_extra_tui_widgets(self):
    return [
        ConditionalContainer(
            Window(FormattedTextControl("Status: connected"), height=1),
            filter=Condition(lambda: self._show_status),
        ),
    ]
```

### `_register_extra_tui_keybindings(kb, *, input_area)`

Called after Hermes registers its own keybindings, before layout is built.

```python
def _register_extra_tui_keybindings(self, kb, *, input_area):
    cli_ref = self

    @kb.add("f3")
    def _clear_input(event):
        input_area.text = ""

    @kb.add("f4")
    def _insert_template(event):
        input_area.text = "/search "
```

**Avoid conflicts** with built-in keybindings: Enter (submit), Escape+Enter (newline), Ctrl-C (interrupt), Ctrl-D (exit), Tab (auto-suggest). Function keys F2+ and Ctrl-combinations are generally safe.

### `_build_tui_layout_children(**widgets)`

Override only for full widget reordering. Most extensions should use `_get_extra_tui_widgets()`.

Parameters include: sudo_widget, secret_widget, approval_widget, clarify_widget, model_picker_widget, spinner_widget, spacer, status_bar, input_rule_top, image_bar, input_area, input_rule_bot, voice_status_bar, completions_menu.

## Running Your CLI

```bash
cd ~/.hermes/hermes-agent
source .venv/bin/activate
python my_cli.py
```

See [[hermes-creating-skills]], [[hermes-plugin-llm-access]], [[hermes-architecture]].
