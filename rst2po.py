#!/usr/bin/python3

import os
import sys
from os.path import abspath, dirname, isdir, isfile, join

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, Gtk

MENU_XML = """
<?xml version="1.0" encoding="UTF-8"?>
<interface>
  <menu id="app-menu">
    <section>
      <item>
        <attribute name="action">app.save</attribute>
        <attribute name="label">Save</attribute>
      </item>
      <item>
        <attribute name="action">app.quit</attribute>
        <attribute name="label">Quit</attribute>
    </item>
    </section>
  </menu>
</interface>
"""


class Application(Gtk.Application):
    def __init__(self, rst, po):
        Gtk.Application.__init__(self, application_id="org.translations")
        self.rst = rst
        self.po = po
        self.window = None

        self.po_header = ""
        self.messages = []
        self.paragraphs = []
        self.mess_idx = 0
        self.para_idx = 0

    def do_startup(self):
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new("save", None)
        action.connect("activate", self.on_save)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)

        builder = Gtk.Builder.new_from_string(MENU_XML, -1)
        self.set_app_menu(builder.get_object("app-menu"))

    def do_activate(self):
        if not self.window:
            self.window = Gtk.ApplicationWindow(application=self)
            self.window.set_default_size(1100, 800)

        self.box = Gtk.Box(spacing=6)
        self.window.add(self.box)

        self.read_po(self.po)
        self.read_rst(self.rst)

        self.window.show_all()

    def on_save(self, action, param):
        merged = join(dirname(abspath(self.po)), "merged")
        if not isdir("merged"):
            os.mkdir(merged)
        with open(os.path.join(merged, self.po), "w")as f:
            f.write(self.po_header)

            for msg in self.messages:
                f.write(msg[0])
                f.write(msg[1])
                f.write(msg[2])

    def on_quit(self, action, param):
        self.quit()

    def read_po(self, po):
        heading = True

        with open(po, "r") as f:
            message = ["", "", ""]

            source = False
            msgid = False
            msgstr = False

            for line in f:
                if heading:
                    if not line.startswith("#: "):
                        self.po_header += line
                        continue
                    else:
                        heading = False

                if line.startswith("#: "):
                    if msgstr:
                        self.messages.append(message)
                        message = ["", "", ""]

                        msgid = False
                        msgstr = False

                    source = True

                elif line.startswith("msgid"):
                    source = False
                    msgid = True

                elif line.startswith("msgstr"):
                    msgid = False
                    msgstr = True

                if source:
                    message[0] = line
                elif msgid:
                    message[1] += line
                elif msgstr:
                    message[2] += line

            # don't forget about latest
            self.messages.append(message)

        scrolled = Gtk.ScrolledWindow()
        self.box.pack_start(scrolled, True, True, 0)

        self.po_listbox = Gtk.ListBox()
        self.po_listbox.set_selection_mode(Gtk.SelectionMode.BROWSE)
        scrolled.add(self.po_listbox)

        for i, msg in enumerate(self.messages):
            self.insert_po_row(i, msg)

        self.po_listbox.select_row(self.po_listbox.get_row_at_index(0))

    def insert_po_row(self, i, msg):
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        row.add(hbox)

        button = Gtk.Button(label="%s" % i)
        button.connect("clicked", self.on_remove_button_clicked)
        hbox.pack_start(button, False, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox.pack_start(vbox, True, True, 0)

        for j in range(3):
            label = Gtk.Label(msg[j], xalign=0)
            vbox.pack_start(label, True, True, 0)

        self.po_listbox.insert(row, i)

    def read_rst(self, rst):
        # we don't want to merge lines starting
        # with section markup and code blocks
        throwaway = ["---", "===", "***", ".. ", "   "]

        with open(rst, "r") as f:
            para = ""
            for line in f:
                if line.strip():
                    # footnote translations are indented sometimes
                    if line.startswith(".. rubric:: Lábjegyzet"):
                        line = line[12:]
                        throwaway = throwaway[0:3]
                        continue

                    # don't collect section markup and code blocks
                    if line[0:3] not in throwaway:
                        # drop bullet list markers
                        if line.startswith("* "):
                            line = line[2:]
                        para += line.lstrip()
                else:
                    if para:
                        self.paragraphs.append(para)
                        para = ""

        scrolled = Gtk.ScrolledWindow()
        self.box.pack_start(scrolled, True, True, 0)

        self.rst_listbox = Gtk.ListBox()
        self.rst_listbox.set_selection_mode(Gtk.SelectionMode.BROWSE)
        scrolled.add(self.rst_listbox)

        for i, msg in enumerate(self.paragraphs):
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
            row.add(hbox)

            button = Gtk.Button(label="%s" % i)
            button.connect("clicked", self.on_add_button_clicked)
            hbox.pack_start(button, False, False, 0)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            hbox.pack_start(vbox, True, True, 0)

            label = Gtk.Label(msg, xalign=0)
            vbox.pack_start(label, True, True, 0)

            self.rst_listbox.add(row)
        self.rst_listbox.select_row(self.rst_listbox.get_row_at_index(0))

    def on_add_button_clicked(self, widget):
        i = widget.get_label()
        rst_idx = int(i)
        self.rst_listbox.select_row(self.rst_listbox.get_row_at_index(rst_idx))
        para = self.paragraphs[rst_idx]
        try:
            self.rst_listbox.select_row(
                self.rst_listbox.get_row_at_index(rst_idx + 1))
        except IndexError:
            pass

        selected_row = self.po_listbox.get_selected_row()
        idx = selected_row.get_index()

        if self.messages[idx][1].startswith('msgid ""'):
            para_lines = ""
            for line in para.splitlines():
                if line:
                    para_lines += '"%s "\n' % line
            para_lines = para_lines.strip() + "\n"
            self.messages[idx][2] = self.messages[idx][2] + para_lines
        else:
            self.messages[idx][2] = 'msgstr "%s"\n\n' % para.strip()

        self.po_listbox.remove(selected_row)
        self.insert_po_row(idx, self.messages[idx])
        try:
            self.po_listbox.select_row(
                self.po_listbox.get_row_at_index(idx + 1))
        except IndexError:
            pass
        self.po_listbox.show_all()

    def on_remove_button_clicked(self, widget):
        i = widget.get_label()
        idx = int(i)
        self.messages[idx][2] = 'msgstr ""\n'

        clicked_row = self.po_listbox.get_row_at_index(idx)
        self.po_listbox.remove(clicked_row)
        self.insert_po_row(idx, self.messages[idx])
        try:
            self.po_listbox.select_row(
                self.po_listbox.get_row_at_index(idx))
        except IndexError:
            pass
        self.po_listbox.show_all()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("rst2po.py needs one filename without extension!")
        sys.exit(1)
    else:
        basename = sys.argv[1]
        rst = basename + ".rst"
        po = basename + ".po"

        if not isfile(rst):
            print("No file: " + rst)
            sys.exit(1)

        if not isfile(po):
            print("No file: " + po)
            sys.exit(1)

    app = Application(rst, po)
    app.run()
