import sys
from typing import List, Optional, Dict, Any, Tuple, cast

import pandas as pd
from PyQt5.QtWidgets import (
    QWidget,
    QMainWindow,
    QMessageBox,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QCompleter,
    QSplitter,
    QStackedWidget,
    QDialog,
)
# On importe Qt pour les types génériques, mais on utilisera les Enums spécifiques
from PyQt5.QtCore import Qt 
from PyQt5.QtGui import QIcon

# Assure-toi que ces imports sont valides dans ton projet
from tfmc.data_manager import DataManager, FilterDialog
from tfmc.graph_dashboard import GraphDashboard
from tfmc.config import STYLE_SHEET, BASE_DIR, AsyncImageLabel
from tfmc.page import (
    HomePage,
    LeaguePage,
    CupPage,
    ClubPage,
    PlayerPage,
    SuggestionPage,
)


class MainWindow(QMainWindow):
    """
    Fenêtre principale de l'application TransfertMarché.
    Gère la navigation, les pages (Stacks) et le panneau de graphiques (Splitter).
    """

    def __init__(self) -> None:
        super().__init__()
        self.dm = DataManager()

        # URLs des logos pour l'en-tête dynamique
        self.league_logos: Dict[str, str] = {
            "Ligue 1": "https://tmssl.akamaized.net//images/logo/header/fr1.png?lm=1732280518",
            "Premier League": "https://tmssl.akamaized.net//images/logo/header/gb1.png?lm=1521104656",
            "La Liga": "https://tmssl.akamaized.net//images/logo/header/es1.png?lm=1725974302",
            "Serie A": "https://tmssl.akamaized.net//images/logo/header/it1.png?lm=1656073460",
            "Bundesliga": "https://tmssl.akamaized.net//images/logo/header/l1.png?lm=1525905518",
            "Liga Portugal": "https://tmssl.akamaized.net//images/logo/header/po1.png",
            "Eredivisie": "https://tmssl.akamaized.net//images/logo/header/nl1.png",
            "Jupiler Pro League": "https://tmssl.akamaized.net//images/logo/header/be1.png",
        }

        self.icon_cache: Dict[str, QIcon] = {}

        # Vérification stricte des DataFrames pour éviter les erreurs de type plus tard
        if self.dm.df_clubs is None or self.dm.df_players is None:
            QMessageBox.critical(
                self, "Erreur", "Impossible de charger les fichiers CSV (df_clubs ou df_players manquant)."
            )
            sys.exit(1)

        # Piles pour la navigation (Précédent / Suivant)
        self.history_stack: List[Tuple[Any, str]] = []
        self.forward_stack: List[Tuple[Any, str]] = []
        self.is_navigating: bool = False

        self.init_ui()

    def init_ui(self) -> None:
        """Initialise l'interface utilisateur (Layouts, Widgets, Signaux)."""
        self.resize(1280, 850)
        self.setWindowTitle("TransfertMarché")
        self.setWindowIcon(QIcon(BASE_DIR + "/logo.png"))
        self.setStyleSheet(STYLE_SHEET)

        central = QWidget()
        self.setCentralWidget(central)
        # Typage explicite pour aider Pyright
        main_layout: QHBoxLayout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. SIDEBAR (Barre latérale)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        side_layout: QVBoxLayout = QVBoxLayout(self.sidebar)

        # Navigation (Back / Forward)
        nav_h: QHBoxLayout = QHBoxLayout()
        self.btn_back = QPushButton("◀")
        self.btn_back.setObjectName("nav_btn")
        self.btn_back.clicked.connect(self.go_back)
        self.btn_fwd = QPushButton("▶")
        self.btn_fwd.setObjectName("nav_btn")
        self.btn_fwd.clicked.connect(self.go_forward)
        nav_h.addWidget(self.btn_back)
        nav_h.addWidget(self.btn_fwd)
        side_layout.addLayout(nav_h)

        # Image contextuelle
        self.img_label = AsyncImageLabel()
        self.img_label.setFixedSize(180, 180)
        self.img_label.setScaledContents(False)
        # Correction Enum: Qt.AlignCenter -> Qt.AlignmentFlag.AlignCenter
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(self.img_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Informations contextuelles
        self.lbl_side_info = QLabel()
        self.lbl_side_info.setObjectName("lbl_side_info")
        self.lbl_side_info.setWordWrap(True)
        self.lbl_side_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_layout.addWidget(self.lbl_side_info)

        # Historique visuel
        side_layout.addWidget(QLabel("Historique", objectName="side_title"))
        self.list_history = QListWidget()
        # Correction Enum: Qt.UserRole -> Qt.ItemDataRole.UserRole
        self.list_history.itemClicked.connect(
            lambda item: self.navigate_to(
                item.data(Qt.ItemDataRole.UserRole), 
                item.data(Qt.ItemDataRole.UserRole + 1), 
                from_history=True
            )
        )
        side_layout.addWidget(self.list_history)

        self.btn_clear_hist = QPushButton("EFFACER L'HISTORIQUE")
        self.btn_clear_hist.setObjectName("clear_btn")
        self.btn_clear_hist.clicked.connect(self.list_history.clear)
        side_layout.addWidget(self.btn_clear_hist)

        # 2. ZONE PRINCIPALE (Droite)
        right_zone = QWidget()
        right_layout: QVBoxLayout = QVBoxLayout(right_zone)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # --- Top Bar ---
        top_bar = QFrame()
        top_bar.setObjectName("top_bar")
        top_bar.setFixedHeight(60)

        top_h: QHBoxLayout = QHBoxLayout(top_bar)
        top_h.setContentsMargins(15, 0, 15, 0)
        top_h.setSpacing(10)

        # Barre de recherche
        self.search_bar = QLineEdit()
        self.search_bar.setObjectName("search_bar")
        self.search_bar.setPlaceholderText("Rechercher club, joueur, ligue...")
        self.search_bar.setFixedWidth(400)

        # Construction sécurisée de la liste de complétion
        # On utilise 'or []' pour garantir qu'on itère sur des listes même si un élément est None
        leagues_list = list(self.dm.leagues.values())
        clubs_list = list(self.dm.df_clubs["name"].dropna().unique()) if self.dm.df_clubs is not None else []
        players_list = list(self.dm.df_players["name"].dropna().unique()) if self.dm.df_players is not None else []
        
        all_names = leagues_list + clubs_list + players_list

        self.completer = QCompleter(all_names, self.search_bar)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.completer.setMaxVisibleItems(15)
        # Note: activated[str] est le signal surchargé pour renvoyer le texte
        self.completer.activated[str].connect(self.on_suggestion_selected) # type: ignore
        self.search_bar.returnPressed.connect(self.on_suggestion_selected)
        self.search_bar.setCompleter(self.completer)

        self.btn_search_icon = QPushButton("🔍")
        self.btn_search_icon.setObjectName("search_btn")
        self.btn_search_icon.setFixedSize(35, 35)
        self.btn_search_icon.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_search_icon.clicked.connect(self.on_search_valid)

        self.btn_filter = QPushButton("Filtres ⚙")
        self.btn_filter.setObjectName("action_btn")
        self.btn_filter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_filter.clicked.connect(self.open_filter_dialog)

        # --- BOUTON GRAPH ---
        self.btn_graph = QPushButton("Stats 📊")
        self.btn_graph.setObjectName("action_btn")
        self.btn_graph.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_graph.setCheckable(True)
        self.btn_graph.clicked.connect(self.toggle_graph_panel)

        top_h.addWidget(self.search_bar)
        top_h.addWidget(self.btn_search_icon)
        top_h.addWidget(self.btn_filter)
        top_h.addWidget(self.btn_graph)
        top_h.addStretch()

        right_layout.addWidget(top_bar)

        # --- STRUCTURE SPLITTER (Contenu | Graphiques) ---
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.saved_splitter_sizes: List[int] = []

        # 1. Le contenu principal (Pages empilées)
        self.stack = QStackedWidget()
        self.page_home = HomePage(self)
        self.page_league = LeaguePage(self)
        self.page_club = ClubPage(self)
        self.page_player = PlayerPage(self)
        self.page_suggestions = SuggestionPage(self)
        self.page_cup = CupPage(self)

        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_league)
        self.stack.addWidget(self.page_club)
        self.stack.addWidget(self.page_player)
        self.stack.addWidget(self.page_suggestions)
        self.stack.addWidget(self.page_cup)

        self.splitter.addWidget(self.stack)

        # 2. Le panneau Graphique (Initialement caché)
        self.graph_panel = GraphDashboard(self)
        self.graph_panel.hide()
        self.splitter.addWidget(self.graph_panel)

        # Configuration du splitter
        self.splitter.setCollapsible(0, False)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)

        right_layout.addWidget(self.splitter)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(right_zone)

        self.navigate_to("home", "home")

    def toggle_graph_panel(self) -> None:
        """Affiche ou masque le panneau des graphiques statistiques."""
        # 1. Identifier les graphiques existants
        dashboards = [
            self.splitter.widget(i)
            for i in range(self.splitter.count())
            if isinstance(self.splitter.widget(i), GraphDashboard)
        ]

        total_w = self.splitter.width()

        if self.btn_graph.isChecked():
            # --- MODE AFFICHAGE ---
            if not dashboards:
                new_dash = GraphDashboard(self)
                self.splitter.addWidget(new_dash)
                dashboards = [new_dash]

            nb_dash = len(dashboards)

            if nb_dash == 1:
                # Partage 50/50
                self.splitter.widget(0).show()
                self.splitter.setSizes([total_w // 2, total_w // 2])
            else:
                # Mode comparatif (on masque le contenu principal si nécessaire ou on divise)
                self.splitter.widget(0).hide()
                self.splitter.setSizes([0, total_w // 2, total_w // 2])

            for db in dashboards:
                db.show()
                db.update_buttons_state()

            self.update_graph_context_live()
        else:
            # --- MODE NAVIGATION (Masquer graphs) ---
            for db in dashboards:
                db.hide()
            self.splitter.widget(0).show()
            self.splitter.setSizes([total_w] + [0] * len(dashboards))

    def apply_context_to_graph(self, graph_widget: GraphDashboard) -> None:
        """
        Applique le contexte de la page actuelle (Joueur, Club, Ligue)
        au widget GraphDashboard spécifié.
        """
        if self.dm.df_players is None or self.dm.df_clubs is None:
            return

        current_page = self.stack.currentWidget()
        try:
            # CAS JOUEUR
            if isinstance(current_page, PlayerPage) and hasattr(current_page, "pid"):
                p_id = current_page.pid
                p_rows = self.dm.df_players[self.dm.df_players["player_id"] == p_id]
                if not p_rows.empty:
                    p_name = p_rows["name"].values[0]
                    graph_widget.set_context("Joueur", str(p_name))

            # CAS CLUB
            elif isinstance(current_page, ClubPage) and hasattr(current_page, "cid"):
                c_id = current_page.cid
                c_rows = self.dm.df_clubs[self.dm.df_clubs["club_id"] == c_id]
                if not c_rows.empty:
                    row = c_rows.iloc[0]
                    graph_widget.set_context(
                        "Club", str(row["name"]), str(row["domestic_competition_id"])
                    )

            # CAS CHAMPIONNAT
            elif isinstance(current_page, LeaguePage) and hasattr(current_page, "lid"):
                l_id = current_page.lid
                l_name = self.dm.leagues.get(l_id, "")
                graph_widget.set_context("Global", str(l_name))

            else:
                graph_widget.set_context("Global")

        except Exception as e:
            print(f"Erreur application contexte graph: {e}")

    def update_graph_context_live(self) -> None:
        """Met à jour TOUS les graphiques visibles avec le contexte actuel."""
        if not self.btn_graph.isChecked():
            return

        for i in range(self.splitter.count()):
            w = self.splitter.widget(i)
            if isinstance(w, GraphDashboard) and not w.isHidden():
                self.apply_context_to_graph(w)
                w.plot()

    def on_suggestion_selected(self, text: Optional[str] = None) -> None:
        """Gère la sélection dans la barre de recherche (Ligue, Club ou Joueur)."""
        search_text = text if text else self.search_bar.text().strip()
        if not search_text:
            return
        
        # Vérification de sécurité pour les DataFrames
        if self.dm.df_clubs is None or self.dm.df_players is None:
            return

        # 1. Est-ce une ligue ?
        lid = next(
            (k for k, v in self.dm.leagues.items() if v.lower() == search_text.lower()),
            None,
        )
        if lid:
            self.navigate_to(lid, "championnat")
            self.search_bar.clear()
            return

        # 2. Est-ce un club ?
        club_match = self.dm.df_clubs[
            self.dm.df_clubs["name"].str.lower() == search_text.lower()
        ]
        if not club_match.empty:
            club_id = int(club_match.iloc[0]["club_id"])
            self.navigate_to(club_id, "club")
            self.search_bar.clear()
            return

        # 3. Est-ce un joueur ?
        player_match = self.dm.df_players[
            self.dm.df_players["name"].str.lower() == search_text.lower()
        ]
        if not player_match.empty:
            player_id = int(player_match.iloc[0]["player_id"])
            self.navigate_to(player_id, "joueur")
            self.search_bar.clear()
            return

        # Sinon, recherche générique
        self.on_search_valid()

    def on_search_valid(self) -> None:
        """Déclenche une recherche générique (page de suggestions)."""
        text = self.search_bar.text().strip()
        if not text or text == "":
            self.navigate_to("home", "home")
        else:
            self.navigate_to(text, "suggestion")

    def open_filter_dialog(self) -> None:
        """Ouvre la boîte de dialogue de filtres avancés."""
        dialog = FilterDialog(self, self.dm)
        if dialog.exec_() == QDialog.Accepted:
            params = dialog.get_params()
            self.apply_filter(params)

    def apply_filter(self, params: Dict[str, Any]) -> None:
        """Applique les filtres sélectionnés et navigue vers les résultats."""
        self.navigate_to(params, "suggestion")

    def navigate_to(
        self,
        data_id: Any,
        type_hint: Optional[str] = None,
        from_history: bool = False,
    ) -> None:
        """
        Système central de navigation. Change la page affichée et met à jour l'historique.

        Args:
            data_id (Any): L'identifiant de la donnée (ID int, str, ou dict de filtres).
            type_hint (str, optional): Le type de page ('club', 'joueur', 'championnat'...).
            from_history (bool): Indique si la navigation provient d'un clic sur l'historique.
        """
        self.search_bar.clearFocus()
        
        # Sécurité pour DataFrames
        if self.dm.df_clubs is None or self.dm.df_players is None:
             # Si les données ne sont pas chargées, on ne peut pas naviguer correctement
             # sauf peut-être vers Home
             if type_hint != "home":
                 return

        if not type_hint:
            if data_id == "home":
                type_hint = "home"
            else:
                return

        # Mise à jour de l'historique si navigation nouvelle
        if not from_history and not self.is_navigating:
            if not self.history_stack or self.history_stack[-1][0] != data_id:
                self.history_stack.append((data_id, type_hint))
                self.forward_stack.clear()

                display_text = str(data_id)
                # Utilisation de cast pour aider Pyright si les DFs sont Optionals
                df_clubs = cast(pd.DataFrame, self.dm.df_clubs)
                df_players = cast(pd.DataFrame, self.dm.df_players)

                if type_hint == "club":
                    try:
                        display_text = df_clubs[
                            df_clubs["club_id"] == data_id
                        ]["name"].values[0]
                    except Exception:
                        pass
                elif type_hint == "joueur":
                    try:
                        display_text = df_players[
                            df_players["player_id"] == data_id
                        ]["name"].values[0]
                    except Exception:
                        pass
                elif type_hint == "championnat":
                    display_text = self.dm.leagues.get(data_id, str(data_id))
                elif type_hint == "home":
                    display_text = "Accueil"
                elif type_hint == "suggestion":
                    if isinstance(data_id, dict):
                        display_text = data_id.get("nom", "Filtre")

                item = QListWidgetItem(str(display_text))
                item.setData(Qt.ItemDataRole.UserRole, data_id)
                item.setData(Qt.ItemDataRole.UserRole + 1, type_hint)
                self.list_history.addItem(item)
                self.list_history.scrollToBottom()

        self.is_navigating = True

        try:
            if type_hint == "home":
                self.stack.setCurrentIndex(0)
                self.img_label.set_image_from_path(BASE_DIR + "/logo.png")
                if self.img_label.pixmap() is None:
                    self.img_label.setText("🏠")
                self.lbl_side_info.setText(
                    "<b>ACCUEIL</b><br>Bienvenue sur Transfertmarché"
                )

            elif type_hint == "championnat":
                cups_ids = ["CL", "EL", "CDR", "FAC", "DFB", "CIT", "NLP", "GRP"]
                league_name = self.dm.leagues.get(data_id, str(data_id))
                
                logo_url = (
                    f"https://tmssl.akamaized.net//images/logo/header/{str(data_id).lower()}.png?lm=1"
                )
                if league_name in self.league_logos:
                    logo_url = self.league_logos[league_name]
                self.img_label.set_image_from_url(logo_url)

                if data_id in cups_ids:
                    self.stack.setCurrentIndex(5)
                    self.page_cup.load(data_id)
                    self.lbl_side_info.setText(f"<b>COUPE</b><br><br>{league_name}")
                else:
                    self.stack.setCurrentIndex(1)
                    self.page_league.load(data_id)
                    self.lbl_side_info.setText(
                        f"<b>CHAMPIONNAT</b><br><br>{league_name}"
                    )

            elif type_hint == "club":
                df_clubs = cast(pd.DataFrame, self.dm.df_clubs)
                self.stack.setCurrentIndex(2)
                self.page_club.load(data_id)
                try:
                    row = df_clubs[
                        df_clubs["club_id"] == data_id
                    ].iloc[0]
                    logo_url = f"https://tmssl.akamaized.net//images/wappen/head/{int(data_id)}.png"
                    self.img_label.set_image_from_url(logo_url)
                    self.lbl_side_info.setText(
                        f"<b>{row['name']}</b><br><br>"
                        f"Stade: {row.get('stadium_name', '-')}<br>"
                        f"Effectif: {row.get('squad_size', '-')} joueurs"
                    )
                except Exception:
                    self.img_label.setText("🛡️")
                    self.lbl_side_info.setText(f"Club ID: {data_id}")

            elif type_hint == "joueur":
                df_players = cast(pd.DataFrame, self.dm.df_players)
                self.stack.setCurrentIndex(3)
                self.page_player.load(data_id)
                try:
                    row = df_players[
                        df_players["player_id"] == data_id
                    ].iloc[0]
                    self.img_label.set_image_from_url(str(row.get("image_url")))
                    age_display = (
                        f"{int(row['age'])} ans" if pd.notna(row.get("age")) else "-"
                    )
                    taille = (
                        f"{row['height_in_cm']} cm"
                        if pd.notna(row.get("height_in_cm"))
                        else "-"
                    )
                    nat = row.get("country_of_citizenship", "-")
                    
                    valeur_str = "-"
                    if pd.notna(row.get("market_value_in_eur")):
                        valeur_float = float(row['market_value_in_eur'])
                        valeur_str = f"{valeur_float / 1e6:.1f} M€"

                    self.lbl_side_info.setText(
                        f"<b>{row['name']}</b><br><br>"
                        f"Âge : {age_display}<br>"
                        f"Taille : {taille}<br>"
                        f"Nationalité : {nat}<br>"
                        f"Valeur : {valeur_str}"
                    )
                except Exception:
                    self.img_label.setText("👤")
                    self.lbl_side_info.setText(f"Joueur ID: {data_id}")

            elif type_hint == "suggestion":
                if isinstance(data_id, str):
                    res = self.dm.filter_players(nom=data_id, limit=50)
                    self.stack.setCurrentIndex(4)
                    self.page_suggestions.load_players(res)
                    self.img_label.setText("🔍")
                    self.lbl_side_info.setText(f"Recherche de joueurs pour : {data_id}")
                else:
                    # Cas d'un dictionnaire de paramètres (Filtres)
                    params = data_id.copy()
                    type_filter = params.pop("type", "joueurs")
                    nom_saisi = params.get("nom", "")
                    if nom_saisi:
                        self.search_bar.setText(nom_saisi)

                    if type_filter == "joueurs":
                        df_res = self.dm.filter_players(**params)
                        self.stack.setCurrentIndex(4)
                        self.page_suggestions.load_players(df_res)
                        self.img_label.setText("⚙")
                        self.lbl_side_info.setText(
                            f"FILTRE JOUEURS\n\n{len(df_res)} résultats"
                        )
                    else:
                        df_res = self.dm.filter_teams(**params)
                        self.stack.setCurrentIndex(4)
                        self.page_suggestions.load_clubs(df_res)
                        self.img_label.setText("⚙")
                        self.lbl_side_info.setText(
                            f"FILTRE CLUBS\n\n{len(df_res)} résultats"
                        )
                    # On réinjecte le type si nécessaire pour l'historique (déjà fait au début)
        finally:
            self.update_graph_context_live()
            self.is_navigating = False

    def go_back(self) -> None:
        """Navigue vers la page précédente dans l'historique."""
        if len(self.history_stack) > 1:
            current = self.history_stack.pop()
            self.forward_stack.append(current)
            # prev_data, prev_type = self.history_stack[-1]
            # Utilisation de l'index sécurisé
            if self.history_stack:
                prev_data = self.history_stack[-1][0]
                prev_type = self.history_stack[-1][1]
                self.navigate_to(prev_data, prev_type, from_history=True)

    def go_forward(self) -> None:
        """Navigue vers la page suivante dans l'historique."""
        if self.forward_stack:
            next_state = self.forward_stack.pop()
            self.history_stack.append(next_state)
            self.navigate_to(next_state[0], next_state[1], from_history=True)