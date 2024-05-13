import requests
from bs4 import BeautifulSoup
import argparse
import concurrent.futures
import json

def listener(url):
    
    product_urls = []

    while url:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        product_links = soup.select('td.loop-product-title a')
        for link in product_links:
            product_urls.append(link['href'])

        pages = soup.select('ul.page-numbers li')[-1]
        next_page = pages.find('a', class_='next page-numbers')
        url = next_page['href'] if next_page else None
      
    print(f'{len(product_urls)} productos encontrados')
    return product_urls
def crawler(url):
    
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    titulo = soup.select_one('h1.product-title').get_text(strip=True)
    
    try:
         imagen_url = soup.select_one('div.prod-structure img')['src']
         
    # NO ME HA DADO MÁS TIEMPO A INDAGAR MÁS EN ESTE PUNTO, PERO LA IDEA ERA DESCARGAR LA IMAGEN SVG Y CONVERTIRLA A PNG :/
    # response = requests.get(imagen_url)
    # with tempfile.NamedTemporaryFile(delete=False, suffix=".svg") as f:
    #     f.write(response.content)
    #     img = svg2rlg(f.name)
    #     renderPM.drawToFile(img, f'products/img/{titulo}.png', fmt='PNG')
    #     print(f'Imagen guardada: products/img/{titulo}.png')
    #     os.unlink(f.name)  # delete the temporary file
    except:
         imagen_url = "Sin imagen"
    
    
    desc = soup.select_one('product-description')
    if desc == None:
        desc = "Sin descripción"
    
    # Información principal
    main_div = soup.select_one('div.product-main-info')
    id = main_div.select('div.product_meta span')[1].get_text(strip=True)
    cas_number = main_div.select('div.product-prop')[1].get_text(strip=True).split(':')[1]
    try:
        synonyms_text = main_div.select_one('div.product-prop-synonyms').get_text(strip=True)
        synonyms_text = synonyms_text.replace('Synonyms:', '') 
        synonyms = synonyms_text.split(', ') if synonyms_text else []
    except:
        synonyms = []
    # Info divs
    info_divs = soup.select('div.product-info-columns')
    
    # Identifiers div
    identifiers = ['CAS Index Name', 'Molecular formula', 'Molecular weight', 'Lipid number', 'Smiles', 'Isomeric', 'InChI:', 'InChIKey']
    data_identifiers = {}
    indentifiers_div = info_divs[0]
    divs = indentifiers_div.select('div.product-prop')
    for div in divs:
        text = div.get_text(strip=True)
        identifier, _, value = text.partition(':')
        
        if identifier in identifiers:
            data_identifiers[identifier] = value
        
    # Product div
    identifiers = ['Purity', 'Storage', 'Supplied as', 'Physical state', 'Documentation', 'MSDS']
    data_prod = {}
    prod_div = info_divs[1]
    divs = prod_div.select('div.product-prop')
    for div in divs:
        text = div.get_text(strip=True)
        identifier, _, value = text.partition(':')
        
        if identifier in identifiers:
            if identifier == 'MSDS':
                data_prod[identifier] = div.select_one('a')['href']
            else:
                data_prod[identifier] = value
            
        
    # Packages
    packages_table = soup.select_one('table.product-variations-table')
    packages = []
    if packages_table:
        rows = packages_table.select('tr')
        for row in rows:
            cells = row.select('td')
            package = {
                'id': cells[0].get_text(strip=True),
                'dosis': cells[1].get_text(strip=True),
                'precio': cells[2].get_text(strip=True),
            }
            packages.append(package)
    
    data = {
        
        'id': id,
        'titulo': titulo,
        'imagen_url': imagen_url,
        # 'imagen': f'products/img/{titulo}.png',
        'descripcion': desc,
        'CAS number': cas_number,
        'CAS index name': data_identifiers.get('CAS Index Name'),
        'estructura':   data_identifiers.get('Molecular formula'),
        'url': url,
        'sinonimos': synonyms,
        'peso molecular': data_identifiers.get('Molecular weight'),
        'numero de lipido': data_identifiers.get('Lipid number'),
        'smiles': data_identifiers.get('Smiles'),
        'isomeric smiles': data_identifiers.get('Isomeric'),
        'InChI': data_identifiers.get('InChI:'),
        'InChIKey': data_identifiers.get('InChIKey'),
        'pureza': data_prod.get('Purity'),
        'almacenamiento': data_prod.get('Storage'),
        'suministrado como': data_prod.get('Supplied as'),
        'estado fisico': data_prod.get('Physical state'),
        'documentacion': data_prod.get('Documentation'),
        'msds': data_prod.get('MSDS'),
        'paquetes': packages,
    }
    
    return data
def main():
    # argparse es una biblioteca para parsear argumentos de terminal
    parser = argparse.ArgumentParser(description='Web Scraper')
    parser.add_argument('-c', type=int, help='Número de crawlers ejecutandose en paralelo')
    args = parser.parse_args()
    
    url = 'https://www.larodan.com/products/category/monounsaturated-fa/'
    # La función listener obtiene todas las url de productos de la url principal
    product_urls = listener(url)
    
    data = []

    # Se crea un ThreadPoolExecutor. El número máximo de workers es el número de crawlers que se ejecutarán en paralelo
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.c) as executor:
        # Para cada url llama un crawler y se almacena el resultado futuro en un diccionario
        future_to_url = {executor.submit(crawler, url): url for url in product_urls}
        # A medida que cada resultado futuro se completa, se añade a la lista de data
        for future in concurrent.futures.as_completed(future_to_url):
            data.append(future.result())

    # data se guarda en un archivo json
    with open('productos.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        print('Data guardada en productos.json')

if __name__ == '__main__':
    main()