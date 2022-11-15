# **R**eal**E**state**M**odeler

Templates para análisis de patrones inmobiliarios.

* Root

```
virtualenv venv --python=python3.10
source venv/bin/activate
pip install -r requirements.txt

```
* Develop mode

```
virtualenv venv --python=python3.10
source venv/bin/activate
python setup.py develop
pip install -r requirements-dev.txt

```

**Patrones de precios**

Entre las principales funcionalidades, el modelador inmobiliario busca facilitar
el aprendizaje de precios observados para distintos productos inmobiliarios:

 * terrenos,
 * departamentos
 * casas y ph
 * alquileres
 * depósitos
 * etc.) ...

![precios_observados](REM/img/observed_prices.png)

... entrenar modelos para la resolución de problemas de regresión y 
ensayar tasaciones a distintos niveles de agregación geográfica (parcelas, manzanas, etc.)

<p float="right">
  <img src="/REM/img/to_predict.png" width="400" />
  <img src="/REM/img/predicted.png" width="400" />
</p>
