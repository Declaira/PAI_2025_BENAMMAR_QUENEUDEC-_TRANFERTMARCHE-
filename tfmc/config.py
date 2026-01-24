import os
from typing import Dict, Union

import pandas as pd
import requests
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel

# --- CONFIGURATION ET STYLES ---
BASE_DIR: str = os.path.dirname(os.path.dirname(__file__))
DATA_PATH: str = os.path.join(BASE_DIR, "data")

COLOR_MAIN: str = "#ffa45f"
COLOR_SIDEBAR: str = "#1a3150"
COLOR_BG: str = "#f5f6f8"
COLOR_LINK: str = "#005ca8"
border_color = "#f1c40f"

STYLE_SHEET: str = f"""
QMainWindow {{ background-color: {COLOR_BG}; }}
QFrame#sidebar {{ background-color: {COLOR_SIDEBAR}; min-width: 220px; max-width: 220px; }}
QLabel#side_title {{ color: white; font-weight: bold; font-size: 14px; margin-top: 10px; }}
QListWidget {{ background: transparent; border: none; color: #cbd5e1; font-size: 12px; }}
QListWidget::item:hover {{ color: white; background: rgba(255,255,255,0.1); }}
QFrame#top_bar {{ background-color: white; border-bottom: 2px solid {COLOR_MAIN}; }}
QLineEdit#search_bar {{ border: 1px solid #cbd5e1; border-radius: 4px; padding: 6px 12px; font-size: 14px; color: #334155; }}
QPushButton#nav_btn {{ background-color: rgba(255,255,255,0.1); color: white; border-radius: 4px; border: none; font-weight: bold; }}
QPushButton#nav_btn:hover {{ background-color: {COLOR_MAIN}; color: black; }}
QPushButton#search_btn {{background-color: #ff8c33;border-radius: 4px;padding: 5px;}}
QPushButton#search_btn:hover {{background-color: {COLOR_MAIN};}}
QLabel#page_title {{ font-size: 26px; font-weight: 800; color: {COLOR_SIDEBAR}; }}
QLabel#stat_val {{ font-size: 22px; font-weight: bold; color: {COLOR_MAIN}; }}
QLabel#lbl_side_info {{color: #94a3b8; font-size: 11px; margin-top: 10px;}}
QLabel#label {{font-size: 10px; color: gray;}}
QLabel#lbl {{font-weight: bold; color: #1a3150; font-size: 13px; margin-bottom: 5px;}}
QLabel#lbl_lbl {{color: #64748b; font-size: 10px; font-weight: bold;}}
QTableWidget {{ border: 1px solid #e2e8f0; border-radius: 6px; background: white; gridline-color: #f1f5f9; }}
QHeaderView::section {{ background-color: #f8fafc; color: {COLOR_SIDEBAR}; font-weight: bold; padding: 8px; border: none; }}
QTableWidget::item:hover {{ background-color: #e8f0fe; color: {COLOR_LINK}; }}
QPushButton#action_btn {{ background-color: {COLOR_SIDEBAR}; color: white; border-radius: 4px; padding: 5px 10px; font-weight: bold; }}
QPushButton#action_btn:hover {{ background-color: #2c5282; }}
QPushButton#clear_btn {{background-color: #ff8c33 ;color: white;border-radius: 4px;padding: 5px;font-size: 10px;margin-top: 5px;border: none;}}
QPushButton#btn_add {{ background-color: #27ae60; color: white; font-weight: bold; border-radius: 4px; font-size: 16px; }}
QPushButton#btn_add:hover {{ background-color: #2ecc71; }}
QPushButton#btn_remove {{ background-color: #e74c3c; color: white; font-weight: bold; border-radius: 4px; font-size: 16px; }}
QPushButton#btn_remove:hover {{ background-color: #c0392b; }}
QGraphicsView#view {{background-color: {COLOR_BG}; border: none;}}
QWidget#graph_dashboard {{background-color: white; border-left: 1px solid #e2e8f0;}}

"""

# Mapping étendu pour les drapeaux
COUNTRY_DATA: Dict[str, Dict[str, str]] = {
    "Spain": {"fr": "Espagne", "code": "es"},
    "England": {"fr": "Angleterre", "code": "gb-eng"},
    "France": {"fr": "France", "code": "fr"},
    "Germany": {"fr": "Allemagne", "code": "de"},
    "Italy": {"fr": "Italie", "code": "it"},
    "San Marino": {"fr": "Saint-Marin", "code": "sm"},
    "Portugal": {"fr": "Portugal", "code": "pt"},
    "Netherlands": {"fr": "Pays-Bas", "code": "nl"},
    "Belgium": {"fr": "Belgique", "code": "be"},
    "Sweden": {"fr": "Suède", "code": "se"},
    "Norway": {"fr": "Norvège", "code": "no"},
    "Denmark": {"fr": "Danemark", "code": "dk"},
    "Faroe Islands": {"fr": "Iles Féroé", "code": "fo"},
    "Poland": {"fr": "Pologne", "code": "pl"},
    "Russia": {"fr": "Russie", "code": "ru"},
    "Belarus": {"fr": "Biélorussie", "code": "by"},
    "Estonia": {"fr": "Estonie", "code": "ee"},
    "Latvia": {"fr": "Lettonie", "code": "lv"},
    "Lithuania": {"fr": "Lithuanie", "code": "lt"},
    "Ukraine": {"fr": "Ukraine", "code": "ua"},
    "Serbia": {"fr": "Serbie", "code": "rs"},
    "Kosovo": {"fr": "Kosovo", "code": "xk"},
    "Montenegro": {"fr": "Monténégro", "code": "me"},
    "Albania": {"fr": "Albanie", "code": "al"},
    "Croatia": {"fr": "Croatie", "code": "hr"},
    "Greece": {"fr": "Grèce", "code": "gr"},
    "Turkey": {"fr": "Turquie", "code": "tr"},
    "Türkiye": {"fr": "Turquie", "code": "tr"},
    "Romania": {"fr": "Roumanie", "code": "ro"},
    "Moldova": {"fr": "Moldavie", "code": "md"},
    "Czech Republic": {"fr": "Tchéquie", "code": "cz"},
    "Hungary": {"fr": "Hongrie", "code": "hu"},
    "Slovakia": {"fr": "Slovaquie", "code": "sk"},
    "Slovenia": {"fr": "Slovénie", "code": "si"},
    "Bosnia-Herzegovina": {"fr": "Bosnie", "code": "ba"},
    "Bulgaria": {"fr": "Bulgarie", "code": "bg"},
    "Austria": {"fr": "Autriche", "code": "at"},
    "Liechtenstein": {"fr": "Liechtenstein", "code": "li"},
    "Switzerland": {"fr": "Suisse", "code": "ch"},
    "Scotland": {"fr": "Ecosse", "code": "gb-sct"},
    "Wales": {"fr": "Pays de Galles", "code": "gb-wls"},
    "Brazil": {"fr": "Brésil", "code": "br"},
    "Argentina": {"fr": "Argentine", "code": "ar"},
    "Uruguay": {"fr": "Uruguay", "code": "uy"},
    "Colombia": {"fr": "Colombie", "code": "co"},
    "Venezuela": {"fr": "Venezuela", "code": "ve"},
    "Mexico": {"fr": "Mexique", "code": "mx"},
    "United States": {"fr": "Etats-Unis", "code": "us"},
    "Canada": {"fr": "Canada", "code": "ca"},
    "Jamaica": {"fr": "Jamaïque", "code": "jm"},
    "Ecuador": {"fr": "Equateur", "code": "ec"},
    "Paraguay": {"fr": "Paraguay", "code": "py"},
    "Chile": {"fr": "Chili", "code": "cl"},
    "Peru": {"fr": "Pérou", "code": "pe"},
    "Bolivia": {"fr": "Bolivie", "code": "bo"},
    "Syria": {"fr": "Syrie", "code": "sy"},
    "Japan": {"fr": "Japon", "code": "jp"},
    "Korea, South": {"fr": "Corée du Sud", "code": "kr"},
    "Korea, North": {"fr": "Corée du Nord", "code": "kp"},
    "China": {"fr": "Chine", "code": "cn"},
    "Macao": {"fr": "Macao", "code": "mo"},
    "Chinese Taipei": {"fr": "Taïwan", "code": "tw"},
    "Australia": {"fr": "Australie", "code": "au"},
    "Papua New Guinea": {"fr": "Papouasie-Nouvelle-Guinée", "code": "pg"},
    "Neukaledonien": {"fr": "Nouvelle-Calédonie", "code": "nc"},
    "Tahiti": {"fr": "Tahiti", "code": "pf"},
    "Mauritania": {"fr": "Mauritanie", "code": "mr"},
    "Malawi": {"fr": "Malawi", "code": "mw"},
    "Mauritius": {"fr": "Maurice", "code": "mu"},
    "Madagascar": {"fr": "Madagascar", "code": "mg"},
    "Cameroon": {"fr": "Cameroun", "code": "cm"},
    "Nigeria": {"fr": "Nigéria", "code": "ng"},
    "Ghana": {"fr": "Ghana", "code": "gh"},
    "Senegal": {"fr": "Sénégal", "code": "sn"},
    "Cape Verde": {"fr": "Cap-Vert", "code": "cv"},
    "Morocco": {"fr": "Maroc", "code": "ma"},
    "Libya": {"fr": "Libye", "code": "ly"},
    "Egypt": {"fr": "Egypte", "code": "eg"},
    "Ivory Coast": {"fr": "Cote d'Ivoire", "code": "ci"},
    "Mali": {"fr": "Mali", "code": "ml"},
    "Burkina Faso": {"fr": "Burkina Faso", "code": "bf"},
    "Comoros": {"fr": "Comores", "code": "km"},
    "The Gambia": {"fr": "Gambie", "code": "gm"},
    "Guinea": {"fr": "Guinée", "code": "gn"},
    "Tunisia": {"fr": "Tunisie", "code": "tn"},
    "Algeria": {"fr": "Algérie", "code": "dz"},
    "Rwanda": {"fr": "Rwanda", "code": "rw"},
    "Burundi": {"fr": "Burundi", "code": "bi"},
    "DR Congo": {"fr": "RD Congo", "code": "cd"},
    "Central African Republic": {"fr": "République Centrafricaine", "code": "cf"},
    "Congo": {"fr": "Congo", "code": "cg"},
    "Chad": {"fr": "Tchad", "code": "td"},
    "South Africa": {"fr": "Afrique du Sud", "code": "za"},
    "Kenya": {"fr": "Kenya", "code": "ke"},
    "Uganda": {"fr": "Ouganda", "code": "ug"},
    "Sudan": {"fr": "Soudan", "code": "sd"},
    "Southern Sudan": {"fr": "Soudan du sud", "code": "ss"},
    "Somalia": {"fr": "Somalie", "code": "so"},
    "Equatorial Guinea": {"fr": "Guinée Équatoriale", "code": "gq"},
    "Sao Tome and Principe": {"fr": "Sao Tomé et Principe", "code": "st"},
    "Gabon": {"fr": "Gabon", "code": "ga"},
    "Angola": {"fr": "Angola", "code": "ao"},
    "Benin": {"fr": "Bénin", "code": "bj"},
    "Kazakhstan": {"fr": "Kazakhstan", "code": "kz"},
    "Kyrgyzstan": {"fr": "Kirghizistan", "code": "kg"},
    "Tajikistan": {"fr": "Tadjikistan", "code": "tj"},
    "Saudi Arabia": {"fr": "Arabie Saoudite", "code": "sa"},
    "United Arab Emirates": {"fr": "Emirats Arabes Unis", "code": "ae"},
    "Palestine": {"fr": "Palestine", "code": "ps"},
    "Jordan": {"fr": "Jordanie", "code": "jo"},
    "Israel": {"fr": "Israël", "code": "il"},
    "Lebanon": {"fr": "Liban", "code": "lb"},
    "Georgia": {"fr": "Géorgie", "code": "ge"},
    "Armenia": {"fr": "Arménie", "code": "am"},
    "Azerbaijan": {"fr": "Azerbaïdjan", "code": "az"},
    "Uzbekistan": {"fr": "Ouzbékistan", "code": "uz"},
    "Turkmenistan": {"fr": "Turkménistan", "code": "tm"},
    "Gambia": {"fr": "Gambie", "code": "gm"},
    "Suriname": {"fr": "Suriname", "code": "sr"},
    "Guyana": {"fr": "Guyana", "code": "gy"},
    "French Guiana": {"fr": "Guyane", "code": "gf"},
    "Haiti": {"fr": "Haïti", "code": "ht"},
    "Curaçao": {"fr": "Curaçao", "code": "cw"},
    "Aruba": {"fr": "Aruba", "code": "aw"},
    "Cuba": {"fr": "Cuba", "code": "cu"},
    "Grenada": {"fr": "Grenade", "code": "gd"},
    "St. Kitts & Nevis": {"fr": "Saint-Christophe-et-Niévès", "code": "kn"},
    "St. Lucia": {"fr": "Sainte-Lucie", "code": "lc"},
    "Montserrat": {"fr": "Montserrat", "code": "ms"},
    "Guadeloupe": {"fr": "Guadeloupe", "code": "gp"},
    "Martinique": {"fr": "Martinique", "code": "mq"},
    "Saint-Martin": {"fr": "Saint-Martin", "code": "fr"},
    "Sint Maarteen": {"fr": "Saint-Martin", "code": "sx"},
    "Togo": {"fr": "Togo", "code": "tg"},
    "Liberia": {"fr": "Libéria", "code": "lr"},
    "Sierra Leone": {"fr": "Sierra Leone", "code": "sl"},
    "Niger": {"fr": "Niger", "code": "ne"},
    "Eritrea": {"fr": "Erythrée", "code": "er"},
    "Ethiopia": {"fr": "Ethiopie", "code": "et"},
    "Zambia": {"fr": "Zambie", "code": "zm"},
    "Zimbabwe": {"fr": "Zimbabwe", "code": "zw"},
    "Guinea-Bissau": {"fr": "Guinée-Bissau", "code": "gw"},
    "Mozambique": {"fr": "Mozambique", "code": "mz"},
    "Northern Ireland": {"fr": "Irlande du Nord", "code": "gb-nir"},
    "Ireland": {"fr": "Irlande", "code": "ie"},
    "Finland": {"fr": "Finlande", "code": "fi"},
    "Iceland": {"fr": "Islande", "code": "is"},
    "Luxembourg": {"fr": "Luxembourg", "code": "lu"},
    "Malta": {"fr": "Malte", "code": "mt"},
    "Cyprus": {"fr": "Chypre", "code": "cy"},
    "North Macedonia": {"fr": "Macédoine du Nord", "code": "mk"},
    "Gibraltar": {"fr": "Gibraltar", "code": "gi"},
    "Thailand": {"fr": "Thaïlande", "code": "th"},
    "Vietnam": {"fr": "Vietnam", "code": "vn"},
    "Philippines": {"fr": "Philippines", "code": "ph"},
    "Indonesia": {"fr": "Indonésie", "code": "id"},
    "Brunei Darussalam": {"fr": "Bruneï", "code": "bn"},
    "Malaysia": {"fr": "Malaisie", "code": "my"},
    "Singapore": {"fr": "Singapour", "code": "sg"},
    "India": {"fr": "Inde", "code": "in"},
    "Pakistan": {"fr": "Pakistan", "code": "pk"},
    "Bangladesh": {"fr": "Bangladesh", "code": "bd"},
    "New Zealand": {"fr": "Nouvelle-Zélande", "code": "nz"},
    "Fiji": {"fr": "Fidji", "code": "fj"},
    "El Salvador": {"fr": "El Salvador", "code": "sv"},
    "Costa Rica": {"fr": "Costa Rica", "code": "cr"},
    "Honduras": {"fr": "Honduras", "code": "hn"},
    "Guatemala": {"fr": "Guatemala", "code": "gt"},
    "Nicaragua": {"fr": "Nicaragua", "code": "ni"},
    "Panama": {"fr": "Panama", "code": "pa"},
    "Dominican Republic": {"fr": "République Dominicaine", "code": "do"},
    "Saint Kitts and Nevis": {"fr": "Saint-Christophe-et-Niévès", "code": "kn"},
    "Barbados": {"fr": "Barbade", "code": "bb"},
    "Bermuda": {"fr": "Bermudes", "code": "bm"},
    "Bonaire": {"fr": "Bonaire", "code": "bq"},
    "Trinidad and Tobago": {"fr": "Trinité-et-Tobago", "code": "tt"},
    "Antigua and Barbuda": {"fr": "Antigua-et-Barbuda", "code": "ag"},
    "Curacao": {"fr": "Curaçao", "code": "cw"},
    "Iraq": {"fr": "Irak", "code": "iq"},
    "Iran": {"fr": "Iran", "code": "ir"},
    "Qatar": {"fr": "Qatar", "code": "qa"},
    "Kuwait": {"fr": "Koweït", "code": "kw"},
    "Bahrain": {"fr": "Bahreïn", "code": "bh"},
    "Oman": {"fr": "Oman", "code": "om"},
    "Afghanistan": {"fr": "Afghanistan", "code": "af"},
}

POSITIONS_FR: Dict[str, str] = {
    "Goalkeeper": "Gardien",
    "Defender": "Défenseur",
    "Midfield": "Milieu",
    "Attack": "Attaquant",
    "Centre-Back": "Défenseur Central",
    "Left-Back": "Latéral Gauche",
    "Right-Back": "Latéral Droit",
    "Defensive Midfield": "Milieu Défensif",
    "Central Midfield": "Milieu Central",
    "Attacking Midfield": "Milieu Offensif",
    "Left Winger": "Ailier Gauche",
    "Right Winger": "Ailier Droit",
    "Centre-Forward": "Avant-centre",
    "Second Striker": "Deuxième Attaquant",
}


class AsyncImageLabel(QLabel):
    """
    Extension de QLabel permettant de charger des images de manière asynchrone
    via une URL ou un chemin de fichier local.
    """

    def set_image_from_url(self, url: Union[str, float]) -> None:
        """
        Télécharge une image depuis une URL et l'affiche dans le label.

        Args:
            url: L'URL de l'image (peut être un float NaN issu de Pandas).
        """
        self.clear()
        if pd.isna(url) or url == "":
            self.setText("No IMG")
            return

        try:
            r = requests.get(str(url), timeout=1.5)
            if r.status_code == 200:
                img = QImage()
                img.loadFromData(r.content)
                pixmap = QPixmap.fromImage(img)
                if not pixmap.isNull():
                    self.setPixmap(
                        pixmap.scaled(
                            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                    )
                else:
                    self.setText("Format Err")
            else:
                self.setText("Not Found")
        except Exception:
            self.setText("Err")

    def set_image_from_path(self, file_path: Union[str, float]) -> None:
        """
        Charge une image depuis un chemin local (ex: C:/images/logo.png).

        Args:
            file_path: Le chemin absolu vers le fichier image.
        """
        self.setAlignment(Qt.AlignCenter)

        # 1. Vérifier si le chemin est vide ou invalide (NaN)
        if not file_path or (pd.isna(file_path)):
            self.setText("Pas de chemin")
            return

        # 2. Charger l'image dans un QPixmap
        pixmap = QPixmap(str(file_path))

        # 3. Vérifier si le chargement a réussi
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
        else:
            self.setText("Format invalide")