# Guide des alertes Flotte225

Ce document explique **toutes les alertes** du système : quand elles se déclenchent,
ce que tu reçois, et **quoi faire exactement** pour les résoudre.

---

## Principe à retenir avant tout

Les alertes ne sont **pas stockées** comme des objets qu'on « ferme » ou qu'on « valide ».
Elles sont **recalculées en direct** à partir des données réelles du véhicule
(entretiens + pleins de carburant), à chaque cycle.

> 🔑 **Conséquence : on ne « résout » jamais une alerte à la main.**
> On corrige la **donnée réelle** (date d'assurance, km de vidange…), et l'alerte
> **disparaît toute seule** au cycle suivant. L'email cesse automatiquement.

Il n'existe **aucun bouton « marquer comme résolu »**, et c'est volontaire.

---

## Quand reçois-tu un email ?

| Canal | Fréquence | Contenu |
|-------|-----------|---------|
| **Email instantané** | Vérification toutes les **15 min** | 1 email **par nouvelle alerte** (ou aggravation warning → critical) |
| **Digest email** | Tous les jours à **22h00** | Récapitulatif de **toutes** les alertes encore actives |
| **WhatsApp** | Tous les jours à **08h00** | Alertes critiques de la flotte |

**Anti-spam :** une fois l'email instantané envoyé pour une alerte, il **n'est pas renvoyé**
tant que l'alerte reste identique. Tu n'es re-notifié que si l'alerte **s'aggrave**
(passage de ⚠️ *warning* à 🔴 *critical*).

> Les emails ne partent qu'aux propriétaires ayant les alertes email **activées**
> dans les paramètres et une adresse email renseignée.

---

## Les 5 types d'alertes

### 1. 🛡️ Assurance expirée — `insurance_expiry`

| | |
|---|---|
| **Source** | Champ *Date d'expiration de l'assurance* (fiche entretien du véhicule) |
| **⚠️ Warning** | L'assurance expire dans **30 jours ou moins** |
| **🔴 Critical** | L'assurance est **déjà expirée** |
| **Message** | « Assurance bientôt expirée » / « Assurance expirée » |

**Quoi faire :**
1. Renouvelle l'assurance du véhicule (dans la vraie vie).
2. Va sur la page **Maintenance** → fiche du véhicule.
3. Mets à jour le champ **Date d'expiration de l'assurance** avec la **nouvelle date**.
4. ✅ Dès que la nouvelle date est à plus de 30 jours, l'alerte disparaît (≤ 15 min).

---

### 2. 🔧 Contrôle technique expiré — `inspection_expiry`

| | |
|---|---|
| **Source** | Champ *Date d'expiration du contrôle technique* (fiche entretien) |
| **⚠️ Warning** | Expire dans **30 jours ou moins** |
| **🔴 Critical** | **Déjà expiré** |
| **Message** | « Contrôle technique bientôt expiré » / « expiré » |

**Quoi faire :**
1. Passe le contrôle technique du véhicule.
2. Page **Maintenance** → fiche du véhicule.
3. Mets à jour le champ **Date d'expiration du contrôle technique**.
4. ✅ Alerte éteinte automatiquement une fois la date repoussée au-delà de 30 jours.

---

### 3. 🛢️ Vidange requise — `oil_change`

| | |
|---|---|
| **Source** | Champ *km de la dernière vidange* comparé au **dernier kilométrage relevé** (saisi via les pleins de carburant) |
| **⚠️ Warning** | **≥ 400 km** parcourus depuis la dernière vidange |
| **🔴 Critical** | **≥ 500 km** parcourus depuis la dernière vidange |
| **Message** | « Vidange bientôt requise » / « Vidange requise » |

> ⚙️ Le seuil est volontairement bas (400/500 km) — vérifie/ajuste-le si besoin
> dans `alert_service.py` (`_oil_change_alert`).

**Quoi faire :**
1. Fais la vidange du véhicule.
2. Page **Maintenance** → fiche du véhicule.
3. Mets à jour le champ **Kilométrage de la dernière vidange** avec le **km actuel** du véhicule.
4. ✅ L'écart repasse sous le seuil → alerte éteinte.

---

### 4. ⛽ Consommation anormale — `consumption_anomaly`

| | |
|---|---|
| **Source** | Historique des pleins (`fuel_entries`) du véhicule |
| **⚠️ Warning** | Le dernier plein montre une consommation avec **> 20 % d'écart** par rapport à la moyenne historique (trop élevée **ou** trop faible) |
| **Pré-requis** | Au moins **2 pleins** enregistrés |
| **Message** | « Consommation anormale détectée » |

**Quoi faire :**
- C'est une alerte **informative** : elle signale un possible problème mécanique,
  un vol de carburant, ou une simple erreur de saisie.
- ⚠️ On ne la « résout » pas manuellement.
- Vérifie d'abord la **saisie** du dernier plein (litres / km cohérents ?).
- Si la donnée est correcte, **inspecte le véhicule**.
- ✅ Elle disparaît d'elle-même quand les pleins suivants ramènent la consommation
  vers la moyenne.

---

### 5. 💸 Pic de coût carburant — `cost_spike`

| | |
|---|---|
| **Source** | Somme des montants carburant (`fuel_entries`) par mois |
| **⚠️ Warning** | Le **mois en cours** dépasse de **plus de 30 %** le total du **mois précédent** |
| **Pré-requis** | Le mois précédent doit avoir un total > 0 |
| **Message** | « Pic de coût carburant détecté » |

**Quoi faire :**
- Alerte **informative** sur la dérive budgétaire.
- On ne la résout pas manuellement.
- Vérifie l'usage du véhicule (kilométrage en hausse ? hausse du prix du carburant ?
  pleins en double saisis par erreur ?).
- ✅ Elle s'efface automatiquement au **changement de mois**, ou si les dépenses
  redescendent sous le seuil.

---

## Récapitulatif : action par type d'alerte

| Alerte | Action concrète | Où | L'alerte s'éteint… |
|--------|-----------------|-----|--------------------|
| Assurance | Mettre à jour la date d'assurance | Maintenance | Date > 30 j dans le futur |
| Contrôle technique | Mettre à jour la date de contrôle | Maintenance | Date > 30 j dans le futur |
| Vidange | Mettre à jour le km de dernière vidange | Maintenance | Écart km sous le seuil |
| Consommation anormale | Vérifier saisie / inspecter véhicule | Carburant | Conso revient à la normale |
| Pic de coût | Vérifier dépenses / usage | — | Changement de mois ou baisse |

---

## Ce qu'il ne faut PAS faire

- ❌ Ne cherche pas un bouton « résoudre / fermer l'alerte » : il n'existe pas.
- ❌ Ne modifie pas le statut du véhicule pour faire taire une alerte
  (un véhicule passé en *inactif* sort des calculs, mais ce n'est pas la bonne façon).
- ✅ Corrige toujours la **donnée d'entretien** réelle → l'alerte se gère elle-même.

---

## Pour les développeurs (référence technique)

| Élément | Fichier |
|---------|---------|
| Calcul des alertes | `backend/app/services/alert_service.py` → `compute_alerts()` |
| Envoi email (instantané + digest) | `backend/app/services/alert_email_service.py` |
| Mémoire anti-spam | `backend/app/models/alert_state.py` (table `alert_states`) |
| Planification (15 min / 22h / 08h) | `backend/app/scheduler/__init__.py` |
| Données d'entretien | `backend/app/models/maintenance.py` |

**Cycle de l'email instantané** (`process_instant_alert_emails`, toutes les 15 min) :
1. Recalcule les alertes du moment.
2. Alerte **disparue** → ligne `alert_states` supprimée.
3. Alerte **nouvelle** → email envoyé + ligne créée (`instant_email_sent = True`).
4. Alerte **identique** → pas d'email, on met juste à jour `last_seen_at`.
5. Alerte **aggravée** (warning → critical) → un email de plus.
