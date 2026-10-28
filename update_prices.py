#!/usr/bin/env python3
"""Тегли дневния архив с цени от kolkostruva.bg (КЗП) и записва docs/prices.json
за избрания град и вериги. Само стандартна библиотека.
Ползване: python update_prices.py            (тегли най-пресния наличен ден)
          python update_prices.py --zip файл.zip   (тест с локален архив)"""
import argparse, csv, datetime, io, json, os, urllib.request, zipfile

CITY = '68134'  # код на населено място: София
# начало на името на файла -> име за показване. Добавяй нови вериги тук.
CHAINS = {'Лидл': 'Лидл', 'Kaufland': 'Кауфланд', 'Кауфланд': 'Кауфланд',
          'T Market': 'Т-Маркет', 'АВАНТИ': 'Аванти', 'ФАНТАСТИКО': 'Фантастико'}
URL = 'https://kolkostruva.bg/opendata_files/{}.zip'

def fix(name):  # имената в zip понякога са записани не в UTF-8
    try:
        return name.encode('cp437').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name

def num(s):
    return float(s.strip().replace(',', '.'))

def rows(raw):
    for enc in ('utf-8-sig', 'cp1251'):
        try:
            text = raw.decode(enc); break
        except UnicodeDecodeError:
            pass
    first = text.split('\n', 1)[0]
    delim = ';' if first.count(';') > first.count(',') else ','
    rd = csv.reader(io.StringIO(text), delimiter=delim, skipinitialspace=True)
    next(rd, None)
    return rd

def build(zf):
    O, OI, P, PI, PR = [], {}, [], {}, {}
    for name in zf.namelist():
        fn = fix(name)
        chain = next((v for k, v in CHAINS.items() if fn.startswith(k)), None)
        if not chain or not fn.lower().endswith('.csv'):
            continue
        for r in rows(zf.read(name)):
            if len(r) < 7 or r[0].strip() != CITY:
                continue
            try:
                reg = num(r[5]); promo = num(r[6]) if r[6].strip() else 0
            except ValueError:
                continue
            ok = (chain, r[1].strip())
            if ok not in OI:
                OI[ok] = len(O); O.append({'chain': chain, 'addr': ok[1]})
            pk = (chain, r[3].strip())
            if pk not in PI:
                PI[pk] = len(P); P.append([chain, pk[1], r[2].strip()])
            PR.setdefault(OI[ok], {})[PI[pk]] = [reg, promo if 0 < promo < reg else 0]
    return O, P, PR

def get_zip():
    today = datetime.date.today()
    for back in range(1, 4):
        d = (today - datetime.timedelta(days=back)).isoformat()
        try:
            with urllib.request.urlopen(URL.format(d), timeout=120) as r:
                return d, zipfile.ZipFile(io.BytesIO(r.read()))
        except Exception as e:
            print('няма данни за', d, e)
    raise SystemExit('Не успях да изтегля данни')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--zip'); a = ap.parse_args()
    if a.zip:
        date, zf = os.path.basename(a.zip)[:10], zipfile.ZipFile(a.zip)
    else:
        date, zf = get_zip()
    O, P, PR = build(zf)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docs', 'prices.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'date': date, 'outlets': O, 'products': P,
                   'prices': {str(k): v for k, v in PR.items()}}, f, ensure_ascii=False, separators=(',', ':'))
    print(date, len(O), 'обекта', len(P), 'продукта', os.path.getsize(out) // 1024, 'KB')
