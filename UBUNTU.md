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

`--setup` creates `.venv` inside the project and installs pinned dependencies. Later launches work offline and do not invoke pip. Run `--setup` again after a source update changes requirements. Move the source folder before creating `.venv`; virtual environments should be recreated after moving to another path or computer. There is no system-wide pip installation and no external AI model download for image background removal.

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

## PNG / JPG characters and automatic background removal

Open the control room and choose **匯入 PNG / JPG**, or drag a single PNG/JPG/JPEG file onto the control room. The imported character replaces the appearance of all pets; their movement and controls continue to work. A preview appears in the control room.

- **匯入時自動去背（純色背景）** enables automatic removal of a near-uniform background connected to the image border.
- **去背容差** controls how closely pixels must match that background. Increase it for slight color variations; reimport the original image to apply a different tolerance.
- Existing transparent PNGs keep their transparency. JPGs are converted into transparent PNGs after removal. Empty margins are cropped.
- Busy photographic backgrounds may be kept with an explanatory notice. This feature works best with a single subject on a plain background. Disable automatic removal if it removes part of the subject.
- Use the reset character button to return to the built-in character. Your original image file is never overwritten. Imported copies are stored with application settings and remain available after restart.

## X11, Wayland and multiple screens

| Session | Movement and screen collisions | Landing on windows |
| --- | --- | --- |
| Xorg / X11 | Supported | Visible X11 windows |
| GNOME Wayland with XWayland | Supported using Qt `xcb` | XWayland windows only |
| Wayland without XWayland / `DISPLAY` | Cannot run desktop pets | Unavailable |

Check your session with `echo "$XDG_SESSION_TYPE"`. Wayland does not expose native applications' positions to this X11 app. If your login screen offers **Ubuntu on Xorg**, choosing it enables detection of all X11 windows. Some newer Ubuntu installations do not offer that session. Use XWayland there; installing `xwayland` can require logout and login before `DISPLAY` appears.

Pets land on exposed portions of window tops and fall when their support is moved or removed. Partially covered windows retain their exposed landing edges. Drag pets to another display; **全員回家** recovers pets and toys to the screen under the pointer. Screen-name matching with RandR maps collision edges into Qt coordinates on differently scaled displays; older servers fall back to the main display's scale. If a compositor reports inconsistent coordinates, disable **在其他視窗頂端落地 / 翻滾**; screen collisions remain available.

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

Run `bash start.sh --doctor`. It checks required shared libraries, the actual X11 connection, selected Qt backend and source Python dependencies.

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
| Import fails / background stays | Use one supported image, plain background, and adjust tolerance. The failure notice leaves the existing character in place. |
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

Run `bash build-linux.sh` on an X11/XWayland desktop to install development dependencies, build once, verify the packaged app and create the new Linux archive. The package includes this guide and the setup helper. CI performs packaged verification on Xvfb; that proves X11 integration, not native Wayland window support.
