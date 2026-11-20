# Architecture Bokebi

## Règle de dépendance

Le cœur `domain/` contient le modèle métier, les cas d’usage et les ports. Il importe la bibliothèque standard et ses propres modules. Django forme la périphérie. Les formulaires valident les entrées HTTP, les vues orchestrent le parcours et les adaptateurs traduisent entre le modèle métier, les bases de données et les services externes.

## Agrégats et persistance

- **Demande d’aide.** `HelpRequest` porte les situations transmises, la date de réception, l’échéance de première réponse et les règles de changement de statut. L’adaptateur verrouille la demande lors d’une transition. La base contacts garde l’e-mail et un identifiant opaque de sondage si la demande y est rattachée. Une demande initiale peut réserver cet identifiant avant que le sondage existe.
- **Sondage.** `Survey` porte le total et les compteurs par situation. Il applique le seuil de trois réponses. Le port de persistance enregistre le reçu et les incréments dans la même transaction, sous un verrou de sondage. Le reçu distingue une session par un identifiant dérivé propre à ce sondage. Il ne contient aucun choix, aucun e-mail ni identifiant de demande.
- **Création après demande.** Chaque autorisation de session est valable une heure après l’envoi. L’identifiant réservé permet de créer le sondage dans une transaction sur sa propre base, sans écrire simultanément dans les contacts. Un reçu de création empêche qu’un rejeu recrée un sondage supprimé. Le reçu expire après un jour. La clé de suppression est dérivée du secret de session et de la demande, puis seule son empreinte est inscrite dans le sondage.
- **Cycle de vie.** La suppression d’un sondage efface ses compteurs et ses reçus de vote. Une demande close est purgée après 30 jours. Les deux opérations sont indépendantes. Les alertes aux opérateurs partent après écriture, et une échéance persistée permet de relancer les alertes en échec.

## Tests

Les tests de domaine utilisent des ports en mémoire. Les tests Django vérifient formulaires, transactions et permissions. Vérifier la concurrence sous PostgreSQL, dont les verrous de ligne garantissent l’atomicité du vote. Les tests navigateur couvrent la navigation, la mise en page et le partage. La CI impose 100 % de lignes et de branches pour le code Python applicatif et le JavaScript. Les migrations sont exercées séparément sur le schéma précédent et sur une base vierge.
