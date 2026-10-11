import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const NAME = 'org.desktoppets.WindowGeometry';
const PATH = '/org/desktoppets/WindowGeometry';
const XML = `<node><interface name="${NAME}">
  <method name="GetWindows">
    <arg type="i" direction="in" name="excludedPid"/>
    <arg type="s" direction="in" name="screenNamesJson"/>
    <arg type="s" direction="out" name="snapshot"/>
  </method>
</interface></node>`;

export default class WindowGeometryExtension extends Extension {
    enable() {
        this._session = GLib.uuid_string_random();
        this._object = Gio.DBusExportedObject.wrapJSObject(XML, this);
        this._object.export(Gio.DBus.session, PATH);
        this._owner = Gio.bus_own_name_on_connection(
            Gio.DBus.session, NAME, Gio.BusNameOwnerFlags.NONE, null, null);
    }

    disable() {
        if (this._owner) {
            Gio.bus_unown_name(this._owner);
            this._owner = 0;
        }
        this._object?.unexport();
        this._object = null;
    }

    GetWindows(excludedPid, screenNamesJson) {
        let names = [];
        try {
            const input = JSON.parse(screenNamesJson);
            if (Array.isArray(input))
                names = input.filter(name => typeof name === 'string').slice(0, 64);
        } catch (_error) { /* Diagnostic callers may omit connector names. */ }
        const manager = global.backend.get_monitor_manager();
        const monitors = [];
        for (let index = 0; index < global.display.get_n_monitors(); index++) {
            const rect = global.display.get_monitor_geometry(index);
            monitors.push({index, rect: [rect.x, rect.y, rect.width, rect.height],
                names: names.filter(name => manager.get_monitor_for_connector(name) === index)});
        }
        const workspace = global.workspace_manager.get_active_workspace();
        const windows = global.display.sort_windows_by_stacking(
            global.get_window_actors().map(actor => actor.meta_window)).reverse();
        const records = [];
        for (const window of windows) {
            try {
                if (window.get_pid() === excludedPid || window.minimized ||
                    !window.showing_on_its_workspace() || !window.located_on_workspace(workspace))
                    continue;
                const type = window.get_window_type();
                if (type === Meta.WindowType.DESKTOP || type === Meta.WindowType.DOCK)
                    continue;
                const rect = window.get_frame_rect();
                if (rect.width <= 0 || rect.height <= 0)
                    continue;
                records.push({
                    id: `${this._session}:${window.get_stable_sequence()}`,
                    pid: window.get_pid(),
                    rect: [rect.x, rect.y, rect.x + rect.width, rect.y + rect.height],
                });
            } catch (_error) {
                // A client may disappear during a geometry read.
            }
        }
        return JSON.stringify({version: 1, monitors, windows: records});
    }
}
