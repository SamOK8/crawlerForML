from flask import Flask, render_template, request, jsonify
import pandas as pd
import json
import matplotlib
from catboost import CatBoostRegressor

# from saut_model_catBoost import age_of_car, mileage_per_year

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import numpy as np

app = Flask(__name__)

# Načtení modelu a mappingu
# with open("model_sautoV5_catBoost.dat", "rb") as f:
#     modelML = pickle.load(f)
with open("mapping.json", "r", encoding="utf-8") as f:
    mapping = json.load(f)
with open("brand_models.json", "r", encoding="utf-8") as f:
    brand_models = json.load(f)
modelML = CatBoostRegressor()

modelML.load_model("model_sautoV6_catBoost(500).cbm")

def vypocet_danove_ceny(porizovaci_cena, rok_odpisu, typ_odpisu):
    if rok_odpisu == 0: return porizovaci_cena
    if typ_odpisu == 'mimoradny':
        return porizovaci_cena * 0.40 if rok_odpisu == 1 else 0.0
    elif typ_odpisu == 'rovnomerny':
        if rok_odpisu == 1:
            odepsano = porizovaci_cena * 0.11
        elif rok_odpisu <= 5:
            odepsano = porizovaci_cena * 0.11 + (porizovaci_cena * 0.2225 * (rok_odpisu - 1))
        else:
            odepsano = porizovaci_cena
        return max(0, porizovaci_cena - odepsano)
    elif typ_odpisu == 'zrychleny':
        zustatek = porizovaci_cena
        for y in range(1, rok_odpisu + 1):
            odpis = porizovaci_cena / 5 if y == 1 else ((zustatek * 2) / (6 - (y - 1)) if y <= 5 else zustatek)
            zustatek -= odpis
        return max(0, zustatek)
    return 0


@app.route('/api/models/<brand>')
def get_models(brand):
    """API endpoint pro dynamické načítání modelů podle značky."""
    models = brand_models.get(brand, [])
    return jsonify(models)


@app.route('/', methods=['GET', 'POST'])
def index():
    plot_url = None
    vysledky = None
    error_msg = None
    form_data = {}

    if request.method == 'POST':
        form_data = request.form

        znacka_text = request.form['znacka'].strip()
        model_text = request.form['model'].strip()

        znacky_lower = [str(z).lower() for z in mapping['znacka']]
        modely_lower = [str(m).lower() for m in mapping['model']]

        if znacka_text.lower() not in znacky_lower:
            error_msg = f"Chyba: Značka '{znacka_text}' nebyla nalezena."
        elif model_text.lower() not in modely_lower:
            error_msg = f"Chyba: Model '{model_text}' nebyl nalezen."
        else:
            znacka_idx = znacky_lower.index(znacka_text.lower())
            model_idx = modely_lower.index(model_text.lower())
            znacka_val = mapping['znacka'][znacka_idx]
            model_val = mapping['model'][model_idx]

            rok_vyroby = int(request.form['rok_vyroby'])
            najeto_start = int(request.form['najeto'])
            vykon = int(request.form['vykon'])
            kapacita_baterie = float(request.form['kapacita_baterie'])

            stav_idx = int(request.form['stav'])
            palivo_idx = int(request.form['palivo'])
            prevodovka_idx = int(request.form['prevodovka'])
            pohon_idx = int(request.form['pohon'])

            stav_val = mapping['stav'][stav_idx]
            palivo_val = mapping['palivo'][palivo_idx]
            prevodovka_val = mapping['prevodovka'][prevodovka_idx]
            pohon_val = mapping['pohon'][pohon_idx]

            najezd_rocne = int(request.form['najezd_rocne'])
            pocet_kroku = int(request.form['pocet_kroku'])
            typ_odpisu = request.form['typ_odpisu']

            # Krok je nyní natvrdo nastaven na 1 rok
            kroky_roky = 1

            roky_osy = [0]
            ceny_trh = []
            ceny_dan = []

            age_of_car = 2026 - rok_vyroby
            mileage_per_year = (najeto_start / age_of_car) if age_of_car > 0 else 0
            df_dnes = pd.DataFrame({
                'znacka': [znacka_val], 'model': [model_val], 'rok': [rok_vyroby],
                'stav': [stav_val], 'najeto': [najeto_start], 'vykon': [vykon],
                'palivo': [palivo_val], 'kapacita_baterie': [kapacita_baterie],
                'prevodovka': [prevodovka_val], 'pohon': [pohon_val], 'age_of_car': [age_of_car], 'mileage_per_year': [mileage_per_year]
            })

            cena_dnes = int(modelML.predict(df_dnes)[0])
            # cena_dnes = np.exp(int(modelML.predict(df_dnes)[0]))

            ceny_trh.append(cena_dnes)
            ceny_dan.append(cena_dnes)

            for i in range(1, pocet_kroku + 1):
                roky_dopredu = i * kroky_roky
                simulovany_rok = rok_vyroby - roky_dopredu
                simulovany_najezd = najeto_start + (najezd_rocne * roky_dopredu)

                sim_age_of_car = 2026 - simulovany_rok
                sim_mileage_per_year = (simulovany_najezd / age_of_car) if age_of_car > 0 else 0
                df_budoucnost = pd.DataFrame({
                    'znacka': [znacka_val], 'model': [model_val], 'rok': [simulovany_rok],
                    'stav': [stav_val], 'najeto': [simulovany_najezd], 'vykon': [vykon],
                    'palivo': [palivo_val], 'kapacita_baterie': [kapacita_baterie],
                    'prevodovka': [prevodovka_val], 'pohon': [pohon_val], 'age_of_car': [sim_age_of_car], 'mileage_per_year': [sim_mileage_per_year]
                })

                cena_budoucnost = int(modelML.predict(df_budoucnost)[0])
                # cena_budoucnost = np.exp(int(modelML.predict(df_budoucnost)[0]))
                dan_budoucnost = vypocet_danove_ceny(cena_dnes, roky_dopredu, typ_odpisu)

                roky_osy.append(roky_dopredu)
                ceny_trh.append(cena_budoucnost)
                ceny_dan.append(dan_budoucnost)

            plt.figure(figsize=(10, 6))
            plt.plot(roky_osy, ceny_trh, marker='o', linestyle='-', color='#3498db', linewidth=3, markersize=8,
                     label='Reálná tržní hodnota (AI Model)')
            plt.plot(roky_osy, ceny_dan, marker='s', linestyle='--', color='#e74c3c', linewidth=2, markersize=6,
                     label='Účetní daňová zůstatková cena')
            plt.title('Porovnání tržní a účetní hodnoty vozu pro firmy', fontsize=15, pad=15)
            plt.xlabel('Roky pořízení', fontsize=12)
            plt.ylabel('Cena (Kč)', fontsize=12)
            plt.grid(True, linestyle='--', alpha=0.6)
            plt.xticks(roky_osy)
            plt.ticklabel_format(style='plain', axis='y')
            plt.legend(loc='upper right', fontsize=11)
            plt.tight_layout()

            img = io.BytesIO()
            plt.savefig(img, format='png', transparent=True)
            img.seek(0)
            plot_url = base64.b64encode(img.getvalue()).decode('utf8')
            plt.close()

            vysledky = {
                "start_cena": cena_dnes,
                "konec_trh": ceny_trh[-1],
                "konec_dan": ceny_dan[-1],
                "skryty_zisk": ceny_trh[-1] - ceny_dan[-1],
                "celkem_let": roky_osy[-1]
            }

    return render_template('index.html', mapping=mapping, brand_models=brand_models, plot_url=plot_url, vysledky=vysledky, error_msg=error_msg,
                           form_data=form_data)


if __name__ == '__main__':
    app.run(debug=True)