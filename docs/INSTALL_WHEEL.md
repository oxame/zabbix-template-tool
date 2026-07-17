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

Les fichiers sont créés dans `dist/` :

```text
zabbix_template_tool-<version>-py3-none-any.whl
zabbix_template_tool-<version>.tar.gz
```

## Installer le wheel

Dans un environnement disposant d’un accès au dépôt Python configuré :

```bash
python -m venv /opt/ztt/venv
source /opt/ztt/venv/bin/activate
python -m pip install /chemin/zabbix_template_tool-<version>-py3-none-any.whl
ztt --version
```

## Installation hors ligne

Sur une machine ayant accès à Internet ou au dépôt Python interne, préparer le répertoire complet :

```bash
mkdir -p wheelhouse
python -m pip download \
  --dest wheelhouse \
  dist/zabbix_template_tool-<version>-py3-none-any.whl
```

Transférer ensuite `wheelhouse/` sur la machine cible, puis installer sans accès réseau :

```bash
python -m venv /opt/ztt/venv
source /opt/ztt/venv/bin/activate
python -m pip install \
  --no-index \
  --find-links /chemin/wheelhouse \
  zabbix-template-tool
```

Le répertoire doit contenir le wheel ZTT et toutes ses dépendances, notamment `ruamel.yaml`, `typer` et `rich` ainsi que leurs dépendances transitives.

## Dépôt Python interne

Après publication dans un dépôt interne compatible PyPI :

```bash
python -m pip install \
  --index-url https://pypi-interne.example/simple \
  --trusted-host pypi-interne.example \
  zabbix-template-tool==<version>
```

L’option `--trusted-host` ne doit être utilisée que lorsque l’infrastructure interne ne dispose pas encore d’un certificat TLS reconnu. La solution recommandée est d’installer l’autorité de certification interne.

## Mise à jour

```bash
source /opt/ztt/venv/bin/activate
python -m pip install --upgrade \
  /chemin/zabbix_template_tool-<nouvelle-version>-py3-none-any.whl
ztt --version
```

## Désinstallation

```bash
source /opt/ztt/venv/bin/activate
python -m pip uninstall zabbix-template-tool
```

## Configuration de l’API Zabbix

Le wheel ne contient aucun token ni fichier de configuration utilisateur. Le fichier de profils peut être placé à l’emplacement choisi :

```bash
export ZTT_CONFIG=/etc/ztt/config.yaml
ztt api test --profile qual
```

ou être indiqué à chaque commande :

```bash
ztt api test \
  --profile qual \
  --config /etc/ztt/config.yaml
```

Les tokens restent fournis par des variables d’environnement distinctes pour QUAL et PROD.

## Artefacts GitHub Actions

Le workflow `Package` construit et vérifie automatiquement le wheel et le source distribution. Les fichiers sont disponibles dans l’artefact :

```text
zabbix-template-tool-distributions
```

Le workflow réinstalle ensuite le wheel dans des environnements Python 3.11, 3.12 et 3.13 et vérifie les commandes principales.