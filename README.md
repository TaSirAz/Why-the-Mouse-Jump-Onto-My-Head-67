# Why-the-Mouse-Jump-Onto-My-Head-67

A customizable desktop pet for **Ubuntu / Linux Mint and Windows**. Grab a pet, throw it, watch it roll and bounce, feed it a snack, or let it keep you company while you focus. The built-in character is Naiwa; you can replace it with your own PNG or JPG.

**[Ubuntu installation, controls and troubleshooting → UBUNTU.md](UBUNTU.md)**

## Ubuntu quick start (updated source)

Install the system packages listed in the Ubuntu guide, including `python3-venv`. Download or clone this source, open its folder in Terminal, then run:

```bash
bash start.sh --setup
bash start.sh --doctor
bash start.sh
```

Setup runs once. Later launches work offline. Optionally add the app to Ubuntu's app menu with `bash start.sh --install-desktop`.

On GNOME Wayland the app uses XWayland (`xcb`): pet movement and controls work, but only XWayland windows can act as platforms. Native Wayland window positions are unavailable. No tray extension is required; the control room and pet's right-click menu expose the controls.

## Import your own character

In the control room, choose **匯入 PNG / JPG**, or drop a PNG/JPG/JPEG into it. Leave **匯入時自動去背** enabled for a plain background; use the tolerance slider to adjust how similar a colour must be to the background. Reimport the original to try a different tolerance.

- Plain backgrounds connected to the image edges are removed automatically.
- Existing PNG transparency and enclosed details are preserved.
- Complex photo backgrounds are kept with an explanation. Use a transparent PNG for a reliable cutout of a photo.
- The preview and all pet copies update together; the imported character survives restart.
- **還原預設角色** restores Naiwa. The original image is never modified.

Imports run in a worker thread, so desktop animation and dragging remain available. Input is limited to 32 MB / 24 million pixels; imported pets are cropped and stored as a bounded transparent PNG. No external model download or account is needed.

## Play

| Action | Behavior |
| --- | --- |
| Left click | Pet, hop, hearts and a reply |
| Drag and release | Throw with momentum, rotation and gravity |
| Double click | Spinning jump |
| Mouse wheel | Resize all pets |
| Right click | Control room, modes, recovery, pause and quit |
| Add pets / balls | Up to six pets and four throwable balls |
| Feed | Pets seek snacks and regain hunger / energy |
| Launch all / antigravity | Throw everything / float upward for ten seconds |
| Wander / follow / party / sleep / focus | Five behavior modes |
| Focus timer | 5 / 15 / 25 / 50 minutes, with a visible completion reminder |

Adaptive collision substeps keep fast small toys from passing through one another. Window tops are one-way platforms: pets fall onto them and can jump upward through them. Slow contacts settle; collision separation respects screen boundaries. Geometry is an approximation, particularly for overlapping windows and differently scaled monitors.

Closing the control room hides it. Use **退出** from the panel or right-click menu to quit and save. Pause stops physics, while dragging and the focus countdown remain available. Reopening the updated launcher brings the current control room forward.

## Downloads and compatibility

New builds use `Why-the-Mouse-Jump-Onto-My-Head-67-Linux-x64.tar.gz` and `Why-the-Mouse-Jump-Onto-My-Head-67-Windows-x64.zip`.

Existing [GitHub releases](https://github.com/TaSirAz/naiwa-desktop-pet/releases) retain the old Naiwa names and features. They do **not** include the new importer or setup options until a new build is published. For the changes in this source, use the source instructions above.

The original Linux binary targets Ubuntu 22.04 / 24.04 and Mint 21 / 22, x86_64. Source startup was checked on Ubuntu 26.04 GNOME / XWayland; broad distro, mixed-scaling and Windows checks are still handled by maintainers and CI. Existing Naiwa settings are copied into the renamed app on first launch without replacing newer settings or deleting the old ones.

## Windows source and packaging

Requires Python 3.10+ (3.12 recommended):

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe naiwa.py --panel
```

`naiwa.py` remains the source entry point for compatibility. Run `build.ps1` for a Windows package or `bash build-linux.sh` for a Linux package. The Linux bundle includes the Ubuntu guide and setup helper. Packaging verification uses the native desktop backend; routine development checks should cover only changed features, as described in [AGENTS.md](AGENTS.md).

The interface uses Traditional Chinese; the Ubuntu guide contains a translation of all controls. Code and asset notices: [LICENSE](LICENSE), [THIRD_PARTY.md](THIRD_PARTY.md).
