from flask import Flask
from flask import url_for
from flask import render_template
from flask import request
from flask import redirect
from flask import session
import pandas as pd
import altair as alt
import json
from kgmodel import (Foresatt, Barn, Soknad, Barnehage)
from kgcontroller import (form_to_object_soknad, insert_soknad, commit_all, select_alle_barnehager)

app = Flask(__name__)
app.secret_key = 'BAD_SECRET_KEY' # nødvendig for session

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/barnehager')
def barnehager():
    information = select_alle_barnehager()
    return render_template('barnehager.html', data=information)

@app.route('/behandle', methods=['GET', 'POST'])
def behandle():
    if request.method == 'POST':
        sd = request.form
        print(sd)
        log = insert_soknad(form_to_object_soknad(sd))
        print(log)
        data = pd.read_excel('./kgdata.xlsx', sheet_name='barnehage')
        antall_ledige_plasser = data['barnehage_ledige_plasser'].sum()
        valgt_barnehage = sd.get('liste_over_barnehager_prioritert_5')
        har_fortrinnsrett = (
            sd.get('fortrinnsrett_barnevern') or 
            sd.get('fortrinnsrett_sykdom_i_familien') or 
            sd.get('fortrinnsrett_sykdome_paa_barnet') or 
            sd.get('fortrinssrett_annet'))
        barnehage_data = data[data['barnehage_navn'] == valgt_barnehage]
        ledige_plasser = not barnehage_data.empty and barnehage_data['barnehage_ledige_plasser'].iloc[0] > 0
        if ledige_plasser:
            resultat = "TILBUD"
        elif har_fortrinnsrett and not ledige_plasser:
            resultat = "VENTELISTE"
        else:
            resultat = "AVSLAG"
        session['information'] = sd
        session['resultat'] = resultat
        return redirect(url_for('svar')) #[1]
    else:
        return render_template('soknad.html')

@app.route('/svar')
def svar():
    resultat = session.get('resultat')
    information = session.get('information')
    return render_template('svar.html', data=information, resultat=resultat)

@app.route('/soknader')
def soknader():
    # Les inn alle relevante ark fra Excel-filen
    excel_data = pd.read_excel('./kgdata.xlsx', sheet_name=['barnehage', 'soknad', 'foresatt'])

    # Hent DataFrames for hvert ark
    soknad_data = excel_data['soknad']
    barnehage_data = excel_data['barnehage']
    foresatt_data = excel_data['foresatt']

    # Slå sammen soknad_data med foresatt_data på foresatt_1 for å få navnet
    soknad_data = soknad_data.merge(foresatt_data[['foresatt_id', 'foresatt_navn']], left_on='foresatt_1', right_on='foresatt_id', how='left')

    # Slå sammen søknadsdata med barnehagedata basert på barnehagens navn
    merged_data = soknad_data.merge(barnehage_data, left_on='barnehager_prioritert', right_on='barnehage_navn', how='left')

    soknader = []
    for index, row in merged_data.iterrows():
        # Sjekk om søknaden har fortrinnsrett
        har_fortrinnsrett = (
            row.get('fr_barnevern') or 
            row.get('fr_sykd_familie') or 
            row.get('fr_sykd_barn') or 
            row.get('fr_annet')
        )
        
        # Sjekk om det er ledige plasser
        ledige_plasser = row['barnehage_ledige_plasser'] > 0 if 'barnehage_ledige_plasser' in row else False

        # Bestem status basert på fortrinnsrett og ledige plasser
        if ledige_plasser:
            status = "TILBUD"
        elif har_fortrinnsrett and not ledige_plasser:
            status = "VENTELISTE"
        else:
            status = "AVSLAG"
        
        # Bruk kolonnen foresatt_navn som navn
        soknad = {
            'navn': row['foresatt_navn'],  # Nå bruker vi navnet fra foresatt_arket
            'barnehage': row['barnehager_prioritert'],
            'fortrinnsrett': har_fortrinnsrett,
            'ledige_plasser': ledige_plasser,
            'status': status
        }
        soknader.append(soknad)
    
    return render_template('soknader.html', soknader=soknader)

@app.route('/statistikk')
def statistikk():
    # Definer år og prosentandeler manuelt for Sandefjord
    år = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023]
    prosentandel = [79.3, 81.1, 81.2, 80.5, 79.1, 81.7, 82.0, 84.9, 87.4]

    # Lag DataFrame med disse dataene
    kommune_data = pd.DataFrame({
        'År': år,
        'Prosent': prosentandel
    })

    # Lag grafen med Altair
    chart = alt.Chart(kommune_data).mark_line(point=True).encode(
        x=alt.X('År:T', title='År'),
        y=alt.Y('Prosent:Q', title='Prosent barn i barnehage'),
        tooltip=['År', 'Prosent']
    ).properties(
        title='Prosent av barn i ett- og to-årsalderen i barnehagen for Sandefjord'
    )

    # Konverter grafen til JSON for å sende til HTML-malen
    chart_json = chart.to_json()

    return render_template('statistikk.html', chart_json=chart_json)


@app.route('/commit')
def commit():
    # Les inn alle arkene fra Excel-filen som en ordbok med ark-navn som nøkler
    excel_data = pd.read_excel('./kgdata.xlsx', sheet_name=None)

    # Konverter hvert ark til en HTML-tabell
    dataframes = {sheet_name: data.to_html(index=False) for sheet_name, data in excel_data.items()}

    # Send dataene til commit.html for visning
    return render_template('commit.html', dataframes=dataframes)





"""
Referanser
[1] https://stackoverflow.com/questions/21668481/difference-between-render-template-and-redirect
"""

"""
Søkeuttrykk

"""