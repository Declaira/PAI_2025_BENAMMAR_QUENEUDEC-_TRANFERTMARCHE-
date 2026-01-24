import os
from typing import Optional, Any, Tuple, List, Dict, TYPE_CHECKING

import pandas as pd
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QDialog,
    QGraphicsView,
    QGraphicsScene,
    QLabel,
    QPushButton,
    QStackedWidget,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QAbstractItemView,
    QTabWidget,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QGraphicsPixmapItem
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFont, QPixmap, QColor, QPen, QBrush, QPainter, QWheelEvent

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from tfmc.config import BASE_DIR, COLOR_MAIN, COLOR_LINK

# Pour éviter les imports circulaires si MainWindow est défini ailleurs
if TYPE_CHECKING:
    from tfmc.main import MainWindow


def format_season_display(year: Any, short: bool = False) -> str:
    """
    Transforme une année (ex: 2024) en format de saison.

    Args:
        year (Any): L'année de début.
        short (bool): Si True, renvoie '24-25', sinon '2024-2025'.

    Returns:
        str: La chaîne formatée de la saison.
    """
    try:
        y = int(year)
        if short:
            return f"{str(y)[2:4]}-{str(y + 1)[2:4]}"
        return f"{y}-{y + 1}"
    except (ValueError, TypeError):
        return str(year)


def parse_season_from_display(display_str: str) -> int:
    """
    Récupère l'année de départ depuis une chaîne formatée (ex: '2024-2025' -> 2024).

    Args:
        display_str (str): La chaîne affichée dans l'interface.

    Returns:
        int: L'année de début (par défaut 2024 en cas d'erreur).
    """
    try:
        return int(display_str.split("-")[0])
    except (ValueError, IndexError):
        return 2024


def create_flag_label(mw: "MainWindow", country_name: str) -> QLabel:
    """
    Crée un QLabel contenant le drapeau d'un pays via le cache de MainWindow.

    Args:
        mw (MainWindow): Référence à la fenêtre principale pour l'accès aux données.
        country_name (str): Nom du pays.

    Returns:
        QLabel: Le label contenant l'image ou le texte du pays.
    """
    label = QLabel()
    label.setAlignment(Qt.AlignCenter)
    label.setObjectName("label")
    # get_flag_pixmap s'occupe maintenant de traduire "Espagne" -> "es"
    pixmap = mw.dm.get_flag_pixmap(country_name)

    if pixmap:
        label.setPixmap(pixmap)
        label.setToolTip(country_name)
    else:
        label.setText(country_name if country_name else "-")
    return label


class MatchDetailDialog(QDialog):
    """
    Boîte de dialogue affichant les statistiques détaillées des joueurs pour un match spécifique.
    """

    def __init__(self, game_id: int, dm: Any, parent_nav_callback: Any) -> None:
        super().__init__()
        self.setWindowTitle(f"Stats du Match {game_id}")
        self.resize(700, 500)
        self.nav = parent_nav_callback
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        # Filtrage et récupération des données
        stats = dm.df_appearances[dm.df_appearances["game_id"] == game_id].copy()
        stats = stats.merge(
            dm.df_players[["player_id", "name", "position"]], on="player_id"
        )

        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Joueur", "Poste", "Buts", "Passes", "Min"]
        )
        self.table.setRowCount(len(stats))

        for i, (_, row) in enumerate(stats.iterrows()):
            it = QTableWidgetItem(str(row["name"]))
            it.setData(Qt.UserRole, row["player_id"])
            it.setForeground(QColor(COLOR_LINK))
            self.table.setItem(i, 0, it)
            self.table.setItem(i, 1, QTableWidgetItem(str(row["position"])))
            self.table.setItem(i, 2, QTableWidgetItem(str(int(row["goals"]))))
            self.table.setItem(i, 3, QTableWidgetItem(str(int(row["assists"]))))
            self.table.setItem(
                i, 4, QTableWidgetItem(str(int(row["minutes_played"])))
            )

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellClicked.connect(self.on_click)
        layout.addWidget(self.table)

    def on_click(self, r: int, c: int) -> None:
        """Gère le clic sur le nom d'un joueur pour naviguer vers sa page."""
        if c == 0:
            pid = self.table.item(r, 0).data(Qt.UserRole)
            self.nav(pid, "joueur")
            self.close()


# --- PAGES ---


class BasePage(QWidget):
    """Classe de base pour toutes les pages de l'application."""

    def __init__(self, mw: "MainWindow") -> None:
        super().__init__()
        self.mw = mw
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)


class HomePage(BasePage):
    """Page d'accueil affichant la carte interactive de l'Europe."""

    def __init__(self, mw: "MainWindow") -> None:
        super().__init__(mw)

        # --- SCÈNE ET VUE ---
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setObjectName("view")
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        map_width, map_height = 960, 735
        self.scene.setSceneRect(0, 0, map_width, map_height)

        # --- CHARGEMENT CARTE ---
        self.map_item = QGraphicsPixmapItem()
        image_path = BASE_DIR+"/europe_map.png"
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    map_width,
                    map_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.map_item.setPixmap(pixmap)
                # Optionnel: rendre la carte légèrement transparente pour le style
                self.map_item.setOpacity(0.8)
                self.scene.addItem(self.map_item)

        # 2. COORDONNÉES
        coords = {
            # --- ÎLES BRITANNIQUES ---
            "GB1": (300, 420),  # Angleterre
            "SC1": (305, 340),  # Ecosse
            # --- EUROPE DE L'OUEST ---
            "FR1": (350, 500),  # France
            "BE1": (375, 460),  # Belgique
            "NL1": (370, 430),  # Pays-Bas
            "L1": (430, 450),  # Allemagne
            # --- PÉNINSULE IBÉRIQUE ---
            "ES1": (250, 620),  # Espagne
            "PO1": (185, 625),  # Portugal
            # --- ITALIE & SUD ---
            "IT1": (450, 600),  # Italie
            "GR1": (600, 650),  # Grèce
            "TR1": (750, 600),  # Turquie
            # --- NORD & EST ---
            "DK1": (430, 370),  # Danemark
            "RU1": (800, 230),  # Russie
            "UKR1": (700, 440),  # Ukraine
            # --- DANS LA MER (GAUCHE) ---
            "CL": (80, 280),  # Champions League
            "EL": (80, 375),  # Europa League
            # --- COUPES NATIONALES (Proches des pays) ---
            "CDR": (280, 620),  # Copa del Rey
            "FAC": (330, 420),  # FA Cup
            "DFB": (460, 450),  # DFB Pokal
            "CIT": (480, 600),  # Coppa Italia
            "NLP": (400, 430),  # KNVB Beker,
            "GRP": (630, 650),  # Kypello Elladas
        }

        # 3. CRÉATION DES POINTS
        for code, name in mw.dm.leagues.items():
            if code not in coords:
                continue
            x, y = coords[code]
            btn = MapPoint(name, code, mw, self.scene, x, y)
            is_championship = "1" in code
            style = "outline: none; border-radius: 15px; font-weight: bold; "

            # --- COUPE D'EUROPE ---
            if code in ["CL", "EL"]:
                symbol = "🌟" if code == "CL" else "✨"
                border_color = "#f1c40f"
                btn.setText(symbol)
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        {style}
                        background-color: #003399;
                        border: 2px solid {border_color};
                        color: white;
                        font-size: 16px;
                    }}
                    QPushButton:hover {{
                        background-color: #0044cc;
                    }}
                """
                )

            # --- COUPES NATIONALES ---
            elif not is_championship:
                btn.setText("🏆")
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        {style}
                        background-color: #95a5a6;
                        border: 2px solid white;
                        color: white;
                        font-size: 14px;
                    }}
                    QPushButton:hover {{
                        background-color: #bdc3c7;
                    }}
                """
                )

            # --- CHAMPIONNATS ---
            else:
                btn.setText("")
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        outline: none; border-radius: 15px; font-weight: bold;
                        background-color: {COLOR_MAIN};
                        border: 2px solid white;
                    }}
                    QPushButton:hover {{
                        background-color: white;
                        border: 2px solid {COLOR_MAIN};
                    }}
                """
                )

            proxy = self.scene.addWidget(btn)
            proxy.setZValue(5)
            proxy.setPos(x - 15, y - 15)
        self.layout.addWidget(self.view)


class MapPoint(QPushButton):
    """Bouton interactif placé sur la carte."""

    def __init__(
        self,
        name: str,
        code: str,
        mw: "MainWindow",
        parent_scene: QGraphicsScene,
        x: float,
        y: float,
    ) -> None:
        super().__init__()
        self.name = name
        self.code = code
        self.mw = mw
        self.setFixedSize(30, 30)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Création du label
        self.label_item = parent_scene.addText(name)
        self.label_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.label_item.setDefaultTextColor(QColor("#ffffff"))
        self.bg_item = parent_scene.addRect(
            self.label_item.boundingRect(), QPen(Qt.NoPen), QBrush(QColor(0, 0, 0, 180))
        )

        # Positionnement
        txt_x = x - (self.label_item.boundingRect().width() / 2)
        txt_y = y + 18
        self.label_item.setPos(txt_x, txt_y)
        self.bg_item.setPos(txt_x, txt_y)

        self.label_item.hide()
        self.bg_item.hide()
        self.label_item.setZValue(10)
        self.bg_item.setZValue(9)

        self.clicked.connect(lambda: self.mw.navigate_to(self.code, "championnat"))

    def enterEvent(self, event: QEvent) -> None:
        self.label_item.show()
        self.bg_item.show()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.label_item.hide()
        self.bg_item.hide()
        super().leaveEvent(event)


class LeaguePage(BasePage):
    """Page affichant le classement d'un championnat."""

    def __init__(self, mw: "MainWindow") -> None:
        super().__init__(mw)
        top = QHBoxLayout()
        self.title = QLabel("Championnat", objectName="page_title")

        self.combo = QComboBox()
        seasons = sorted(mw.dm.seasons, reverse=True)
        self.combo.addItems([format_season_display(s) for s in seasons])
        self.combo.currentTextChanged.connect(self.update)

        top.addWidget(self.title)
        top.addStretch()
        top.addWidget(QLabel("Saison:"))
        top.addWidget(self.combo)
        self.layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Pos", "Club", "Pts", "BP", "BC", "Diff"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Empêche l'édition
        self.table.cellClicked.connect(self.on_click)
        self.layout.addWidget(self.table)
        self.lid: Optional[str] = None

    def load(self, lid: str) -> None:
        """Charge les données d'une ligue spécifique."""
        self.lid = lid
        self.title.setText(self.mw.dm.leagues.get(lid, lid))
        self.update()

    def update(self) -> None:
        """Met à jour le tableau en fonction de la saison sélectionnée."""
        s_text = self.combo.currentText()
        if not s_text:
            return
        s = parse_season_from_display(s_text)
        df = self.mw.dm.df_games[
            (self.mw.dm.df_games["competition_id"] == self.lid)
            & (self.mw.dm.df_games["season"] == s)
        ]
        res = {}
        for _, r in df.iterrows():
            h, a = int(r["home_club_id"]), int(r["away_club_id"])
            try:
                hg, ag = int(r["home_club_goals"]), int(r["away_club_goals"])
            except (ValueError, TypeError):
                hg, ag = 0, 0

            for t in [h, a]:
                if t not in res:
                    res[t] = {"p": 0, "bp": 0, "bc": 0, "cj": 0}

            res[h]["bp"] += hg
            res[h]["bc"] += ag
            res[a]["bp"] += ag
            res[a]["bc"] += hg

            if hg > ag:
                res[h]["p"] += 3
            elif ag > hg:
                res[a]["p"] += 3
            else:
                res[h]["p"] += 1
                res[a]["p"] += 1

        standings = []
        for cid, d in res.items():
            short_name = self.mw.dm.get_club_name(cid, short=True)
            standings.append({"id": cid, "name": short_name, **d})

        # Tri par points puis différence de buts
        standings.sort(key=lambda x: (x["p"], x["bp"] - x["bc"]), reverse=True)

        self.table.setRowCount(len(standings))
        for i, row in enumerate(standings):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))

            # Nom du club
            it = QTableWidgetItem(str(row["name"]))
            it.setData(Qt.UserRole, row["id"])
            it.setForeground(QColor(COLOR_LINK))
            self.table.setItem(i, 1, it)

            self.table.setItem(i, 2, QTableWidgetItem(str(row["p"])))
            self.table.setItem(i, 3, QTableWidgetItem(str(row["bp"])))
            self.table.setItem(i, 4, QTableWidgetItem(str(row["bc"])))
            self.table.setItem(
                i, 5, QTableWidgetItem(str(row["bp"] - row["bc"]))
            )

    def on_click(self, r: int, c: int) -> None:
        """Gère le clic sur un club pour naviguer vers sa page."""
        if c == 1:
            item = self.table.item(r, 1)
            if item:
                cid = item.data(Qt.UserRole)
                self.mw.navigate_to(cid, "club")


# --- WIDGET DE DESSIN DE L'ARBRE ---
class CupBracketWidget(QGraphicsView):
    """Vue graphique affichant l'arbre de tournoi (Bracket)."""

    def __init__(self, mw: "MainWindow", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.mw = mw

        # --- CONFIGURATION ZOOM & PAN ---
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(
            QGraphicsView.ScrollHandDrag
        )  # Active le déplacement au clic-glissé
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.box_w = 180
        self.box_h = 70
        self.dx = 60
        self.dy = 30

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Gestion du zoom avec la molette."""
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self.scale(zoom_factor, zoom_factor)

    def draw_bracket(self, bracket_data: List[List[Dict[str, Any]]]) -> None:
        """
        Dessine l'arbre complet du tournoi.

        Args:
            bracket_data: Liste de listes de matchs (ex: [Huitièmes, Quarts, Demies...]).
        """
        self.scene.clear()
        self.resetTransform()

        if not bracket_data:
            return
        prev_level_nodes = []

        for col, matches in enumerate(bracket_data):
            current_level_nodes = []
            x = col * (self.box_w + self.dx)
            for row, m_info in enumerate(matches):
                if col == 0:
                    y = row * (self.box_h + self.dy)
                else:
                    idx1, idx2 = row * 2, row * 2 + 1
                    if idx2 < len(prev_level_nodes):
                        y = (
                            prev_level_nodes[idx1][1] + prev_level_nodes[idx2][1]
                        ) / 2
                    else:
                        y = row * (self.box_h + self.dy) * (2**col)

                self.draw_match_box(x, y, m_info)
                current_level_nodes.append((x, y))

                if col > 0 and (row * 2 + 1) < len(prev_level_nodes):
                    child1_x = prev_level_nodes[row * 2][0] + self.box_w
                    child1_y = prev_level_nodes[row * 2][1] + self.box_h / 2
                    child2_y = prev_level_nodes[row * 2 + 1][1] + self.box_h / 2
                    mid_x = child1_x + self.dx / 2
                    pen = QPen(QColor("#cbd5e0"), 2)
                    self.scene.addLine(child1_x, child1_y, mid_x, child1_y, pen)
                    self.scene.addLine(child1_x, child2_y, mid_x, child2_y, pen)
                    self.scene.addLine(mid_x, child1_y, mid_x, child2_y, pen)
                    self.scene.addLine(mid_x, y + self.box_h / 2, x, y + self.box_h / 2, pen)

            prev_level_nodes = current_level_nodes

        rect = self.scene.itemsBoundingRect().adjusted(-100, -100, 100, 100)
        self.setSceneRect(rect)
        self.fitInView(rect, Qt.KeepAspectRatio)

    def draw_match_box(self, x: float, y: float, m: Dict[str, Any]) -> None:
        """Dessine une boîte individuelle pour un match."""
        # Fond de la boîte
        self.scene.addRect(
            x, y, self.box_w, self.box_h, QPen(QColor("#cbd5e0")), QBrush(Qt.white)
        )

        # Couleurs
        green = "#27ae60"
        red = "#e74c3c"
        blue_link = "#3498db"
        gray = QColor("#7f8c8d")

        # Récupération des données
        s1_total = m.get("s1_1", 0)
        s2_total = m.get("s1_2", 0)
        is_double = m.get("is_double", False)

        # --- LOGIQUE DU VAINQUEUR ---
        winner = 0  # 0: nul, 1: équipe 1, 2: équipe 2

        if s1_total > s2_total:
            winner = 1
        elif s2_total > s1_total:
            winner = 2
        elif is_double:
            away_goals_t1 = m.get("s2_1", 0)
            away_goals_t2 = m.get("s1_2_raw", 0)

            if away_goals_t1 > away_goals_t2:
                winner = 1
            elif away_goals_t2 > away_goals_t1:
                winner = 2

        # --- ÉQUIPE 1 ---
        btn1 = QPushButton(str(m.get("team1", "???")))
        color1 = green if winner == 1 else (red if winner == 2 else "#1a3150")
        btn1.setStyleSheet(
            f"QPushButton {{ color: {color1}; background: transparent; border: none; font-weight: bold; text-align: left; padding: 0px; }} "
            f"QPushButton:hover {{ color: {blue_link}; text-decoration: underline; }}"
        )
        btn1.setCursor(Qt.PointingHandCursor)
        btn1.setFixedWidth(int(self.box_w - 10))
        btn1.clicked.connect(lambda: self.mw.navigate_to(m.get("t1_id"), "club"))

        proxy1 = self.scene.addWidget(btn1)
        proxy1.setPos(x + 5, y + 2)

        # --- ÉQUIPE 2 ---
        btn2 = QPushButton(str(m.get("team2", "???")))
        color2 = green if winner == 2 else (red if winner == 1 else "#1a3150")
        btn2.setStyleSheet(
            f"QPushButton {{ color: {color2}; background: transparent; border: none; font-weight: bold; text-align: left; padding: 0px; }} "
            f"QPushButton:hover {{ color: {blue_link}; text-decoration: underline; }}"
        )
        btn2.setCursor(Qt.PointingHandCursor)
        btn2.setFixedWidth(int(self.box_w - 10))
        btn2.clicked.connect(lambda: self.mw.navigate_to(m.get("t2_id"), "club"))

        proxy2 = self.scene.addWidget(btn2)
        proxy2.setPos(x + 5, y + 42)

        # --- AFFICHAGE DES SCORES ---
        if is_double:
            # Aller (Score du match 1)
            aller_txt = self.scene.addText(
                f"{m.get('s1_1_raw', 0)}-{m.get('s1_2_raw', 0)}"
            )
            aller_txt.setPos(x + 8, y + 22)
            aller_txt.setDefaultTextColor(gray)
            aller_txt.setFont(QFont("Segoe UI", 8))

            # TOTAL (Cumulé)
            total_txt = self.scene.addText(f"{s1_total}-{s2_total}")
            total_txt.setPos(x + (self.box_w / 2) - 18, y + 22)
            total_txt.setFont(QFont("Segoe UI", 9, QFont.Bold))
            # Si gagné aux buts à l'extérieur
            if s1_total == s2_total and winner != 0:
                total_txt.setDefaultTextColor(QColor(blue_link))

            # Retour (Score du match 2)
            retour_txt = self.scene.addText(f"{m.get('s2_1', 0)}-{m.get('s2_2', 0)}")
            retour_txt.setPos(x + self.box_w - 45, y + 22)
            retour_txt.setDefaultTextColor(gray)
            retour_txt.setFont(QFont("Segoe UI", 8))
        else:
            # Match unique
            st = self.scene.addText(f"{s1_total} - {s2_total}")
            st.setPos(x + (self.box_w / 2) - 20, y + 22)
            st.setFont(QFont("Segoe UI", 9, QFont.Bold))
            st.setDefaultTextColor(QColor("#1a3150"))


# --- FENÊTRE DE DÉTAILS DES MATCHS ---
class MatchDetailsDialog(QDialog):
    """Dialogue listant les matchs d'une équipe donnée."""

    def __init__(
        self,
        team_name: str,
        matches_df: pd.DataFrame,
        mw: "MainWindow",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Détails des matchs : {team_name}")
        self.setMinimumSize(700, 450)
        self.mw = mw
        self.dm = mw.dm

        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Match", "Score", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        for _, m in matches_df.sort_values("date", ascending=False).iterrows():
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Date
            self.table.setItem(row, 0, QTableWidgetItem(str(m["date"])))

            # Match
            h_short = self.dm.get_club_name(m["home_club_id"], short=True)
            a_short = self.dm.get_club_name(m["away_club_id"], short=True)
            match_text = f"{h_short} vs {a_short}"
            self.table.setItem(row, 1, QTableWidgetItem(match_text))

            # Score
            h_g = int(m["home_club_goals"]) if pd.notna(m["home_club_goals"]) else 0
            a_g = int(m["away_club_goals"]) if pd.notna(m["away_club_goals"]) else 0
            self.table.setItem(row, 2, QTableWidgetItem(f"{h_g} - {a_g}"))

            # Bouton Stats
            btn = QPushButton("Stats")
            btn.clicked.connect(
                lambda chk, gid=m["game_id"]: MatchDetailDialog(
                    gid, self.mw.dm, self.mw.navigate_to
                ).exec_()
            )
            self.table.setCellWidget(row, 3, btn)

        layout.addWidget(self.table)


# --- PAGE DE COUPE PRINCIPALE ---
class CupPage(BasePage):
    """Page principale pour l'affichage d'une coupe (Groupes + Phase finale)."""

    def __init__(self, mw: "MainWindow") -> None:
        super().__init__(mw)
        self.lid: Optional[str] = None

        # Header
        top = QHBoxLayout()
        self.title = QLabel("Compétition", objectName="page_title")
        self.combo_season = QComboBox()
        self.combo_season.currentTextChanged.connect(self.update)
        top.addWidget(self.title)
        top.addStretch()
        top.addWidget(QLabel("Saison :"))
        top.addWidget(self.combo_season)
        self.layout.addLayout(top)

        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # --- Onglet Phase de Groupes ---
        self.scroll_groups = QScrollArea()
        self.scroll_groups.setWidgetResizable(True)
        self.group_content = QWidget()
        self.group_lay = QVBoxLayout(self.group_content)
        self.scroll_groups.setWidget(self.group_content)

        # --- Onglet Phase Finale ---
        self.knockout_widget = QWidget()
        self.ko_layout = QVBoxLayout(self.knockout_widget)

        view_ctrl = QHBoxLayout()
        self.view_selector = QComboBox()
        self.view_selector.addItems(["Arbre Visuel (Bracket)", "Tableau Liste"])
        self.view_selector.currentIndexChanged.connect(
            lambda i: self.ko_stack.setCurrentIndex(i)
        )
        view_ctrl.addWidget(QLabel("Format d'affichage :"))
        view_ctrl.addWidget(self.view_selector)
        view_ctrl.addStretch()
        self.ko_layout.addLayout(view_ctrl)

        self.ko_stack = QStackedWidget()
        self.bracket_view = CupBracketWidget(mw)
        self.tree_view = QTreeWidget()
        self.tree_view.setHeaderLabels(
            ["Équipe 1", "Aller", "TOTAL", "Retour", "Équipe 2"]
        )
        self.tree_view.setColumnWidth(0, 200)
        self.tree_view.setColumnWidth(4, 200)
        self.tree_view.itemClicked.connect(self.on_tree_click)

        self.ko_stack.addWidget(self.bracket_view)
        self.ko_stack.addWidget(self.tree_view)
        self.ko_layout.addWidget(self.ko_stack)

        self.tabs.addTab(self.scroll_groups, "Phase de Groupes")
        self.tabs.addTab(self.knockout_widget, "Phase Finale")

    def on_group_click(self, row: int, col: int) -> None:
        """Gère le clic sur un club dans les tableaux de groupes."""
        if col == 1:
            table = self.sender()
            item = table.item(row, col)
            club_id = item.data(Qt.UserRole)
            if club_id:
                self.mw.navigate_to(club_id, "club")

    def on_tree_click(self, item: QTreeWidgetItem, col: int) -> None:
        """Gère le clic sur un club dans la liste de phase finale."""
        if col in [0, 4]:
            club_id = item.data(col, Qt.UserRole)
            if club_id:
                self.mw.navigate_to(club_id, "club")

    def load(self, lid: str) -> None:
        """Charge une compétition spécifique."""
        self.lid = lid
        self.title.setText(self.mw.dm.leagues.get(lid, lid))

        self.combo_season.blockSignals(True)
        self.combo_season.clear()
        df_comp = self.mw.dm.df_games[self.mw.dm.df_games["competition_id"] == lid]
        seasons = sorted(df_comp["season"].unique(), reverse=True)
        self.combo_season.addItems([format_season_display(s) for s in seasons])
        self.combo_season.blockSignals(False)

        s_text = self.combo_season.currentText()
        s_val = parse_season_from_display(s_text) if s_text else None

        has_groups = not df_comp[
            (df_comp["season"] == s_val)
            & (df_comp["round"].str.contains("Group", case=False, na=False))
        ].empty

        if not has_groups:
            self.tabs.setTabVisible(0, False)
            self.tabs.setCurrentIndex(1)
        else:
            self.tabs.setTabVisible(0, True)
            self.tabs.setCurrentIndex(0)

        self.update()

    def update(self) -> None:
        """Met à jour les données affichées selon la saison."""
        s_text = self.combo_season.currentText()
        if not s_text:
            return
        s = parse_season_from_display(s_text)

        df = self.mw.dm.df_games[
            (self.mw.dm.df_games["competition_id"] == self.lid)
            & (self.mw.dm.df_games["season"] == s)
        ]

        if self.tabs.isTabVisible(0):
            self.build_groups(df)

        self.build_knockout_data(df)

    def build_groups(self, df: pd.DataFrame) -> None:
        """Construit les tableaux pour la phase de groupes."""
        for i in reversed(range(self.group_lay.count())):
            if self.group_lay.itemAt(i).widget():
                self.group_lay.itemAt(i).widget().setParent(None)

        g_df = df[df["round"].str.contains("Group", case=False, na=False)]
        if g_df.empty:
            return

        unique_rounds = sorted(g_df["round"].unique())

        for g_name in unique_rounds:
            group_container = QFrame()
            group_vbox = QVBoxLayout(group_container)

            display_name = (
                "Classement Général" if len(unique_rounds) == 1 else f"Classement {g_name}"
            )
            lbl = QLabel(display_name)
            lbl.setObjectName("lbl")

            group_vbox.addWidget(lbl)

            stats = {}
            group_matches = g_df[g_df["round"] == g_name]

            for _, r in group_matches.iterrows():
                hid, aid = int(r["home_club_id"]), int(r["away_club_id"])
                try:
                    hg, ag = int(r["home_club_goals"]), int(r["away_club_goals"])
                except (ValueError, TypeError):
                    hg, ag = 0, 0

                for tid in [hid, aid]:
                    if tid not in stats:
                        stats[tid] = {"pts": 0, "mj": 0, "bp": 0, "bc": 0}

                stats[hid]["mj"] += 1
                stats[aid]["mj"] += 1
                stats[hid]["bp"] += hg
                stats[hid]["bc"] += ag
                stats[aid]["bp"] += ag
                stats[aid]["bc"] += hg

                if hg > ag:
                    stats[hid]["pts"] += 3
                elif ag > hg:
                    stats[aid]["pts"] += 3
                else:
                    stats[hid]["pts"] += 1
                    stats[aid]["pts"] += 1

            t = QTableWidget(0, 6)
            t.setHorizontalHeaderLabels(
                ["Pos", "Club", "Pts", "MJ", "Diff", "Détails"]
            )
            t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            t.setEditTriggers(QAbstractItemView.NoEditTriggers)
            t.cellClicked.connect(self.on_group_click)

            sorted_teams = sorted(
                stats.items(),
                key=lambda x: (x[1]["pts"], x[1]["bp"] - x[1]["bc"]),
                reverse=True,
            )

            for i, (tid, d) in enumerate(sorted_teams):
                row = t.rowCount()
                t.insertRow(row)
                t.setItem(row, 0, QTableWidgetItem(str(i + 1)))

                short_name = self.mw.dm.get_club_name(tid, short=True)
                item_name = QTableWidgetItem(short_name)
                item_name.setData(Qt.UserRole, tid)
                item_name.setForeground(QColor("#3498db"))
                t.setItem(row, 1, item_name)

                t.setItem(row, 2, QTableWidgetItem(str(d["pts"])))
                t.setItem(row, 3, QTableWidgetItem(str(d["mj"])))
                t.setItem(row, 4, QTableWidgetItem(str(d["bp"] - d["bc"])))

                team_matches = group_matches[
                    (group_matches["home_club_id"] == tid)
                    | (group_matches["away_club_id"] == tid)
                ].copy()
                btn = QPushButton("Voir Matchs")
                btn.clicked.connect(
                    lambda _, n=short_name, m=team_matches: MatchDetailsDialog(
                        n, m, self.mw
                    ).exec_()
                )
                t.setCellWidget(row, 5, btn)

            row_height = 39
            header_height = 40
            calculated_height = (len(sorted_teams) * row_height) + header_height
            t.setFixedHeight(min(600, calculated_height + 5))

            group_vbox.addWidget(t)
            group_container.setContentsMargins(0, 0, 0, 30)
            self.group_lay.addWidget(group_container)

    def build_knockout_data(self, df: pd.DataFrame) -> None:
        """Prépare et structure les données pour la phase à élimination directe."""
        round_filters = [
            ("Finale", ["^Final$", "^Final 1st leg$", "^Final 2nd leg$"]),
            ("Demies", ["Semi-Finals"]),
            ("Quarts", ["Quarter-Finals"]),
            ("Huitièmes", ["Last 16", "Round of 16", "Eighth-Finals"]),
        ]
        bracket_data_ordered = []
        self.tree_view.clear()

        for label, keywords in round_filters:
            pattern = "|".join(keywords)
            m_df = df[
                df["round"].str.contains(
                    pattern, case=False, na=False, regex=True
                )
            ]
            if m_df.empty:
                continue

            # --- AJOUT AU TABLEAU ---
            round_item = QTreeWidgetItem()
            self.tree_view.addTopLevelItem(round_item)
            round_item.setText(0, label.upper())
            round_item.setBackground(0, QColor("#e2e8f0"))
            round_item.setExpanded(True)

            current_round_matches = []
            processed_matchups = set()

            for _, m in m_df.sort_values("date").iterrows():
                hid, aid = int(m["home_club_id"]), int(m["away_club_id"])
                pair = tuple(sorted([hid, aid]))
                if pair in processed_matchups:
                    continue

                duels = m_df[
                    (
                        (m_df["home_club_id"] == hid)
                        & (m_df["away_club_id"] == aid)
                    )
                    | (
                        (m_df["home_club_id"] == aid)
                        & (m_df["away_club_id"] == hid)
                    )
                ]

                m1_row = duels[
                    duels["round"].str.contains("1st leg", case=False, na=False)
                ]
                m2_row = duels[
                    duels["round"].str.contains("2nd leg", case=False, na=False)
                ]

                child = QTreeWidgetItem(round_item)
                green = QColor("#27ae60")
                red = QColor("#e74c3c")
                blue = QColor("#3498db")

                t1_short = self.mw.dm.get_club_name(hid, short=True)
                t2_short = self.mw.dm.get_club_name(aid, short=True)

                child.setData(0, Qt.UserRole, hid)
                child.setData(4, Qt.UserRole, aid)

                winner = 0

                if not m1_row.empty and not m2_row.empty:
                    r1 = m1_row.iloc[0]
                    r2 = m2_row.iloc[0]
                    s1_h, s1_a = int(r1["home_club_goals"]), int(
                        r1["away_club_goals"]
                    )
                    s2_h, s2_a = int(r2["home_club_goals"]), int(
                        r2["away_club_goals"]
                    )
                    total_1, total_2 = s1_h + s2_a, s1_a + s2_h

                    if total_1 > total_2:
                        winner = 1
                    elif total_2 > total_1:
                        winner = 2
                    else:
                        if s2_a > s1_a:
                            winner = 1
                        elif s1_a > s2_a:
                            winner = 2

                    child.setText(0, t1_short)
                    child.setText(1, f"{s1_h} - {s1_a}")
                    child.setText(2, f"{total_1} - {total_2}")
                    child.setText(3, f"{s2_a} - {s2_h}")
                    child.setText(4, t2_short)

                    if total_1 == total_2 and winner != 0:
                        child.setForeground(2, QBrush(blue))

                    m_info = {
                        "team1": t1_short,
                        "team2": t2_short,
                        "t1_id": hid,
                        "t2_id": aid,
                        "s1_1": total_1,
                        "s1_2": total_2,
                        "s1_1_raw": s1_h,
                        "s1_2_raw": s1_a,
                        "s2_1": s2_a,
                        "s2_2": s2_h,
                        "is_double": True,
                    }
                else:
                    s1, s2 = int(m["home_club_goals"]), int(m["away_club_goals"])
                    if s1 > s2:
                        winner = 1
                    elif s2 > s1:
                        winner = 2
                    child.setText(0, t1_short)
                    child.setText(2, f"{s1} - {s2}")
                    child.setText(4, t2_short)
                    m_info = {
                        "team1": t1_short,
                        "team2": t2_short,
                        "t1_id": hid,
                        "t2_id": aid,
                        "s1_1": s1,
                        "s1_2": s2,
                        "is_double": False,
                    }

                child.setForeground(
                    0,
                    QBrush(
                        green if winner == 1 else (red if winner == 2 else Qt.black)
                    ),
                )
                child.setForeground(
                    4,
                    QBrush(
                        green if winner == 2 else (red if winner == 1 else Qt.black)
                    ),
                )

                current_round_matches.append(m_info)
                processed_matchups.add(pair)

            bracket_data_ordered.insert(0, current_round_matches)

        if bracket_data_ordered:
            self.bracket_view.draw_bracket(bracket_data_ordered)


class ClubPage(BasePage):
    """Page détaillant les infos d'un club (Effectif, Matchs, Mercato)."""

    def __init__(self, mw: "MainWindow") -> None:
        super().__init__(mw)
        top = QHBoxLayout()
        self.title = QLabel("Club", objectName="page_title")
        self.combo = QComboBox()

        seasons = sorted(mw.dm.seasons, reverse=True)
        self.combo.addItems([format_season_display(s) for s in seasons])
        self.combo.currentTextChanged.connect(self.update)

        top.addWidget(self.title)
        top.addStretch()
        top.addWidget(QLabel("Saison:"))
        top.addWidget(self.combo)
        self.layout.addLayout(top)

        self.content_lay = QHBoxLayout()

        self.tabs = QTabWidget()
        self.tab_squad = QTableWidget()
        self.tab_matches = QTableWidget()
        self.tab_mercato = QTableWidget()

        # Connect clicks
        self.tab_squad.cellClicked.connect(self.on_squad_click)
        self.tab_matches.cellClicked.connect(self.on_match_click)
        self.tab_mercato.cellClicked.connect(self.on_mercato_click)

        self.tabs.addTab(self.tab_squad, "Effectif")
        self.tabs.addTab(self.tab_matches, "Matchs")
        self.tabs.addTab(self.tab_mercato, "Mercato")

        self.content_lay.addWidget(self.tabs, stretch=3)
        self.layout.addLayout(self.content_lay)
        self.cid: Optional[int] = None
        self.chart_view: Optional[Any] = None

    def load(self, cid: int) -> None:
        """Charge les données d'un club donné."""
        self.cid = cid
        c_info = self.mw.dm.df_clubs[self.mw.dm.df_clubs["club_id"] == cid].iloc[0]
        self.title.setText(c_info["name"])
        if self.chart_view:
            self.chart_view.deleteLater()
            self.chart_view = None
        self.update()

    def update(self) -> None:
        """Met à jour les onglets selon la saison sélectionnée."""
        s_text = self.combo.currentText()
        if not s_text:
            return
        s = parse_season_from_display(s_text)
        cid = self.cid

        # 1. SQUAD
        apps = self.mw.dm.df_appearances.merge(
            self.mw.dm.df_games[["game_id", "season"]], on="game_id"
        )
        pids = apps[(apps["player_club_id"] == cid) & (apps["season"] == s)][
            "player_id"
        ].unique()
        squad = self.mw.dm.df_players[self.mw.dm.df_players["player_id"].isin(pids)]

        self.tab_squad.setRowCount(len(squad))
        self.tab_squad.setColumnCount(5)
        self.tab_squad.setHorizontalHeaderLabels(
            ["Nom", "Âge", "Poste", "Valeur", "Nat."]
        )
        self.tab_squad.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        for i, (_, p) in enumerate(squad.iterrows()):
            # Colonne 0 : Nom
            it = QTableWidgetItem(str(p["name"]))
            it.setData(Qt.UserRole, p["player_id"])
            it.setForeground(QColor(COLOR_LINK))
            self.tab_squad.setItem(i, 0, it)

            # Colonne 1 : Âge
            age = p["age"]
            age_val = f"{int(age)} ans" if pd.notna(age) else "-"
            age_item = QTableWidgetItem(age_val)
            age_item.setTextAlignment(Qt.AlignCenter)
            self.tab_squad.setItem(i, 1, age_item)

            # Colonne 2 : Poste
            poste_val = str(p.get("sub_position", "-"))
            poste_item = QTableWidgetItem(poste_val)
            poste_item.setTextAlignment(Qt.AlignCenter)
            self.tab_squad.setItem(i, 2, poste_item)

            # Colonne 3 : Valeur Marchande
            v = (
                f"{p['market_value_in_eur'] / 1e6:.1f}M€"
                if pd.notna(p["market_value_in_eur"])
                else "-"
            )
            v_item = QTableWidgetItem(v)
            v_item.setTextAlignment(Qt.AlignCenter)
            self.tab_squad.setItem(i, 3, v_item)

            # Colonne 4 : Nationalité/Drapeau
            nat_name = str(p["country_of_citizenship"])
            flag_label = create_flag_label(self.mw, nat_name)
            self.tab_squad.setCellWidget(i, 4, flag_label)

        # 2. MATCHS
        games = self.mw.dm.df_games[
            (
                (self.mw.dm.df_games["home_club_id"] == cid)
                | (self.mw.dm.df_games["away_club_id"] == cid)
            )
            & (self.mw.dm.df_games["season"] == s)
        ].sort_values("date", ascending=False)
        self.tab_matches.setRowCount(len(games))
        self.tab_matches.setColumnCount(5)
        self.tab_matches.setHorizontalHeaderLabels(
            ["Date", "Adv.", "Score", "Adv.", "Détails"]
        )

        for i, (_, g) in enumerate(games.iterrows()):
            self.tab_matches.setItem(i, 0, QTableWidgetItem(str(g["date"])))
            h_name = self.mw.dm.get_club_name(g["home_club_id"], short=True)
            a_name = self.mw.dm.get_club_name(g["away_club_id"], short=True)

            h_it = QTableWidgetItem(h_name)
            h_it.setData(Qt.UserRole, g["home_club_id"])
            h_it.setForeground(QColor(COLOR_LINK))
            self.tab_matches.setItem(i, 1, h_it)

            self.tab_matches.setItem(
                i,
                2,
                QTableWidgetItem(
                    f"{int(g['home_club_goals'])}-{int(g['away_club_goals'])}"
                ),
            )

            a_it = QTableWidgetItem(a_name)
            a_it.setData(Qt.UserRole, g["away_club_id"])
            a_it.setForeground(QColor(COLOR_LINK))
            self.tab_matches.setItem(i, 3, a_it)

            btn = QPushButton("Stats")
            btn.clicked.connect(
                lambda chk, gid=g["game_id"]: MatchDetailDialog(
                    gid, self.mw.dm, self.mw.navigate_to
                ).exec_()
            )
            self.tab_matches.setCellWidget(i, 4, btn)

        # 3. MERCATO
        tr = self.mw.dm.df_transfers[
            (
                (self.mw.dm.df_transfers["from_club_id"] == cid)
                | (self.mw.dm.df_transfers["to_club_id"] == cid)
            )
            & (self.mw.dm.df_transfers["season"] == s)
        ]
        self.tab_mercato.setRowCount(len(tr))
        self.tab_mercato.setColumnCount(4)
        self.tab_mercato.setHorizontalHeaderLabels(
            ["Joueur", "Type", "Partenaire", "Prix"]
        )

        for i, (_, t) in enumerate(tr.iterrows()):
            it = QTableWidgetItem(str(t["player_name"]))
            it.setData(Qt.UserRole, t["player_id"])
            it.setForeground(QColor(COLOR_LINK))
            self.tab_mercato.setItem(i, 0, it)

            is_arr = t["to_club_id"] == cid
            m_type = "Arrivée" if is_arr else "Départ"
            item_type = QTableWidgetItem(m_type)
            item_type.setForeground(QColor("green" if is_arr else "red"))
            self.tab_mercato.setItem(i, 1, item_type)

            other = str(t["from_club_name"]) if is_arr else str(t["to_club_name"])
            oid = t["from_club_id"] if is_arr else t["to_club_id"]
            oit = QTableWidgetItem(other)
            oit.setData(Qt.UserRole, oid)
            oit.setForeground(QColor(COLOR_LINK))
            self.tab_mercato.setItem(i, 2, oit)

            p = (
                f"{t['transfer_fee'] / 1e6:.1f}M€"
                if pd.notna(t["transfer_fee"])
                else "-"
            )
            self.tab_mercato.setItem(i, 3, QTableWidgetItem(p))

    def on_squad_click(self, r: int, c: int) -> None:
        if c == 0:
            self.mw.navigate_to(self.tab_squad.item(r, 0).data(Qt.UserRole), "joueur")

    def on_match_click(self, r: int, c: int) -> None:
        if c in [1, 3]:
            self.mw.navigate_to(self.tab_matches.item(r, c).data(Qt.UserRole), "club")

    def on_mercato_click(self, r: int, c: int) -> None:
        if c == 0:
            self.mw.navigate_to(self.tab_mercato.item(r, 0).data(Qt.UserRole), "joueur")
        if c == 2:
            self.mw.navigate_to(self.tab_mercato.item(r, 2).data(Qt.UserRole), "club")


class PlayerPage(BasePage):
    """Page affichant les statistiques et l'historique d'un joueur."""

    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)
        self.pid: Optional[int] = None

        # --- EN-TÊTE ---
        header_layout = QHBoxLayout()
        self.title = QLabel("Joueur")
        self.title.setObjectName("page_title")
        header_layout.addWidget(self.title)
        header_layout.addStretch()

        self.layout.addLayout(header_layout)

        # --- CARTES DE STATS ---
        stats_box = QHBoxLayout()

        # On utilise les noms de variables de ta version précédente pour la compatibilité
        self.card_goals_lay, self.card_g = self.create_stat_card("Buts", "0")
        self.card_assists_lay, self.card_a = self.create_stat_card("Passes D.", "0")
        self.card_value_lay, self.card_v = self.create_stat_card("Valeur", "-")
        self.card_pos_lay, self.card_p = self.create_stat_card("Poste", "-")

        stats_box.addLayout(self.card_goals_lay)
        stats_box.addLayout(self.card_assists_lay)
        stats_box.addStretch()
        stats_box.addLayout(self.card_value_lay)
        stats_box.addSpacing(20)
        stats_box.addLayout(self.card_pos_lay)

        self.layout.addLayout(stats_box)

        self.layout.addWidget(QLabel("<b>Historique & Stats par saison :</b>"))

        # --- CONTENU PRINCIPAL ---
        self.content_layout = QHBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(5)  # Ajout de la colonne Minutes
        self.table.setMouseTracking(True)

        self.table.setHorizontalHeaderLabels(
            ["Saison", "Club", "Buts", "Passes", "Min"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.cellClicked.connect(self.on_click)

        self.content_layout.addWidget(self.table, stretch=2)

        # Canvas pour le graphique interne
        self.canvas: Optional[FigureCanvas] = None
        self.layout.addLayout(self.content_layout)

    def create_stat_card(self, label: str, value: str) -> Tuple[QVBoxLayout, QLabel]:
        """Crée une carte de stat et retourne le layout ET le label de valeur pour mise à jour ultérieure."""
        l = QVBoxLayout()
        val_lbl = QLabel(value)
        val_lbl.setObjectName("stat_val")

        lbl_lbl = QLabel(label.upper())
        lbl_lbl.setObjectName("lbl_lbl")

        l.addWidget(val_lbl, alignment=Qt.AlignCenter)
        l.addWidget(lbl_lbl, alignment=Qt.AlignCenter)
        return l, val_lbl

    def load(self, pid: int) -> None:
        """Charge les données d'un joueur."""
        self.pid = pid
        # 1. Récupération des infos générales du joueur
        p_info = self.mw.dm.df_players[self.mw.dm.df_players["player_id"] == pid].iloc[
            0
        ]

        # Mise à jour du titre principal
        pos = p_info.get("sub_position", "-")
        self.title.setText(f"{p_info['name']}")

        # 2. Mise à jour du Poste
        self.card_p.setText(str(pos))

        # 3. Mise à jour de la Valeur
        val = p_info.get("market_value_in_eur")
        if pd.notna(val) and val > 0:
            val_display = f"{val / 1e6:.1f}M€"
        else:
            val_display = "-"
        self.card_v.setText(val_display)

        # --- LOGIQUE DE STATISTIQUES ---
        apps = self.mw.dm.df_appearances[self.mw.dm.df_appearances["player_id"] == pid]

        if not apps.empty:
            apps = apps.merge(
                self.mw.dm.df_games[["game_id", "season"]], on="game_id"
            )
            apps = apps.merge(
                self.mw.dm.df_clubs[["club_id", "name"]],
                left_on="player_club_id",
                right_on="club_id",
            )

            agg = (
                apps.groupby(["season", "club_id", "name"])
                .agg({"goals": "sum", "assists": "sum", "minutes_played": "sum"})
                .reset_index()
                .sort_values("season", ascending=False)
            )

            # Mise à jour des cartes Buts et Passes
            self.card_g.setText(str(int(agg["goals"].sum())))
            self.card_a.setText(str(int(agg["assists"].sum())))

            # Remplissage du tableau
            self.table.setRowCount(len(agg))
            for i, (_, row) in enumerate(agg.iterrows()):
                self.table.setItem(i, 0, QTableWidgetItem(f"{int(row['season'])}"))
                c_it = QTableWidgetItem(str(row["name"]))
                c_it.setData(Qt.UserRole, row["club_id"])
                c_it.setForeground(QColor(COLOR_LINK))  # Ou COLOR_LINK si défini
                self.table.setItem(i, 1, c_it)
                self.table.setItem(i, 2, QTableWidgetItem(str(int(row["goals"]))))
                self.table.setItem(i, 3, QTableWidgetItem(str(int(row["assists"]))))
                self.table.setItem(
                    i, 4, QTableWidgetItem(str(int(row["minutes_played"])))
                )
        else:
            # Si aucune stat, on remet les compteurs à 0
            self.card_g.setText("0")
            self.card_a.setText("0")
            self.table.setRowCount(0)

    def on_click(self, r: int, c: int) -> None:
        if c == 1:
            self.mw.navigate_to(self.table.item(r, 1).data(Qt.UserRole), "club")


class SuggestionPage(BasePage):
    """Page de résultats de recherche."""

    def __init__(self, mw: "MainWindow") -> None:
        super().__init__(mw)
        self.title = QLabel("Résultats", objectName="page_title")
        self.layout.addWidget(self.title)
        self.table = QTableWidget()
        self.table.cellClicked.connect(self.on_click)
        self.layout.addWidget(self.table)
        self.mode = "joueur"

    def load_players(self, df: pd.DataFrame) -> None:
        """Affiche la liste des joueurs trouvés."""
        self.mode = "joueur"
        self.title.setText(f"Joueurs trouvés ({len(df)})")
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Nom", "Age", "Poste", "Valeur", "Nat."])
        self.table.setRowCount(len(df))
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i, (_, r) in enumerate(df.iterrows()):
            it = QTableWidgetItem(str(r["name"]))
            it.setData(Qt.UserRole, r["player_id"])
            it.setForeground(QColor(COLOR_LINK))
            self.table.setItem(i, 0, it)

            nat_name = str(r["country_of_citizenship"])
            flag_label = create_flag_label(self.mw, nat_name)

            self.table.setItem(i, 1, QTableWidgetItem(""))
            age_val = r["age"]
            age_str = f"{int(age_val)} ans" if pd.notna(age_val) else "-"
            self.table.setItem(i, 1, QTableWidgetItem(age_str))
            self.table.setItem(i, 2, QTableWidgetItem(str(r["position"])))
            self.table.setItem(
                i,
                3,
                QTableWidgetItem(
                    f"{r['market_value_in_eur'] / 1e6:.1f}M€"
                    if pd.notna(r["market_value_in_eur"])
                    else "-"
                ),
            )
            self.table.setCellWidget(i, 4, flag_label)

    def load_clubs(self, df: pd.DataFrame) -> None:
        """Affiche la liste des clubs trouvés."""
        self.mode = "club"
        self.title.setText(f"Clubs trouvés ({len(df)})")
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Nom", "Stade"])
        self.table.setRowCount(len(df))
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i, (_, r) in enumerate(df.iterrows()):
            it = QTableWidgetItem(str(r["name"]))
            it.setData(Qt.UserRole, r["club_id"])
            it.setForeground(QColor(COLOR_LINK))
            self.table.setItem(i, 0, it)
            self.table.setItem(
                i, 1, QTableWidgetItem(str(r.get("stadium_name", "-")))
            )

    def on_click(self, r: int, c: int) -> None:
        if c == 0:
            uid = self.table.item(r, 0).data(Qt.UserRole)
            self.mw.navigate_to(uid, self.mode)