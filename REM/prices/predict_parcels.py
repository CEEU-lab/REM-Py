import argparse
import sys
import yaml
import os
from REM.properaty_data import *
from REM.datasources import *
from REM.models import *
from REM.utils import neighbors_mean
import joblib

def run(download_offer=False, area_clip='thiner', property_type='demolicion'):
    print('')
    print("====== INICIANDO SIMULACION DE PRECIOS ======")
    # PRECIOS DE OFERTA
    # TODO: generalizar consumo de insumos inmobiliarios (!= Properati)
    if download_offer:
        print('')
        print('... Descargando oferta inmobiliaria desde Properati market place ...')
        bbox = get_bbox(comunas=[4,8]) # TODO: Generalizar seleccion de zonas/bbox
        query_sur = get_query(bbox, sd='2021-01-01',ed='2022-08-14') # TODO: Generalizar seleccion de fechas
        client = get_client()
        oferta_residencial = query_properati(client=client, query=query_sur)
        print('')
        print('Resultados de dercarga:')
        print('----------------------')
        print('Total avisos residenciales: {}'.format(len(oferta_residencial)))
        print('Superficie valida:')
        print(oferta_residencial['surface_total'].isna().value_counts())
        propiedades = gpd.GeoDataFrame(oferta_residencial, crs=4326,
                                       geometry=gpd.points_from_xy(oferta_residencial['longitud'],
                                                                   oferta_residencial['latitud']))
        propiedades.start_date = pd.to_datetime(propiedades.start_date)

    else:
        # TODO: Definir esquema de fields para tabla de parcelas
        print('')
        print('... Leyendo oferta inmobiliaria desde ruta local ... ')
        propiedades = read_local_properati(path='../data/oferta_residencial_properaty.csv')
        propiedades.start_date = pd.to_datetime(propiedades.start_date)

    # AREA DE ESTUDIO
    # TODO I: Agregar opcion de conexion a Posgre DB
    # TODO II: Generalizar seleccion de mascaras
    parcelas = caba_parcelas(source_idx=1)
    if area_clip == 'thiner':
        mascara = thiner_bound(path='../data/BarOli_V1/layers/P_BP_AREA_5347.shp')
    elif area_clip == 'coarser':
        mascara = comunas(idx=[4,8]) # se pueden usar otras comunas tambien
    else:
        raiseValueError("El area de recorte debe ser superior o inferior")
    parcelas_sur = build_study_area(parcelas, mascara)

    ## PRECIOS DE OFERTA
    print('')
    print('... Computando precios de oferta inmobiliaria observados por parcela ...')
    propiedades_target = properaty_observed_prices(propiedades, parcelas_sur, property_type)
    ref_price = propiedades_target.groupby('smp')[['usdm2']].mean()
    parcelas_sur['usdm2'] = parcelas_sur['smp'].map(ref_price['usdm2'])
    parcelas_sur.replace([np.inf, -np.inf], np.nan, inplace=True)

    print('')
    print('... Computando atributos de parcelas ...')
    gkbs = '+proj=tmerc +lat_0=-34.6297166 +lon_0=-58.4627 +k=0.9999980000000001 +x_0=100000 +y_0=100000 +ellps=intl +units=m +no_defs'
    parcelas_sur['area'] = parcelas_sur.to_crs(gkbs).geometry.area
    precios_vecinos = neighbors_mean(base_data=parcelas_sur, observation_cols=['usdm2','area'], n=10)
    parcelas_sur['precios_vecinos'] = precios_vecinos

    # Configs: variables explicativas
    with open(os.getenv('config', "..") + "/config/settings.yaml") as f:
        cfg = yaml.safe_load(f)

    # TODO: generalizar seleccion de modelos para problemas de regresion
    if property_type=='demolicion':
        rootname = 'terrenos_root'
    elif property_type=='residencial':
        rootname = 'deptos_root'
    else:
        raiseValueError("Ruta no encontrada")

    model_path = cfg['xgboost'][rootname]
    expvars = cfg['xgboost']['expvars_names']
    xvars_df = pd.read_csv(cfg['xgboost']['expvars_df'], index_col='smp')

    parcelas_cprecio = parcelas_sur[~parcelas_sur['usdm2'].isna()].copy()
    parcelas_sprecio = parcelas_sur[parcelas_sur['usdm2'].isna()].copy()

    parcelas_sprecio_idx = parcelas_sprecio[['smp','precios_vecinos','area']].copy()
    parcelas_feat = parcelas_sprecio_idx.set_index('smp').join(xvars_df[expvars]).reset_index()

    print('')
    print('... Adjudicando precios de parcelas sin oferta ...')
    xgb = joblib.load(model_path)
    pred_usdm2 = xgb.predict(parcelas_feat.set_index('smp'))
    parcelas_feat['usdm2'] = pred_usdm2
    parcelas_pred = dict(zip(parcelas_feat.smp, parcelas_feat['usdm2']))
    parcelas_sprecio['usdm2'] = parcelas_sprecio['smp'].map(parcelas_pred)
    parcelas_precios_pred = pd.concat([parcelas_cprecio, parcelas_sprecio])
    parcelas_precios_pred.to_file('../runs/sim_prices.geojson', driver='GeoJSON')
    parcelas_precios_pred[['smp','usdm2']].to_csv('../runs/sim_prices.csv')
    print('')
    print("====== SIMULACION DE PRECIOS FINALIZADA CON EXITO ======")
    return None

if __name__ == '__main__':
    # Ejecutar simulacion de precios con argumentos opcionales
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser()
        parser.add_argument("-do", "--download_offer", type=eval, default=False, help="Descarga oferta de Properati")
        parser.add_argument("-ac", "--area_clip", type=str, default='thiner', help="Define bbox para consulta avisos")
        parser.add_argument("-pt", "--property_type", type=str, default='demolicion', help="Define producto inmobiliario residencial o demolicion")
        args = parser.parse_args()

        download_offer = args.download_offer if args.download_offer else False
        area_clip = args.area_clip if args.area_clip else 'thiner'
        property_type = args.property_type if args.property_type else 'demolicion'

        run(download_offer, area_clip, property_type)

    else:
        run()
