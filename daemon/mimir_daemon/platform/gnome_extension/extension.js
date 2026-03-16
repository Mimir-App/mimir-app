'use strict';

const { Gio } = imports.gi;

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

let _dbusImpl = null;
let _ownerId = null;

var _handler = {
    GetActiveWindow: function() {
        const focusWindow = global.display.get_focus_window();
        if (!focusWindow) return [0, '', ''];
        const pid = focusWindow.get_pid() || 0;
        const wmClass = focusWindow.get_wm_class() || '';
        const title = focusWindow.get_title() || '';
        return [pid, wmClass, title];
    }
};

function enable() {
    _dbusImpl = Gio.DBusExportedObject.wrapJSObject(IFACE_XML, _handler);
    _dbusImpl.export(Gio.DBus.session, '/org/mimir/WindowTracker');
    _ownerId = Gio.bus_own_name(
        Gio.BusType.SESSION,
        'org.mimir.WindowTracker',
        Gio.BusNameOwnerFlags.NONE,
        null, null, null
    );
}

function disable() {
    if (_dbusImpl) {
        _dbusImpl.unexport();
        _dbusImpl = null;
    }
    if (_ownerId) {
        Gio.bus_unown_name(_ownerId);
        _ownerId = null;
    }
}

function init() {
    // Nothing to initialize
}
