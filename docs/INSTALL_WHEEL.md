# Installation professionnelle avec un wheel Python

ZTT peut être distribué sous forme de paquet Python `.whl`. Cette méthode permet d’installer une version déterminée sans cloner le dépôt Git et convient aux environnements de qualification, de production et aux réseaux isolés.

## Construire le paquet

Depuis la racine du dépôt :

```bash
python -m venv .venv-build
source .venv-build/bin/activate
python -m pip install --upgrade pip build twine
python -m build
python -m twine check dist/*
```

Sous Windows PowerShell :

```powershell
py -m venv .venv-build
.venv-build\Scripts\Activate.ps1
python -m pip install --upgrade pip build twine
python -m build
python -m twine check dist/*
```

Les fichiers sont créés dans `dist/` :

```text
zabbix_template_tool-<version>-py3-none-any.whl
zabbix_template_tool-<version>.tar.gz
```

Le suffixe `py3-none-any` indique un wheel Python pur, sans dépendance à un système d’exploitation ou à une architecture particulière.

## Installer le wheel

Dans un environnement disposant d’un accès au dépôt Python configuré :

```bash
python -m venv /opt/ztt/venv
source /opt/ztt/venv/bin/activate
python -m pip install /chemin/zabbix_template_tool-<version>-py3-none-any.whl
ztt --version
```

Pour une installation strictement figée, conserver également le wheel et les versions exactes de ses dépendances dans un dépôt d’artefacts interne.

## Préparer une installation hors ligne

Sur une machine ayant accès à Internet ou au dépôt Python interne :

```bash
mkdir -p wheelhouse
python -m pip download \
  --dest wheelhouse \
  dist/zabbix_template_tool-<version>-py3-none-any.whl
```

Le répertoire obtenu contient ZTT et ses dépendances transitives. Transférer ensuite `wheelhouse/` sur la machine cible et installer sans accès réseau :

```bash
python -m venv /opt/ztt/venv
source /opt/ztt/venv/bin/activate
python -m pip install \
  --no-index \
  --find-links /chemin/wheelhouse \
  zabbix-template-tool==<version>
```

Contrôler l’installation :

```bash
python -m pip check
ztt --version
ztt --help
```

## Dépôt Python interne

Après publication dans un dépôt compatible PyPI, par exemple Nexus, Artifactory ou devpi :

```bash
python -m pip install \
  --index-url https://pypi-interne.example/simple \
  zabbix-template-tool==<version>
```

Pour une autorité de certification interne, configurer le certificat de confiance plutôt que de désactiver la vérification TLS. L’option `--trusted-host` ne doit être utilisée qu’en solution transitoire contrôlée.

## Mise à jour et retour arrière

```bash
source /opt/ztt/venv/bin/activate
python -m pip install --upgrade \
  /chemin/zabbix_template_tool-<nouvelle-version>-py3-none-any.whl
```

Pour revenir à une version précédente :

```bash
python -m pip install --force-reinstall \
  /chemin/zabbix_template_tool-<ancienne-version>-py3-none-any.whl
```

## Désinstallation

```bash
source /opt/ztt/venv/bin/activate
python -m pip uninstall zabbix-template-tool
```

## Sécurité et contenu du paquet

Le workflow de packaging vérifie que le wheel :

- contient le paquet `ztt` et son point d’entrée CLI ;
- ne contient pas de fichier `.env`, de configuration utilisateur, de cache Python ou de données Git ;
- possède des métadonnées valides selon `twine check` ;
- est installable sur Python 3.11, 3.12 et 3.13 ;
- passe `pip check` après installation.

Aucun token, mot de passe ou fichier de configuration local ne doit être ajouté au paquet.

## Artefacts GitHub Actions

Le workflow `Package` construit le wheel et la distribution source. Les fichiers sont disponibles pendant 30 jours dans l’artefact :

```text
zabbix-template-tool-distributions
```

Une publication automatique vers un dépôt Python pourra être ajoutée ultérieurement sur les tags de version, après configuration d’un environnement GitHub protégé et de l’authentification du dépôt interne.
