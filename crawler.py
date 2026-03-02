import csv

from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import json
import os

driver = webdriver.Chrome()
vsechna_auta_data = []

def ziskej_parametr(nazev_parametru):
    try:
        xpath = f"//th[text()='{nazev_parametru}']/following-sibling::td"
        return driver.find_element(By.XPATH, xpath).text
    except:
        return None


def ziskej_rok_vyroby():
    vyrobeno = ziskej_parametr("Vyrobeno:")
    if vyrobeno:
        if "/" in vyrobeno:
            return vyrobeno.split("/")[1]
        return vyrobeno

    v_provozu = ziskej_parametr("V provozu od:")
    if v_provozu:
        if "/" in v_provozu:
            return v_provozu.split("/")[1]
        return v_provozu

    return None


soubor_historie = "zpracovana_auta.json"
zpracovane_url = set()

if os.path.exists(soubor_historie):
    with open(soubor_historie, "r", encoding="utf-8") as f:
        zpracovane_url = set(json.load(f))

print(f"V historii máme už {len(zpracovane_url)} zpracovaných aut.")



for cislo_stranky in range(1, 15):
    # https://www.sauto.cz/inzerce/osobni/?palivo=elektro&
    # https://www.sauto.cz/inzerce/osobni/?razeni=od-nejlevnejsich&  prvnich 50 stranek done
    # https://www.sauto.cz/inzerce/osobni/?razeni=od-nejdrazsich&

    # https://www.sauto.cz/inzerce/osobni/?

    url_seznamu = f"https://www.sauto.cz/inzerce/osobni/?strana={cislo_stranky}"
    print(f"--- Načítám seznam: Stránka {cislo_stranky} ---")
    driver.get(url_seznamu)
    time.sleep(4)

    car_links_elements = driver.find_elements(By.CSS_SELECTOR, "li.c-item a")

    url_adresy_aut = []
    for link_el in car_links_elements:
        url = link_el.get_attribute("href")

        if url and "detail" in url and url not in zpracovane_url:
            url_adresy_aut.append(url)
    url_adresy_aut = list(set(url_adresy_aut))


    print(f"Našlo se {len(url_adresy_aut)} novych aut")
    print(url_adresy_aut)

    for auto in url_adresy_aut:
        driver.get(auto)
        time.sleep(1)

        try:
            nadpis = driver.find_elements(By.CSS_SELECTOR, ".c-item-title__name-prefix a")
            znacka = nadpis[0].text if len(nadpis) > 0 else None
            model = nadpis[1].text if len(nadpis) > 1 else None

            rok = ziskej_rok_vyroby()
            palivo = ziskej_parametr("Palivo:")
            prevodovka = ziskej_parametr("Převodovka:")

            stav_raw = ziskej_parametr("Stav:")
            stav = stav_raw.split("Prověřit")[0].strip() if stav_raw else None

            cena_element = driver.find_elements(By.CSS_SELECTOR, ".c-a-basic-info__price")
            cena = cena_element[0].text.replace(" ", "").replace("Kč", "") if cena_element else None

            najeto_raw = ziskej_parametr("Najeto:")
            if najeto_raw:
                if "Z" in najeto_raw:
                    najeto = najeto_raw.replace(" ", "").replace("km", "").split("Z")[0] if najeto_raw else None
                else:
                    najeto = najeto_raw.replace(" ", "").replace("km", "") if najeto_raw else None

            vykon_raw = ziskej_parametr("Výkon:")
            vykon = vykon_raw.split("(")[0].replace(" ", "").replace("kW", "") if vykon_raw else None
            pohon = ziskej_parametr("Pohon:")

            kapacita_baterie_raw = ziskej_parametr("Kapacita akumulátoru:")
            kapacita_baterie = kapacita_baterie_raw.split(" ")[0] if kapacita_baterie_raw else 0

            auto_data = {
                "znacka": znacka,
                "model": model,
                "cena": int(cena) if cena else None,
                "rok": int(rok) if rok else None,
                "stav": stav,
                "najeto": int(najeto) if najeto else None,
                "vykon": int(vykon) if vykon else None,
                "palivo": palivo,
                "kapacita_baterie": int(kapacita_baterie),
                "prevodovka": prevodovka,
                "pohon": pohon
            }

            print(auto_data)
        except Exception as e:
            print(f"Chyba při získávání dat pro auto {auto}: {e}")
            continue

        nazev_souboru = "sauto_dataset.csv"
        soubor_existuje = os.path.isfile(nazev_souboru)

        with open(nazev_souboru, mode="a", encoding="utf-8", newline="") as csv_file:
            hlavicka = auto_data.keys()
            writer = csv.DictWriter(csv_file, fieldnames=hlavicka)

            if not soubor_existuje:
                writer.writeheader()

            writer.writerow(auto_data)

        zpracovane_url.add(auto)
        with open("zpracovana_auta.json", "w", encoding="utf-8") as f:
            json.dump(list(zpracovane_url), f, indent=4)
