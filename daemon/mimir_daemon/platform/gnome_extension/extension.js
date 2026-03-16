import Gio from 'gi://Gio';

const IFACE_XML = `
<node>
  <interface name="org.mimir.WindowTracker">
    <method name="GetActiveWindow">
      <arg type="u" direction="out" name="pid"/>
      <arg type="s" direction="out" name="wm_class"/>
      <arg type="s" direction="out" name="title"/>
    </method>
  </interface>
</node>`;

export default class MimirWindowTracker {
    enable() {
        this._dbusImpl = Gio.DBusExportedObject.wrapJSObject(IFACE_XML, this);
        this._dbusImpl.export(Gio.DBus.session, '/org/mimir/WindowTracker');
        this._ownerId = Gio.bus_own_name(
            Gio.BusType.SESSION,
            'org.mimir.WindowTracker',
            Gio.BusNameOwnerFlags.NONE,
            null, null, null
        );
    }

    disable() {
        if (this._dbusImpl) {
            this._dbusImpl.unexport();
            this._dbusImpl = null;
        }
        if (this._ownerId) {
            Gio.bus_unown_name(this._ownerId);
            this._ownerId = null;
        }
    }

    GetActiveWindow() {
        const focusWindow = global.display.get_focus_window();
        if (!focusWindow) return [0, '', ''];
        const pid = focusWindow.get_pid() || 0;
        const wmClass = focusWindow.get_wm_class() || '';
        const title = focusWindow.get_title() || '';
        return [pid, wmClass, title];
    }
}
