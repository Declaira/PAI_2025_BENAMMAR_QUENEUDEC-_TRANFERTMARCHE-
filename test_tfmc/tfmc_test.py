import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

# Import des fonctions et classes à tester
from tfmc.page import format_season_display, parse_season_from_display
from tfmc.data_manager import DataManager

# --- TESTS UNITAIRES : page.py ---

def test_format_season_display():
    """Teste le formatage de l'affichage des saisons."""
    # Cas normal
    assert format_season_display(2023) == "2023-2024"
    assert format_season_display("2023") == "2023-2024"
    
    # Cas court
    assert format_season_display(2023, short=True) == "23-24"
    
    # Cas limite (changement de siècle/millénaire)
    assert format_season_display(1999) == "1999-2000"
    assert format_season_display(1999, short=True) == "99-00"
    
    # Gestion des erreurs (doit retourner l'input en string)
    assert format_season_display("invalid") == "invalid"

def test_parse_season_from_display():
    """Teste l'extraction de l'année depuis la chaîne d'affichage."""
    assert parse_season_from_display("2023-2024") == 2023
    assert parse_season_from_display("23-24") == 23 # Note: la fonction split juste sur '-'
    
    # Cas par défaut défini dans le code (try/except renvoie 2024)
    assert parse_season_from_display("invalid") == 2024
    assert parse_season_from_display("") == 2024

# --- FIXTURES POUR DATA MANAGER ---

@pytest.fixture
def mock_data_manager():
    """
    Crée une instance de DataManager avec des données simulées (mock).
    On empêche le chargement réel des fichiers CSV/Kaggle via patch.
    """
    with patch("DataManager.load_data") as mock_load:
        # On initialise le manager (le load_data réel est sauté)
        dm = DataManager()
        
        # Injection de fausses données (DataFrames) pour les tests
        
        # 1. Mock Players
        dm.df_players = pd.DataFrame({
            'player_id': [1, 2, 3, 4],
            'name': ['Mbappe', 'Messi', 'Ronaldo', 'Unknown'],
            'country_of_citizenship': ['France', 'Argentina', 'Portugal', 'Mars'],
            'position': ['Attaquant', 'Attaquant', 'Attaquant', 'Défenseur'],
            'age': [25, 36, 38, 20],
            'market_value_in_eur': [180000000, 50000000, 15000000, 1000000]
        })
        
        # 2. Mock Clubs
        dm.df_clubs = pd.DataFrame({
            'club_id': [10, 20, 30],
            'name': ['Paris SG', 'Inter Miami', 'Al Nassr'],
            'short_name': ['PSG', 'Miami', 'Al-Nassr'],
            'domestic_competition_id': ['FR1', 'US1', 'SA1']
        })
        
        # 3. Mock Games (Pour le classement)
        # Compétition FR1, Saison 2023
        # Match 1: Paris SG (10) vs Club B (20) -> 2-1 (Paris gagne)
        # Match 2: Club B (20) vs Paris SG (10) -> 1-1 (Nul)
        dm.df_games = pd.DataFrame({
            'game_id': [100, 101],
            'competition_id': ['FR1', 'FR1'],
            'season': [2023, 2023],
            'home_club_id': [10, 20],
            'away_club_id': [20, 10],
            'home_club_goals': [2, 1],
            'away_club_goals': [1, 1]
        })
        
        # 4. Mock Ligues (dictionnaire déjà présent dans __init__, on s'assure qu'il est là)
        # dm.leagues est déjà initialisé
        
        return dm

# --- TESTS UNITAIRES : data_manager.py ---

def test_get_club_name(mock_data_manager):
    """Teste la récupération du nom d'un club."""
    dm = mock_data_manager
    
    # Nom complet
    assert dm.get_club_name(10) == "Paris SG"
    
    # Nom court
    assert dm.get_club_name(10, short=True) == "PSG"
    
    # ID inconnu
    assert dm.get_club_name(999) == "Club 999"

def test_filter_players_basics(mock_data_manager):
    """Teste le filtrage basique des joueurs (Nom, Nationalité, Poste)."""
    dm = mock_data_manager
    
    # Filtre par nom (insensible à la casse)
    res = dm.filter_players(nom="mbap")
    assert len(res) == 1
    assert res.iloc[0]['name'] == "Mbappe"
    
    # Filtre par nationalité
    res = dm.filter_players(nationalite="Argentina")
    assert len(res) == 1
    assert res.iloc[0]['name'] == "Messi"
    
    # Filtre combiné (Nom + Poste) - Cas négatif
    res = dm.filter_players(nom="Mbappe", poste="Défenseur")
    assert len(res) == 0

def test_filter_players_numeric(mock_data_manager):
    """Teste les filtres numériques (Age, Valeur)."""
    dm = mock_data_manager
    
    # Age min/max
    # Ronaldo (38), Messi (36), Mbappe (25), Unknown (20)
    res = dm.filter_players(age_min=30)
    assert len(res) == 2  # Messi et Ronaldo
    assert "Mbappe" not in res['name'].values
    
    # Valeur marchande (en millions dans les arguments de la fonction)
    # Mbappe(180M), Messi(50M), Ronaldo(15M), Unknown(1M)
    
    # >= 100M
    res = dm.filter_players(val_min=100)
    assert len(res) == 1
    assert res.iloc[0]['name'] == "Mbappe"
    
    # <= 20M
    res = dm.filter_players(val_max=20)
    assert len(res) == 2 # Ronaldo et Unknown

def test_filter_teams(mock_data_manager):
    """Teste le filtrage des équipes."""
    dm = mock_data_manager
    
    # Filtre par nom
    res = dm.filter_teams(nom="Paris")
    assert len(res) == 1
    assert res.iloc[0]['name'] == "Paris SG"
    
    # Filtre par ligue
    # Dans le mock, Paris SG est en 'FR1' (Ligue 1)
    res = dm.filter_teams(ligue="Ligue 1")
    assert len(res) == 1
    assert res.iloc[0]['club_id'] == 10
    
    # Filtre par ligue vide ou incorrecte
    res = dm.filter_teams(ligue="Premier League") # Aucune équipe mockée en PL
    assert len(res) == 0

def test_get_club_rank_history(mock_data_manager):
    """
    Teste le calcul du classement historique.
    Scénario Mocké (FR1, 2023) :
    - Match 1 : Paris (Home) 2 - 1 Miami (Away) => Paris +3 pts, Miami +0
    - Match 2 : Miami (Home) 1 - 1 Paris (Away) => Miami +1 pt, Paris +1 pt
    
    Total : Paris 4 pts, Miami 1 pt.
    Classement attendu : Paris 1er, Miami 2ème.
    """
    dm = mock_data_manager
    
    # --- Test pour Paris SG (ID 10) ---
    df_history_psg = dm.get_club_rank_history(10)
    
    assert not df_history_psg.empty
    row = df_history_psg.iloc[0]
    assert row['Saison'] == "2023"
    assert row['Classement'] == 1 # Premier avec 4 pts
    
    # --- Test pour Inter Miami (ID 20) ---
    # Note: Dans le mock df_clubs, j'ai mis Inter Miami en 'US1', 
    # MAIS dans df_games, j'ai simulé qu'ils jouent en 'FR1' pour que le calcul se fasse ensemble.
    # DataManager.get_club_rank_history regarde d'abord la competition_id du club dans df_clubs.
    # IL FAUT DONC QUE LE CLUB SOIT LISTÉ DANS LA MÊME COMPÉTITION DANS df_clubs POUR QUE ÇA MARCHE.
    
    # Correction dynamique du mock pour ce test spécifique :
    dm.df_clubs.loc[dm.df_clubs['club_id'] == 20, 'domestic_competition_id'] = 'FR1'
    
    df_history_miami = dm.get_club_rank_history(20)
    assert not df_history_miami.empty
    row_m = df_history_miami.iloc[0]
    assert row_m['Classement'] == 2 # Deuxième avec 1 pt

    # --- Test pour un club sans matchs ---
    df_history_empty = dm.get_club_rank_history(30) # Al Nassr (SA1) n'a pas de matchs mockés
    assert df_history_empty.empty
