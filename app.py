from cgitb import text
import glob
from re import A
import subprocess
from xml.sax import parseString
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTextEdit, QMenu,
                            QVBoxLayout, QMenuBar, QAction, QListWidget, QListWidgetItem,
                            QFileDialog, QMessageBox)
from PyQt5.QtGui import QContextMenuEvent, QKeyEvent, QTextCursor, QFont, QTextCharFormat, QSyntaxHighlighter, QColor
from PyQt5.QtCore import Qt, QPoint, QRegExp

KEYWORDS = [
    "int", "float", "double", "const", "char", "return", "if", "else",
    "else if", "for", "do", "while", "auto", "void", "class ", "template", "enum", "struct",
    "typedef", "typename",
    "cout", "cin", "string", "getline", "vector"
]
HASH_THINGS = [
    "#include", "#define", "#pragma", "#ifndef", "#endif"
]

USER_ENTERED = []

class SyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#3333FF"))  # Blue color for keywords
        keyword_format.setFontWeight(QFont.Weight.Bold)
        self.keyword_patterns = KEYWORDS
        self.keyword_format = keyword_format
        
        self.hashes_format = QTextCharFormat()
        self.hashes_format.setForeground(QColor("#00ad48"))
        self.hashes_format.setFontWeight(QFont.Weight.Medium)
        self.hashes_format.setFontItalic(True)
        self.hashes_patterns = HASH_THINGS
        
        self.others = QTextCharFormat()
        self.others.setForeground(QColor("#765d9c"))
        self.others_p = ["\\{", "\\}", "\\(", "\\)"]
        
        self.namespace_format = QTextCharFormat()
        self.namespace_format.setForeground(QColor("#569db3"))
        self.namespace_format.setFontWeight(QFont.Weight.Light)
        self.namespace_format.setFontItalic(True)
        self.namespace_patterns = ["std", "stringstream", "fstream", "filesystem"]

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#00BB00"))
        self.string_pattern = r'".*"'
        
        self.imports_format = QTextCharFormat()
        self.imports_format.setForeground(QColor("#00bda0"))
        self.imports_pattern = r'<.*>'

        self.comment_format = QTextCharFormat()
        self.comment_format.setForeground(QColor("#888888"))  # Gray color for comments
        self.comment_pattern = r'//[^\n]*'

    def highlightBlock(self, text):
        for pattern, format in [
            (self.string_pattern, self.string_format),
            (self.comment_pattern, self.comment_format),
            (self.imports_pattern, self.imports_format)
        ]:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        for pattern in self.keyword_patterns:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, self.keyword_format)
                index = expression.indexIn(text, index + length)
        
        for pattern in self.hashes_patterns:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, self.hashes_format)
                index = expression.indexIn(text, index + length)
        
        for pattern in self.namespace_patterns:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, self.namespace_format)
                index = expression.indexIn(text, index + length)
        
        for pattern in self.others_p:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, self.others)
                index = expression.indexIn(text, index + length)


class MainWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        
        self.path = ''
        self.saved = False
        
        # MENU #
        
        self.menuBar = QMenuBar(self)
        
        self.init_file_menu()
        
        # ---- #
        
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        
        self.text_edit = TextEdit(self)
        self.text_edit.setFont(QFont("Droid Sans Mono", 18))
        
        self.lay.addWidget(self.menuBar)
        self.lay.addWidget(self.text_edit)
    
    def init_file_menu(self):
        fileMenu = QMenu("File", self)
        
        action_save = QAction("Save", self)
        action_save.triggered.connect(self.show_save_file_dialog)
        action_save.setShortcut("Ctrl+S")
        
        action_open = QAction("Open", self)
        action_open.setShortcut("Ctrl+O")
        action_open.triggered.connect(self.show_open_file_dialog)
        
        action_save_as = QAction("Save as", self)
        action_save_as.setShortcut("Ctrl+Shift+S")
        action_save_as.triggered.connect(self.show_saveAs_file_dialog)
        
        action_new = QAction("New", self)
        action_new.setShortcut("Ctrl+N")
        action_new.triggered.connect(self.new_file)
        
        fileMenu.addActions([
            action_save,
            action_save_as,
            action_new,
            action_open
        ])
        
        self.menuBar.addMenu(fileMenu)
    
    
    def show_save_file_dialog(self):
        if self.path != '':
            with open(self.path, 'w') as f:
                f.write(self.text_edit.toPlainText())
            return
        
        dialog = QFileDialog()
        
        file, _ = dialog.getSaveFileName(self, "Save file", filter="C++ files (*.cpp *.hpp *.c *.h);; All files (*)")
        
        if file:
            with open(file[0], 'x') as f:
                f.write(self.text_edit.toPlainText())
            
            self.path = file[0]
            self.saved = True
    
    def show_saveAs_file_dialog(self):
        dialog = QFileDialog()
        
        file, _ = dialog.getSaveFileName(self, "Save file as", filter="C++ files (*.cpp *.hpp *.c *.h);; All files (*)")
        
        if file:
            with open(file[0], 'x') as f:
                f.write(self.text_edit.toPlainText())
            
            self.path = file[0]
            self.saved = True
    
    def show_open_file_dialog(self):
        if not self.saved:
            reply = self.ask("File is not saved! would you like to save it?")
            if reply: self.show_save_file_dialog()
            elif reply == None: return
                    
        dialog = QFileDialog()
        
        file, _ = dialog.getOpenFileName(self, "Open file", filter="C++ files (*.cpp *.hpp *.c *.h);; All files (*)")
        
        if file:
            with open(file, 'r') as f:
                self.text_edit.setText(f.read())
            
            self.path = file
            self.saved = True
    
    def new_file(self):
        if not self.saved:
            reply = self.ask("File is not saved! would you like to save it?")
            if reply: self.show_save_file_dialog()
            elif reply == None: return
            
        self.path = ''
        self.saved = True
        self.text_edit.clear()
            
    def ask(self, msg):
        reply = QMessageBox.question(self, "Confirm", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        
        if reply == QMessageBox.StandardButton.Yes:
            return True
        
        elif reply == QMessageBox.StandardButton.No:
            return False
        
        else:
            return None


class TextEdit(QTextEdit):
    def __init__(self, parent: MainWidget):
        super().__init__()
        self.p = parent
        self.tabCount = 0
        self.setTabStopWidth(33)
        
        self.textChanged.connect(self.on_change)
        
        self.syntax_highlighter = SyntaxHighlighter(self.document())
    
    def on_change(self):
        self.p.saved = False
    
    def keyPressEvent(self, e: QKeyEvent | None) -> None:
        if e.key() == Qt.Key.Key_QuoteDbl:
            self.pair_completion("\"", 1)
        
        elif e.key() == Qt.Key.Key_Apostrophe:
            self.pair_completion("\'", 1)
        
        elif e.key() == Qt.Key.Key_BraceLeft:
            self.pair_completion("{", 1, "}")
        
        elif e.key() == Qt.Key.Key_BracketLeft:
            self.pair_completion("[", 1, "]")
        
        elif e.key() == Qt.Key.Key_ParenLeft:
            self.pair_completion("(", 1, ")")
        
        elif e.key() == Qt.Key.Key_Backspace:
            if self.toPlainText() == '':
                return
            
            text_cursor = self.textCursor()
            previous_char = self.toPlainText()[text_cursor.position() - 1]
            if previous_char in ('\'', '\"', '{', '(', '['):
                self.remove_previous_and_next()

            elif previous_char == '\t':
                text_cursor.deletePreviousChar()
                self.setTextCursor(text_cursor)
                if self.tabCount != 0: self.tabCount -= 1
            
            else:
                super().keyPressEvent(e)
                
        # Auto Import
        
        elif e.text() == 'r':
            super().keyPressEvent(e)
            self.auto_import_r()
            
        elif e.text() in ['t', 'n']:
            super().keyPressEvent(e)
            self.auto_import_m()
        
        elif e.text() == 'm':
            super().keyPressEvent(e)
            self.auto_import_stream()
        
        # Auto completion
        
        elif e.key() == Qt.Key.Key_Tab:
            text_cursor = self.textCursor()
            text_cursor.insertText('\t')
            self.setTextCursor(text_cursor)
            self.tabCount += 1
        
        elif e.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            if self.toPlainText() == '':
                super().keyPressEvent(e)
                return

            text_cursor = self.textCursor()
            previous_char = self.toPlainText()[text_cursor.position() - 1]

            text_cursor.insertText(f'\n{'\t' * self.tabCount}' if self.tabCount > 0 else '\n')
            self.setTextCursor(text_cursor)
        
        else:
            super().keyPressEvent(e)
    
    def auto_import_r(self):
        text_cursor = self.textCursor()
        text_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, 6)
        print(text_cursor.selectedText())
        if text_cursor.hasSelection() and text_cursor.selectedText() == 'vector':
            if not '#include <vector>' in self.toPlainText():
                self.auto_import("vector")
                text_cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.MoveAnchor)
                text_cursor.clearSelection()
                self.setTextCursor(text_cursor)
    
    def auto_import_m(self):
        text_cursor = self.textCursor()
        text_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, 4)
        if text_cursor.hasSelection() and text_cursor.selectedText() == 'cout':
            if not '#include <iostream>' in self.toPlainText():
                self.auto_import('iostream')
                text_cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.MoveAnchor)
                text_cursor.clearSelection()
                self.setTextCursor(text_cursor)
            return

        text_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, 3)

        if text_cursor.hasSelection() and text_cursor.selectedText() == 'cin':
            if not '#include <iostream>' in self.toPlainText():
                self.auto_import('iostream')
                text_cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.MoveAnchor)
                text_cursor.clearSelection()
                self.setTextCursor(text_cursor)
            return
    
    def auto_import_stream(self):
        text_cursor = self.textCursor()
        text_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, 7)

        if text_cursor.hasSelection() and text_cursor.selectedText() == 'fstream':
            if not '#include <fstream>' in self.toPlainText():
                self.auto_import('fstream')
                text_cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.MoveAnchor)
                text_cursor.clearSelection()
                self.setTextCursor(text_cursor)
            return
        
        text_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, 10)

        if text_cursor.hasSelection() and text_cursor.selectedText() == 'filesystem':
            if not '#include <filesystem>' in self.toPlainText():
                self.auto_import('filesystem')
                text_cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.MoveAnchor)
                text_cursor.clearSelection()
                self.setTextCursor(text_cursor)
            return

        text_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, 12)

        if text_cursor.hasSelection() and text_cursor.selectedText() == 'stringstream':
            if not '#include <sstream>' in self.toPlainText():
                self.auto_import('sstream')
                text_cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.MoveAnchor)
                text_cursor.clearSelection()
                self.setTextCursor(text_cursor)
            return
        
    
    def auto_import(self, module: str):
        text_cursor = self.textCursor()
        text_cursor.clearSelection()
        text_cursor.setPosition(0)
        text_cursor.insertText(f"#include <{module}>\n")
        text_cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.MoveAnchor)
        self.setTextCursor(text_cursor)
    
    def remove_previous_and_next(self):
        text_cursor = self.textCursor()
        text_cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, 1)
        text_cursor.removeSelectedText()
        text_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, 1)
        text_cursor.removeSelectedText()

    def pair_completion(self, a: str, move_by: int, b: str | None = None):
        text_cursor = self.textCursor()
        text_cursor.insertText(f"{a}{b}" if b else a * 2)
        text_cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, move_by)
        self.setTextCursor(text_cursor)


if __name__ == '__main__':
    app = QApplication([])
    main_window = QMainWindow()
    main_window.setWindowTitle("AnC++")
    main_window.resize(800, 600)
    
    widget = MainWidget()

    main_window.setCentralWidget(widget)
    main_window.show()
    
    app.exec()