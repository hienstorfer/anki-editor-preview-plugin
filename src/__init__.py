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
        ed.webview = AnkiWebView(title="editor_preview")
        # This is taken out of clayout.py
        ed.webview.stdHtml(
            ed.mw.reviewer.revHtml(),
            css=["css/reviewer.css"],
            js=self.js,
            context=ed,
        )

        if not config['showPreviewAutomatically']:
            ed.webview.hide()

        self._inject_splitter(ed)
        gui_hooks.editor_did_fire_typing_timer.append(lambda o: self.onedit_hook(ed, o))
        gui_hooks.editor_did_load_note.append(lambda o: None if o != ed else self.editor_note_hook(o))

    def _inject_splitter(self, editor: editor.Editor):
        layout = editor.outerLayout
        split = QSplitter()
        split.setOrientation(Qt.Vertical)
        web_index = layout.indexOf(editor.web)
        layout.removeWidget(editor.web)
        split.addWidget(editor.web)
        split.addWidget(editor.webview)
        splitRatio = config['splitRatio']
        upperR, lowerR = [int(r) for r in splitRatio.split(":")]
        split.setStretchFactor(0, upperR)
        split.setStretchFactor(1, lowerR)
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
        if origin.webview.isHidden():
            origin.webview.show()
        else:
            origin.webview.hide()


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
            editor.webview.eval(self._obtainCardText(editor.note))

eprev = EditorPreview()
