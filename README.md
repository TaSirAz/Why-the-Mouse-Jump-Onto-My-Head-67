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

For local AI subject detection, run `bash start.sh --setup-ai` once after source setup. Setup installs the optional runtime and foreground model; later launches and image imports work offline. Optionally add the app to Ubuntu's app menu with `bash start.sh --install-desktop`.

On GNOME Wayland the app uses XWayland (`xcb`). An optional read-only GNOME bridge adds native Wayland window interaction; without it, only XWayland windows act as platforms. Install the bridge with `bash start.sh --install-gnome-bridge`, then follow the guide to reload the session and enable it. No tray extension is required; the control room and pet's right-click menu expose the controls.

## Import your own character

In the control room, choose **匯入 PNG / JPG**, or drop a PNG/JPG/JPEG into it. Default automatic removal uses **local AI subject segmentation**, including photographs and varied backgrounds. Images are processed on this computer and are never uploaded.

- Use **智慧主體去背** for photos / complex backgrounds. Existing transparent pixels remain transparent; AI can further trim the subject.
- Use **純色背景快速去背** for flat illustrations; adjust its tolerance and reimport the original.
- Turn removal off to keep an existing cutout unchanged (apart from size limits and empty-margin cropping).
- The preview and all pet copies update together; the imported character survives restart.
- **還原預設角色** restores Naiwa. The original image is never modified.

Imports run in a worker thread, so animation and dragging remain responsive. Input is limited to 32 MB / 24 million pixels. The AI runtime and small U2NETP model require a one-time setup; missing components produce an explicit setup message, without silently preserving the photo's background and claiming success.

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

Contacts are tracked so standing or sustained contact does not generate repeated HIT counts or inject spin. Adaptive collision substeps keep fast small toys from passing through one another. Window tops are one-way platforms: pets fall onto them and can jump upward through them. Slow contacts settle; collision separation respects the rotated visible alpha outline. Ubuntu pet windows bypass GNOME work-area placement, so the visible character can touch the physical screen edges. Pets ride supporting windows while they move and fall when the window closes or minimizes; optional side/underside collisions add rebounds. Geometry is an approximation, particularly for overlapping windows and differently scaled monitors.

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
