import pandas as pd
import re
import math

def clean_werknemers(value):
    try:
        val = float(value)

        if val >= 100:
            val = val / 100
        elif val >= 10:
            val = val / 10

        return math.ceil(val)
    except (ValueError, TypeError):
        return 1

def clean_ig_volgers(value):
    try:
        val = str(value).strip().upper()
        if 'K' in val:
            num = float(val.replace('K', '').replace(',', '.'))
            return int(num * 1000)
        val = re.sub(r'[^\d]', '', val)
        return int(val)
    except (ValueError, TypeError):
        return 0

def clean_webshop(value):
    try:
        val = str(value).strip().lower()
        if val in ['yes', 'ja', 'y', 'true', '1']:
            return 'Yes'
        elif val in ['no', 'nee', 'n', 'false', '0']:
            return 'No'
        return 'No'
    except:
        return 'No'

def clean_data(file):
    df = pd.read_csv(file, delimiter=';', encoding="latin1")

    # Clean and rename columns
    df["Werknemers"] = df["Werknemers"].apply(clean_werknemers)
    df["Vestigingen"] = df["Vestigingen"].apply(clean_werknemers)
    df["IGfollowers"] = df["IGfollowers"].apply(clean_ig_volgers)
    df["Webshop"] = df["Webshop"].apply(clean_webshop)

    # Drop the old columns if needed
    # df.drop(columns=["werknemers", "Vestigingen", "IG volgers", "webshop", "Opmeringen", "Whatsapp", "Website Language"], inplace=True)

    # Save the cleaned data
    df.to_csv(file, index=False, sep=';')
