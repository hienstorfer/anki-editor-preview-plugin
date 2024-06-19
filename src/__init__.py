import json
from typing import Set

from anki import hooks, buildinfo
from aqt import editor, gui_hooks, mw
from aqt.utils import *
from aqt.theme import theme_manager
from aqt.webview import AnkiWebView

config = mw.addonManager.getConfig(__name__)

class EditorPreview(object):
    editors: Set[editor.Editor] = set()
    js = [
        "js/mathjax.js",
        "js/vendor/mathjax/tex-chtml.js",
        "js/reviewer.js",
    ]

    def __init__(self):
        gui_hooks.editor_did_init.append(self.editor_init_hook)
        gui_hooks.editor_did_init_buttons.append(self.editor_init_button_hook)
        gui_hooks.editor_did_load_note.append(self.editor_note_hook)
        gui_hooks.editor_did_fire_typing_timer.append(self.onedit_hook)
        gui_hooks.browser_did_change_row.append(self.on_browser_row_change)
        buildversion = buildinfo.version.split(".")

        if int(buildversion[0]) >= 24 or (int(buildversion[0]) == 23 and int(buildversion[1]) == 12 and 2 < len(buildversion) and int(buildversion[2])) >= 1:
            self.js = [
                "js/mathjax.js",
                "js/vendor/mathjax/tex-chtml-full.js",
                "js/reviewer.js",
            ]
        elif int(buildversion[0]) < 23 and int(buildversion[2]) < 45:
            self.js = [
                "js/vendor/jquery.min.js",
                "js/vendor/css_browser_selector.min.js",
                "js/mathjax.js",
                "js/vendor/mathjax/tex-chtml.js",
                "js/reviewer.js",
            ]

    def editor_init_hook(self, ed: editor.Editor):
        ed.editor_preview = AnkiWebView(title="editor_preview")
        ed.editor_preview.stdHtml(
            ed.mw.reviewer.revHtml(),
            css=["css/reviewer.css"],
            js=self.js,
            context=ed,
        )

        if not config["showPreviewAutomatically"]:
            ed.editor_preview.hide()

        self._inject_splitter(ed)

    def _get_splitter(self, editor):
        mainR, editorR = [int(r) * 10000 for r in config["splitRatio"].split(":")]
        location = config["location"]
        split = QSplitter()
        if location == "above":
            split.setOrientation(Qt.Orientation.Vertical)
            split.addWidget(editor.editor_preview)
            split.addWidget(editor.wrapped_web)
            sizes = [editorR, mainR]
        elif location == "below":
            split.setOrientation(Qt.Orientation.Vertical)
            split.addWidget(editor.wrapped_web)
            split.addWidget(editor.editor_preview)
            sizes = [mainR, editorR]
        elif location == "left":
            split.setOrientation(Qt.Orientation.Horizontal)
            split.addWidget(editor.editor_preview)
            split.addWidget(editor.wrapped_web)
            sizes = [editorR, mainR]
        elif location == "right":
            split.setOrientation(Qt.Orientation.Horizontal)
            split.addWidget(editor.wrapped_web)
            split.addWidget(editor.editor_preview)
            sizes = [mainR, editorR]
        else:
            raise ValueError("Invalid value for config key location")

        split.setSizes(sizes)
        return split

    def _inject_splitter(self, editor: editor.Editor):
        layout = editor.web.parentWidget().layout()
        if layout is None:
            layout = QVBoxLayout()
            editor.web.parentWidget().setLayout(layout)
        web_index = layout.indexOf(editor.web)
        layout.removeWidget(editor.web)

        editor.wrapped_web = QWidget()
        wrapLayout = QHBoxLayout()
        editor.wrapped_web.setLayout(wrapLayout)
        wrapLayout.addWidget(editor.web)

        split = self._get_splitter(editor)
        layout.insertWidget(web_index, split)

    def editor_note_hook(self, editor):
        self.editors = set(filter(lambda it: it.note is not None, self.editors))
        self.editors.add(editor)
        editor.cached_fields = list(editor.note.fields)
        self.refresh(editor)

    def editor_init_button_hook(self, buttons, editor):
        addon_path = os.path.dirname(__file__)
        icons_dir = os.path.join(addon_path, "icons")
        b = editor.addButton(
            icon=os.path.join(icons_dir, "file.svg"),
            cmd="_editor_toggle_preview",
            tip="Toggle Live Preview",
            func=lambda o=editor: self.onEditorPreviewButton(o),
            disables=False,
        )
        buttons.append(b)

    def onEditorPreviewButton(self, origin: editor.Editor):
        if origin.editor_preview.isHidden():
            origin.editor_preview.show()
        else:
            origin.editor_preview.hide()

    def _obtainCardText(self, card):
        if card:
            a = mw.prepare_card_text_for_display(card.answer())
            a = gui_hooks.card_will_show(a, card, "clayoutAnswer")
            bodyclass = theme_manager.body_classes_for_card_ord(card.ord, theme_manager.night_mode)
            bodyclass += " editor-preview"

            return f"_showAnswer({json.dumps(a)},'{bodyclass}');"
        else:
            return "_showAnswer('', '');"

    def onedit_hook(self, note):
        for editor in self.editors:
            if editor.note == note and editor.cached_fields != note.fields:
                editor.cached_fields = list(note.fields)
                self.refresh(editor)

    def on_browser_row_change(self, browser):
        if browser.card:
            self.current_card_id = browser.card.id
            self.refresh_all_editors()

    def refresh_all_editors(self):
        for editor in self.editors:
            self.refresh(editor)

    def refresh(self, editor):
        if hasattr(self, 'current_card_id'):
            card = mw.col.getCard(self.current_card_id)
            editor.editor_preview.eval(self._obtainCardText(card))

eprev = EditorPreview()
