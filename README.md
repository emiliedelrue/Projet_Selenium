# Projet selenium

## Pré requis

`````
# installer python3
brew install python3  

# Créer un environnement virtuel
python3 -m venv selenium_env

# Activation de l'environnement
source selenium_env/bin/activate

# Installer selenium
pip install selenium
`````

## Lancement du projet

`````
python script.py --specialty SPECIALTY --location LOCATION [--max-results MAX_RESULTS] [--insurance-sector {1,2,non_conventionne}] [--consultation-type {visio,sur_place}] [--price-min PRICE_MIN] [--price-max PRICE_MAX] [--output OUTPUT]

#Par exemple :
python script.py --spe "dermatologue" --location "75001" --max-results 10 --output "mes_docteurs.csv"
`````