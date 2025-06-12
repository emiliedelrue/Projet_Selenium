from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import re
import time
import csv
import argparse
import os


class Doctolib:
    def __init__(self):
        service = Service(GeckoDriverManager().install())
        self.driver = webdriver.Firefox(service=service)
        self.wait = WebDriverWait(self.driver, 10)
        self.doctors_data = []


    def cookies(self):
        try :
            reject_btn = self.wait.until(
                EC.element_to_be_clickable((By.ID, "didomi-notice-disagree-button"))
            )
            reject_btn.click()
            self.wait.until(EC.invisibility_of_element_located((By.ID, "didomi-notice-disagree-button")))
        except:
            pass
    
    def rechercheDocteur(self, spe, location):
        try:
            self.driver.get("https://www.doctolib.fr/")
            
            self.cookies()
            
            if spe:
                specialty_input = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 
                        "input.searchbar-input.searchbar-query-input"
                    ))
                )
                
                specialty_input.clear()
                specialty_input.send_keys(spe)
                
                try:
                    first_suggestion = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 
                            "#search-query-input-results-container li:first-child"
                        ))
                    )
                    first_suggestion.click()
                except:
                    specialty_input.send_keys(Keys.ENTER)
            
            if location:
                location_input = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 
                        "input.searchbar-input.searchbar-place-input"
                    ))
                )
                
                location_input.clear()
                location_input.send_keys(location)
                
                try:
                    first_location = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 
                            "#search-place-input-results-container li:nth-child(2)"
                        ))
                    )
                    first_location.click()
                except:
                    location_input.send_keys(Keys.ENTER)


            search_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                    "button.searchbar-submit-button"
                ))
            )
            search_button.click()

            
            return True
            
        except Exception as e:
            print(f"Erreur lors de la recherche: {e}")
            return False


    def filtres(self, insurance_sector=None, consultation_type=None,price_min=None, price_max=None, address_filter=None):
        try:
            filter_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 
                    "button[data-test='filters-button']"))
            )
            filter_btn.click()
            
            if insurance_sector:
                self._apply_insurance_filter(insurance_sector)
            
            if consultation_type:
                self._apply_consultation_type_filter(consultation_type)
            
            if price_min or price_max:
                self._apply_price_filter(price_min, price_max)
            
            apply_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR,
                    "button[data-test='apply-filters-button']"))
            )
            apply_btn.click()
            
            time.sleep(3) 
            
        except Exception as e:
            print(f"Erreur lors de l'application des filtres: {e}")

    def extract_availability(self, card):
        try:
            restriction_spans = card.find_elements(By.XPATH, 
                ".//span[contains(text(), 'patients déjà suivis') or contains(text(), 'réserve la prise de rendez-vous')]")
            
            if restriction_spans:
                print("  Réservé aux patients suivis")
                return "Réservé aux patients déjà suivis"
            
            availability_container = card.find_elements(By.CSS_SELECTOR, "[data-test-id='availabilities-container']")
            
            if availability_container:
                container = availability_container[0]
                
                all_spans = container.find_elements(By.TAG_NAME, "span")
                
                for span in all_spans:
                    text = span.text.strip().lower()
                    
                    if any(phrase in text for phrase in [
                        'patients déjà suivis',
                        'pas de créneaux',
                        'aucun créneau',
                        'non disponible'
                    ]):
                        print(f"  Restriction trouvée: {span.text[:50]}...")
                        return "Non disponible - " + span.text.strip()
                    
                    if any(phrase in text for phrase in [
                        'prochain rdv',
                        'disponible',
                        'septembre', 'octobre', 'novembre', 'décembre'
                    ]):
                        print(f"  Disponibilité trouvée: {span.text}")
                        return span.text.strip()
            
            rdv_buttons = card.find_elements(By.XPATH, ".//button[contains(text(), 'Prendre rendez-vous')]")
            
            if rdv_buttons:
                print("  Bouton RDV présent")
                return "Créneaux à vérifier - Clic requis"
            else:
                print("  Aucun bouton RDV")
                return "Pas de prise de RDV en ligne"
                
        except Exception as e:
            print(f"  Erreur extraction dispo: {e}")
            return "Erreur lors de la vérification"



    def get_doctor_pricing(self, card):
        try:
            price_elements = card.find_elements(By.CSS_SELECTOR, 
                "[class*='price'], [class*='tarif'], [class*='euro']")
            
            for price_elem in price_elements:
                text = price_elem.text
                if '€' in text:
                    print(f"  Prix trouvé sur la carte: {text}")
                    return text
            
            rdv_buttons = card.find_elements(By.XPATH, 
                ".//button[contains(text(), 'Prendre') or contains(text(), 'rendez')]")
            
            for btn in rdv_buttons:
                try:
                    print("  Clic sur bouton RDV...")
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(2)
                    
                    tarifs = self.driver.find_elements(By.CSS_SELECTOR, 
                        ".dl-profile-card .dl-profile-fee-name:contains('Consultation') + .dl-profile-fee-tag")
                    
                    if tarifs:
                        premier_tarif = tarifs[0].text
                        print(f"  Premier tarif trouvé: {premier_tarif}")
                        self.driver.back()
                        time.sleep(1)
                        return premier_tarif
                        
                    self.driver.back()
                    time.sleep(1)
                    
                except Exception as e:
                    continue
                    
            return "Prix à vérifier"
            
        except Exception as e:
            return "Non disponible"


    def doctors(self, max_results):
        """Extrait les informations essentielles des docteurs"""
        doctors_data = []
        
        try:
            print("Attente du chargement des résultats...")
            time.sleep(3)
            
            print("Recherche des cartes de docteurs...")
            doctor_cards = self.driver.find_elements(By.CSS_SELECTOR, ".dl-card-content")
            
            if not doctor_cards:
                print("Aucune carte de docteur trouvée")
                return doctors_data
            
            print(f"{len(doctor_cards)} cartes trouvées")
            print(f"Extraction de {min(len(doctor_cards), max_results)} docteurs...")
            
            for i, card in enumerate(doctor_cards[:max_results]):
                try:
                    print(f"Extraction docteur {i+1}...")
                    
                    # === NOM COMPLET ===
                    nom_complet = "Non trouvé"
                    try:
                        nom_element = card.find_element(By.CSS_SELECTOR, "h2")
                        nom_complet = nom_element.text.strip()
                        print(f"  Nom: {nom_complet}")
                    except Exception as e:
                        print(f"  Nom non trouvé: {e}")
                    
                    # === PROCHAINE DISPONIBILITÉ ===
                    disponibilite = self.extract_availability(card)
                    
                    # === CONSULTATION VIDÉO ===
                    consultation_video = "Non"
                    consultation_type = "Sur place uniquement"
                    try:
                        video_icon = card.find_element(By.CSS_SELECTOR, 
                            "svg[aria-label*='vidéo'], svg[data-test-id='telehealth-icon'], svg[data-icon-name*='video']")
                        consultation_video = "Oui"
                        consultation_type = "Vidéo disponible"
                        print(f"  Consultation vidéo: {consultation_video}")
                    except:
                        print(f"  Consultation sur place uniquement")
                    
                    # === SECTEUR D'ASSURANCE ET PRIX ===
                    secteur_assurance = "Non trouvé"
                    prix_consultation = "Non disponible"
                    try:
                        all_text_elements = card.find_elements(By.CSS_SELECTOR, "p, span, div")
                        
                        for elem in all_text_elements:
                            text = elem.text.strip().lower()
                            
                            if "secteur 1" in text:
                                secteur_assurance = "Secteur 1"
                            elif "secteur 2" in text:
                                secteur_assurance = "Secteur 2"
                            elif "non conventionné" in text:
                                secteur_assurance = "Non conventionné"
                            elif "conventionné" in text and "secteur" not in text:
                                secteur_assurance = "Conventionné (Secteur 1)"
                            
                            import re
                            prix_patterns = [
                                r'(\d+)\s*€',
                                r'(\d+)\s*euros?',
                                r'tarif[:\s]*(\d+)',
                                r'consultation[:\s]*(\d+)'
                            ]
                            
                            for pattern in prix_patterns:
                                prix_match = re.search(pattern, text)
                                if prix_match:
                                    prix_consultation = f"{prix_match.group(1)}€"
                                    break
                        
                        print(f"  Secteur: {secteur_assurance}")
                        print(f"  Prix: {prix_consultation}")
                        
                    except Exception as e:
                        print(f"  Secteur/Prix non trouvés: {e}")
                    
                    # === ADRESSE COMPLÈTE ===
                    rue = "Non trouvée"
                    code_postal = "Non trouvé"
                    ville = "Non trouvée"
                    
                    try:
                        address_elements = card.find_elements(By.CSS_SELECTOR, 
                            "p.XZWvFVZmM9FHf461kjNO, p[data-design-system-component='Paragraph']")
                        
                        import re
                        for elem in address_elements:
                            text = elem.text.strip()
                            
                            cp_ville_match = re.match(r'(\d{5})\s+(.+)', text)
                            if cp_ville_match:
                                code_postal = cp_ville_match.group(1)
                                ville = cp_ville_match.group(2)
                                print(f"  Code postal: {code_postal}")
                                print(f"  Ville: {ville}")
                            
                            elif any(word in text.lower() for word in ['rue', 'avenue', 'boulevard', 'place', 'square', 'allée', 'impasse']):
                                rue = text
                                print(f"  Rue: {rue}")
                    
                    except Exception as e:
                        print(f" Adresse non trouvée: {e}")

                    print(" Extraction des tarifs...")
                    try:
                        prix_principal = self.get_doctor_pricing(card)
                    except Exception as e:
                        print(f" Erreur tarifs: {e}")
                        prix_principal = "Non disponible"

                    
                    # === CRÉATION DE L'OBJET DOCTEUR ===
                    doctor_data = {
                        'nom_complet': nom_complet,
                        'disponibilite': disponibilite,
                        'consultation_type': consultation_type,
                        'consultation_video': consultation_video,
                        'secteur_assurance': secteur_assurance,
                        'prix_consultation_principale': prix_principal,
                        'rue': rue,
                        'code_postal': code_postal,
                        'ville': ville
                    }
                    
                    doctors_data.append(doctor_data)
                    print(f" Docteur {i+1} extrait: {nom_complet}")
                    print("─" * 60)
                    
                except Exception as e:
                    print(f"Erreur docteur {i+1}: {e}")
                    continue
            
            print(f"{len(doctors_data)} docteurs extraits au total !")
            return doctors_data
            
        except Exception as e:
            print(f"Erreur générale: {e}")
            return doctors_data


    def format_tarifs(self, tarifs):
        if not tarifs:
            return "Non disponible"
        
        tarifs_str = " | ".join([f"{t['type']}: {t['prix']}" for t in tarifs])
        return tarifs_str

    def save_to_csv(self, filename, doctors_data):
        if not doctors_data:
            print("Aucune donnée à sauvegarder")
            return
        
        fieldnames = ['nom_complet', 'disponibilite', 'consultation_type', 
                    'consultation_video', 'secteur_assurance', 'prix_consultation_principale',
                    'rue', 'code_postal', 'ville'] 
        
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(doctors_data)
        
        chemin_complet = os.path.abspath(filename)
        print(f"{len(doctors_data)} entrées sauvegardées dans: {filename}")
        print(f"Emplacement: {chemin_complet}")



    def close(self):
        if self.driver:
            self.driver.quit()
        

def main():
    parser = argparse.ArgumentParser(description='Scraper Doctolib')
    parser.add_argument('--specialty', required=True, help='Spécialité médicale')
    parser.add_argument('--location', required=True, help='Lieu de recherche')
    parser.add_argument('--max-results', type=int, default=10, help='Nombre max de résultats')
    parser.add_argument('--insurance-sector', choices=['1', '2', 'non_conventionne'], help='Secteur d\'assurance')
    parser.add_argument('--consultation-type', choices=['visio', 'sur_place'], help='Type de consultation')
    parser.add_argument('--price-min', type=int, help='Prix minimum')
    parser.add_argument('--price-max', type=int, help='Prix maximum')
    parser.add_argument('--output', default='doctors_data.csv', help='Fichier de sortie CSV')
    
    args = parser.parse_args()
    
    scraper = Doctolib()
    
    try:
        print(f"Recherche: {args.specialty} à {args.location}")
        
        if scraper.rechercheDocteur(args.specialty, args.location):
            print("Recherche effectuée !")

            
            try:
                print("Extraction des données...")
                doctors = scraper.doctors(args.max_results) 
                print(f"{len(doctors)} docteurs trouvés !")
                
                if doctors:
                    print("Sauvegarde CSV...")
                    scraper.save_to_csv(args.output, doctors)  
                    print("CSV sauvegardé !")
                else:
                    print("Aucune donnée à sauvegarder")
                    
            except Exception as e:
                print(f"Erreur extraction: {e}")
                
        else:
            print("Échec de la recherche")
            
    except Exception as e:
        print(f"Erreur générale: {e}")
        
            
    finally:
        scraper.close()

if __name__ == "__main__":
    main()

