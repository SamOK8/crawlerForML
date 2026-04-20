from flask import Flask, render_template, request
import pickle
import pandas as pd
import numpy as np
import json
import matplotlib


matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

with open("model_sautoV4.dat", "rb") as f:
    modelML = pickle.load(f)
with open("mapping.json", "r", encoding="utf-8") as f:
    mapping = json.load(f)

# with open("RFmodel_sautoV3.dat", "rb") as f:
#     rf_model = pickle.load(f)
# with open("LRmodel_sautoV3.dat", "rb") as f:
#     lr_model = pickle.load(f)
#
#
# def predikce_ceny(vstupni_data):
#     linear_features = ["rok", "najeto", "vykon"]
#
#     y_pred_test_lr = lr_model.predict(vstupni_data[linear_features])
#     y_pred_test_rf_correction = rf_model.predict(vstupni_data)
#
#     final_predictions = y_pred_test_lr + y_pred_test_rf_correction
#     final_predictions = np.clip(final_predictions, a_min=5000, a_max=None)
#     return final_predictions



# Pomocná funkce pro výpočet daňové zůstatkové ceny (CZ legislativa)
def vypocet_danove_ceny(porizovaci_cena, rok_odpisu, typ_odpisu):
    if rok_odpisu == 0:
        return porizovaci_cena

    if typ_odpisu == 'mimoradny':
        # Elektromobily: 1. rok 60 %, 2. rok 40 %
        if rok_odpisu == 1:
            return porizovaci_cena * 0.40
        else:
            return 0.0

    elif typ_odpisu == 'rovnomerny':
        # 1. rok 11 %, další roky 22,25 %
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
            if y == 1:
                odpis = porizovaci_cena / 5
            elif y <= 5:
                odpis = (zustatek * 2) / (6 - (y - 1))
            else:
                odpis = zustatek
            zustatek -= odpis
        return max(0, zustatek)

    return 0


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

            rok_vyroby = int(request.form['rok_vyroby'])
            najeto_start = int(request.form['najeto'])
            vykon = int(request.form['vykon'])
            kapacita_baterie = float(request.form['kapacita_baterie'])
            stav = int(request.form['stav'])
            palivo = int(request.form['palivo'])
            prevodovka = int(request.form['prevodovka'])
            pohon = int(request.form['pohon'])

            najezd_rocne = int(request.form['najezd_rocne'])
            kroky_roky = int(request.form['kroky_roky'])
            pocet_kroku = int(request.form['pocet_kroku'])
            typ_odpisu = request.form['typ_odpisu']

            sloupce = ['znacka', 'model', 'rok', 'stav', 'najeto', 'vykon', 'palivo', 'kapacita_baterie', 'prevodovka',
                       'pohon']

            roky_osy = [0]
            ceny_trh = []
            ceny_dan = []

            # Aktuální (pořizovací) cena
            vstup_dnes = np.array(
                [[znacka_idx, model_idx, rok_vyroby, stav, najeto_start, vykon, palivo, kapacita_baterie, prevodovka,
                  pohon]])
            df_dnes = pd.DataFrame(vstup_dnes, columns=sloupce)
            cena_dnes = int(modelML.predict(df_dnes)[0])
            # cena_dnes = int(predikce_ceny(df_dnes)[0])

            ceny_trh.append(cena_dnes)
            ceny_dan.append(cena_dnes)

            # Predikce do budoucna
            for i in range(1, pocet_kroku + 1):
                roky_dopredu = i * kroky_roky
                simulovany_rok = rok_vyroby - roky_dopredu
                simulovany_najezd = najeto_start + (najezd_rocne * roky_dopredu)

                # Tržní model
                vstup_budoucnost = np.array(
                    [[znacka_idx, model_idx, simulovany_rok, stav, simulovany_najezd, vykon, palivo, kapacita_baterie,
                      prevodovka, pohon]])
                df_budoucnost = pd.DataFrame(vstup_budoucnost, columns=sloupce)
                cena_budoucnost = int(modelML.predict(df_budoucnost)[0])
                # cena_budoucnost = int(predikce_ceny(df_budoucnost)[0])

                # Daňový model
                dan_budoucnost = vypocet_danove_ceny(cena_dnes, roky_dopredu, typ_odpisu)

                roky_osy.append(roky_dopredu)
                ceny_trh.append(cena_budoucnost)
                ceny_dan.append(dan_budoucnost)

            # Vykreslení grafu se dvěma křivkami
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

            # Uložení grafu
            img = io.BytesIO()
            plt.savefig(img, format='png', transparent=True)
            img.seek(0)
            plot_url = base64.b64encode(img.getvalue()).decode('utf8')
            plt.close()

            # Výpočet skrytého zisku (Trh minus Daně v posledním kroku)
            skryty_zisk = ceny_trh[-1] - ceny_dan[-1]

            vysledky = {
                "start_cena": cena_dnes,
                "konec_trh": ceny_trh[-1],
                "konec_dan": ceny_dan[-1],
                "skryty_zisk": skryty_zisk,
                "celkem_let": roky_osy[-1]
            }

    return render_template('index.html', mapping=mapping, plot_url=plot_url, vysledky=vysledky, error_msg=error_msg,
                           form_data=form_data)


if __name__ == '__main__':
    app.run(debug=True)