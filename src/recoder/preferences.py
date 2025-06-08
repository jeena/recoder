import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gio, Adw
import re

@Gtk.Template(resource_path="/net/jeena/recoder/preferences.ui")
class RecoderPreferences(Adw.PreferencesWindow):
    __gtype_name__ = "RecoderPreferences"

    output_folder_entry = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self.prefs_changed = False
        self.settings = Gio.Settings.new("net.jeena.recoder.preferences")

        current_value = self.settings.get_string("output-folder-template")
        self.output_folder_entry.set_text(current_value)

        self.output_folder_entry.connect("changed", self.on_output_folder_changed)
        self.settings.connect("changed::output-folder-template", self.on_setting_changed)

    def validate_template(self, text):
        allowed_pattern = r'^[\w\s\-./~${}]+$'
        if not re.match(allowed_pattern, text):
            return False

        if text.count("{{") != text.count("}}"):
            return False

        var_pattern = r'\{\{([a-zA-Z0-9_]+)\}\}'
        for var in re.findall(r'\{\{.*?\}\}', text):
            if not re.match(var_pattern, var):
                return False

        if '//' in text.replace('file://', ''):
            return False

        return True

    def on_output_folder_changed(self, entry):
        text = entry.get_text()

        if self.validate_template(text):
            self.settings.set_string("output-folder-template", text)
            self.prefs_changed = True
            entry.remove_css_class("error")
        else:
            entry.add_css_class("error")

    def on_setting_changed(self, settings, key):
        if key == "output-folder-template":
            new_val = settings.get_string(key)
            if self.output_folder_entry.get_text() != new_val:
                self.output_folder_entry.set_text(new_val)
