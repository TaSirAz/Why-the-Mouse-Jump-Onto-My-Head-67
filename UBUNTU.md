# Ubuntu installation and usage

**Why-the-Mouse-Jump-Onto-My-Head-67** is the new application name. The repository URL and the source entry point `naiwa.py` remain usable. The interface uses Traditional Chinese; this guide translates its controls.

## Quick start: this computer

Open a terminal in this project folder and run:

```bash
bash launch.sh
```

This chat's launcher keeps settings and imported images in the project's `data/` folder. You do not need to install the app again. For a fresh installation on another computer, use the instructions below.

## Choose an installation

| Option | Use it when | Requirements |
| --- | --- | --- |
| Updated source | You want the new collision and PNG/JPG import features now | Python 3.10+, `python3-venv`, internet for initial setup |
| Linux package built from this source | You have the new `.tar.gz` archive | x86_64 Ubuntu desktop; Python/Qt included |
| Older Naiwa release | You downloaded an existing `Naiwa-Linux-x64.tar.gz` | Follow that archive's guide; new commands/features are absent |

Linux packages target Ubuntu 22.04/24.04 and compatible Mint releases. Newer Ubuntu versions may work through XWayland but are not all tested. ARM source installations depend on availability of matching PySide6 wheels; the supplied binary is x86_64.

Use a normal logged-in graphical desktop. X11 or XWayland is required for movable desktop pets. Do not run the app with `sudo`.

## 1. Install system packages

Open Ubuntu Terminal and run:

```bash
sudo apt update
sudo apt install libegl1 libgl1 libdbus-1-3 libfontconfig1 libx11-xcb1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xinerama0 libxcb-xfixes0 libxcb-shape0 libxcb-xinput0 fonts-noto-cjk xwayland
```

The fonts package makes Chinese controls readable. These package-manager commands are the only installation steps requiring `sudo`.

## 2A. Install updated source

Install the source prerequisites:

```bash
sudo apt install python3 python3-venv git
```

Download and extract the updated source, or clone the repository:

```bash
git clone https://github.com/TaSirAz/naiwa-desktop-pet.git
cd naiwa-desktop-pet
bash start.sh --setup
bash start.sh --doctor
bash start.sh
```

If GitHub reports “Repository not found”, check that your account can access the repository. You can also use **Code → Download ZIP** in your signed-in browser, extract it, and open the extracted folder in Terminal. That folder must contain `naiwa.py`, `project_info.py`, `start.sh`, `requirements.txt` and `assets/`.

`--setup` creates `.venv` inside the project and installs pinned dependencies. Later launches work offline and do not invoke pip. Run `--setup` again after a source update changes requirements. Move the source folder before creating `.venv`; virtual environments should be recreated after moving to another path or computer. There is no system-wide pip installation. Optional AI photo removal has its own one-time setup below.

## 2B. Install a Linux package

1. Open [Releases](https://github.com/TaSirAz/naiwa-desktop-pet/releases). Download a Linux `.tar.gz` archive built from the updated source when available.
2. Extract it in Files and move the whole folder to a permanent location, such as `~/Applications/`. New packages are named **Why-the-Mouse-Jump-Onto-My-Head-67-Linux-x64.tar.gz**; older releases retain the Naiwa name.
3. Keep the executable, `_internal/`, `start.sh`, `linux_setup.py` and `project_info.py` together. Do not mix files from different releases.
4. Open that folder in Terminal and run:

```bash
bash start.sh --doctor
bash start.sh
```

The package includes Python and Qt; `--setup` does not install pip dependencies for it. The diagnostic helper uses Ubuntu's `python3`. If unavailable, install it with `sudo apt install python3`. A package has not been published merely because this guide describes its name.

## 3. Add an application-menu shortcut

From the updated source or package folder, run:

```bash
bash start.sh --install-desktop
```

Search the application menu for **Why-the-Mouse-Jump-Onto-My-Head-67**. Opening the app again brings the existing control room forward. Closing the control room hides it; quitting requires the pet's right-click menu or the tray menu. Login autostart is not enabled.

Keep the folder in place. After moving it, rerun the registration command. Launcher errors are written to `~/.local/state/WhyTheMouseJumpOntoMyHead67/launcher.log` (or `$XDG_STATE_HOME/WhyTheMouseJumpOntoMyHead67/launcher.log`).

The standard shortcut uses standard settings. To retain this chat's portable `data/` settings, continue using `bash launch.sh`.

## PNG / JPG characters and local AI foreground detection

Open the control room and choose **匯入 PNG / JPG**, or drag one PNG/JPG/JPEG file onto it. The character replaces the appearance of all pets; movement continues during processing, and a preview shows the result. Existing PNG transparency is preserved.

For real photographs, first enable local AI once from the **source** folder:

```bash
bash start.sh --setup-ai
```

This installs the optional CPU inference dependencies from `requirements-background.txt` and downloads the small U2NETP ONNX foreground model into `models/u2netp.onnx`. Internet access is required for setup; photo inference then runs offline on this computer. No photo is uploaded. Restart the app after installing dependencies. AI-enabled binary packages include the runtime and model and need no source setup.

The automatic mode uses the AI subject mask for photographic or varied backgrounds. It preserves a soft silhouette and crops empty margins. A separately selected plain-color mode is useful for illustrations; its tolerance controls how closely background colors must match. Keeping the background is also available. If AI dependencies or the model are missing, the app displays setup instructions instead of silently treating a photograph as a plain-color image.

The result is saved as a transparent PNG in application data, while the original source file is never modified. Resetting the character returns to the built-in appearance. AI segmentation can omit small details or include unwanted objects; use a clearer single-subject photo, retain the background, or import a PNG already cut out to get the desired result.

## X11, Wayland and multiple screens

| Session | Movement and screen collisions | Landing on windows |
| --- | --- | --- |
| Xorg / X11 | Supported | Visible X11 windows |
| GNOME Wayland with XWayland | Supported using Qt `xcb` | XWayland windows by default; native Wayland windows with optional bridge |
| Wayland without XWayland / `DISPLAY` | Cannot run desktop pets | Unavailable |

Check your session with `echo "$XDG_SESSION_TYPE"`. Wayland does not expose native applications' positions directly to this X11 app. The optional GNOME Shell geometry bridge below supplies read-only positions from the compositor. If your login screen offers **Ubuntu on Xorg**, choosing it enables detection of all X11 windows. Some newer Ubuntu installations do not offer that session. Use XWayland there; installing `xwayland` can require logout and login before `DISPLAY` appears.

Pets land on exposed portions of window tops, ride a moving supporting window and fall when it is minimized, closed or leaves the active workspace. Window interaction can use top platforms or solid sides according to the control-room option. The screen boundary uses the full display geometry, so pets can reach the physical display edge rather than stopping at the reserved desktop work area. Partially covered windows retain their exposed landing edges. Drag pets to another display; **全員回家** recovers pets and toys to the screen under the pointer. Screen-name matching with RandR maps collision edges into Qt coordinates on differently scaled displays; older servers fall back to the main display's scale. If a compositor reports inconsistent coordinates, disable **與視窗互動（落地 / 跟隨移動）**; screen collisions remain available.

## Optional GNOME native-window interaction

On GNOME Shell 45–50, an optional companion extension lets pets interact with native Wayland window geometry as well as XWayland windows. The pet itself continues to use XWayland for positionable transparent windows; this is not a switch to a native Wayland renderer.

From the source or updated package folder:

```bash
bash start.sh --install-gnome-bridge
```

This copies the extension into your user's GNOME extension directory and tries to enable it. GNOME may not discover a newly copied extension until you **save your work, log out, and log in**. If the helper asks for that, then run:

```bash
gnome-extensions enable window-geometry@desktoppets.local
bash start.sh --doctor
bash start.sh
```

The doctor should report **GNOME bridge: connected**. The app reads geometry asynchronously and falls back to X11 if the bridge is unavailable. Only the active workspace's unminimized windows are supplied. The service exports stable session window IDs, process IDs and frame rectangles; it exports no titles or window contents and has no methods to move, resize or control applications. It does not enable GNOME's unsafe `Eval` interface.

The extension API targets GNOME Shell 45–50; other desktops and older GNOME versions retain X11-only detection. Remove it with:

```bash
bash start.sh --remove-gnome-bridge
```

For extension load errors, use `gnome-extensions info window-geometry@desktoppets.local` and `journalctl --user -b -o cat | rg 'WindowGeometry|window-geometry'`. The implementation follows [GNOME extension lifecycle](https://gjs.guide/extensions/overview/anatomy.html), [GJS D-Bus service export](https://gjs.guide/guides/gio/dbus.html), and [Mutter's read-only frame geometry API](https://gnome.pages.gitlab.gnome.org/mutter/meta/method.Window.get_frame_rect.html).

## Controls

| Control / label | Action |
| --- | --- |
| Left click | Pet the character and make it hop |
| Drag and release | Throw it; hold still before releasing to avoid a throw |
| Double click | Spinning jump |
| Mouse wheel | Resize all pets |
| Right click → 控制室 | Open controls |
| 全員發射 | Launch every toy |
| 甜甜圈時間 / 餵甜甜圈 | Feed pets |
| 多一隻 / 增加 | Add a pet, up to six |
| 丟一顆球 | Add a throwable ball, up to four |
| 反重力 10 秒 | Float upward for ten seconds |
| 全員回家 / 找回所有桌寵 | Recover pets and toys |
| 自由翻滾 / 追著滑鼠跑 / 暴走派對 | Wander / follow pointer / party |
| 乖乖睡覺 / 專注陪伴 | Sleep / quiet focus mode |
| 開始專注 | Start the selected focus timer |
| 暫停 / 繼續 | Pause/resume physics; dragging and focus countdown still work |
| 清掉球與點心 | Remove balls and food |
| 退出 | Quit and save |

Changing modes cancels the focus timer. Completion uses tray notifications when available and otherwise opens the control room. GNOME's tray support varies; right-clicking a pet always provides controls.

## Troubleshooting

Run `bash start.sh --doctor`. It checks required shared libraries, the actual X11 connection, selected Qt backend, source Python dependencies, and the optional GNOME geometry bridge.

| Symptom | Fix |
| --- | --- |
| No X11/XWayland display | Use Terminal inside the logged-in desktop. Do not invent a `DISPLAY` value. See the session table above. |
| X11 connection failed | Use the logged-in user's terminal; check that `DISPLAY` and `XAUTHORITY` belong to that session. Avoid `sudo` and bare SSH. |
| Qt cannot load `xcb` | Install step 1's packages. `QT_DEBUG_PLUGINS=1 bash start.sh` shows the missing library. |
| `ensurepip` unavailable | Install `python3-venv`, rerun `--setup`. A custom Python needs its matching venv package. |
| Python dependencies missing | Run `bash start.sh --setup` with internet access. Avoid `sudo pip`. |
| Chinese labels show squares | Install `fonts-noto-cjk`, quit, and restart. |
| No tray icon | Use the pet's right-click menu; a tray extension is optional. |
| Menu launcher seems silent | Read the launcher log described above, or run `bash start.sh` in Terminal. |
| Pet off screen | Open controls and choose **全員回家**. |
| Pet disappears on a workspace | Return to the workspace where it was launched; GNOME controls workspace behavior. |
| Import fails / background stays | Check AI setup/model readiness, use a clear subject photo, or choose plain-color removal for an illustration. The failure notice leaves the existing character in place. |
| Packaged executable permission denied | Run `chmod +x Why-the-Mouse-Jump-Onto-My-Head-67`, then `bash start.sh`. The filesystem must permit executable files. |

## Settings, updates and removal

Normal settings are stored in `~/.local/share/DesktopPets/WhyTheMouseJumpOntoMyHead67/`, or the equivalent directory beneath `$XDG_DATA_HOME`. This contains `settings.json` and imported image copies. On the first launch after renaming, supported legacy Naiwa settings are migrated; the old directory is retained. The portable chat launcher uses the same layout inside its `data/` folder.

Quit before updating. Extract a new package into a separate folder and register its shortcut. With source updates, rerun `--setup` when requirements change. Back up the whole settings directory to retain custom characters, rather than only `settings.json`.

Remove the menu shortcut with:

```bash
bash start.sh --remove-desktop
```

Then delete the application folder if no longer needed. Standard settings remain until explicitly removed. Deleting this chat's portable folder also deletes its local settings and imported copies.

## Maintainer verification and packaging

Focused regressions can run without a desktop:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest test_physics test_pet_images test_ubuntu -q
```

The native X11 regression requires a controlled X server:

```bash
xvfb-run -a -s "-screen 0 1280x800x24" env QT_QPA_PLATFORM=xcb .venv/bin/python -m unittest test_linux_desktop -q
```

`offscreen` verifies logic only; it is not evidence of a visible desktop window. Startup screenshot verification requires `xcb` and a working graphical display. GNOME may move synthetic test windows, so Xvfb is preferable for deterministic native-window tests.

Run `bash build-linux.sh --with-ai` on an X11/XWayland desktop to install development and inference dependencies, download the model, build once, verify the packaged app and create an AI-enabled Linux archive. `bash build-linux.sh` includes AI when its runtime/model have already been installed, and otherwise produces a smaller package requiring separate source AI setup. The package includes this guide and the setup helper. CI performs packaged verification on Xvfb; that proves X11 integration. Native Wayland interaction additionally requires enabling the GNOME extension in a real GNOME session and confirming its bridge status.
