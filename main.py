import sys
import re
import pandas as pd
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple, Union
import requests

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QCompleter,
    QFrame,
    QListWidget,
    QMessageBox,
    QAbstractItemView,
    QStyledItemDelegate,
    QFormLayout,
    QSpinBox,
    QDialog,
    QTabWidget,
    QDialogButtonBox,
)
from PyQt5.QtCore import Qt, QModelIndex, QEvent
from PyQt5.QtGui import QFont, QPixmap, QImage, QColor

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# --- CONSTANTES DE STYLE ---
COLOR_MAIN = "#ffa45f"  # Orange
COLOR_SIDEBAR = "#1a3150"  # Bleu foncé professionnel
COLOR_BG = "#f5f6f8"  # Gris très clair fond
COLOR_LINK = "#005ca8"  # Bleu lien

STYLE_SHEET = f"""
QMainWindow {{ background-color: {COLOR_BG}; }}

/* Sidebar */
QFrame#sidebar {{ background-color: {COLOR_SIDEBAR}; min-width: 200px; max-width: 200px; }}
QLabel#side_title {{ color: white; font-weight: bold; font-size: 14px; margin-top: 10px; }}
QListWidget {{ background: transparent; border: none; color: #cbd5e1; font-size: 12px; }}
QListWidget::item:hover {{ color: white; background: rgba(255,255,255,0.1); }}

/* Top Bar */
QFrame#top_bar {{ background-color: white; border-bottom: 2px solid {COLOR_MAIN}; }}
QLineEdit#search_bar {{
    border: 1px solid #cbd5e1; border-radius: 4px; padding: 6px 12px; font-size: 14px; color: #334155;
}}

/* Navigation Buttons */
QPushButton#nav_btn {{
    background-color: rgba(255,255,255,0.1); color: white; border-radius: 4px; border: none; font-weight: bold;
}}
QPushButton#nav_btn:hover {{ background-color: {COLOR_MAIN}; color: black; }}

/* Headings */
QLabel#page_title {{ font-size: 26px; font-weight: 800; color: {COLOR_SIDEBAR}; }}
QLabel#stat_val {{ font-size: 22px; font-weight: bold; color: {COLOR_MAIN}; }}

/* Tables */
QTableWidget {{
    border: 1px solid #e2e8f0; border-radius: 6px; background: white; gridline-color: #f1f5f9;
}}
QHeaderView::section {{
    background-color: #f8fafc; color: {COLOR_SIDEBAR}; font-weight: bold; padding: 8px; border: none;
}}
QTableWidget::item:hover {{
    background-color: #eef2f7;
}}

QPushButton#clear_btn {{
    background-color: #e11d48;
    color: white;
    border-radius: 4px;
    padding: 4px;
    font-size: 10px;
    margin-top: 5px;
}}

QPushButton#search_btn {{
    background-color: {COLOR_MAIN};
    border-radius: 4px;
    padding: 5px;
}}
QPushButton#search_btn:hover {{
    background-color: #ff8c33;
}}

QPushButton#filter_btn {{
    background-color: {COLOR_SIDEBAR};
    color: white;
    border-radius: 4px;
    padding: 5px 10px;
    font-weight: bold;
}}
QPushButton#filter_btn:hover {{
    background-color: #2c5282;
}}
"""

# --- DICTIONNAIRE DES DRAPEAUX ---
COUNTRY_CODES: Dict[str, str] = {
    "Espagne": "es",
    "Angleterre": "gb-eng",
    "France": "fr",
    "Allemagne": "de",
    "Italie": "it",
    "Portugal": "pt",
    "Pays-Bas": "nl",
    "Belgique": "be",
    "Suède": "se",
    "Norvège": "no",
    "Danemark": "dk",
    "Pologne": "pl",
    "Russie": "ru",
    "Ukraine": "ua",
    "Serbie": "rs",
    "Albanie": "al",
    "Croatie": "hr",
    "Grèce": "gr",
    "Turquie": "tr",
    "Türkiye": "tr",
    "Roumanie": "ro",
    "Tchéquie": "cz",
    "Hongrie": "hu",
    "Slovaquie": "sk",
    "Slovénie": "si",
    "Bosnie": "ba",
    "Bulgarie": "bg",
    "Autriche": "at",
    "Suisse": "ch",
    "Écosse": "gb-sct",
    "Pays de Galles": "gb-wls",
    "Brésil": "br",
    "Argentine": "ar",
    "Uruguay": "uy",
    "Colombie": "co",
    "Venezuela": "ve",
    "Mexique": "mx",
    "États-Unis": "us",
    "Canada": "ca",
    "Jamaïque": "jm",
    "Équateur": "ec",
    "Paraguay": "py",
    "Chili": "cl",
    "Pérou": "pe",
    "Bolivie": "bo",
    "Syrie": "sy",
    "Japon": "jp",
    "Corée du Sud": "kr",
    "Chine": "cn",
    "Australie": "au",
    "Mauritanie": "mr",
    "Cameroun": "cm",
    "Nigeria": "ng",
    "Ghana": "gh",
    "Sénégal": "sn",
    "Maroc": "ma",
    "Égypte": "eg",
    "Côte d'Ivoire": "ci",
    "Mali": "ml",
    "Burkina Faso": "bf",
    "Comores": "km",
    "Guinée": "gn",
    "Tunisie": "tn",
    "Algérie": "dz",
    "RD Congo": "cd",
    "République Centrafricaine": "cf",
    "Congo": "cg",
    "Afrique du Sud": "za",
    "Kenya": "ke",
    "Ouganda": "ug",
    "Soudan": "sd",
    "Guinée Équatoriale": "gq",
    "Gabon": "ga",
    "Angola": "ao",
    "Bénin": "bj",
    "Kazakhstan": "kz",
    "Arabie Saoudite": "sa",
    "Émirats Arabes Unis": "ae",
    "Israël": "il",
    "Liban": "lb",
    "Géorgie": "ge",
    "Ouzbékistan": "uz",
    "Gambie": "gm",
    "Suriname": "sr",
    "Haïti": "ht",
    "Curaçao": "cw",
    "Aruba": "aw",
    "Guadeloupe": "gp",
    "Martinique": "mq",
    "Togo": "tg",
    "Libéria": "lr",
    "Sierra Leone": "sl",
    "Niger": "ne",
    "Érythrée": "er",
    "Éthiopie": "et",
    "Zambie": "zm",
    "Zimbabwe": "zw",
    "Guinée-Bissau": "gw",
    "Mozambique": "mz",
    "Irlande du Nord": "gb-nir",
    "Irlande": "ie",
    "Finlande": "fi",
    "Islande": "is",
    "Luxembourg": "lu",
    "Malte": "mt",
    "Chypre": "cy",
    "Macédoine du Nord": "mk",
    "Gibraltar": "gi",
    "Thaïlande": "th",
    "Vietnam": "vn",
    "Philippines": "ph",
    "Indonésie": "id",
    "Malaisie": "my",
    "Singapour": "sg",
    "Inde": "in",
    "Pakistan": "pk",
    "Bangladesh": "bd",
    "Nouvelle-Zélande": "nz",
    "Fidji": "fj",
    "El Salvador": "sv",
    "Costa Rica": "cr",
    "Honduras": "hn",
    "Guatemala": 'gt',
    "Nicaragua": 'ni',
    "Panama": 'pa',
    "République Dominicaine": 'do',
    "Saint-Christophe-et-Niévès": 'kn',
    "Barbade": 'bb',
    "Trinité-et-Tobago": 'tt',
    "Irak": 'iq',
    "Iran": 'ir',
    "Qatar": 'qa',
    "Koweït": 'kw',
    "Bahreïn": 'bh',
    "Oman": 'om',
    "Afghanistan": 'af',
}


# --- GESTION DES DONNÉES ---
class DataManager:
    """Gère le chargement, le parsing et le filtrage des données CSV."""

    def __init__(self) -> None:
        self.df_clubs_season: pd.DataFrame = pd.DataFrame()
        self.df_clubs_profile: pd.DataFrame = pd.DataFrame()
        self.df_joueurs: pd.DataFrame = pd.DataFrame()
        self.players_stats_parsed: pd.DataFrame = pd.DataFrame()
        self.flag_cache: Dict[str, QPixmap] = {}

    def format_currency(self, value: Union[float, str, int]) -> str:
        """Formate une valeur numérique en chaîne monétaire (ex: 1.5M €)."""
        if pd.isna(value) or value == "" or value == 0:
            return "Retraite"
        try:
            val = float(value)
            if val >= 1_000_000:
                return f"{val / 1_000_000:.1f}M €"
            if val >= 1_000:
                return f"{val / 1_000:.0f}K €"
            return f"{val:.0f} €"
        except (ValueError, TypeError):
            return str(value)

    def load_data(self) -> bool:
        """Charge les fichiers CSV nécessaires à l'application."""
        try:
            self.df_clubs_season = pd.read_csv("clubs_par_saisons.csv")
            self.df_clubs_profile = pd.read_csv("clubs_profile.csv")
            self.df_joueurs = pd.read_csv("joueurs.csv")

            # Calcul de l'âge centralisé
            def calculate_age_display(dob: Any) -> str:
                if pd.isna(dob) or dob == "":
                    return "-"
                try:
                    birth_date = datetime.strptime(str(dob), "%Y-%m-%d")
                    today = datetime.today()
                    age = (
                        today.year
                        - birth_date.year
                        - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    )
                    return f"{age} ans"
                except ValueError:
                    return "-"

            self.df_joueurs["age_display"] = self.df_joueurs["dateOfBirth"].apply(
                calculate_age_display
            )
            self.df_clubs_season["Saison"] = self.df_clubs_season["Saison"].astype(str)
            self._parse_player_history()
            return True
        except Exception as e:
            print(f"Erreur chargement CSV: {e}")
            return False

    def get_flag_pixmap(self, country_name: str) -> Optional[QPixmap]:
        """Récupère et met en cache l'image du drapeau pour un pays donné."""
        code = COUNTRY_CODES.get(country_name)
        if not code:
            return None
        if code in self.flag_cache:
            return self.flag_cache[code]
        try:
            url = f"https://flagcdn.com/w40/{code}.png"
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                scaled_pixmap = pixmap.scaled(
                    25, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.flag_cache[code] = scaled_pixmap
                return scaled_pixmap
        except requests.RequestException:
            pass
        return None

    def _parse_player_history(self) -> None:
        """Parse l'historique textuel des joueurs pour créer un DataFrame structuré."""
        regex = r"(.+?)\s\((\d{4}-\d{4})\):\s*(\d+)B,\s*(\d+)PD"
        data = []
        for _, row in self.df_joueurs.iterrows():
            raw_hist = str(row["Historique_Clubs_Stats"])
            if raw_hist == "nan":
                continue
            blocks = raw_hist.split("|")
            for block in blocks:
                match = re.search(regex, block.strip())
                if match:
                    data.append(
                        {
                            "name": row["name"],
                            "club": match.group(1).strip(),
                            "season": match.group(2).strip(),
                            "goals": int(match.group(3)),
                            "assists": int(match.group(4)),
                            "portraitUrl": row["portraitUrl"],
                            "position": row["positionName"],
                            "market_value": float(row.get("currentMarketValue", 0)),
                            "nationality": row["Nationalité 1"],
                        }
                    )
        self.players_stats_parsed = pd.DataFrame(data)

    def filtre_joueurs(
        self,
        nom: Optional[str] = None,
        equipe: Optional[str] = None,
        nationalite: Optional[str] = None,
        poste: Optional[str] = None,
        age_min: Optional[int] = None,
        age_max: Optional[int] = None,
        buts_min: Optional[int] = None,
        buts_max: Optional[int] = None,
        passes_min: Optional[int] = None,
        passes_max: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Filtre la liste des joueurs en fonction des critères spécifiés.
        """

        def test_nom(nom_joueur: str) -> bool:
            return nom.lower() in str(nom_joueur).lower() if nom else True

        def test_equipe(historique: Any) -> bool:
            if isinstance(historique, list) and len(historique) > 0:
                for season in historique:
                    if equipe and equipe.lower() in season.lower():
                        return True
            return False

        def calcul_age_int(date_of_birth: Any) -> int:
            try:
                if pd.isna(date_of_birth):
                    return -1
                today = date.today()
                dob = datetime.strptime(str(date_of_birth), "%Y-%m-%d").date()
                return (
                    today.year
                    - dob.year
                    - ((today.month, today.day) < (dob.month, dob.day))
                )
            except ValueError:
                return -1

        def get_goals_total(historique: Any) -> int:
            goals_nb = 0
            if isinstance(historique, list) and len(historique) > 0:
                for season in historique:
                    if "B," in season:
                        try:
                            part = season.split("): ")[1]
                            g_str = part.split("B")[0]
                            goals_nb += int(g_str)
                        except (IndexError, ValueError):
                            pass
            return goals_nb

        def get_assists_total(historique: Any) -> int:
            assists_nb = 0
            if isinstance(historique, list) and len(historique) > 0:
                for season in historique:
                    if "PD" in season:
                        try:
                            part = season.split("): ")[1]
                            pd_part = part.split(",")[1].strip()
                            a_str = pd_part.replace("PD", "")
                            assists_nb += int(a_str)
                        except (IndexError, ValueError):
                            pass
            return assists_nb

        df = self.df_joueurs.copy()

        # Préparation de la colonne Historique en liste
        if any([equipe, buts_min, buts_max, passes_min, passes_max]):
            df["Historique_Clubs_Stats_List"] = (
                df["Historique_Clubs_Stats"].astype(str).str.split("|")
            )

        if nom:
            df = df[df.name.apply(test_nom)]

        if age_min is not None or age_max is not None:
            df["Age_Int"] = df.dateOfBirth.apply(calcul_age_int)
            if age_min is not None:
                df = df[df.Age_Int >= age_min]
            if age_max is not None:
                df = df[df.Age_Int <= age_max]

        if nationalite:
            df = df[
                (df["Nationalité 1"] == nationalite)
                | (df["Nationalité 2"] == nationalite)
            ]

        if poste:
            df = df[df.positionName == poste]

        if equipe:
            df = df[df.Historique_Clubs_Stats_List.apply(test_equipe)]

        if buts_min is not None or buts_max is not None:
            df["Total_Buts"] = df.Historique_Clubs_Stats_List.apply(get_goals_total)
            if buts_min is not None:
                df = df[df.Total_Buts >= buts_min]
            if buts_max is not None:
                df = df[df.Total_Buts <= buts_max]

        if passes_min is not None or passes_max is not None:
            df["Total_Passes"] = df.Historique_Clubs_Stats_List.apply(get_assists_total)
            if passes_min is not None:
                df = df[df.Total_Passes >= passes_min]
            if passes_max is not None:
                df = df[df.Total_Passes <= passes_max]

        return df

    def filter_teams(
        self,
        nom: Optional[str] = None,
        effectif: Optional[str] = None,
        championnat_actuel: Optional[str] = None,
        classement_actuel: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Filtre la liste des équipes (clubs).
        """

        def test_nom(nom_club: str) -> bool:
            return nom.lower() in str(nom_club).lower() if nom else True

        def test_effectif(effectif_equipe: str) -> bool:
            return effectif.lower() in str(effectif_equipe).lower() if effectif else True

        df = self.df_clubs_season.copy()

        if nom:
            df = df[df.Nom_Club.apply(test_nom)]

        if classement_actuel is not None and classement_actuel > 0:
            df = df[df["Classement"] == classement_actuel]
            df = df[df["Saison"] == "2024-2025"]

        if championnat_actuel:
            df = df[df["Championnat"] == championnat_actuel]
            df = df[df["Saison"] == "2024-2025"]

        if effectif:
            df = df[df.Effectif.apply(test_effectif)]

        return df.drop_duplicates(subset=["Nom_Club"])


def create_flag_label(mw: "MainWindow", country_name: str) -> QLabel:
    """Crée un QLabel avec le drapeau via le cache de MainWindow (mw)."""
    label = QLabel()
    label.setAlignment(Qt.AlignCenter)

    pixmap = mw.dm.get_flag_pixmap(country_name)
    if pixmap:
        label.setPixmap(pixmap)
    else:
        label.setText(country_name if country_name else "-")
        label.setStyleSheet("font-size: 10px; color: gray;")
    return label


# --- BOITE DE DIALOGUE FILTRE ---
class FilterDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, data_manager: Optional[DataManager] = None):
        super().__init__(parent)
        self.setWindowTitle("Filtres avancés")
        self.resize(500, 600)
        self.dm = data_manager

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- ONGLET JOUEURS ---
        self.tab_players = QWidget()
        self.init_player_tab()
        self.tabs.addTab(self.tab_players, "Joueurs")

        # --- ONGLET CLUBS ---
        self.tab_clubs = QWidget()
        self.init_club_tab()
        self.tabs.addTab(self.tab_clubs, "Clubs")

        # BOUTONS
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Appliquer")
        buttons.button(QDialogButtonBox.Cancel).setText("Annuler")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def init_player_tab(self) -> None:
        layout = QFormLayout(self.tab_players)

        self.p_nom = QLineEdit()
        self.p_equipe = QLineEdit()
        self.p_equipe.setPlaceholderText("A joué dans ce club...")

        self.p_nat = QComboBox()
        self.p_nat.addItem("Toutes", None)
        if self.dm:
            nats = sorted(self.dm.df_joueurs["Nationalité 1"].dropna().unique())
            self.p_nat.addItems(nats)

        self.p_poste = QComboBox()
        self.p_poste.addItem("Tous", None)
        if self.dm:
            postes = sorted(self.dm.df_joueurs["positionName"].dropna().unique())
            self.p_poste.addItems(postes)

        # Helper pour range spinbox
        def make_range() -> Tuple[QHBoxLayout, QSpinBox, QSpinBox]:
            box = QHBoxLayout()
            s_min = QSpinBox()
            s_min.setRange(0, 1000)
            s_min.setValue(0)
            s_max = QSpinBox()
            s_max.setRange(0, 1000)
            s_max.setValue(0)  # 0 means disabled/max

            # Special values
            s_min.setSpecialValueText("0")
            s_max.setSpecialValueText("100")

            box.addWidget(QLabel("Min:"))
            box.addWidget(s_min)
            box.addWidget(QLabel("Max:"))
            box.addWidget(s_max)
            return box, s_min, s_max

        self.lay_age, self.p_age_min, self.p_age_max = make_range()
        self.lay_buts, self.p_buts_min, self.p_buts_max = make_range()
        self.lay_pass, self.p_pass_min, self.p_pass_max = make_range()

        # Configuration des plages logiques
        self.p_age_min.setRange(15, 50)
        self.p_age_min.setValue(15)
        self.p_age_max.setRange(15, 50)
        self.p_age_max.setValue(50)

        layout.addRow("Nom / Prénom:", self.p_nom)
        layout.addRow("Club où il a joué:", self.p_equipe)
        layout.addRow("Nationalité:", self.p_nat)
        layout.addRow("Poste:", self.p_poste)
        layout.addRow("Âge:", self.lay_age)
        layout.addRow("Buts (Carrière):", self.lay_buts)
        layout.addRow("Passes D. (Carrière):", self.lay_pass)

    def init_club_tab(self) -> None:
        layout = QFormLayout(self.tab_clubs)

        self.c_nom = QLineEdit()
        self.c_effectif = QLineEdit()
        self.c_effectif.setPlaceholderText("Contient ce joueur...")

        self.c_champ = QComboBox()
        self.c_champ.addItem("Tous", None)
        if self.dm:
            champs = sorted(self.dm.df_clubs_season["Championnat"].dropna().unique())
            self.c_champ.addItems(champs)

        self.c_classement = QSpinBox()
        self.c_classement.setRange(0, 25)
        self.c_classement.setSpecialValueText("Peu importe")
        self.c_classement.setValue(0)

        layout.addRow("Nom du club:", self.c_nom)
        layout.addRow("Joueur dans l'effectif:", self.c_effectif)
        layout.addRow("Championnat:", self.c_champ)
        layout.addRow("Classement (24/25):", self.c_classement)

    def get_filter_params(self) -> Dict[str, Any]:
        """Récupère les données et retourne un dictionnaire de paramètres."""
        mode = "joueurs" if self.tabs.currentIndex() == 0 else "clubs"
        params: Dict[str, Any] = {}

        if mode == "joueurs":
            params["type"] = "joueurs"
            if self.p_nom.text():
                params["nom"] = self.p_nom.text()
            if self.p_equipe.text():
                params["equipe"] = self.p_equipe.text()
            if (
                self.p_nat.currentData() != "Toutes"
                and self.p_nat.currentIndex() > 0
            ):
                params["nationalite"] = self.p_nat.currentText()
            if (
                self.p_poste.currentData() != "Tous"
                and self.p_poste.currentIndex() > 0
            ):
                params["poste"] = self.p_poste.currentText()

            # Age
            if self.p_age_min.value() > 15:
                params["age_min"] = self.p_age_min.value()
            if self.p_age_max.value() < 50:
                params["age_max"] = self.p_age_max.value()

            # Buts
            if self.p_buts_min.value() > 0:
                params["buts_min"] = self.p_buts_min.value()
            if self.p_buts_max.value() > 0:
                params["buts_max"] = self.p_buts_max.value()

            # Passes
            if self.p_pass_min.value() > 0:
                params["passes_min"] = self.p_pass_min.value()
            if self.p_pass_max.value() > 0:
                params["passes_max"] = self.p_pass_max.value()

        else:
            params["type"] = "clubs"
            if self.c_nom.text():
                params["nom"] = self.c_nom.text()
            if self.c_effectif.text():
                params["effectif"] = self.c_effectif.text()
            if self.c_champ.currentIndex() > 0:
                params["championnat_actuel"] = self.c_champ.currentText()
            if self.c_classement.value() > 0:
                params["classement_actuel"] = self.c_classement.value()

        return params


# --- WIDGET D'IMAGE ASYNCHRONE ---
class AsyncImageLabel(QLabel):
    def set_image_from_url(self, url: str) -> None:
        self.setText("Chargement...")
        self.setAlignment(Qt.AlignCenter)
        try:
            if pd.isna(url) or url == "":
                self.setText("Pas d'image")
                return
            response = requests.get(url, timeout=1.5)
            if response.status_code == 200:
                img = QImage()
                img.loadFromData(response.content)
                self.setPixmap(
                    QPixmap.fromImage(img).scaled(
                        self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                )
            else:
                self.setText("Erreur IMG")
        except Exception:
            self.setText("N/A")


class HoverDelegate(QStyledItemDelegate):
    def helpEvent(
        self, event: QEvent, view: QAbstractItemView, option: Any, index: QModelIndex
    ) -> bool:
        if index.isValid() and index.column() in [0, 1]:
            view.setCursor(Qt.PointingHandCursor)
        else:
            view.setCursor(Qt.ArrowCursor)
        return super().helpEvent(event, view, option, index)


class BasePage(QWidget):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__()
        self.mw = main_window
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)


# --- PAGES ---
class HomePage(BasePage):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)
        self.layout.setAlignment(Qt.AlignCenter)
        welcome_lbl = QLabel("Bienvenue sur TransfertMarché")
        welcome_lbl.setObjectName("page_title")
        welcome_lbl.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(welcome_lbl)

        sub_lbl = QLabel("Sélectionnez un championnat ou recherchez un joueur/club")
        sub_lbl.setStyleSheet("color: #64748b; font-size: 16px;")
        sub_lbl.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(sub_lbl)
        self.layout.addSpacing(40)

        grid = QHBoxLayout()
        for league in self.mw.league_logos.keys():
            btn = QPushButton(league)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(150, 50)
            btn.setObjectName("search_btn")
            btn.setStyleSheet("font-weight: bold; color: black;")
            btn.clicked.connect(
                lambda checked, l=league: self.mw.navigate_to(l, "championnat")
            )
            grid.addWidget(btn)
        self.layout.addLayout(grid)


class SuggestionPage(BasePage):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)
        self.title = QLabel("Résultats de recherche")
        self.title.setObjectName("page_title")
        self.layout.addWidget(self.title)

        self.table = QTableWidget()
        self.table.setMouseTracking(True)
        self.table.setItemDelegate(HoverDelegate(self.table))
        self.table.cellClicked.connect(self.on_click)
        self.layout.addWidget(self.table)

        self.current_mode = "joueur"  # ou "club"

    def load(self, query: str) -> None:
        """Recherche textuelle simple (par défaut joueurs)."""
        self.current_mode = "joueur"
        self.title.setText(f"🔍 Résultats commençant par : '{query}'")
        df = self.mw.dm.df_joueurs
        pattern = r"(^|\s)" + re.escape(query)
        results = df[
            df["name"].str.contains(pattern, case=False, na=False, regex=True)
        ]
        self.populate_player_table(results)

    def load_from_filter(self, df: pd.DataFrame, mode: str) -> None:
        """Chargement depuis le filtre avancé."""
        self.current_mode = "joueur" if mode == "joueurs" else "club"
        self.title.setText(f"🔍 Résultats du filtre ({len(df)} trouvés)")

        if self.current_mode == "joueur":
            self.populate_player_table(df)
        else:
            self.populate_club_table(df)

    def populate_player_table(self, df: pd.DataFrame) -> None:
        self.table.clear()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Joueur", "Âge", "Valeur", "Poste", "Nationalité"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        self.table.setRowCount(len(df))
        for i, (_, row) in enumerate(df.iterrows()):
            self.table.setItem(i, 0, QTableWidgetItem(str(row["name"])))
            self.table.setItem(
                i, 1, QTableWidgetItem(str(row.get("age_display", "-")))
            )
            raw_val = row.get("marketValue", row.get("currentMarketValue", 0))
            self.table.setItem(
                i, 2, QTableWidgetItem(self.mw.dm.format_currency(raw_val))
            )
            self.table.setItem(i, 3, QTableWidgetItem(str(row.get("positionName", "-"))))
            nat_name = row.get("Nationalité 1", "-")
            self.table.setCellWidget(i, 4, create_flag_label(self.mw, nat_name))

    def populate_club_table(self, df: pd.DataFrame) -> None:
        self.table.clear()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(
            ["Club", "Championnat", "Effectif (Aperçu)"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        self.table.setRowCount(len(df))
        for i, (_, row) in enumerate(df.iterrows()):
            item_club = QTableWidgetItem(row["Nom_Club"])
            item_club.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(i, 0, item_club)

            self.table.setItem(
                i, 1, QTableWidgetItem(str(row.get("Championnat", "-")))
            )

            eff = str(row.get("Effectif", ""))
            if len(eff) > 50:
                eff = eff[:50] + "..."
            self.table.setItem(i, 2, QTableWidgetItem(eff))

    def on_click(self, row: int, col: int) -> None:
        if col == 0:
            name = self.table.item(row, 0).text()
            if self.current_mode == "joueur":
                self.mw.navigate_to(name, "joueur")
            else:
                self.mw.navigate_to(name, "club")


class LeaguePage(BasePage):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)
        self.title = QLabel("Championnat")
        self.title.setObjectName("page_title")

        self.combo_season = QComboBox()
        self.combo_season.currentTextChanged.connect(self.on_season_changed)

        self.btn_toggle_pie = QPushButton("Répartitions Nationalités")
        self.btn_toggle_pie.setCheckable(True)
        self.btn_toggle_pie.clicked.connect(self.toggle_pie_visibility)
        self.btn_toggle_pie.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_pie.setStyleSheet("padding: 5px; font-weight: bold;")

        top_h = QHBoxLayout()
        top_h.addWidget(self.title)
        top_h.addStretch()
        top_h.addWidget(self.btn_toggle_pie)
        top_h.addSpacing(10)
        top_h.addWidget(QLabel("Saison:"))
        top_h.addWidget(self.combo_season)
        self.layout.addLayout(top_h)

        self.content_layout = QHBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Pos", "Club", "Effectif (Aperçu)"])
        self.table.setMouseTracking(True)
        self.table.setItemDelegate(HoverDelegate(self.table))
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.cellClicked.connect(self.on_table_click)
        self.content_layout.addWidget(self.table, stretch=2)

        self.canvas: Optional[FigureCanvas] = None
        self.content_layout.addSpacing(10)
        self.layout.addLayout(self.content_layout)

    def load(self, league_name: str) -> None:
        self.title.setText(f"{league_name}")
        df = self.mw.dm.df_clubs_season
        seasons = sorted(
            df[df["Championnat"] == league_name]["Saison"].unique(), reverse=True
        )
        self.combo_season.blockSignals(True)
        self.combo_season.clear()
        self.combo_season.addItems(seasons)
        self.combo_season.blockSignals(False)
        self.update_table()
        self.update_pie()

    def on_season_changed(self) -> None:
        self.update_table()
        if self.btn_toggle_pie.isChecked():
            self.update_pie()

    def toggle_pie_visibility(self) -> None:
        if self.btn_toggle_pie.isChecked():
            self.update_pie()
        else:
            if self.canvas:
                self.canvas.hide()

    def get_nationality_fig(
        self, NomChampionnat: str, saison: str, seuil: int = 1
    ) -> Optional[Figure]:
        df = self.mw.dm.df_clubs_season[
            (self.mw.dm.df_clubs_season.Championnat == NomChampionnat)
            & (self.mw.dm.df_clubs_season.Saison == saison)
        ].copy()
        if df.empty:
            return None
        df["Effectif"] = df["Effectif"].str.split(", ")
        df = df.explode("Effectif")
        df_merge = df.merge(
            self.mw.dm.df_joueurs, left_on="Effectif", right_on="name", how="left"
        )
        nb = (
            df_merge["Nationalité 1"]
            .value_counts()
            .add(df_merge["Nationalité 2"].value_counts(), fill_value=0)
        )
        threshold = (seuil / 100) * nb.sum()
        counts_grouped = nb[nb >= threshold].copy()
        others_count = nb[nb < threshold].sum()
        if others_count > 0:
            counts_grouped[f"Autres (<{seuil}%)"] = others_count
        fig = plt.Figure(figsize=(5, 5), dpi=80, facecolor=COLOR_BG)
        ax = fig.add_subplot(111)
        counts_grouped.plot.pie(autopct="%1.1f%%", startangle=140, ax=ax)
        ax.set_title(f"Répartition des nationalités\n{NomChampionnat} ({saison})")
        ax.set_ylabel("")
        return fig

    def update_pie(self) -> None:
        if self.canvas:
            self.content_layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
            self.canvas = None
        if not self.btn_toggle_pie.isChecked():
            return
        league = self.title.text().replace("🏆 ", "")
        season = self.combo_season.currentText()
        fig = self.get_nationality_fig(league, season, seuil=1)
        if fig:
            self.canvas = FigureCanvas(fig)
            self.canvas.setMinimumWidth(350)
            self.content_layout.addWidget(self.canvas, stretch=1)
            self.canvas.show()

    def update_table(self) -> None:
        league = self.title.text().replace("🏆 ", "")
        season = self.combo_season.currentText()
        df = self.mw.dm.df_clubs_season
        data = df[(df["Championnat"] == league) & (df["Saison"] == season)].sort_values(
            "Classement"
        )
        self.table.setRowCount(len(data))
        for i, (_, row) in enumerate(data.iterrows()):
            self.table.setItem(i, 0, QTableWidgetItem(str(int(row["Classement"]))))
            item_club = QTableWidgetItem(row["Nom_Club"])
            item_club.setForeground(QColor(COLOR_LINK))
            item_club.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(i, 1, item_club)
            eff = str(row["Effectif"])
            if len(eff) > 80:
                eff = eff[:80] + "..."
            self.table.setItem(i, 2, QTableWidgetItem(eff))

    def on_table_click(self, row: int, col: int) -> None:
        if col == 1:
            club_name = self.table.item(row, 1).text()
            self.mw.navigate_to(club_name, "club")


class ClubPage(BasePage):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)
        self.title = QLabel("Club")
        self.title.setObjectName("page_title")
        self.combo_season = QComboBox()
        self.combo_season.currentTextChanged.connect(self.update_squad)

        self.btn_evolution = QPushButton("⚽ Buts")
        self.btn_evolution.setCheckable(True)
        self.btn_evolution.setCursor(Qt.PointingHandCursor)
        self.btn_evolution.clicked.connect(lambda: self.toggle_graph("evolution"))
        self.btn_evolution.setStyleSheet("padding: 5px; font-weight: bold;")

        self.btn_nuage = QPushButton("📈 Classement")
        self.btn_nuage.setCheckable(True)
        self.btn_nuage.setCursor(Qt.PointingHandCursor)
        self.btn_nuage.clicked.connect(lambda: self.toggle_graph("nuage"))
        self.btn_nuage.setStyleSheet("padding: 5px; font-weight: bold;")

        self.btn_age = QPushButton("🎂 Âges")
        self.btn_age.setCheckable(True)
        self.btn_age.clicked.connect(lambda: self.toggle_graph("age"))
        self.btn_age.setCursor(Qt.PointingHandCursor)
        self.btn_age.setStyleSheet("padding: 5px; font-weight: bold;")

        top_h = QHBoxLayout()
        top_h.addWidget(self.title)
        top_h.addStretch()
        top_h.addWidget(self.btn_evolution)
        top_h.addWidget(self.btn_nuage)
        top_h.addWidget(self.btn_age)
        top_h.addSpacing(10)
        top_h.addWidget(QLabel("Saison:"))
        top_h.addWidget(self.combo_season)
        self.layout.addLayout(top_h)

        self.content_layout = QHBoxLayout()
        self.table_squad = QTableWidget()
        self.table_squad.setColumnCount(5)
        self.table_squad.setHorizontalHeaderLabels(
            ["Joueur", "Âge", "Valeur", "Poste", "Nationalité"]
        )
        self.table_squad.cellClicked.connect(self.on_player_click)
        self.table_squad.setMouseTracking(True)
        self.table_squad.setItemDelegate(HoverDelegate(self.table_squad))

        header = self.table_squad.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self.table_squad.setColumnWidth(3, 150)
        self.content_layout.addWidget(self.table_squad, stretch=3)

        self.canvas: Optional[FigureCanvas] = None
        self.layout.addLayout(self.content_layout)

    def toggle_graph(self, graph_type: str) -> None:
        self.btn_evolution.setChecked(
            graph_type == "evolution" and self.btn_evolution.isChecked()
        )
        self.btn_nuage.setChecked(
            graph_type == "nuage" and self.btn_nuage.isChecked()
        )
        self.btn_age.setChecked(graph_type == "age" and self.btn_age.isChecked())
        if any(
            [
                self.btn_evolution.isChecked(),
                self.btn_nuage.isChecked(),
                self.btn_age.isChecked(),
            ]
        ):
            self.update_graph(graph_type)
        else:
            self.remove_canvas()

    def remove_canvas(self) -> None:
        if self.canvas:
            self.content_layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
            self.canvas = None

    def update_graph(self, graph_type: str) -> None:
        self.remove_canvas()
        club_name = self.title.text().replace("🛡️ ", "")
        fig = None
        if graph_type == "evolution":
            fig = self.get_evolution_fig(club_name)
        elif graph_type == "nuage":
            fig = self.get_classement_fig(club_name)
        elif graph_type == "age":
            fig = self.get_age_histo_fig(club_name)

        if fig:
            fig.patch.set_facecolor("#f5f6f8")
            self.canvas = FigureCanvas(fig)
            self.canvas.setMinimumWidth(400)
            self.content_layout.addWidget(self.canvas, stretch=1)

    def load(self, club_name: str) -> None:
        self.title.setText(f"🛡️ {club_name}")
        self.btn_evolution.setChecked(False)
        self.btn_nuage.setChecked(False)
        self.remove_canvas()
        df = self.mw.dm.df_clubs_season
        seasons = sorted(
            df[df["Nom_Club"] == club_name]["Saison"].unique(), reverse=True
        )
        self.combo_season.blockSignals(True)
        self.combo_season.clear()
        self.combo_season.addItems(seasons)
        self.combo_season.blockSignals(False)
        self.update_squad()

    def get_evolution_fig(self, NomEquipe: str) -> Optional[Figure]:
        df_joueurs = self.mw.dm.df_joueurs.loc[
            :, ["name", "Historique_Clubs_Stats"]
        ].copy()
        df_joueurs["Historique_Clubs_Stats"] = df_joueurs[
            "Historique_Clubs_Stats"
        ].str.split("|")

        def parse_team(s: str) -> str:
            return s.strip().split(" (")[0]

        def parse_year(s: str) -> str:
            full_year = s.strip().split("): ")[0][-9:]
            return f"{full_year[2:4]}/{full_year[7:9]}"

        def parse_goals(s: str) -> int:
            try:
                content = s.strip().split("): ")[1]
                goals_str = ""
                for char in content:
                    if char == "B":
                        break
                    goals_str += char
                return int(goals_str)
            except Exception:
                return 0

        stats_list = []
        for historique in df_joueurs.Historique_Clubs_Stats:
            if isinstance(historique, list):
                for season_str in historique:
                    if len(season_str) > 10 and parse_team(season_str) == NomEquipe:
                        stats_list.append(
                            {
                                "Saison": parse_year(season_str),
                                "Buts": parse_goals(season_str),
                            }
                        )
        if not stats_list:
            return None
        df_final = pd.DataFrame(stats_list)
        bpd = df_final.groupby("Saison")["Buts"].sum().reset_index()

        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)
        bars = ax.bar(bpd["Saison"], bpd["Buts"], color="#ffa45f")
        ax.bar_label(bars, padding=3, fontsize=9, fontweight="bold")
        ax.set_title(f"Évolution des buts :", color="#1a3150", fontweight="bold")
        ax.set_ylabel("Nombre total de buts")
        ax.tick_params(axis="x", rotation=90)
        fig.tight_layout()
        return fig

    def get_classement_fig(self, NomEquipe: str) -> Optional[Figure]:
        df = self.mw.dm.df_clubs_season[
            self.mw.dm.df_clubs_season.Nom_Club == NomEquipe
        ].copy()
        if df.empty:
            return None
        df["Saison_Courte"] = df["Saison"].apply(lambda x: f"{x[2:4]}/{x[7:9]}")
        max_clubs = 20
        df["Hauteur_Barre"] = (max_clubs + 1) - df["Classement"]
        df = df.sort_values("Saison")
        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)
        bars = ax.bar(df["Saison_Courte"], df["Hauteur_Barre"], color="#ffa45f")
        vrais_classements = df["Classement"].tolist()
        ax.bar_label(bars, labels=vrais_classements, padding=3, fontweight="bold")
        ax.set_title(f"Évolution du classement :", color="#1a3150", fontweight="bold")
        ax.set_yticks([])
        ax.set_xlabel("Saisons")
        ax.tick_params(axis="x", rotation=90)
        fig.tight_layout()
        return fig

    def get_age_histo_fig(self, NomEquipe: str) -> Optional[Figure]:
        import numpy as np

        saison_active = self.combo_season.currentText()

        # 1. Filtrer les données du club pour la saison
        df_club = self.mw.dm.df_clubs_season[
            (self.mw.dm.df_clubs_season.Nom_Club == NomEquipe)
            & (self.mw.dm.df_clubs_season.Saison == saison_active)
        ].copy()

        if df_club.empty or pd.isna(df_club.iloc[0]["Effectif"]):
            return None

        # 2. Éclater la liste des joueurs
        df_club["Effectif"] = df_club["Effectif"].str.split(", ")
        df_club = df_club.explode("Effectif")
        df_club["Effectif"] = df_club["Effectif"].str.strip()

        # 3. Merger avec les infos joueurs pour avoir les dates de naissance
        df_merge = df_club.merge(
            self.mw.dm.df_joueurs, left_on="Effectif", right_on="name", how="left"
        )

        # 4. Calcul de l'âge si non présent numériquement
        def get_age_int(dob: Any) -> Optional[int]:
            try:
                if pd.isna(dob):
                    return None
                birth = datetime.strptime(str(dob), "%Y-%m-%d")
                today = date.today()
                return (
                    today.year
                    - birth.year
                    - ((today.month, today.day) < (birth.month, birth.day))
                )
            except Exception:
                return None

        # On crée une colonne 'Age_Calculated' propre
        df_merge["Age_Calculated"] = df_merge["dateOfBirth"].apply(get_age_int)
        ages = df_merge["Age_Calculated"].dropna().astype(int)

        if ages.empty:
            return None

        # 5. Création du graphique Matplotlib
        fig = Figure(figsize=(5, 5), dpi=100)
        ax = fig.add_subplot(111)

        min_age, max_age = int(ages.min()), int(ages.max())
        all_ages = np.arange(min_age, max_age + 1)
        bins = np.arange(min_age, max_age + 2) - 0.5

        n, bins_edges, _ = ax.hist(ages, bins=bins, color="#ffa45f", edgecolor="white")

        # Labels numériques au-dessus des barres
        for i in range(len(n)):
            if n[i] > 0:
                ax.text(
                    min_age + i,
                    n[i] + 0.1,
                    int(n[i]),
                    ha="center",
                    fontsize=8,
                    fontweight="bold",
                )

        # Axe X vertical avec tous les âges
        ax.set_xticks(all_ages)
        ax.set_xticklabels(all_ages, rotation=90, fontsize=8)

        # Style
        ax.set_title(
            f"Répartition des âges ({saison_active})",
            color="#1a3150",
            fontweight="bold",
        )
        ax.set_xlabel("Âge (ans)")
        ax.set_ylabel("Nombre de joueurs")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        fig.tight_layout()
        return fig

    def update_squad(self) -> None:
        club = self.title.text().replace("🛡️ ", "")
        season = self.combo_season.currentText()
        df_clubs = self.mw.dm.df_clubs_season
        df_players = self.mw.dm.df_joueurs
        row = df_clubs[
            (df_clubs["Nom_Club"] == club) & (df_clubs["Saison"] == season)
        ]
        self.table_squad.setRowCount(0)
        if not row.empty:
            squad_str = str(row.iloc[0]["Effectif"])
            player_names = [p.strip() for p in squad_str.split(",") if p.strip()]
            self.table_squad.setRowCount(len(player_names))
            for i, p_name in enumerate(player_names):
                self.table_squad.setItem(i, 0, QTableWidgetItem(p_name))
                p_info = df_players[df_players["name"] == p_name]
                if not p_info.empty:
                    info = p_info.iloc[0]
                    self.table_squad.setItem(
                        i, 1, QTableWidgetItem(str(info.get("age_display", "-")))
                    )
                    raw_val = info.get(
                        "marketValue", info.get("currentMarketValue", 0)
                    )
                    self.table_squad.setItem(
                        i, 2, QTableWidgetItem(self.mw.dm.format_currency(raw_val))
                    )
                    self.table_squad.setItem(
                        i, 3, QTableWidgetItem(str(info.get("positionName", "-")))
                    )
                    nat_name = info.get("Nationalité 1", "-")
                    self.table_squad.setCellWidget(
                        i, 4, create_flag_label(self.mw, nat_name)
                    )
                else:
                    for col in range(1, 4):
                        self.table_squad.setItem(i, col, QTableWidgetItem("-"))
            if self.btn_age.isChecked():
                self.update_graph("age")

    def on_player_click(self, row: int, col: int) -> None:
        if col == 0:
            player_name = self.table_squad.item(row, 0).text()
            self.mw.navigate_to(player_name, "joueur")


class PlayerPage(BasePage):
    def __init__(self, main_window: "MainWindow") -> None:
        super().__init__(main_window)
        self.title = QLabel("Joueur")
        self.title.setObjectName("page_title")
        self.layout.addWidget(self.title)

        stats_box = QHBoxLayout()
        self.card_goals = self.create_stat_card("Buts", "0")
        self.card_assists = self.create_stat_card("Passes D.", "0")
        self.card_value = self.create_stat_card("Valeur", "-")
        self.card_position = self.create_stat_card("Poste", "-")
        stats_box.addLayout(self.card_goals)
        stats_box.addLayout(self.card_assists)
        stats_box.addStretch()
        stats_box.addLayout(self.card_value)
        stats_box.addSpacing(20)
        stats_box.addLayout(self.card_position)
        self.layout.addLayout(stats_box)

        self.layout.addWidget(QLabel("<b>Historique & Stats par saison :</b>"))
        self.table_hist = QTableWidget()
        self.table_hist.setColumnCount(4)
        self.table_hist.setMouseTracking(True)
        self.table_hist.setItemDelegate(HoverDelegate(self.table_hist))
        self.table_hist.setHorizontalHeaderLabels(
            ["Saison", "Club", "Buts", "Passes D."]
        )
        self.table_hist.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_hist.cellClicked.connect(self.on_club_click)
        self.layout.addWidget(self.table_hist)

    def create_stat_card(self, label: str, value: str) -> QVBoxLayout:
        l = QVBoxLayout()
        val_lbl = QLabel(value)
        val_lbl.setObjectName("stat_val")
        lbl_lbl = QLabel(label.upper())
        lbl_lbl.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        l.addWidget(val_lbl)
        l.addWidget(lbl_lbl)
        return l

    def load(self, player_name: str) -> None:
        self.title.setText(f"⚽ {player_name}")
        df = self.mw.dm.players_stats_parsed
        player_data = df[df["name"] == player_name].sort_values(
            "season", ascending=False
        )
        total_g = player_data["goals"].sum()
        total_a = player_data["assists"].sum()
        self.card_goals.itemAt(0).widget().setText(str(total_g))
        self.card_assists.itemAt(0).widget().setText(str(total_a))
        raw_value = (
            player_data["market_value"].iloc[0] if not player_data.empty else 0
        )
        if raw_value <= 0:
            display_value = "Retraite"
        else:
            if raw_value >= 1000000:
                display_value = f"{raw_value/1000000:.1f}M €"
            else:
                display_value = f"{raw_value/1000:.0f}K €"
        poste = player_data["position"].iloc[0] if not player_data.empty else "-"
        self.card_position.itemAt(0).widget().setText(poste)
        self.card_value.itemAt(0).widget().setText(display_value)

        self.table_hist.setRowCount(len(player_data))
        for i, (_, row) in enumerate(player_data.iterrows()):
            self.table_hist.setItem(i, 0, QTableWidgetItem(row["season"]))
            item_club = QTableWidgetItem(row["club"])
            item_club.setForeground(QColor(COLOR_LINK))
            item_club.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table_hist.setItem(i, 1, item_club)
            self.table_hist.setItem(i, 2, QTableWidgetItem(str(row["goals"])))
            self.table_hist.setItem(i, 3, QTableWidgetItem(str(row["assists"])))

    def on_club_click(self, row: int, col: int) -> None:
        if col == 1:
            club_name = self.table_hist.item(row, 1).text()
            self.mw.navigate_to(club_name, "club")


# --- FENÊTRE PRINCIPALE ---
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.dm = DataManager()
        self.league_logos = {
            "Ligue 1": "https://tmssl.akamaized.net//images/logo/header/fr1.png?lm=1732280518",
            "Premier League": "https://tmssl.akamaized.net//images/logo/header/gb1.png?lm=1521104656",
            "La Liga": "https://tmssl.akamaized.net//images/logo/header/es1.png?lm=1725974302",
            "Serie A": "https://tmssl.akamaized.net//images/logo/header/it1.png?lm=1656073460",
            "Bundesliga": "https://tmssl.akamaized.net//images/logo/header/l1.png?lm=1525905518",
        }

        if not self.dm.load_data():
            QMessageBox.critical(
                self, "Erreur", "Impossible de charger les fichiers CSV."
            )
            sys.exit(1)

        self.history_stack: List[Tuple[str, str]] = []
        self.forward_stack: List[Tuple[str, str]] = []
        self.is_navigating = False

        self.init_ui()

    def init_ui(self) -> None:
        self.resize(1280, 800)
        self.setWindowTitle("TransfertMarché")
        self.setStyleSheet(STYLE_SHEET)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        side_layout = QVBoxLayout(self.sidebar)

        nav_h = QHBoxLayout()
        self.btn_back = QPushButton("◀")
        self.btn_back.setObjectName("nav_btn")
        self.btn_back.clicked.connect(self.go_back)
        self.btn_fwd = QPushButton("▶")
        self.btn_fwd.setObjectName("nav_btn")
        self.btn_fwd.clicked.connect(self.go_forward)
        nav_h.addWidget(self.btn_back)
        nav_h.addWidget(self.btn_fwd)
        side_layout.addLayout(nav_h)

        self.img_label = AsyncImageLabel()
        self.img_label.setFixedSize(180, 180)
        self.img_label.setScaledContents(False)
        self.img_label.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(self.img_label, alignment=Qt.AlignCenter)

        self.lbl_side_info = QLabel()
        self.lbl_side_info.setStyleSheet(
            "color: #94a3b8; font-size: 11px; margin-top: 10px;"
        )
        self.lbl_side_info.setWordWrap(True)
        self.lbl_side_info.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(self.lbl_side_info)

        side_layout.addWidget(QLabel("Historique", objectName="side_title"))
        self.list_history = QListWidget()
        self.list_history.itemClicked.connect(
            lambda item: self.navigate_to(item.text(), from_history=True)
        )
        side_layout.addWidget(self.list_history)

        self.btn_clear_hist = QPushButton("EFFACER L'HISTORIQUE")
        self.btn_clear_hist.setObjectName("clear_btn")
        self.btn_clear_hist.clicked.connect(self.list_history.clear)
        side_layout.addWidget(self.btn_clear_hist)

        # 2. Zone Principale
        right_zone = QWidget()
        right_layout = QVBoxLayout(right_zone)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        top_bar = QFrame()
        top_bar.setObjectName("top_bar")
        top_bar.setFixedHeight(60)

        top_h = QHBoxLayout(top_bar)
        top_h.setContentsMargins(15, 0, 15, 0)
        top_h.setSpacing(10)

        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("search_bar")
        self.search_bar.setPlaceholderText("Rechercher...")
        self.search_bar.setFixedWidth(400)
        self.search_bar.returnPressed.connect(self.on_search_valid)

        self.btn_search_icon = QPushButton("🔍")
        self.btn_search_icon.setObjectName("search_btn")
        self.btn_search_icon.setFixedSize(35, 35)
        self.btn_search_icon.setCursor(Qt.PointingHandCursor)
        self.btn_search_icon.clicked.connect(self.on_search_valid)

        # --- NOUVEAU BOUTON FILTRE ---
        self.btn_filter = QPushButton("Filtres ⚙")
        self.btn_filter.setObjectName("filter_btn")
        self.btn_filter.setCursor(Qt.PointingHandCursor)
        self.btn_filter.clicked.connect(self.open_filter_dialog)

        top_h.addWidget(self.search_bar)
        top_h.addWidget(self.btn_search_icon)
        top_h.addWidget(self.btn_filter)  # Ajout du bouton ici
        top_h.addStretch()

        right_layout.addWidget(top_bar)

        all_names = (
            list(self.dm.df_clubs_season["Championnat"].unique())
            + list(self.dm.df_clubs_season["Nom_Club"].unique())
            + list(self.dm.df_joueurs["name"].unique())
        )
        all_names = [x for x in all_names if pd.notna(x)]
        completer = QCompleter(all_names)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.activated.connect(self.navigate_to)
        self.search_bar.setCompleter(completer)

        self.stack = QStackedWidget()
        self.page_home = HomePage(self)
        self.page_league = LeaguePage(self)
        self.page_club = ClubPage(self)
        self.page_player = PlayerPage(self)
        self.page_suggestions = SuggestionPage(self)

        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_league)
        self.stack.addWidget(self.page_club)
        self.stack.addWidget(self.page_player)
        self.stack.addWidget(self.page_suggestions)

        self.navigate_to("Accueil", "home")

        right_layout.addWidget(self.stack)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(right_zone)

    def open_filter_dialog(self) -> None:
        dialog = FilterDialog(self, self.dm)
        if dialog.exec_() == QDialog.Accepted:
            params = dialog.get_filter_params()
            self.apply_filter(params)

    def apply_filter(self, params: Dict[str, Any]) -> None:
        type_filter = params.pop("type")

        # --- AJOUT : Mise à jour de la barre de recherche ---
        # On vérifie si un nom a été saisi dans les paramètres du filtre
        nom_saisi = params.get("nom", "")
        if nom_saisi:
            self.search_bar.setText(nom_saisi)
        # ----------------------------------------------------

        if type_filter == "joueurs":
            df_res = self.dm.filtre_joueurs(**params)
        else:
            df_res = self.dm.filter_teams(**params)

        # Navigation vers la page de suggestion avec les résultats
        self.stack.setCurrentIndex(4)
        self.page_suggestions.load_from_filter(df_res, type_filter)

        # Mise à jour de l'interface latérale
        if type_filter == "joueurs":
            self.lbl_side_info.setText(f"RÉSULTATS FILTRE\nJOUEURS : {nom_saisi}")
        else:
            self.lbl_side_info.setText(f"RÉSULTATS FILTRE\nCLUBS : {nom_saisi}")

        self.img_label.setText("⚙")

    def on_search_valid(self) -> None:
        text = self.search_bar.text().strip()
        if not text:
            self.navigate_to("Accueil", "home")
            return
        if text in self.dm.df_clubs_season["Championnat"].values:
            self.navigate_to(text, "championnat")
        elif text in self.dm.df_clubs_season["Nom_Club"].values:
            self.navigate_to(text, "club")
        elif text in self.dm.df_joueurs["name"].values:
            self.navigate_to(text, "joueur")
        else:
            self.navigate_to(text, "suggestion")

    def navigate_to(
        self,
        name: str,
        type_hint: Optional[str] = None,
        from_history: bool = False,
    ) -> None:
        self.search_bar.clear()
        if not name:
            return

        if not type_hint:
            if name == "Accueil":
                type_hint = "home"
            elif name in self.dm.df_clubs_season["Championnat"].values:
                type_hint = "championnat"
            elif name in self.dm.df_clubs_season["Nom_Club"].values:
                type_hint = "club"
            elif name in self.dm.df_joueurs["name"].values:
                type_hint = "joueur"
            else:
                type_hint = "suggestion"

        if not from_history and not self.is_navigating:
            if not self.history_stack or self.history_stack[-1][0] != name:
                self.history_stack.append((name, type_hint))
                self.forward_stack.clear()
                self.list_history.addItem(name)
                self.list_history.scrollToBottom()

        self.is_navigating = True

        try:
            if type_hint == "home":
                self.stack.setCurrentIndex(0)
                self.img_label.setText("🏠")
                self.lbl_side_info.setText("ACCUEIL")

            elif type_hint == "championnat":
                self.stack.setCurrentIndex(1)
                self.page_league.load(name)
                logo_url = self.league_logos.get(name)
                if logo_url:
                    self.img_label.set_image_from_url(logo_url)
                else:
                    self.img_label.setText("🏆")
                self.lbl_side_info.setText(f"COMPÉTITION\n\n{name}")

            elif type_hint == "club":
                self.stack.setCurrentIndex(2)
                self.page_club.load(name)
                info = self.dm.df_clubs_profile[
                    self.dm.df_clubs_profile["name"] == name
                ]
                if not info.empty:
                    row = info.iloc[0]
                    self.img_label.set_image_from_url(row.get("crestUrl"))
                    self.lbl_side_info.setText(
                        f"CLUB\n\nStade: {row.get('stadium', '-')}\nVille: {row.get('city', '-')}"
                    )
                else:
                    self.img_label.setText("🛡️")
                    self.lbl_side_info.setText("CLUB")

            elif type_hint == "joueur":
                self.stack.setCurrentIndex(3)
                self.page_player.load(name)
                info = self.dm.df_joueurs[self.dm.df_joueurs["name"] == name]
                if not info.empty:
                    row = info.iloc[0]
                    self.img_label.set_image_from_url(row.get("portraitUrl"))
                    age_display = row.get("age_display", "-")
                    taille = row.get("taille", "-")
                    nat1 = row.get("Nationalité 1", "-")
                    nat2 = row.get("Nationalité 2", "-")
                    sidebar_text = (
                        f"<b>JOUEUR</b><br><br>Âge : {age_display}<br>"
                        f"Taille : {taille}m<br>Nationalité sportive: {nat1}<br>"
                    )
                    if pd.notna(nat2) and nat2 != "":
                        sidebar_text += f"2ème nationalité : {nat2}"
                    self.lbl_side_info.setText(sidebar_text)

            elif type_hint == "suggestion":
                self.stack.setCurrentIndex(4)
                self.page_suggestions.load(name)
                self.img_label.setText("🔍")
                self.lbl_side_info.setText(f"Recherche de joueurs pour : {name}")

        finally:
            self.is_navigating = False

    def go_back(self) -> None:
        if len(self.history_stack) > 1:
            current = self.history_stack.pop()
            self.forward_stack.append(current)
            prev_name, prev_type = self.history_stack[-1]
            self.navigate_to(prev_name, prev_type, from_history=True)

    def go_forward(self) -> None:
        if self.forward_stack:
            next_state = self.forward_stack.pop()
            self.history_stack.append(next_state)
            self.navigate_to(next_state[0], next_state[1], from_history=True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())