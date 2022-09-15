import pandas as pd
import geopandas as gpd
import yaml
from google.cloud import bigquery
from google.oauth2 import service_account
import os
from REM.utils import ajuste_inflacion


#############################################################
####### MODULO PARA CONSUMIR PORTALES INMOBILIARIOS #########
#############################################################
# 1. PROPERATI
# 2. MERCADO LIBRE
# 3. ARGENPROP
# 4. ZONAPROP
# 5. CenturyXXI

##################### 1. PROPERATI ##########################
def get_query(bbox,sd='2021-01-01',ed='2022-08-14'):
    '''
    bbox (GeoDataFrame): bbox coords
    sd (string): start date publicación - %Y%m%d
    ed (string): end date publicación - %Y%m%d
    '''
    query_string = """
                    SELECT
                           place.lat as latitud,
                           place.lon as longitud,
                           place.l3 as localidad,
                           start_date,
                           property.type,
                           property.type_i18n,
                           property.surface_total,
                           property.surface_covered,
                           property.price,
                           property.description,
                           FORMAT_DATE('%m-%Y', start_date) as periodo,
                    FROM `properati-dw.public.ads`
                    WHERE start_date >= "{}" AND end_date <= "{}"
                    AND property.operation = "Venta"
                    AND property.currency = "USD"
                    AND place.lat > {} AND place.lat < {}
                    AND place.lon < {} AND place.lon > {}
                    AND property.type IN ("Lote", "PH", "Casa", "Departamento")
                    ORDER BY
                    periodo DESC
                    """.format(sd, ed,
                               bbox['miny'][0], bbox['maxy'][0],
                               bbox['maxx'][0], bbox['minx'][0])
    return query_string

def get_bbox(comunas_idx):
    '''
    Devuelve el bounding box para un conjunto de comunas.
    ...
    Args:

    comunas_idx (list): int indicando comuna idx
    '''
    comunas = gpd.read_file('https://storage.googleapis.com/python_mdg/carto_cursos/comunas.zip')
    zona_sur = comunas[comunas['COMUNAS'].isin(comuna_idx)].copy().to_crs(4326)

    # limite exterior comunas
    zona_sur['cons'] = 0
    sur = zona_sur.dissolve(by='cons')
    return sur.bounds

def get_client():
    with open(os.getenv('config', "..") + "/config/settings.yaml") as f:
        cfg = yaml.safe_load(f)

    project_id = cfg['bigquery']['project_id']
    service_account_key = '../'+cfg['bigquery']['credentials']

    key = service_account.Credentials.from_service_account_file(service_account_key)
    client = bigquery.Client(credentials=key,project=project_id)
    return client

def query_properati(client, query):
    query_job = client.query(query)
    df = query_job.result().to_dataframe()
    return df

def read_local_properati(path):
    oferta_residencial = pd.read_csv(path)
    propiedades = gpd.GeoDataFrame(oferta_residencial, crs=4326,
                                   geometry=gpd.points_from_xy(oferta_residencial['longitud'],
                                                               oferta_residencial['latitud']))
    return propiedades

def properaty_observed_prices(propiedades, parcelas, property_type):
    '''
    Recorta los Point de avisos dentro de las parcelas para construir
    el precio promedio de una tipologia en venta + precio promedio m2
    dentro del poligono de la parcela.
    '''
    label_pclas = gpd.sjoin(propiedades, parcelas[['smp','geometry']], predicate='within')
    rates = pd.read_csv('../data/usa_inflation.csv')
    propiedades_pclas = ajuste_inflacion(gdf=label_pclas, inflation=rates) # crea "price_adj"
    print('')
    print("Cantidad de avisos informan superficie:")
    print("***************************************")
    print(propiedades_pclas.surface_total.isna().value_counts())

    # TODO: Implementar diccionario con distintas posibilidades de agrupamiento
    if property_type == 'demolicion':
        print("Tipo de oferta: Terreno")
        producto_inmobiliario = ['Casa','PH','Lote']
    elif property_type == 'residencial':
        print("Tipo de oferta: Residencial construido")
        producto_inmobiliario = ['Departamento']
    else:
        raiseValueError("No se reconoce como tipo de oferta valida.")

    # Define el tipo de producto inmobiliario
    propiedades_target = propiedades_pclas.loc[propiedades_pclas['type'].isin(producto_inmobiliario)].copy()

    # Ajuste de superficies
    superficies = []
    for r in propiedades_target.iterrows():
        if pd.isna(r[1].surface_total):
            if pd.isna(r[1].surface_covered):
                superficies.append(r[1].surface_total)
            elif pd.isna(r[1].surface_covered) == False:
                # tomamos superficie cubierta como valida
                superficies.append(r[1].surface_covered)
            else:
                pass
        else:
            superficies.append(r[1].surface_total)

    propiedades_target['sup'] = superficies
    # Superficie no informada
    propiedades_target['sup_tot'] = propiedades_target['sup'].fillna(0)
    # Asumiendo superficie mediana
    propiedades_target['sup_tot_f'] = propiedades_target['sup'].fillna(propiedades_target['sup'].median())

    propiedades_target['usdm2'] = propiedades_target['price_adj']/propiedades_target['sup_tot']
    propiedades_target['usdm2_f'] = propiedades_target['price_adj']/propiedades_target['sup_tot_f']

    return propiedades_target
