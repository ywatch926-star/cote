
## Diagnostic de l’affichage

Avant redémarrage, le navigateur recevait une page HTML à la place des MP4 ajoutés après le démarrage de Vite, ce qui provoquait `DEMUXER_ERROR_COULD_NOT_OPEN`. Le serveur a été redémarré proprement sur le port 5173.

Après redémarrage, les tests HTTP locaux renvoient bien `video/mp4` pour les fichiers normal et slow. Dans le navigateur, la vidéo active `seq_0028_slow.mp4` possède une durée de 0,117 s, une résolution 1920×1080, `readyState: 1` et aucune erreur de décodage. Le manifeste contient toujours 86 séquences et 10,0 secondes.

Le rendu visuel reste à contrôler car la séquence active au moment de la capture peut être une image très sombre. La cause HTML/fichier introuvable est corrigée par le redémarrage du serveur.
