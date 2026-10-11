# Ubuntu installation and usage

**Why-the-Mouse-Jump-Onto-My-Head-67 v1.2.1** is available from the [release page](https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67/releases/tag/v1.2.1). The [Linux x64 archive](https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67/releases/download/v1.2.1/Why-the-Mouse-Jump-Onto-My-Head-67-Linux-x64.tar.gz) includes Python, Qt and local AI background removal. The public [repository](https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67) has the source; its entry point remains `naiwa.py` for compatibility. The default character is a hamster. The interface uses Traditional Chinese, and this guide translates its controls.

For the easiest fresh installation, install the system packages in step 1, then follow **2B: Linux package**. Choose **2A: source** if you want to edit or build the application.

## Choose an installation

| Option | Use it when | Requirements |
| --- | --- | --- |
| Public source | You want to edit the app or build it yourself | Python 3.10+, `python3-venv`, internet for initial setup |
| v1.2.1 Linux package | Recommended for a normal installation | x86_64 Ubuntu desktop; Python/Qt/AI included |
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
git clone https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67.git
cd Why-the-Mouse-Jump-Onto-My-Head-67
bash start.sh --setup
bash start.sh --doctor
bash start.sh
```

The repository is public; cloning or using **Code → Download ZIP** needs no GitHub sign-in. If you see “Repository not found”, check the exact new URL above. After downloading a ZIP, extract it and open the extracted folder in Terminal. That folder must contain `naiwa.py`, `project_info.py`, `start.sh`, `requirements.txt` and `assets/`.

`--setup` creates `.venv` inside the project and installs pinned dependencies. Later launches work offline and do not invoke pip. Run `--setup` again after a source update changes requirements. Move the source folder before creating `.venv`; virtual environments should be recreated after moving to another path or computer. There is no system-wide pip installation. Optional AI photo removal has its own one-time setup below.

## 2B. Install a Linux package

1. Open [v1.2.1](https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67/releases/tag/v1.2.1). Download [**Why-the-Mouse-Jump-Onto-My-Head-67-Linux-x64.tar.gz**](https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67/releases/download/v1.2.1/Why-the-Mouse-Jump-Onto-My-Head-67-Linux-x64.tar.gz).
2. Extract it in Files and move the whole folder to a permanent location, such as `~/Applications/`. The extracted directory is **Why-the-Mouse-Jump-Onto-My-Head-67**. Older releases retain the Naiwa name.
3. Keep the whole extracted directory together, including the executable, `_internal/`, launcher and setup helpers. Do not mix files from different releases.
4. Open that folder in Terminal and run:

```bash
bash start.sh --doctor
bash start.sh
```

The package includes Python and Qt; `--setup` does not install pip dependencies for it. The diagnostic helper uses Ubuntu's `python3`. If unavailable, install it with `sudo apt install python3`. The v1.2.1 Linux download includes the AI runtime and model, so neither `--setup` nor `--setup-ai` is needed. AI photo imports work offline.

## 3. Add an application-menu shortcut

From the updated source or package folder, run:

```bash
bash start.sh --install-desktop
```

Search the application menu for **Why-the-Mouse-Jump-Onto-My-Head-67**. Opening the app again brings the existing control room forward. Closing the control room hides it; quitting requires the pet's right-click menu or the tray menu. Login autostart is not enabled.

Keep the folder in place. After moving it, rerun the registration command. Launcher errors are written to `~/.local/state/WhyTheMouseJumpOntoMyHead67/launcher.log` (or `$XDG_STATE_HOME/WhyTheMouseJumpOntoMyHead67/launcher.log`).

The standard shortcut uses standard settings. If you already use a portable copy containing `launch.sh`, continue launching it with `bash launch.sh` to retain that copy's local `data/` settings.

## PNG / JPG characters and local AI foreground detection

Open the control room and choose **匯入 PNG / JPG**, or drag one PNG/JPG/JPEG file onto it. The character replaces the appearance of all pets; movement continues during processing, and a preview shows the result. Existing PNG transparency is preserved.

For real photographs, first enable local AI once from the **source** folder:

```bash
bash start.sh --setup-ai
```

This installs the optional CPU inference dependencies from `requirements-background.txt` and downloads the small U2NETP ONNX foreground model into `models/u2netp.onnx`. Internet access is required for setup; photo inference then runs offline on this computer. No photo is uploaded. Restart the app after installing dependencies. AI-enabled binary packages include the runtime and model and need no source setup.

The automatic mode uses the AI subject mask for photographic or varied backgrounds. It preserves a soft silhouette and crops empty margins. A separately selected plain-color mode is useful for illustrations; its tolerance controls how closely background colors must match. Keeping the background is also available. If AI dependencies or the model are missing, the app displays setup instructions instead of silently treating a photograph as a plain-color image.

The result is saved as a transparent PNG in application data, while the original source file is never modified. Resetting the character returns to the built-in hamster. AI segmentation can omit small details or include unwanted objects; use a clearer single-subject photo, retain the background, or import a PNG already cut out to get the desired result.

## X11, Wayland and multiple screens

| Session | Movement and screen collisions | Landing on windows |
| --- | --- | --- |
| Xorg / X11 | Supported | Visible X11 windows |
| GNOME Wayland with XWayland | Supported using Qt `xcb` | XWayland windows; native windows when the optional GNOME bridge is connected |
| KDE Plasma Wayland with XWayland | Uses Qt `xcb` | XWayland windows only; the GNOME bridge does not support KDE |
| Wayland without XWayland / `DISPLAY` | Cannot run desktop pets | Unavailable |

Check your session with `echo "$XDG_SESSION_TYPE"`. Wayland does not expose native applications' positions directly to this X11 app. The optional GNOME Shell geometry bridge below supplies native-window positions after it is enabled and connected. If your login screen offers **Ubuntu on Xorg**, choosing it enables detection of all X11 windows. Some newer Ubuntu installations do not offer that session. Use XWayland there; installing `xwayland` can require logout and login before `DISPLAY` appears.

Pets land on exposed portions of window tops, ride a moving supporting window and fall when it is minimized, closed or leaves the active workspace. Window interaction can use top platforms or solid sides according to the control-room option. The screen boundary uses the full display geometry, so pets can reach the physical display edge rather than stopping at the reserved desktop work area. Partially covered windows retain their exposed landing edges. Drag pets to another display; **全員回家** recovers pets and toys to the screen under the pointer. Screen-name matching with RandR maps collision edges into Qt coordinates on differently scaled displays; older servers fall back to the main display's scale. If a compositor reports inconsistent coordinates, disable **與視窗互動（落地 / 跟隨移動）**; screen collisions remain available.

## Optional GNOME native-window interaction

The companion extension targets **GNOME Shell 45–50**. It exports read-only native Wayland and XWayland window geometry from GNOME; it does not support KDE Plasma or other compositors. The pet itself still uses XWayland for movable transparent windows. **Live GNOME Wayland verification is still pending.**

From the source or updated package folder, install its files:

```bash
bash start.sh --install-gnome-bridge
```

A successful installation message confirms that files were copied, not that GNOME loaded the extension. On a **first installation**, save your work, **log out and log back in** so GNOME discovers the new extension. GNOME Shell 50 has no supported D-Bus method to load a newly copied local extension immediately; `ReloadExtension` is deprecated and does not provide that step.

After logging back in, open a terminal in the application folder and run:

```bash
gnome-extensions enable window-geometry@desktoppets.local
bash start.sh --doctor
```

The diagnostic must report **GNOME bridge: connected**. An installed directory or a successful enable command alone is not proof that the geometry service is available. If the app is already running, it reconnects automatically within about five seconds; **do not restart it just to connect the bridge**. If the app is not running after login, launch it normally with `bash start.sh`.

The app reads geometry asynchronously. When the bridge is unavailable, or differently scaled monitors cannot be mapped safely to Qt screen coordinates, it falls back to X11/XWayland-only detection and shows the corresponding status. Native-window interaction requires a connected bridge and usable monitor mappings; the app does not guess unmatched coordinates. Only the active workspace's unminimized windows are supplied.

The service exports stable session window IDs, process IDs and frame rectangles. It exports no titles or window contents and has no methods to move, resize or control applications. It does not enable GNOME's unsafe `Eval` interface.

Remove the optional extension with:

```bash
bash start.sh --remove-gnome-bridge
```

For load errors, use `gnome-extensions info window-geometry@desktoppets.local` and `journalctl --user -b -o cat | rg 'WindowGeometry|window-geometry'`. Confirm the version with `gnome-shell --version`. The implementation follows [GNOME extension lifecycle](https://gjs.guide/extensions/overview/anatomy.html), [GJS D-Bus service export](https://gjs.guide/guides/gio/dbus.html), and [Mutter's read-only frame geometry API](https://gnome.pages.gitlab.gnome.org/mutter/meta/method.Window.get_frame_rect.html). The first-install limitation is defined in [GNOME Shell 50.1's extension manager](https://github.com/GNOME/gnome-shell/blob/50.1/js/ui/extensionSystem.js) and [D-Bus implementation](https://github.com/GNOME/gnome-shell/blob/50.1/js/ui/shellDBus.js).

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

Normal settings are stored in `~/.local/share/DesktopPets/WhyTheMouseJumpOntoMyHead67/`, or the equivalent directory beneath `$XDG_DATA_HOME`. This contains `settings.json` and imported image copies. On the first launch after renaming, supported legacy Naiwa settings are migrated; the old directory is retained. Portable copies using `launch.sh` use the same layout inside their `data/` folder.

Quit before updating. Extract a new package into a separate folder and register its shortcut. With source updates, rerun `--setup` when requirements change. Back up the whole settings directory to retain custom characters, rather than only `settings.json`.

Remove the menu shortcut with:

```bash
bash start.sh --remove-desktop
```

Then delete the application folder if no longer needed. Standard settings remain until explicitly removed. Deleting a portable application folder also deletes any local `data/` settings and imported copies inside it.

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

Run `bash build-linux.sh --with-ai` on an X11/XWayland desktop to install development and inference dependencies, download the model, build once, verify the packaged app and create an AI-enabled Linux archive. `bash build-linux.sh` includes AI when its runtime/model have already been installed, and otherwise produces a smaller package requiring separate source AI setup. The package includes this guide and the setup helper. CI performs packaged verification on Xvfb; that proves X11 integration. Live GNOME Wayland verification is still pending. It requires a real GNOME session, a connected bridge and usable monitor mappings; Xvfb cannot demonstrate that native interaction.
