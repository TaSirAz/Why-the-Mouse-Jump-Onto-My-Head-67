# Why-the-Mouse-Jump-Onto-My-Head-67

A customizable desktop pet for **Ubuntu / Linux Mint and Windows**. Grab a pet, throw it, watch it roll and bounce, feed it a snack, or let it keep you company while you focus. The built-in character is a hamster; you can replace it with your own PNG or JPG.

**[Ubuntu installation, controls and troubleshooting → UBUNTU.md](UBUNTU.md)**

## Ubuntu download (v1.2.0)

Download the [v1.2.0 Linux x64 archive](https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67/releases/download/v1.2.0/Why-the-Mouse-Jump-Onto-My-Head-67-Linux-x64.tar.gz) from the [v1.2.0 release](https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67/releases/tag/v1.2.0). Install the graphics/font packages listed in [UBUNTU.md](UBUNTU.md), extract the whole archive, open the extracted folder in Terminal, and run:

```bash
bash start.sh --doctor
bash start.sh
```

The Linux package includes Python, Qt, the AI runtime and the foreground model. Keep its `_internal/` directory with the executable; no pip or AI model setup is needed for this download. Source and packages remain compatible with legacy Naiwa settings.

## Ubuntu source installation

Install the system packages listed in the Ubuntu guide, including `python3-venv` and `git`, then clone the public repository:

```bash
git clone https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67.git
cd Why-the-Mouse-Jump-Onto-My-Head-67
bash start.sh --setup
bash start.sh --doctor
bash start.sh
```

For local AI subject detection, run `bash start.sh --setup-ai` once after source setup. Setup installs the optional runtime and foreground model; later launches and image imports work offline. Optionally add the app to Ubuntu's app menu with `bash start.sh --install-desktop`.

On GNOME Wayland the app uses XWayland (`xcb`), and XWayland windows act as collision platforms. The optional read-only GNOME bridge for native Wayland windows is experimental and has **not been verified**; native Wayland interaction is excluded from the v1.2.0 completion claim. See the Ubuntu guide if you want to test it. No tray extension is required; the control room and pet's right-click menu expose the controls.

## Import your own character

In the control room, choose **匯入 PNG / JPG**, or drop a PNG/JPG/JPEG into it. Default automatic removal uses **local AI subject segmentation**, including photographs and varied backgrounds. Images are processed on this computer and are never uploaded.

- Use **智慧主體去背** for photos / complex backgrounds. Existing transparent pixels remain transparent; AI can further trim the subject.
- Use **純色背景快速去背** for flat illustrations; adjust its tolerance and reimport the original.
- Turn removal off to keep an existing cutout unchanged (apart from size limits and empty-margin cropping).
- The preview and all pet copies update together; the imported character survives restart.
- **還原預設角色** restores the built-in hamster. The original image is never modified.

Imports run in a worker thread, so animation and dragging remain responsive. Input is limited to 32 MB / 24 million pixels. Source installations require one-time AI runtime/model setup; the v1.2.0 binary packages include both. Missing components produce an explicit setup message, without silently preserving the photo's background and claiming success.

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

[v1.2.0](https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67/releases/tag/v1.2.0) provides renamed Linux and Windows downloads, with PNG/JPG import, local AI foreground detection, collision fixes and setup tools. The [public repository](https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67) can be cloned or downloaded as a source ZIP without signing in.

| Platform | Download | Start |
| --- | --- | --- |
| Ubuntu / Linux Mint x64 | [Linux archive](https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67/releases/download/v1.2.0/Why-the-Mouse-Jump-Onto-My-Head-67-Linux-x64.tar.gz) | Extract the whole folder, then run `bash start.sh` |
| Windows x64 | [Windows ZIP](https://github.com/TaSirAz/Why-the-Mouse-Jump-Onto-My-Head-67/releases/download/v1.2.0/Why-the-Mouse-Jump-Onto-My-Head-67-Windows-x64.zip) | Extract the whole folder, then open `Why-the-Mouse-Jump-Onto-My-Head-67.exe` |

Both v1.2.0 packages include Python, Qt and local AI inference; no separate Python installation is needed to launch them. Keep the executable and its `_internal/` directory together. Older Naiwa releases retain their original names and features; use their own installation instructions.

The original Linux binary targets Ubuntu 22.04 / 24.04 and Mint 21 / 22, x86_64. Source startup was checked on Ubuntu 26.04 GNOME / XWayland; broad distro, mixed-scaling and Windows checks are still handled by maintainers and CI. Existing Naiwa settings are copied into the renamed app on first launch without replacing newer settings or deleting the old ones.

## Windows source and packaging

Requires Python 3.10+ (3.12 recommended):

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe naiwa.py --panel
```

`naiwa.py` remains the source entry point for compatibility. Run `build.ps1` for a Windows package or `bash build-linux.sh --with-ai` for an AI-enabled Linux package. The Linux bundle includes the Ubuntu guide and setup helper. Packaging verification uses the native desktop backend; routine development checks should cover only changed features, as described in [AGENTS.md](AGENTS.md).

The interface uses Traditional Chinese; the Ubuntu guide contains a translation of all controls. Code and asset notices: [LICENSE](LICENSE), [THIRD_PARTY.md](THIRD_PARTY.md).
