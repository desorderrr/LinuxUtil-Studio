# App logos

The SVGs in this folder come from [Simple Icons](https://simpleicons.org)
(release 15.x), which is released under **CC0 1.0 Universal** — see
<https://github.com/simple-icons/simple-icons/blob/master/LICENSE.md>.

They are vendored here on purpose, so the app never needs network access to
show an icon.

Every logo is the trademark of its respective owner. They are used only to
identify the application being installed, which is a normal, nominative use.
No endorsement is implied.

## Format

- One file per catalogue `id`: `assets/logos/<id>.svg`.
- Simple Icons offers a single-colour glyph; the brand colour lives in the
  SVG's `fill` attribute, so it also tells the UI which tile colour to use
  (light tile for dark logos, dark tile for light ones).

Missing a logo? No problem: `ui/icons.py` falls back to the desktop icon theme
and then to a tile with the app's initials.
