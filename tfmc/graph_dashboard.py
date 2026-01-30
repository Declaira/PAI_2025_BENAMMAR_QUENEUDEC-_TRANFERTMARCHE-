import pandas as pd
import numpy as np
from datetime import date
from typing import Optional, Any, Dict, TYPE_CHECKING, List, cast

# Matplotlib
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.axes import Axes

# PyQt5
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QCompleter,
    QFrame,
    QSplitter,
    QGridLayout,
)
from PyQt5.QtCore import Qt, QTimer

from tfmc.config import COLOR_MAIN, COLOR_BG, COLOR_SIDEBAR

if TYPE_CHECKING:
    from tfmc.main_window import MainWindow


class GraphDashboard(QWidget):
    """
    Widget contenant le panneau de contrôle et la zone de dessin Matplotlib.
    Permet d'afficher des statistiques dynamiques selon le contexte (Global, Championnat, Club, Joueur).
    """

    def __init__(
        self, main_window: "MainWindow", parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.mw = main_window
        self.dm = main_window.dm
        self.current_inputs: Dict[str, Any] = {}

        self.layout_main = QVBoxLayout(self) # Renommé pour éviter conflit avec méthode layout()
        self.setObjectName("graph_dashboard")

        # --- ZONE DE CONTRÔLE (Haut) ---
        self.controls = QFrame()
        self.grid = QGridLayout(self.controls)
        self.grid.setContentsMargins(10, 10, 10, 10)

        # Bouton Ajouter (+)
        self.btn_add = QPushButton("+")
        self.btn_add.setToolTip("Ajouter un graphique de comparaison à gauche")
        self.btn_add.setFixedSize(30, 30)
        self.btn_add.setObjectName("btn_add")
        # Correction Enum
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.clicked.connect(self.add_comparison_graph)
        self.grid.addWidget(self.btn_add, 0, 0)

        # Bouton Supprimer (-)
        self.btn_remove = QPushButton("-")
        self.btn_remove.setToolTip("Fermer ce graphique")
        self.btn_remove.setFixedSize(30, 30)
        self.btn_remove.setObjectName("btn_remove")
        # Correction Enum
        self.btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_remove.clicked.connect(self.remove_dashboard)
        self.grid.addWidget(self.btn_remove, 0, 1)

        # 1. Choix du MODE
        self.grid.addWidget(QLabel("Mode d'analyse :"), 0, 2)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Global", "Championnat", "Club", "Joueur"])
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        self.grid.addWidget(self.combo_mode, 0, 3)

        # 2. Zone dynamique (Inputs)
        self.dynamic_frame = QFrame()
        self.dynamic_layout = QVBoxLayout(self.dynamic_frame)
        self.dynamic_layout.setContentsMargins(0, 0, 0, 0)
        self.grid.addWidget(self.dynamic_frame, 1, 0, 1, 4)

        # 3. Bouton Update
        self.btn_update = QPushButton("Générer Graphique 📊")
        self.btn_update.setObjectName("action_btn")
        # Correction Enum
        self.btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_update.clicked.connect(self.plot)
        self.grid.addWidget(self.btn_update, 2, 0, 1, 4)

        self.layout_main.addWidget(self.controls)

        # --- ZONE GRAPHIQUE (Bas) ---
        self.figure = Figure(figsize=(5, 5), dpi=100)
        if hasattr(self.figure, "patch"):
             self.figure.patch.set_facecolor(COLOR_BG)  # type: ignore
        
        self.canvas = FigureCanvas(self.figure) # type: ignore
        self.layout_main.addWidget(self.canvas)

        self.on_mode_changed()
        QTimer.singleShot(10, self.update_buttons_state)

    def add_comparison_graph(self) -> None:
        """Ajoute un nouveau panneau de graphique dans le splitter principal."""
        new_dash = GraphDashboard(self.mw)
        self.mw.splitter.addWidget(new_dash)
        new_dash.show()
        # Masquer le contenu principal pour laisser place aux graphs
        widget_zero = self.mw.splitter.widget(0)
        if widget_zero:
            widget_zero.hide()

        total_w = self.mw.splitter.width()
        # Répartition équitable de l'espace
        self.mw.splitter.setSizes([0, total_w // 2, total_w // 2])

        # Mise à jour de l'état des boutons pour tous les graphs
        for i in range(self.mw.splitter.count()):
            w = self.mw.splitter.widget(i)
            if isinstance(w, GraphDashboard):
                w.update_buttons_state()
        new_dash.plot()

    def remove_dashboard(self) -> None:
        """Supprime ce panneau graphique et réajuste l'affichage."""
        # 1. Supprimer ce widget
        self.setParent(None)
        self.deleteLater()

        # 2. Vérifier ce qu'il reste
        dashboards = [
            self.mw.splitter.widget(i)
            for i in range(self.mw.splitter.count())
            if isinstance(self.mw.splitter.widget(i), GraphDashboard)
        ]

        total_w = self.mw.splitter.width()
        widget_zero = self.mw.splitter.widget(0)

        if len(dashboards) == 1:
            # --- RETOUR AU MODE CÔTÉ À CÔTÉ (Contenu + 1 Graph) ---
            if widget_zero:
                widget_zero.show()
            self.mw.splitter.setSizes([int(total_w * 0.5), int(total_w * 0.5)])
            dashboards[0].update_buttons_state()

        elif len(dashboards) == 0:
            # Plus de graphiques, on affiche le contenu en plein écran
            if widget_zero:
                widget_zero.show()
            self.mw.splitter.setSizes([total_w])
            self.mw.btn_graph.setChecked(False)

    def update_buttons_state(self) -> None:
        """Met à jour l'activation des boutons (+) et (-) selon le nombre de widgets graphiques."""
        main_splitter = self.parent()
        # Navigation sécurisée vers le parent QSplitter
        while main_splitter and not isinstance(main_splitter, QSplitter):
            main_splitter = main_splitter.parent()

        if isinstance(main_splitter, QSplitter):
            dashboards = [
                main_splitter.widget(i)
                for i in range(main_splitter.count())
                if isinstance(main_splitter.widget(i), GraphDashboard)
            ]
            count = len(dashboards)
            for db in dashboards:
                if isinstance(db, GraphDashboard): # Double check pour le typage
                    # --- Bouton AJOUT (+) ---
                    if count >= 2:
                        db.btn_add.setEnabled(False)
                        db.btn_add.setStyleSheet(
                            "background-color: #bdc3c7; color: white; border-radius: 4px;"
                        )
                    else:
                        db.btn_add.setEnabled(True)
                        db.btn_add.setStyleSheet(
                            "background-color: #27ae60; color: white; border-radius: 4px; font-weight: bold;"
                        )

                    # --- Bouton FERMER (-) ---
                    if count <= 1:
                        db.btn_remove.setEnabled(False)
                        db.btn_remove.setStyleSheet(
                            "background-color: #bdc3c7; color: white; border-radius: 4px;"
                        )
                    else:
                        db.btn_remove.setEnabled(True)
                        db.btn_remove.setStyleSheet(
                            "background-color: #e74c3c; color: white; border-radius: 4px; font-weight: bold;"
                        )

    def set_context(
        self, mode_type: str, name: Optional[str] = None, extra_id: Optional[str] = None
    ) -> None:
        """
        Met à jour le contexte du graphique (auto-sélection des listes déroulantes).
        """
        # 1. Définir le Mode (Club, Joueur, etc.)
        if mode_type == "Global" and name:
            mode_type = "Championnat"

        # Correction Enum
        index = self.combo_mode.findText(mode_type, Qt.MatchFlag.MatchContains)
        if index >= 0:
            self.combo_mode.setCurrentIndex(index)

        # 2. Remplissage des champs
        if mode_type == "Joueur" and name:
            if "player" in self.current_inputs:
                self.current_inputs["player"].setText(name)

        elif mode_type == "Club" and name:
            if "club" in self.current_inputs:
                combo_club = self.current_inputs["club"]
                idx_club = combo_club.findText(name)
                if idx_club >= 0:
                    combo_club.setCurrentIndex(idx_club)
                else:
                    combo_club.setEditText(name)

                # B. Sélectionner automatiquement la Ligue associée
                if extra_id and "league" in self.current_inputs:
                    league_name = self.dm.leagues.get(extra_id)
                    if league_name:
                        combo_l = self.current_inputs["league"]
                        idx_l = combo_l.findText(league_name)
                        if idx_l >= 0:
                            combo_l.setCurrentIndex(idx_l)

        elif mode_type == "Championnat" and name:
            if "league" in self.current_inputs:
                c_league = self.current_inputs["league"]
                idx_l = c_league.findText(name)
                if idx_l >= 0:
                    c_league.setCurrentIndex(idx_l)

    def clear_dynamic_area(self) -> None:
        """Nettoie tous les widgets de la zone dynamique."""
        for i in reversed(range(self.dynamic_layout.count())):
            item = self.dynamic_layout.itemAt(i)
            if item:
                w = item.widget()
                if w:
                    w.setParent(None)
        self.current_inputs = {}

    def on_mode_changed(self) -> None:
        """Reconstruit l'interface dynamique selon le mode sélectionné."""
        self.clear_dynamic_area()
        mode = self.combo_mode.currentText()

        # --- INPUTS COMMUNS ---
        distrib_metrics = [
            "Répartition par Âge",
            "Répartition par Nationalité",
            "Répartition par Poste",
            "Répartition par Pied",
        ]

        if mode == "Global":
            l1 = QLabel("Analyse Globale (Tous les joueurs) :")
            c_metric = QComboBox()
            c_metric.addItems(distrib_metrics + ["Répartition Valeur Marchande"])
            self.dynamic_layout.addWidget(l1)
            self.dynamic_layout.addWidget(c_metric)
            self.current_inputs = {"metric": c_metric}

        elif mode == "Championnat":
            major_leagues_names = [
                name for code, name in self.dm.leagues.items() if "1" in code
            ]

            # Interface : Ajout des noms triés par ordre alphabétique
            l1 = QLabel("Choisir le Championnat :")
            c_league = QComboBox()
            c_league.addItems(sorted(major_leagues_names))

            l2 = QLabel("Type de Graphique :")
            c_metric = QComboBox()
            c_metric.addItems(distrib_metrics + ["Répartition Valeur Marchande"])

            self.dynamic_layout.addWidget(l1)
            self.dynamic_layout.addWidget(c_league)
            self.dynamic_layout.addWidget(l2)
            self.dynamic_layout.addWidget(c_metric)
            self.current_inputs = {"league": c_league, "metric": c_metric}

        elif mode == "Club":
            l_league = QLabel("Filtre Ligue :")
            c_league = QComboBox()
            c_league.addItems(sorted({k: v for k,v in self.dm.leagues.items() if '1' in k}.values()))

            l_club = QLabel("Club :")
            c_club = QComboBox()
            c_club.setEditable(True)
            
            # Correction Completer Mode
            comp = c_club.completer()
            if comp:
                comp.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

            c_league.currentTextChanged.connect(
                lambda txt: self.populate_clubs(txt, c_club)
            )
            self.populate_clubs(c_league.currentText(), c_club)

            # Selecteur de saison pour l'effectif
            l_season = QLabel("Saison (pour effectif) :")
            c_season = QComboBox()
            c_season.addItems([str(s) for s in self.dm.seasons])

            l_metric = QLabel("Type de Graphique :")
            c_metric = QComboBox()
            c_metric.addItems(
                [
                    "Évolution : Classement",
                    "Évolution : Buts marqués",
                    "Effectif : Âges",
                    "Effectif : Nationalités",
                    "Effectif : Postes",
                ]
            )

            self.dynamic_layout.addWidget(l_league)
            self.dynamic_layout.addWidget(c_league)
            self.dynamic_layout.addWidget(l_club)
            self.dynamic_layout.addWidget(c_club)
            self.dynamic_layout.addWidget(l_season)
            self.dynamic_layout.addWidget(c_season)
            self.dynamic_layout.addWidget(l_metric)
            self.dynamic_layout.addWidget(c_metric)

            self.current_inputs = {
                "club": c_club,
                "season": c_season,
                "metric": c_metric,
                "league": c_league,
            }

        elif mode == "Joueur":
            # Sécurité si df_players est None
            player_names = list(self.dm.df_players["name"].unique()) if self.dm.df_players is not None else []
            
            l_p = QLabel("Rechercher Joueur :")
            line_player = QLineEdit()
            line_player.setPlaceholderText("Nom du joueur...")
            completer = QCompleter(player_names)
            # Corrections Enums
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            line_player.setCompleter(completer)

            l_m = QLabel("Statistiques :")
            c_metric = QComboBox()
            c_metric.addItems(
                [
                    "Buts & Passes",
                    "Buts & Passes (/90)",
                    "Cartons (Jaunes/Rouges)",
                    "Minutes jouées",
                ]
            )

            self.dynamic_layout.addWidget(l_p)
            self.dynamic_layout.addWidget(line_player)
            self.dynamic_layout.addWidget(l_m)
            self.dynamic_layout.addWidget(c_metric)
            self.current_inputs = {"player": line_player, "metric": c_metric}

    def populate_clubs(self, league_name: str, combo_club: QComboBox) -> None:
        """Remplit la liste des clubs en fonction de la ligue choisie."""
        combo_club.clear()
        if self.dm.df_clubs is None:
            return

        lid = next((k for k, v in self.dm.leagues.items() if v == league_name), None)
        if lid:
            clubs = self.dm.df_clubs[
                self.dm.df_clubs["domestic_competition_id"] == lid
            ]["name"].sort_values()
            combo_club.addItems(clubs)

    def plot(self) -> None:
        """Génère le graphique en fonction des inputs actuels."""
        self.figure.clear()
        ax: Axes = self.figure.add_subplot(111) # type: ignore
        mode = self.combo_mode.currentText()

        # Sécurité DataFrames
        if self.dm.df_players is None or self.dm.df_clubs is None:
             ax.text(0.5, 0.5, "Données non chargées", ha="center")
             self.canvas.draw()
             return

        # --- Dispatch vers les fonctions de dessin ---
        if mode == "Global":
            self.plot_distribution(
                ax, self.dm.df_players, self.current_inputs["metric"].currentText(), "Global"
            )
        elif mode == "Championnat":
            l_name = self.current_inputs["league"].currentText()
            lid = next((k for k, v in self.dm.leagues.items() if v == l_name), None)
            
            club_ids = self.dm.df_clubs[
                self.dm.df_clubs["domestic_competition_id"] == lid
            ]["club_id"]
            
            df_filtered = self.dm.df_players[
                self.dm.df_players["current_club_id"].isin(club_ids)
            ]
            self.plot_distribution(
                ax, df_filtered, self.current_inputs["metric"].currentText(), l_name
            )
        elif mode == "Club":
            self.plot_club_stats(ax)
        elif mode == "Joueur":
            self.plot_player_stats(ax)

        #self.figure.tight_layout()
        self.canvas.draw()

    # --- LOGIQUE GRAPHIQUE ---

    def plot_distribution(
        self, ax: Axes, df: pd.DataFrame, metric: str, title_suffix: str
    ) -> None:
        """
        Génère les graphiques de distribution (Global et Championnat).
        """
        if df.empty:
            ax.text(0.5, 0.5, "Pas de données", ha="center")
            return

        # --- 1. ÂGE (Histogramme) ---
        if "Âge" in metric:
            ages = df["age"].dropna()
            ax.hist(
                ages,
                bins=range(15, 45),
                color=COLOR_MAIN,
                edgecolor="white",
                alpha=0.9,
            )
            ax.set_title(
                f"Distribution des Âges - {title_suffix}",
                color=COLOR_SIDEBAR,
                fontweight="bold",
            )
            ax.set_xlabel("Âge")
            ax.set_ylabel("Nombre de joueurs")

        # --- 2. NATIONALITÉ (Pie Chart) ---
        elif "Nationalité" in metric:
            # 1. Calcul des fréquences et pourcentages
            counts = df["country_of_citizenship"].value_counts()
            total = counts.sum()
            percents = (counts / total) * 100

            # 2. Séparation : > 1% et les autres
            mask_superior = percents >= 1.0
            top_counts = counts[mask_superior].copy()
            others_count = counts[~mask_superior].sum()

            # 3. Ajout de la catégorie "Autres" si elle n'est pas vide
            if others_count > 0:
                if "Autres" in top_counts:
                    top_counts["Autres"] += others_count
                else:
                    top_counts["Autres"] = others_count

            # 4. Tri pour un affichage propre
            if "Autres" in top_counts:
                others_val = top_counts.pop("Autres")
                top_counts = top_counts.sort_values(ascending=False)
                top_counts["Autres"] = others_val
            else:
                top_counts = top_counts.sort_values(ascending=False)

            # 5. Dessin du Pie Chart
            colors = plt.cm.Pastel1.colors # type: ignore
            ax.pie(
                top_counts,
                labels=top_counts.index,
                autopct="%1.1f%%",
                startangle=140,
                colors=colors,
                textprops={"fontsize": 8},
            )

            ax.set_title(
                f"Nationalités (>1%) - {title_suffix}",
                color=COLOR_SIDEBAR,
                fontweight="bold",
            )

        # --- 3. POSTE & PIED (Transformés en Pie Charts) ---
        elif "Poste" in metric or "Pied" in metric:
            col = "position" if "Poste" in metric else "foot"
            counts = df[col].value_counts()
            colors = plt.cm.Pastel2.colors # type: ignore
            ax.pie(
                counts,
                labels=counts.index,
                autopct="%1.1f%%",
                startangle=90,
                colors=colors,
                pctdistance=0.85,
                textprops={"fontsize": 8},
            )

            ax.set_title(
                f"Répartition par {col.capitalize()} - {title_suffix}",
                color=COLOR_SIDEBAR,
                fontweight="bold",
            )

        # --- 4. VALEUR MARCHANDE ---
        elif "Valeur" in metric:
            vals = df["market_value_in_eur"].dropna() / 1e6
            ax.hist(vals, bins=30, color="#2ecc71", edgecolor="white")
            ax.set_title(
                f"Distribution des Valeurs (M€) - {title_suffix}",
                color=COLOR_SIDEBAR,
                fontweight="bold",
            )
            ax.set_xlabel("Valeur en Millions d'Euros")
            ax.set_ylabel("Nombre de joueurs")
            ax.yaxis.grid(True, linestyle="--", alpha=0.6)

    def plot_club_stats(self, ax: Axes) -> None:
        """Gère l'affichage des graphiques spécifiques aux clubs."""
        if self.dm.df_clubs is None:
            return

        c_name = self.current_inputs["club"].currentText()
        metric = self.current_inputs["metric"].currentText()
        season_selected = self.current_inputs["season"].currentText()

        club_row = self.dm.df_clubs[self.dm.df_clubs["name"] == c_name]
        if club_row.empty:
            return
        cid = int(club_row.iloc[0]["club_id"])

        # --- OPTION 1 : ÉVOLUTION DU CLASSEMENT ---
        if "Classement" in metric:
            df = self.dm.get_club_rank_history(cid)
            if df.empty:
                ax.text(0.5, 0.5, "Données de classement indisponibles", ha="center")
                return
            df["Saison_Label"] = df["Saison"].apply(
                lambda x: f"{x[2:4]}/{str(int(x) + 1)[2:4]}"
            )
            max_clubs = 20
            df["Hauteur"] = (max_clubs + 1) - df["Classement"]
            bars = ax.bar(df["Saison_Label"], df["Hauteur"], color=COLOR_MAIN)
            ax.bar_label(
                bars, labels=df["Classement"].tolist(), padding=3, fontweight="bold"
            )
            ax.set_title(
                f"Évolution du classement :\n{c_name}",
                color=COLOR_SIDEBAR,
                fontweight="bold",
            )
            ax.set_yticks([])
            ax.tick_params(axis="x", rotation=45)

        # --- OPTION 2 : ÉVOLUTION DES BUTS ---
        elif "Buts" in metric:
            df_g = self.dm.df_games
            if df_g is not None:
                games = df_g[
                    (df_g["home_club_id"] == cid) | (df_g["away_club_id"] == cid)
                ]
                stats = []
                for s in sorted(games["season"].unique()):
                    s_games = games[games["season"] == s]
                    total_goals = sum(
                        [
                            g["home_club_goals"]
                            if g["home_club_id"] == cid
                            else g["away_club_goals"]
                            for _, g in s_games.iterrows()
                        ]
                    )
                    stats.append(
                        {
                            "Saison": f"{str(s)[2:4]}/{str(int(s) + 1)[2:4]}",
                            "Buts": total_goals,
                        }
                    )
                df_stats = pd.DataFrame(stats)
                if not df_stats.empty:
                    bars = ax.bar(df_stats["Saison"], df_stats["Buts"], color=COLOR_MAIN)
                    ax.bar_label(bars, padding=3, fontweight="bold")
                    ax.set_title(
                        f"Buts marqués par saison :\n{c_name}",
                        color=COLOR_SIDEBAR,
                        fontweight="bold",
                    )
                    ax.tick_params(axis="x", rotation=45)

        # --- OPTION 3 : RÉPARTITION EFFECTIF (Âge, Poste, Nat) ---
        else:
            self._plot_club_squad_distribution(
                ax, cid, c_name, int(season_selected), metric
            )

    def _plot_club_squad_distribution(
        self, ax: Axes, cid: int, c_name: str, season: int, metric: str
    ) -> None:
        """Sous-fonction pour dessiner la répartition de l'effectif d'un club."""
        if self.dm.df_appearances is None or self.dm.df_games is None or self.dm.df_players is None:
            return

        apps = self.dm.df_appearances.merge(
            self.dm.df_games[["game_id", "season"]], on="game_id"
        )
        pids = apps[
            (apps["player_club_id"] == cid) & (apps["season"] == season)
        ]["player_id"].unique()

        if len(pids) == 0:
            ax.text(
                0.5, 0.5, f"Pas d'effectif trouvé pour {season}", ha="center"
            )
            return

        squad = self.dm.df_players[
            self.dm.df_players["player_id"].isin(pids)
        ].copy()

        if "Âges" in metric:
            current_year = date.today().year
            diff_year = current_year - season
            squad["age_at_season"] = squad["age"] - diff_year
            ages = squad["age_at_season"].dropna().astype(int)
            if len(ages) > 0:
                min_a, max_a = int(ages.min()), int(ages.max())
                bins = range(min_a, max_a + 2)
                n, bins_edges, patches = ax.hist(
                    ages, bins=bins, color=COLOR_MAIN, edgecolor="white"
                )
                for i in range(len(n)):
                    if n[i] > 0:
                        ax.text(
                            bins_edges[i] + 0.5,
                            n[i] + 0.1,
                            int(n[i]),
                            ha="center",
                            fontsize=8,
                            fontweight="bold",
                        )
            ax.set_title(
                f"Pyramide des Âges ({season})", color=COLOR_SIDEBAR, fontweight="bold"
            )
            ax.set_xlabel("Âge")
            # ax.set_xticks(range(min_a, max_a + 1)) # Peut causer erreur si range vide

        elif "Nationalités" in metric:
            counts = squad["country_of_citizenship"].value_counts().head(8)
            counts.plot(kind="bar", ax=ax, color=COLOR_MAIN, width=0.6)
            if len(ax.containers) > 0:
                ax.bar_label(ax.containers[0], padding=3)
            ax.set_title(
                f"Nationalités ({season})", color=COLOR_SIDEBAR, fontweight="bold"
            )
            plt.setp(ax.get_xticklabels(), rotation=45, ha="right")

        elif "Postes" in metric:
            counts = squad["position"].value_counts()
            if not counts.empty:
                counts.plot(
                    kind="pie", ax=ax, autopct="%1.0f%%", colors=plt.cm.Pastel1.colors # type: ignore
                )
            ax.set_ylabel("")
            ax.set_title(
                f"Répartition Postes ({season})",
                color=COLOR_SIDEBAR,
                fontweight="bold",
            )

    def plot_player_stats(self, ax: Axes) -> None:
        """Génère les graphiques de statistiques individuelles des joueurs."""
        if self.dm.df_players is None or self.dm.df_appearances is None or self.dm.df_games is None:
            return

        p_name = self.current_inputs["player"].text().strip()
        metric = self.current_inputs["metric"].currentText()

        # Recherche joueur
        p_row = self.dm.df_players[
            self.dm.df_players["name"].str.contains(p_name, case=False, na=False)
        ]
        if p_row.empty:
            ax.text(0.5, 0.5, "Joueur introuvable", ha="center")
            return
        pid = p_row.iloc[0]["player_id"]
        real_name = p_row.iloc[0]["name"]

        # Données
        apps = self.dm.df_appearances[self.dm.df_appearances["player_id"] == pid]
        apps = apps.merge(self.dm.df_games[["game_id", "season"]], on="game_id")

        # Agrégation
        agg = (
            apps.groupby("season")
            .agg(
                {
                    "goals": "sum",
                    "assists": "sum",
                    "minutes_played": "sum",
                    "yellow_cards": "sum",
                    "red_cards": "sum",
                }
            )
            .sort_index()
        )

        if agg.empty:
            ax.text(0.5, 0.5, "Pas de stats", ha="center")
            return

        seasons = [str(s)[2:] for s in agg.index]  # 2022 -> 22
        x = np.arange(len(seasons))

        if "Buts & Passes" in metric:
            width = 0.35
            if "90" in metric:
                agg["g90"] = (agg["goals"] / agg["minutes_played"] * 90).fillna(0)
                agg["a90"] = (agg["assists"] / agg["minutes_played"] * 90).fillna(0)

                rects1 = ax.bar(
                    x - width / 2, agg["g90"], width, label="Buts/90", color=COLOR_MAIN
                )
                rects2 = ax.bar(
                    x + width / 2,
                    agg["a90"],
                    width,
                    label="Passes/90",
                    color=COLOR_SIDEBAR,
                )
                ax.set_title(
                    f"Efficacité par 90 min : \n{real_name}",
                    color=COLOR_SIDEBAR,
                    fontweight="bold",
                )
                ax.bar_label(rects1, padding=3, fmt="%.2f", fontweight="bold")
                ax.bar_label(rects2, padding=3, fmt="%.2f", fontweight="bold")
            else:
                rects1 = ax.bar(
                    x - width / 2, agg["goals"], width, label="Buts", color=COLOR_MAIN
                )
                rects2 = ax.bar(
                    x + width / 2,
                    agg["assists"],
                    width,
                    label="Passes",
                    color=COLOR_SIDEBAR,
                )
                ax.set_title(
                    f"Buts & Passes décisives : \n{real_name}",
                    color=COLOR_SIDEBAR,
                    fontweight="bold",
                )
                ax.bar_label(rects1, padding=3, fontweight="bold")
                ax.bar_label(rects2, padding=3, fontweight="bold")

            ax.set_xticks(x)
            ax.set_xticklabels(seasons)
            ax.tick_params(axis="x", rotation=45)
            ax.legend()

        elif "Cartons" in metric:
            p1 = ax.bar(x, agg["yellow_cards"], label="Jaunes", color="#f1c40f")
            p2 = ax.bar(
                x,
                agg["red_cards"],
                bottom=agg["yellow_cards"],
                label="Rouges",
                color="#e74c3c",
            )
            ax.set_title(
                f"Discipline : \n{real_name}", color=COLOR_SIDEBAR, fontweight="bold"
            )
            ax.set_xticks(x)
            ax.set_xticklabels(seasons)
            ax.tick_params(axis="x", rotation=45)
            ax.legend()
            ax.bar_label(p1, label_type="center", fontweight="bold")
            ax.bar_label(p2, label_type="center", fontweight="bold")

        elif "Minutes" in metric:
            bars = ax.bar(seasons, agg["minutes_played"], color=COLOR_MAIN)
            ax.set_title(
                f"Temps de jeu : \n{real_name}", color=COLOR_SIDEBAR, fontweight="bold"
            )
            ax.bar_label(bars, padding=3, fontweight="bold", fontsize=9)
            ax.tick_params(axis="x", rotation=45)
            ax.yaxis.grid(True, linestyle="--", alpha=0.3)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)