import os
import pandas as pd
import requests
import numpy as np
import kagglehub
from typing import Optional, Dict, Any
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QComboBox, QLineEdit, QDialogButtonBox,
                             QFormLayout, QSpinBox, QDialog, QTabWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from config import COUNTRY_DATA, DATA_PATH, POSITIONS_FR

# --- GESTION DES DONNÉES ---
class DataManager:
    def __init__(self):
        self.leagues = {
            # --- LIGUES ---
            'FR1': 'Ligue 1', 'ES1': 'LaLiga', 'GB1': 'Premier League', 
            'IT1': 'Serie A', 'L1': 'Bundesliga', 'PO1': 'Liga Portugal',
            'NL1':'Eredivisie', 'BE1':'Jupiler Pro League','DK1':'Superliga',
            'RU1':'Premier Liga','UKR1':'Premier Liga','TR1':'Süper Lig',
            'SC1':'Scottish Premiership','GR1':'Super League 1',
            # --- COUPES ---
            'CL': 'UEFA Champions League',
            'EL': 'Europa League',
            'CDR': 'Copa del Rey',
            'FAC': 'FA Cup',
            'DFB': 'DFB-Pokal',
            'CIT': 'Coppa Italia',
            'NLP': 'KNVB Beker',
            'GRP': 'Kypello Elladas'
        }
        self.flag_cache: Dict[str, QPixmap] = {}
        self.load_data()

    def get_flag_pixmap(self, country_name: str) -> Optional[QPixmap]:
        """Récupère et met en cache l'image du drapeau pour un nom (FR/EN) ou un code."""
        if not country_name or country_name == "-":
            return None

        # 1. Résolution du code ISO via le dictionnaire global
        code = None
        if country_name in COUNTRY_DATA:
            code = COUNTRY_DATA[country_name]["code"]
        else:
            for data in COUNTRY_DATA.values():
                if data["fr"] == country_name:
                    code = data["code"]
                    break
        if not code:
            if len(country_name) <= 3:
                code = country_name.lower()
            else:
                return None

        # 2. Gestion du cache
        if code in self.flag_cache:
            return self.flag_cache[code]

        # 3. Téléchargement si non présent dans le cache
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
    
    def prepare_local_data(self):
        if not os.path.exists(DATA_PATH):
            os.makedirs(DATA_PATH)
            print("Téléchargement des données Kaggle...")
            try:
                cache_path = kagglehub.dataset_download("davidcariboo/player-scores")
                files = ['clubs.csv', 'players.csv', 'games.csv', 'appearances.csv', 'transfers.csv']
                for f in files:
                    src = os.path.join(cache_path, f)
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(DATA_PATH, f))
            except Exception as e:
                print(f"Erreur téléchargement: {e}")

    def load_data(self):
        self.prepare_local_data()

        try:
            self.df_clubs = pd.read_csv(os.path.join(DATA_PATH, "clubs.csv"))
            self.df_players = pd.read_csv(os.path.join(DATA_PATH, "players.csv"))
            self.df_games = pd.read_csv(os.path.join(DATA_PATH, "games.csv"))
            self.df_appearances = pd.read_csv(os.path.join(DATA_PATH, "appearances.csv"))
            self.df_transfers = pd.read_csv(os.path.join(DATA_PATH, "transfers.csv"))

            # --- TRADUCTIONS ---
            # Traduction des pays (Nationalité)
            def translate_country(c):
                if pd.isna(c): return c
                return COUNTRY_DATA.get(c, {}).get("fr", c)
            
            self.df_players['country_of_citizenship'] = self.df_players['country_of_citizenship'].apply(translate_country)
            
            # Traduction des postes
            self.df_players['position'] = self.df_players['position'].map(POSITIONS_FR).fillna(self.df_players['position'])
            self.df_players['sub_position'] = self.df_players['sub_position'].map(POSITIONS_FR).fillna(self.df_players['sub_position'])

            if 'transfer_season' in self.df_transfers.columns:
                self.df_transfers = self.df_transfers.rename(columns={'transfer_season': 'season'})
            
            def conv_s(v):
                v = str(v).strip()
                if '/' in v: return 2000 + int(v.split('/')[0])
                return pd.to_numeric(v, errors='coerce')
            
            self.df_transfers['season'] = self.df_transfers['season'].apply(conv_s)
            self.seasons = sorted(self.df_games['season'].dropna().unique().astype(int), reverse=True)
            
            # --- CALCUL DE L'ÂGE ---
            def calculate_age(dob: Any) -> Any:
                dob = str(dob)[:10]
                if pd.isna(dob) or dob == "" or dob == "nan" or dob == "None":
                    return np.nan  # Utiliser NaN au lieu de "-"
                try:
                    birth_date = datetime.strptime(str(dob), "%Y-%m-%d")
                    today = datetime.today()
                    age = (
                        today.year
                        - birth_date.year
                        - ((today.month, today.day) < (birth_date.month, birth_date.day))
                    )
                    return int(age)
                except Exception:
                    return np.nan
            
            self.df_players['age'] = self.df_players['date_of_birth'].apply(calculate_age)

            return True
        except Exception as e:
            print(f"Erreur chargement CSV: {e}")
            return False
        
    def filter_players(self, nom=None, nationalite=None, poste=None, age_min=None, age_max=None, 
                       val_min=None, val_max=None, sort_by="market_value_in_eur", limit=100):
        df = self.df_players.copy()
        
        if nom:
            df = df[df['name'].str.contains(nom, case=False, na=False)]
        if nationalite and nationalite != "Toutes":
            df = df[df['country_of_citizenship'] == nationalite]
        if poste and poste != "Tous":
            df = df[df['position'] == poste]
        
        # Filtres numériques
        if age_min: df = df[df['age'] >= age_min]
        if age_max: df = df[df['age'] <= age_max]
        if val_min: df = df[df['market_value_in_eur'] >= val_min * 1000000]
        if val_max: df = df[df['market_value_in_eur'] <= val_max * 1000000]

        ascending = True if sort_by in ['name', 'age'] else False
        if sort_by in df.columns:
            df = df.sort_values(by=sort_by, ascending=ascending)

        return df.head(limit)
    
    def filter_teams(self, nom=None, ligue=None):
        df = self.df_clubs.copy()
        if nom:
            df = df[df['name'].str.contains(nom, case=False, na=False)]
        if ligue and ligue != "Tous":
            lid = next((k for k, v in self.leagues.items() if v == ligue), None)
            if lid: df = df[df['domestic_competition_id'] == lid]
        return df
    
    def get_club_name(self, cid: int, short: bool = False) -> str:
        """Récupère le nom du club. Si short=True, tente de renvoyer le short_name."""
        r = self.df_clubs[self.df_clubs['club_id'] == cid]
        if r.empty:
            return f"Club {cid}"
        
        if short:
            s_name = r.iloc[0].get('short_name')
            if pd.notna(s_name) and str(s_name).strip() != "":
                return str(s_name)
        
        return r.iloc[0]['name']
    
    def get_club_rank_history(self, club_id):
        """Calcule le classement historique d'un club à partir de df_games."""
        # Trouver la compétition nationale du club
        c_info = self.df_clubs[self.df_clubs['club_id'] == club_id]
        if c_info.empty: return pd.DataFrame()
        comp_id = c_info.iloc[0]['domestic_competition_id']
        
        # Filtrer les matchs de cette compétition
        df_comp = self.df_games[self.df_games['competition_id'] == comp_id].copy()
        history = []

        for s in sorted(df_comp['season'].unique()):
            s_games = df_comp[df_comp['season'] == s]
            res = {}
            # Calcul des points pour tous les clubs de la ligue cette saison là
            for _, r in s_games.iterrows():
                h, a = r['home_club_id'], r['away_club_id']
                hg, ag = r['home_club_goals'], r['away_club_goals']
                for t in [h, a]: 
                    if t not in res: res[t] = {'p':0, 'bp':0, 'bc':0}
                res[h]['bp']+=hg; res[h]['bc']+=ag; res[a]['bp']+=ag; res[a]['bc']+=hg
                if hg > ag: res[h]['p']+=3
                elif ag > hg: res[a]['p']+=3
                else: res[h]['p']+=1; res[a]['p']+=1
            
            # Trier pour obtenir le classement
            standings = sorted(res.items(), key=lambda x: (x[1]['p'], x[1]['bp']-x[1]['bc']), reverse=True)
            ranks = {item[0]: i+1 for i, item in enumerate(standings)}
            
            if club_id in ranks:
                history.append({'Saison': str(s), 'Classement': ranks[club_id]})
        
        return pd.DataFrame(history)

class FilterDialog(QDialog):
    def __init__(self, parent, dm):
        super().__init__(parent)
        self.setWindowTitle("Filtres avancés")
        self.resize(400, 600)
        self.dm = dm
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # --- Onglet Joueurs ---
        self.tab_p = QWidget()
        form_p = QFormLayout(self.tab_p)
        self.p_nom = QLineEdit()
        self.p_nat = QComboBox(); self.p_nat.addItem("Toutes"); self.p_nat.addItems(sorted(dm.df_players['country_of_citizenship'].dropna().unique()))
        self.p_poste = QComboBox(); self.p_poste.addItem("Tous"); self.p_poste.addItems(sorted(dm.df_players['position'].dropna().unique()))
        self.p_min_val = QSpinBox(); self.p_min_val.setRange(0, 500); self.p_min_val.setSuffix(" M€"); self.p_min_val.setValue(1)
        self.p_max_val = QSpinBox(); self.p_max_val.setRange(0, 500); self.p_max_val.setSuffix(" M€"); self.p_max_val.setValue(10)
        self.p_age_min = QSpinBox(); self.p_age_min.setRange(15, 50); self.p_age_min.setValue(15)
        self.p_age_max = QSpinBox(); self.p_age_max.setRange(15, 50); self.p_age_max.setValue(45)
        
        # --- Tri et Limite ---
        self.p_sort = QComboBox()
        self.p_sort.addItem("Valeur Marchande", "market_value_in_eur")
        self.p_sort.addItem("Nom", "name")
        self.p_sort.addItem("Age", "age")
        self.p_sort.addItem("Taille", "height_in_cm")
        
        self.p_limit = QSpinBox()
        self.p_limit.setRange(1, 500); self.p_limit.setValue(20)
        
        form_p.addRow("Nom:", self.p_nom)
        form_p.addRow("Nationalité:", self.p_nat)
        form_p.addRow("Poste:", self.p_poste)
        form_p.addRow("Valeur Min:", self.p_min_val)
        form_p.addRow("Valeur Max:", self.p_max_val)
        form_p.addRow("Âge Min:", self.p_age_min)
        form_p.addRow("Âge Max:", self.p_age_max)
        form_p.addRow("Trier par:", self.p_sort)
        form_p.addRow("Nombre de résultats:", self.p_limit)
        
        # --- Onglet Clubs ---
        self.tab_c = QWidget()
        form_c = QFormLayout(self.tab_c)
        self.c_nom = QLineEdit()
        self.c_ligue = QComboBox(); self.c_ligue.addItem("Tous"); self.c_ligue.addItems(sorted(dm.leagues.values()))
        form_c.addRow("Nom:", self.c_nom)
        form_c.addRow("Ligue:", self.c_ligue)
        
        self.tabs.addTab(self.tab_p, "Joueurs")
        self.tabs.addTab(self.tab_c, "Clubs")
        layout.addWidget(self.tabs)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_params(self):
        mode = "joueurs" if self.tabs.currentIndex() == 0 else "clubs"
        p = {'type': mode}
        if mode == "joueurs":
            if self.p_nom.text(): p['nom'] = self.p_nom.text()
            p['nationalite'] = self.p_nat.currentText()
            p['poste'] = self.p_poste.currentText()
            p['val_min'] = self.p_min_val.value()
            p['val_max'] = self.p_max_val.value()
            p['age_min'] = self.p_age_min.value()
            p['age_max'] = self.p_age_max.value()
            p['sort_by'] = self.p_sort.currentData()
            p['limit'] = self.p_limit.value()
        else:
            if self.c_nom.text(): p['nom'] = self.c_nom.text()
            p['ligue'] = self.c_ligue.currentText()
        return p