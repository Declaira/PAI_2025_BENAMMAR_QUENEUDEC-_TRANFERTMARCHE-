import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from tfmc.main_window import MainWindow

def main() -> None:
    """
    Point d'entrée principal de l'application.
    """
    # Initialisation de l'application Qt
    app = QApplication(sys.argv)

    # Configuration de la police globale (Segoe UI est privilégiée sur Windows)
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Création et affichage de la fenêtre principale
    # Assurez-vous que MainWindow possède un constructeur __init__ compatible
    window = MainWindow()
    window.show()

    # Exécution de la boucle d'événements
    # sys.exit attend un code de retour entier (int)
    sys.exit(int(app.exec_()))

if __name__ == "__main__":
    main()