import pandas as pd
import geopandas as gpd
import requests
from shapely.geometry import shape
import warnings

def caba_parcelas(source_idx=1):
    '''
    Clipea las parcelas de las zona sur dentro de los limites de las Comunas 4 y 8.
    '''
    source = ['GBAData','Local']
    if source[source_idx] == 'GBAData':
        print('Downloading parcels from bsas data ...')
        par_root = 'https://cdn.buenosaires.gob.ar/datosabiertos/datasets/secretaria-de-desarrollo-urbano/parcelas/parcelas.geojson'
    else:
        print('Leyendo parcelas desde directorio local ...')
        par_root = '../data/BarOli_V1/layers/parcelas copiar copiar.shp'

    parcelas = gpd.read_file(par_root)
    return parcelas

def api_parcelas(iter):
    '''
    Consulta parcelas de Caba desde API de Catastro
    ...

    iter(iterable): lista, array o serie de pandas
    '''
    print('******************************************')
    print('Retrieving parcels from CATASTRO API ...')
    print('******************************************')

    API_BASE_URL = "https://datosabiertos-catastro-apis.buenosaires.gob.ar/catastro/"
    results=[]

    for i in iter:
        geom = API_BASE_URL+'geometria?smp={}'.format(i)
        data = API_BASE_URL+'parcela?smp={}'.format(i)
        r_geom = requests.get(geom).json()
        r_data = requests.get(data).json()
        results.append([r_geom, r_data])

    print('Parcelas consultadas:{}'.format(len(results)))
    print(' ')
    print('... procesando resultados')
    parcels_list = []

    for r in results:
        try:
            gdf = gpd.GeoDataFrame.from_features(r[0]['features'])
            lon = r[1]['centroide'][0] # lon
            lat = r[1]['centroide'][1] # lat
            data = {}

            for k,v in r[1].items():
                if (k != 'centroide') and (k!='puertas'):
                    data[k] = v

            df = pd.DataFrame(data, index=[0])
            df['lon_ctroid'], df['lat_ctroid'] = lon, lat
            parcel = gdf[['geometry','tipo','codigo']].set_index('codigo').join(df.set_index('smp'))
            parcels_list.append(parcel)
            print('Parcelas obtenidas: {}'.format(len(parcels_list)))
        except:
            pass
    print(' ')
    print('Consulta terminada')
    return parcels_list

def comunas(idx=[4,8]):
    '''
    Polígonos de las comunas 4 y 8.
    '''
    comunas = gpd.read_file('https://storage.googleapis.com/python_mdg/carto_cursos/comunas.zip')
    zona_sur = comunas[comunas['COMUNAS'].isin(idx)].copy().to_crs(4326)
    return zona_sur

def thiner_bound(path):
    '''
    Polígono del área de estudio
    '''
    mascara = gpd.read_file(path)
    return mascara

def build_study_area(parcelas, mascara):
    '''
    Recorta un set de parcelas dentro de una mascara.
    '''
    if parcelas.crs == mascara.crs:
        subset = parcelas.clip(mascara)
    else:
        warnings.warn("Los sistemas de coordenadas difieren. Adaptando mascara a CRS de parcelas")
        subset = parcelas.clip(mascara.to_crs(parcelas.crs))
    return subset

def usa_inflation():
    '''
    Dataset con porcentajes de inflación mensual y acumulado anual en formato wide.
    '''
    return pd.read_csv('../data/usa_inflation.csv')
