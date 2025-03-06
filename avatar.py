import sys
import time
import os
import random
from threading import Thread
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTimer, Qt, QPoint


class FloatingImage(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Variables de mouvement et état
        self.gravity = 1
        self.jump_strength = -15
        self.dy = 0
        self.dx = 0
        self.on_ground = False
        self.flying = False
        self.friction = 0.95
        self.moving_left = False
        self.moving_right = False
        self.moving_up = False
        self.moving_down = False
        self.jump_requested = False
        self.dragging = False
        self.hidden_in_folder = False  # Ajouté pour gérer l'entrée dans les dossiers
        self.offset = QPoint()
        self.last_mouse_pos = QPoint()
        self.last_mouse_time = 0

        # Variables pour aller vers un dossier
        self.target_folder = None
        self.target_position = None
        self.moving_to_folder = False

        # Chargement de l'image
        self.label = QLabel(self)
        pixmap = QPixmap("avatar.png")
        if pixmap.isNull():
            print("Erreur : Impossible de charger avatar.png")
        self.label.setPixmap(pixmap)
        self.label.adjustSize()
        self.resize(pixmap.width(), pixmap.height())
        self.label.show()
        self.show()

        # Timer de mise à jour
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_movement)
        self.timer.start(30)

        # Mode IA (désactivé au début)
        self.ai_mode = False
        self.ai_timer = QTimer()
        self.ai_timer.timeout.connect(self.update_ai_behavior)  # Appelle une fonction pour changer le comportement

        self.ai_wants_to_fly = False  # L'IA ne veut pas voler au départ
        self.last_flight_toggle_time = time.time()  # Dernière activation/désactivation du vol

        self.sprint_active = False  # Indique si l'avatar est en sprint
        self.sprint_timer = 0  # Temps depuis lequel la touche est maintenue
        self.base_speed = 3  # Vitesse normale
        self.sprint_speed = 5  # Vitesse en sprint
        self.current_speed = self.base_speed  # Vitesse actuelle

        self.bounce_factor = 0.5  # Facteur de rebond (50% de la vitesse est conservée)
        self.bounce_threshold = 10  # Vitesse minimale pour rebondir

    def update_ai_behavior(self):
        import random
        """L'IA choisit une action et l'exécute."""
        if not self.ai_mode:
            return  # L'IA ne bouge pas si elle est désactivée

        actions = []

        # Mode MARCHE (si au sol)
        if self.on_ground:
            actions.extend(["left", "right", "jump", "idle"])  # Il peut marcher, sauter ou rien faire

        # Mode VOL (si activé)
        if self.flying:
            actions.extend(["fly_up", "fly_down", "fly_left", "fly_right", "idle"])

        # Si l'avatar est en l'air mais pas en vol, il ne peut que tomber
        if not self.on_ground and not self.flying:
            actions = ["idle"]  # Rien à faire, il chute tout seul

        action = random.choice(actions)  # Choisit une action au hasard
        print(f"🤖 L'IA a choisi : {action}")

        # Exécute l'action
        if action == "left":
            self.moving_left = True
            self.moving_right = False
        elif action == "right":
            self.moving_right = True
            self.moving_left = False
        elif action == "jump" and self.on_ground:
            self.dy = self.jump_strength  # Applique le saut
            self.on_ground = False
        elif action == "fly_up" and self.flying:
            self.moving_up = True
        elif action == "fly_down" and self.flying:
            self.moving_down = True
        elif action == "fly_left" and self.flying:
            self.moving_left = True
        elif action == "fly_right" and self.flying:
            self.moving_right = True
        elif action == "idle":
            self.moving_left = self.moving_right = self.moving_up = self.moving_down = False  # Arrête tout

    def update_movement(self):
        if self.hidden_in_folder:
            return  # Ne rien faire si caché


        if self.moving_to_folder and self.target_position:
            x, y = self.x(), self.y()
            target_x, target_y = self.target_position
            if abs(x - target_x) > 3:
                x += 3 if x < target_x else -3
            if abs(y - target_y) > 3:
                y += 3 if y < target_y else -3
            self.move(x, y)

            if abs(x - target_x) <= 5 and abs(y - target_y) <= 5:
                self.moving_to_folder = False
                self.flying = False
                print(f"Arrivé au dossier {self.target_folder} !")

        elif not self.moving_to_folder and not self.dragging:
            screen = QApplication.primaryScreen().geometry()
            x, y = self.x(), self.y()

            if self.flying:
                if self.moving_up:
                    y -= 5
                if self.moving_down:
                    y += 5
                if self.moving_left:
                    x -= 5
                if self.moving_right:
                    x += 5
            else:
                self.dy += self.gravity
                y += self.dy
                x += self.dx

                if self.moving_left:
                    x -= 5
                if self.moving_right:
                    x += 5

                self.dx *= self.friction
                self.dy *= self.friction

                if y + self.height() >= screen.height():
                    y = screen.height() - self.height()
                    self.on_ground = True
                    self.dy = 0
                    self.dx = 0
                else:
                    self.on_ground = False

            if x <= 0 or x + self.width() >= screen.width():
                self.dx = 0
            # Vérifier si on touche le plafond (rebond)
            if y <= 0:
                y = 0
                if abs(self.dy) > self.bounce_threshold:  # Si la vitesse est suffisante
                    self.dy = -self.dy * self.bounce_factor
                else:
                    self.dy = 0

            x = max(0, min(screen.width() - self.width(), x))
            y = max(0, min(screen.height() - self.height(), y))

            # L'IA décide d'activer ou désactiver le vol
            current_time = time.time()
            if current_time - self.last_flight_toggle_time > 10:  # Attendre au moins 10 sec avant un changement
                if self.flying:  # Si elle vole déjà
                    if current_time - self.last_flight_toggle_time > 60:  # Vol max de 1 min
                        self.flying = False
                        self.moving_up = self.moving_down = False  # Arrêter les déplacements verticaux
                        self.last_flight_toggle_time = current_time
                        print("✈️ L'IA désactive le vol")
                else:  # Si elle est au sol
                    if random.random() < 0.1:  # 10% de chance d'activer le vol
                        self.flying = True
                        self.last_flight_toggle_time = current_time
                        print("🚀 L'IA active le vol")

            # Vérifier si on doit activer le sprint
            if (self.moving_left or self.moving_right):
                if not self.sprint_active and time.time() - self.sprint_timer >= 1:  # Sprint après 1 sec
                    self.sprint_active = True
                    self.current_speed = self.sprint_speed  # Augmente la vitesse
            elif not self.moving_left and not self.moving_right:
                self.sprint_active = False
                self.current_speed = self.base_speed  # Revenir à la vitesse normale

            # Appliquer la vitesse actuelle
            if self.moving_left:
                x -= self.current_speed
            if self.moving_right:
                x += self.current_speed


            self.move(int(x), int(y))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.moving_left = True
            self.sprint_timer = time.time()  # Enregistre le moment où la touche est pressée

        elif event.key() == Qt.Key_Right:
            self.moving_right = True
            self.sprint_timer = time.time()  # Enregistre le moment où la touche est pressée

        elif event.key() == Qt.Key_Up and self.flying:
            self.moving_up = True
        elif event.key() == Qt.Key_Down and self.flying:
            self.moving_down = True
        elif event.key() == Qt.Key_Space and self.on_ground:
            self.dy = self.jump_strength
            self.on_ground = False
        elif event.key() == Qt.Key_V:
            self.flying = not self.flying
            if self.flying:
                self.dy = 0
        if event.key() == Qt.Key_I:
            self.ai_mode = not self.ai_mode  # Active/Désactive le mode IA
            if self.ai_mode:
                print("✅ Mode IA activé !")
                self.ai_timer.start(2000)  # Change de comportement toutes les 2 secondes
            else:
                print("❌ Mode IA désactivé !")
                self.ai_timer.stop()


    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.moving_left = False
        elif event.key() == Qt.Key_Right:
            self.moving_right = False
        elif event.key() == Qt.Key_Up:
            self.moving_up = False
        elif event.key() == Qt.Key_Down:
            self.moving_down = False
        if event.key() == Qt.Key_Left or event.key() == Qt.Key_Right:
            self.moving_left = False
            self.moving_right = False
            self.sprint_active = False  # Désactive le sprint
            self.current_speed = self.base_speed  # Remet la vitesse normale

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()
            self.last_mouse_pos = event.globalPos()
            self.last_mouse_time = time.time()

    def mouseMoveEvent(self, event):
        if self.dragging:
            screen = QApplication.primaryScreen().geometry()
            new_x = event.globalX() - self.offset.x()
            new_y = event.globalY() - self.offset.y()
            new_x = max(0, min(screen.width() - self.width(), new_x))
            new_y = max(0, min(screen.height() - self.height(), new_y))
            self.move(new_x, new_y)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            time_elapsed = time.time() - self.last_mouse_time
            if time_elapsed < 0.15:
                mouse_delta = event.globalPos() - self.last_mouse_pos
                speed_factor = 0.2
                self.dx = mouse_delta.x() * speed_factor
                self.dy = mouse_delta.y() * speed_factor


app = QApplication(sys.argv)
window = FloatingImage()
window.show()
sys.exit(app.exec_())
