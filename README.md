# Repository plugin QGIS — FTTH Permessi Manager

Repository personale per installare e **aggiornare automaticamente** il plugin
QGIS sui computer dei colleghi da remoto, **senza VPN**. Funziona tramite un URL
pubblico HTTPS (GitHub Pages): ogni collega lo aggiunge una volta in QGIS e da lì
riceve installazione e aggiornamenti come per i plugin ufficiali.

---

## Come è fatto

```
qgis-repo-ftth/
├── FTTH_PERMIT_MANAGER.zip     ← il plugin (caricane di nuovi qui)
├── build.py                    ← genera in automatico plugins.xml, index.html, icone
├── plugins.xml                 ← GENERATO: l'elenco che legge QGIS (non editarlo a mano)
├── index.html                  ← GENERATO: pagina web con l'URL e l'elenco plugin
├── icons/                      ← GENERATO: icone estratte dai plugin
├── .github/workflows/build.yml ← automazione: rigenera e pubblica a ogni caricamento
├── .nojekyll                   ← serve a GitHub Pages per pubblicare i file così come sono
└── .gitignore
```

`plugins.xml`, `index.html` e `icons/` sono **rigenerati da soli**: non serve
toccarli a mano.

---

## Configurazione iniziale (una volta sola, ~5 minuti)

1. Crea un nuovo repository **pubblico** su GitHub, per esempio `qgis-repo-ftth`.
2. Carica in questo repository tutto il contenuto di questa cartella
   (puoi trascinare i file direttamente nella pagina del repo su github.com,
   oppure usare git).
3. Vai in **Settings → Pages** del repository e imposta
   **Source: GitHub Actions**.
4. Fatto. Alla prima esecuzione la GitHub Action genera tutto e pubblica il sito.

L'URL da dare ai colleghi sarà:

```
https://TUOUSERNAME.github.io/qgis-repo-ftth/plugins.xml
```

(sostituisci `TUOUSERNAME` con il tuo nome utente GitHub, e `qgis-repo-ftth`
con il nome che hai dato al repository). L'indirizzo esatto compare anche nella
pagina web `index.html` e nel log della Action (scheda **Actions**).

> L'URL di download dentro `plugins.xml` viene costruito **da solo** dalla Action
> in base al nome del tuo repository: non devi scriverlo tu.

---

## Istruzioni per i colleghi (una volta sola)

In QGIS:

1. **Plugin → Gestisci e installa plugin… → Impostazioni**
2. In *Repository dei plugin* → **Aggiungi…**
3. Nome: a piacere (es. `FTTH interno`) — URL: l'indirizzo del `plugins.xml` qui sopra
4. **OK**, poi vai nella scheda *Non installati*, cerca **FTTH Permessi Manager**
   e premi **Installa plugin**.

Da quel momento, quando pubblichi una nuova versione, QGIS la segnala da solo
nella scheda **Aggiornabili**.

---

## Come pubblicare un aggiornamento

Il flusso è pensato per essere banale:

1. Nel plugin, aumenta il numero di `version` nel file `metadata.txt`
   (es. da `0.69` a `0.70`). **Questo è l'unico passo obbligatorio** perché
   l'aggiornamento venga proposto ai colleghi.
2. Rigenera lo `.zip` del plugin.
3. Carica il nuovo `.zip` in questo repository (anche solo trascinandolo nella
   pagina del repo su github.com — puoi sovrascrivere quello vecchio o aggiungerne
   uno con nome diverso).
4. **Stop.** La Action riparte da sola, rilegge la versione dall'interno dello zip,
   rigenera `plugins.xml` e ripubblica. Entro un paio di minuti i colleghi vedono
   l'aggiornamento in QGIS.

Note utili:

- Se lasci nel repo più `.zip` dello stesso plugin, viene pubblicata
  **automaticamente la versione più alta**: non devi cancellare i vecchi.
- Il numero di versione viene letto **dall'interno** dello zip (dal `metadata.txt`),
  quindi conta quello, non il nome del file.
- Se un collega non vede subito l'aggiornamento, è solo cache: basta riaprire il
  Gestore plugin o riavviare QGIS.

---

## Provarlo in locale (facoltativo)

Per rigenerare e vedere l'output senza pubblicare:

```bash
# genera plugins.xml/index.html usando un URL a scelta
REPO_BASE_URL="http://localhost:8000/" python3 build.py

# servi la cartella e prova ad aggiungere http://localhost:8000/plugins.xml in QGIS
python3 -m http.server 8000
```

Lo script non richiede librerie esterne: gira con qualsiasi Python 3.

---

## Attenzione alla riservatezza

GitHub Pages è **pubblico**: chiunque abbia l'URL può scaricare il plugin.
Se il codice deve restare riservato, le alternative senza VPN sono un hosting con
autenticazione (QGIS supporta la basic auth nelle impostazioni del repository)
oppure GitHub Releases su repo privato con token. Per un plugin a uso interno ma
non segreto, GitHub Pages va benissimo.
