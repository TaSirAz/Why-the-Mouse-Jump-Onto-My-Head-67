"""Run the Linux binary on X11 and verify detection of an actual external window."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from Xlib import X, Xatom, display


def main():
    executable = Path(sys.argv[1] if len(sys.argv) > 1 else "dist/Naiwa/Naiwa").resolve()
    connection = display.Display()
    window = connection.screen().root.create_window(120, 260, 550, 180, 0, X.CopyFromParent)
    window.change_property(connection.intern_atom("_NET_WM_PID"), Xatom.CARDINAL, 32, [os.getpid()])
    window.map()
    connection.sync()
    try:
        with tempfile.TemporaryDirectory(prefix="naiwa-linux-verify-") as directory:
            report_path = Path(directory) / "startup.json"
            process = subprocess.run([str(executable), "--verify-startup-report", str(report_path)],
                env={**os.environ, "QT_QPA_PLATFORM": "xcb", "QT_SCALE_FACTOR": "1"},
                capture_output=True, text=True, timeout=25)
            if not report_path.exists():
                raise RuntimeError("Linux executable failed before Qt startup: " + process.stderr[-3000:])
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if process.returncode != 0 or not report["ok"] or report["platform"] != "xcb":
                raise RuntimeError("Linux startup failed: " + json.dumps(report) + process.stderr[-2000:])
            if [120, 260, 670, 440] not in report["window_rects"]:
                raise RuntimeError("External X11 window detection failed: " + json.dumps(report))
            output = Path("verification")
            output.mkdir(exist_ok=True)
            (output / "linux-startup.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"Linux packaged startup passed: Qt {report['qt']}, xcb, pet rendering, panel, external window detection and clean exit.")
    finally:
        window.destroy()
        connection.sync()
        connection.close()


if __name__ == "__main__":
    main()
