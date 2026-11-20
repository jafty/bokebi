# Déploiement Railway

## Préparer les services

Configurer deux services PostgreSQL privés pour les données de sondage et les demandes d’aide. Le service web utilise les variables suivantes.

- `DATABASE_URL` et `CONTACT_DATABASE_URL` pointent vers les deux bases.
- `SECRET_KEY`, `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS` correspondent au déploiement HTTPS avec `DEBUG=0`.
- `BOKEBI_PUBLIC_URL` contient l’origine HTTPS utilisée dans les liens d’alerte. En production, utiliser `https://www.bokebi.fr` pour conserver le chemin vers la file admin.
- `BREVO_API_KEY`, `BREVO_SENDER_EMAIL` et `CONTACT_NOTIFICATION_RECIPIENTS` configurent les alertes. Le corps du message contient uniquement un lien vers la file admin. L’équipe se charge ensuite de la réponse depuis la boîte `entraide@bokebi.fr`.

## Bascule du parcours historique

1. Sauvegarder séparément les deux bases. Les tables historiques restent en place avec leurs données. Le nouveau parcours utilise ses propres tables et les anciens liens de sondage ne sont plus servis.
2. Démarrer le service web. Son point d’entrée migre chaque base séparément et collecte les fichiers statiques.
3. Configurer un service de maintenance Railway depuis le même dépôt, avec `/railway.maintenance.toml` comme fichier de configuration. Lui donner les mêmes accès de base et paramètres de notification. La tâche `python manage.py maintain_bokebi` s’exécute toutes les cinq minutes et termine ensuite. Activer ce service une fois les migrations web terminées.
4. Créer un compte admin avec `python manage.py createsuperuser`, puis attribuer à l’équipe les permissions de lecture des sondages et de lecture et changement des demandes. Définir la durée effective de conservation des sauvegardes et des e-mails avant publication.

## Vérifier avant l’ouverture

1. Envoyer une demande de bout en bout. Vérifier l’alerte, l’accès à la file, la réponse depuis `entraide@bokebi.fr`, puis les actions de suivi de statut. Vérifier qu’une demande nouvelle âgée de plus de 24 heures est signalée en retard et que les week-ends et jours fériés sont couverts par l’équipe.
2. Tester le sondage et ses résultats à un, deux et trois votes dans des sessions différentes. Vérifier le brouillon WhatsApp sur smartphone, puis supprimer le sondage de test avec sa clé.
3. Vérifier dans les logs Railway une exécution réussie de la tâche et, sur un dossier de test clos depuis 30 jours, l’effacement de la demande. Vérifier que les agrégats de sondage restent disponibles.

## Retour arrière

Si une erreur bloque la bascule avant toute saisie sur le nouveau parcours, remettre l’ancien service avec les deux sauvegardes correspondantes. Après les premières demandes réelles, privilégier une correction sur la nouvelle version en conservant les nouveaux enregistrements. Toute restauration des bases s’effectue séparément.
