import json

from anki import hooks, buildinfo
from aqt import editor, gui_hooks, mw
from aqt.utils import *
from aqt.theme import theme_manager
from aqt.webview import AnkiWebView

config = mw.addonManager.getConfig(__name__)

class EditorPreview(object):
    js=[
        "js/mathjax.js",
        "js/vendor/mathjax/tex-chtml.js",
        "js/reviewer.js",
    ]

    def __init__(self):
        gui_hooks.editor_did_init.append(self.editor_init_hook)
        gui_hooks.editor_did_init_buttons.append(self.editor_init_button_hook)
        if int(buildinfo.version.split(".")[2]) < 45: # < 2.1.45
            self.js = [
                "js/vendor/jquery.min.js",
                "js/vendor/css_browser_selector.min.js",
                "js/mathjax.js",
                "js/vendor/mathjax/tex-chtml.js",
                "js/reviewer.js",
            ]


    def editor_init_hook(self, ed: editor.Editor):
        ed.editor_preview = AnkiWebView(title="editor_preview")
        # This is taken out of clayout.py
        ed.editor_preview.stdHtml(
            ed.mw.reviewer.revHtml(),
            css=["css/reviewer.css"],
            js=self.js,
            context=ed,
        )

        if not config['showPreviewAutomatically']:
            ed.editor_preview.hide()

        self._inject_splitter(ed)
        gui_hooks.editor_did_fire_typing_timer.append(lambda o: self.onedit_hook(ed, o))
        gui_hooks.editor_did_load_note.append(lambda o: None if o != ed else self.editor_note_hook(o))

    def _get_splitter(self, editor):
        layout = editor.outerLayout
        mainR, editorR = [int(r) for r in config['splitRatio'].split(":")]
        location = config['location']
        split = QSplitter()
        if location == 'above':
            split.setOrientation(Qt.Vertical)
            split.addWidget(editor.editor_preview)
            split.addWidget(editor.web)
            sizes = [editorR, mainR]
        elif location ==  'below':
            split.setOrientation(Qt.Vertical)
            split.addWidget(editor.web)
            split.addWidget(editor.editor_preview)
            sizes = [mainR, editorR]
        elif location == 'left':
            split.setOrientation(Qt.Horizontal)
            split.addWidget(editor.editor_preview)
            split.addWidget(editor.web)
            sizes = [editorR, mainR]
        elif location == 'right':
            split.setOrientation(Qt.Horizontal)
            split.addWidget(editor.web)
            split.addWidget(editor.editor_preview)
            sizes = [mainR, editorR]
        else:
            raise ValueError("Invalid value for config key location")

        split.setSizes(sizes)
        return split


    def _inject_splitter(self, editor: editor.Editor):
        layout = editor.outerLayout
        web_index = layout.indexOf(editor.web)
        layout.removeWidget(editor.web)

        split = self._get_splitter(editor)
        layout.insertWidget(web_index, split)


    def editor_note_hook(self, editor):
        self.onedit_hook(editor, editor.note)

    def editor_init_button_hook(self, buttons, editor):
        addon_path = os.path.dirname(__file__)
        icons_dir = os.path.join(addon_path, 'icons')
        b = editor.addButton(icon=os.path.join(icons_dir, 'file.svg'), cmd="_editor_toggle_preview", tip='Toggle Live Preview',
                    func=lambda o=editor: self.onEditorPreviewButton(o), disables=False
             )
        buttons.append(b)

    def onEditorPreviewButton(self, origin: editor.Editor):
        if origin.editor_preview.isHidden():
            origin.editor_preview.show()
        else:
            origin.editor_preview.hide()


    def _obtainCardText(self, note):
        c = note.ephemeral_card()
        a = mw.prepare_card_text_for_display(c.answer())
        a = gui_hooks.card_will_show(a, c, "clayoutAnswer")
        if theme_manager.night_mode:
            bodyclass = theme_manager.body_classes_for_card_ord(c.ord, mw.pm.night_mode())
        else:
            bodyclass = theme_manager.body_classes_for_card_ord(c.ord)
        bodyclass += " editor-preview"

        return f"_showAnswer({json.dumps(a)},'{bodyclass}');"

    def onedit_hook(self, editor, origin):
        if editor.note == origin:
            editor.editor_preview.eval(self._obtainCardText(editor.note))

eprev = EditorPreview()
