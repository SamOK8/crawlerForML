import pickle
import pandas as pd
import numpy as np


with open("model_sauto.dat", "rb") as f:
    modelML = pickle.load(f)

znacka = 65
model = 364
rok = 2019
stav = 1
najeto = 230000
vykon = 220
palivo = 0
kapacita_baterie = 55
prevodovka = 0
pohon = 2


vstup = np.array([[znacka, model, rok, stav, najeto, vykon, palivo, kapacita_baterie, prevodovka, pohon]])


# 1. Definujte názvy sloupců (musí být ve stejném pořadí jako hodnoty v poli)
sloupce = ['znacka', 'model', 'rok', 'stav', 'najeto', 'vykon', 'palivo', 'kapacita_baterie', 'prevodovka', 'pohon']

# 2. Vytvořte DataFrame
vstup_df = pd.DataFrame(vstup, columns=sloupce)

# 3. Teď už můžete predikovat bez varování
predikce = modelML.predict(vstup_df)
print(f"Odhadovaná cena: {predikce[0]} Kč")