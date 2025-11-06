"""
Transfermarkt-like PyQt5 GUI (moderne avec grid stats)
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QMainWindow, QLineEdit, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QComboBox, QFrame,
    QSpinBox, QTextEdit, QDialog, QDialogButtonBox, QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QFont, QPixmap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

color_main = "#ffa45f"
color_content = "#f0f0f0"  # fond uniforme pour le contenu
STYLE = f"""
QMainWindow {{
    background-color: {color_main};
    color: #222;
}}

/* === SIDEBAR === */
QFrame#sidebar {{
    background-color: #002b5c;
    color: white;
    border-right: 2px solid #ff6f00;
}}
QFrame#sidebar QLabel {{
    color: #ffffff;
    font-weight: bold;
}}


/* === GLOBAL INPUTS === */
QLineEdit {{
    border: 1px solid #ccc;
    border-radius: 6px;
    padding: 6px;
    background-color: #ffffff;
    selection-background-color: #ff6f00;
}}
QComboBox, QSpinBox {{
    border: 1px solid #ccc;
    border-radius: 6px;
    padding: 4px;
    background: white;
}}

/* === BUTTONS === */
QPushButton {{
    background-color: #ff6f00;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: #ffa040;
}}
QPushButton:pressed {{
    background-color: #e65c00;
}}

/* === SUGGESTION LIST === */
QListWidget {{
    border: 1px solid #ccc;
    border-radius: 6px;
    padding: 4px;
    background: #ffffff;
}}
QListWidget::item:selected {{
    background-color: #dbe9ff;
}}

/* === TEXT AREAS === */
QTextEdit {{
    background-color: #f5f8fb;
    border: 1px solid #d0d4db;
    border-radius: 6px;
    color: #222;
}}
"""

# ---- MOCK DATA API ----
try:
    import pandas as pd
except:
    pd = None

try:
    import data_api
except:
    class MockAPI:
        players = [
            {"id": 1, "name": "Kylian Mbappé"},
            {"id": 2, "name": "Erling Haaland"},
            {"id": 3, "name": "Lionel Messi"},
        ]
        @staticmethod
        def search_players(q):
            return [p for p in MockAPI.players if q.lower() in p["name"].lower()]
        suggest_players_by_substring = search_players
        @staticmethod
        def get_player_info(pid):
            p = next((x for x in MockAPI.players if x["id"] == pid), None)
            return {"id": pid, "name": p["name"], "age": 25, "position": "FW",
                    "club": "Mock FC", "market_value": "€100M", "photo_path": None,
                    "description": "Mock player info."}
        @staticmethod
        def get_recommendations(pid):
            return [p for p in MockAPI.players if p["id"] != pid]
        @staticmethod
        def get_player_stats(pid):
            import numpy as np
            seasons = [f"20{10+i}/{11+i}" for i in range(6)]
            goals = np.random.randint(0, 20, 6)
            assists = np.random.randint(0, 10, 6)
            return pd.DataFrame({"season": seasons, "goals": goals, "assists": assists})
    data_api = MockAPI

# ---- PLOT CANVAS ----
class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure(figsize=(5,4), dpi=100, facecolor=color_main)
        self.ax = fig.add_subplot(111, facecolor=color_content)
        super().__init__(fig)
    def plot_line(self, x, y, title=""):
        self.ax.clear()
        self.ax.plot(x, y, marker='o', color="#0073e6")
        self.ax.set_title(title)
        self.ax.grid(True)
        self.draw()

# ---- SEARCH BOX ----
class SearchBox(QLineEdit):
    def __init__(self, suggestion_list, parent=None):
        super().__init__(parent)
        self.suggestion_list = suggestion_list
    def keyPressEvent(self, event):
        if self.suggestion_list.isVisible():
            if event.key() == Qt.Key_Down:
                row = self.suggestion_list.currentRow()+1
                if row < self.suggestion_list.count(): self.suggestion_list.setCurrentRow(row)
                return
            elif event.key() == Qt.Key_Up:
                row = self.suggestion_list.currentRow()-1
                if row >= 0: self.suggestion_list.setCurrentRow(row)
                return
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
                item = self.suggestion_list.currentItem()
                if item: self.suggestion_list.itemClicked.emit(item)
                return
        super().keyPressEvent(event)

# ---- HISTORY DIALOG ----
class HistoryDialog(QDialog):
    def __init__(self, history, callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Historique des joueurs")
        self.resize(300,400)
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        for pid,name in history:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole,pid)
            self.list.addItem(item)
        layout.addWidget(self.list)
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        layout.addWidget(btns)
        btns.rejected.connect(self.close)
        self.list.itemDoubleClicked.connect(lambda i: (callback(i.data(Qt.UserRole)), self.close()))

# ---- MAIN WINDOW ----
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Transfertmarché")
        self.resize(1300,850)
        self.setStyleSheet(STYLE)
        self.history=[]
        self.history_index=-1

        main = QWidget()
        self.setCentralWidget(main)
        main_layout = QHBoxLayout(main)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        self.sidebar = self.build_sidebar()
        main_layout.addWidget(self.sidebar)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.setSpacing(0)

        header = self.build_header()
        right_layout.addWidget(header,0)

        self.main_content = self.build_main_content()
        right_layout.addWidget(self.main_content,1)

        main_layout.addWidget(right_panel,1)
        QApplication.instance().installEventFilter(self)

    # -------------------------
    # HEADER
    # -------------------------
    def build_header(self):
        container = QFrame()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(10,10,10,10)
        layout.setSpacing(10)

        self.suggestion_list = QListWidget()
        self.suggestion_list.hide()
        self.suggestion_list.setParent(self)
        self.suggestion_list.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)

        self.search_box = SearchBox(self.suggestion_list)
        self.search_box.setPlaceholderText("Rechercher un joueur...")
        self.search_box.setFixedWidth(400)
        layout.addWidget(self.search_box)

        self._timer = QTimer(singleShot=True, interval=250)
        self.search_box.textChanged.connect(lambda:self._timer.start())
        self._timer.timeout.connect(self.update_suggestions)
        self.suggestion_list.itemClicked.connect(self.on_suggestion_clicked)

        layout.addStretch(1)
        layout.addWidget(QLabel("Position:"))
        self.position_filter = QComboBox()
        self.position_filter.addItems(["Tous","GK","DF","MF","FW"])
        layout.addWidget(self.position_filter)
        layout.addWidget(QLabel("Âge min:"))
        self.age_min=QSpinBox(); self.age_min.setRange(15,50); self.age_min.setValue(16)
        layout.addWidget(self.age_min)
        layout.addWidget(QLabel("Âge max:"))
        self.age_max=QSpinBox(); self.age_max.setRange(15,50); self.age_max.setValue(40)
        layout.addWidget(self.age_max)
        layout.addWidget(QLabel("Ligue:"))
        self.league_filter = QComboBox()
        self.league_filter.addItems(["Toutes","Ligue 1","Premier League","LaLiga","Bundesliga","Serie A"])
        layout.addWidget(self.league_filter)

        self.apply_btn=QPushButton("Appliquer filtres")
        self.apply_btn.clicked.connect(self.on_apply_filters)
        layout.addWidget(self.apply_btn)

        return container

    # -------------------------
    # SIDEBAR
    # -------------------------
    def build_sidebar(self):
        frame=QFrame()
        frame.setObjectName("sidebar")
        frame.setMinimumWidth(350)
        vbox=QVBoxLayout(frame)
        vbox.setContentsMargins(10,10,10,10)
        vbox.setSpacing(10)

        nav_layout=QHBoxLayout()
        self.back_btn=QPushButton("← Retour")
        self.forward_btn=QPushButton("→ Avancer")
        self.history_btn=QPushButton("Historique")
        self.back_btn.clicked.connect(self.go_back)
        self.forward_btn.clicked.connect(self.go_forward)
        self.history_btn.clicked.connect(self.show_history)
        nav_layout.addWidget(self.back_btn)
        nav_layout.addWidget(self.forward_btn)
        nav_layout.addWidget(self.history_btn)
        vbox.addLayout(nav_layout)

        self.photo_label=QLabel()
        self.photo_label.setFixedHeight(220)
        self.photo_label.setAlignment(Qt.AlignCenter)
        vbox.addWidget(self.photo_label)

        self.lbl_name=QLabel("Aucun joueur sélectionné")
        self.lbl_name.setFont(QFont('Arial',12,QFont.Bold))
        vbox.addWidget(self.lbl_name)

        self.lbl_info=QLabel("")
        vbox.addWidget(self.lbl_info)

        self.txt_description=QTextEdit()
        self.txt_description.setReadOnly(True)
        vbox.addWidget(self.txt_description,1)

        vbox.addWidget(QLabel("Joueurs susceptibles de vous intéresser:"))
        self.rec_list=QListWidget()
        self.rec_list.itemClicked.connect(lambda i:self.load_player(i.data(Qt.UserRole)))
        vbox.addWidget(self.rec_list,1)

        return frame

    # -------------------------
    # MAIN CONTENT
    # -------------------------
    def build_main_content(self):
        frame=QFrame()
        layout=QVBoxLayout(frame)
        layout.setContentsMargins(10,10,10,10)
        layout.setSpacing(10)

        # Stats grid
        self.stats_container=QFrame()
        self.stats_container.setStyleSheet(f"background-color:{color_main}; border-radius:10px;")
        self.stats_layout=QGridLayout(self.stats_container)
        self.stats_layout.setContentsMargins(10,10,10,10)
        self.stats_layout.setHorizontalSpacing(30)
        self.stats_layout.setVerticalSpacing(10)
        layout.addWidget(self.stats_container,1)

        # Graph
        self.plot_canvas=PlotCanvas(self)
        layout.addWidget(self.plot_canvas,2)

        return frame

    # -------------------------
    # SUGGESTIONS
    # -------------------------
    def update_suggestions(self):
        text=self.search_box.text().strip()
        if not text:
            self.suggestion_list.hide()
            return
        try: results = data_api.suggest_players_by_substring(text)
        except: results=[]
        self.suggestion_list.clear()
        for p in results:
            item = QListWidgetItem(p['name'])
            item.setData(Qt.UserRole,p['id'])
            self.suggestion_list.addItem(item)
        if not results: self.suggestion_list.hide(); return
        pos = self.search_box.mapToGlobal(self.search_box.rect().bottomLeft())
        self.suggestion_list.move(pos)
        self.suggestion_list.setFixedWidth(self.search_box.width())
        self.suggestion_list.show()
        self.suggestion_list.raise_()
        self.search_box.setFocus()

    def on_suggestion_clicked(self,item):
        pid=item.data(Qt.UserRole)
        self.search_box.setText(item.text())
        self.search_box.setFocus()
        self.suggestion_list.hide()
        self.load_player(pid)

    # -------------------------
    # FILTER CALLBACK
    # -------------------------
    def on_apply_filters(self):
        print(f"Filtres appliqués : Pos={self.position_filter.currentText()}, Ligue={self.league_filter.currentText()}, Age={self.age_min.value()}-{self.age_max.value()}")

    # -------------------------
    # LOAD PLAYER + HISTORY
    # -------------------------
    def load_player(self,pid):
        self.search_box.setText('')
        info=data_api.get_player_info(pid)
        self.lbl_name.setText(info.get('name',''))
        desc=f"Club: {info.get('club')} | Age: {info.get('age')} | Poste: {info.get('position')} | Valeur: {info.get('market_value')}"
        self.lbl_info.setText(desc)
        self.txt_description.setPlainText(info.get('description',''))
        if info.get('photo_path'):
            pix=QPixmap(info['photo_path'])
            self.photo_label.setPixmap(pix.scaled(200,200,Qt.KeepAspectRatio,Qt.SmoothTransformation))
        else: self.photo_label.setPixmap(QPixmap())
        self.rec_list.clear()
        for r in data_api.get_recommendations(pid):
            item=QListWidgetItem(r['name'])
            item.setData(Qt.UserRole,r['id'])
            self.rec_list.addItem(item)
        self.update_stats(pid)

        # History
        name=info.get('name','')
        if not self.history or self.history[self.history_index][0]!=pid:
            self.history=self.history[:self.history_index+1]
            self.history.append((pid,name))
            self.history_index=len(self.history)-1

    def go_back(self):
        if self.history_index>0:
            self.history_index-=1
            pid,_=self.history[self.history_index]
            self.load_player(pid)
    def go_forward(self):
        if self.history_index<len(self.history)-1:
            self.history_index+=1
            pid,_=self.history[self.history_index]
            self.load_player(pid)
    def show_history(self):
        dlg=HistoryDialog(self.history,self.load_player,self)
        dlg.exec_()

    # -------------------------
    # UPDATE STATS (GRID)
    # -------------------------
    def update_stats(self,pid):
        # Clear previous
        for i in reversed(range(self.stats_layout.count())):
            widget=self.stats_layout.itemAt(i).widget()
            if widget: widget.setParent(None)

        df=data_api.get_player_stats(pid)
        if isinstance(df,pd.DataFrame):
            totals={'Seasons':len(df),'Goals':int(df['goals'].sum()),'Assists':int(df['assists'].sum())}
            row=0
            for key,value in totals.items():
                label_key=QLabel(str(key))
                label_key.setAlignment(Qt.AlignCenter)
                label_key.setStyleSheet("font-weight:bold; background:#ffffff; border-radius:6px; padding:6px;")
                label_value=QLabel(str(value))
                label_value.setAlignment(Qt.AlignCenter)
                label_value.setStyleSheet("background:#ffffff; border-radius:6px; padding:6px;")
                self.stats_layout.addWidget(label_key,row,0)
                self.stats_layout.addWidget(label_value,row,1)
                row+=1

        self.plot_canvas.plot_line(df['season'],df['goals'],'Goals by Season')

    # -------------------------
    # EVENT FILTER FOR HIDE SUGGESTIONS
    # -------------------------
    def eventFilter(self,source,event):
        if event.type()==QEvent.MouseButtonPress:
            if self.suggestion_list.isVisible() and not self.suggestion_list.geometry().contains(event.globalPos()):
                if source is not self.search_box:
                    self.suggestion_list.hide()
        return super().eventFilter(source,event)

# ---- MAIN ----
def main():
    app=QApplication(sys.argv)
    w=MainWindow()
    w.show()
    sys.exit(app.exec_())

if __name__=="__main__":
    main()
