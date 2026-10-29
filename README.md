# filo-social

Pubblicazione automatica dei post Instagram di @filomarbella (Filo Marbella – Costa del Sol).

- `posts/queue/*.json`: post in coda (`publish_date`, `images`, `caption`).
- `media/`: immagini dei post.
- `scripts/publish.py`: pubblica i post in scadenza tramite l'API Instagram.
- `.github/workflows/publish.yml`: esegue lo script ogni lunedì mattina (e a richiesta).

La chiave Meta è nel Secret `META_TOKEN` del repository. Non va mai scritta nei file.
