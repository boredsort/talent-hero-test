import logging
import os
import json
from datetime import datetime

from ebay_com_au import EbayProductStrategy

output_path = 'output'
target_file = 'target_links.txt'

def execute():
    
    target_file_exists = os.path.exists(target_file)

    if not target_file_exists:
        raise Exception(f'Unable to find target file, name {target_file}')

    target_links = []
    with open(target_file, 'r') as file:
        logging.info('Reading targetfile')
        txt = file.read()
        txt = txt.replace('\n',' ').replace(',',' ')
        target_links = txt.split()

    strategy = EbayProductStrategy()
    results = []
    for url in target_links:
        data = strategy.execute(url)
        results.append(data)

        output_dir_exists = os.path.exists(output_path)
        if not output_dir_exists:
            os.makedirs(output_path)
        
        timestamp = int(datetime.timestamp(datetime.now()))

        with open(f'{output_path}/{timestamp}.json', 'w', encoding='UTF-8', ) as file:
            logging.info(f'Writing to file: {timestamp}.json')
            file.write(json.dumps(data.get('data'), indent=4))
    
        with open(f'{output_path}/{timestamp}.html', 'w', encoding='UTF-8') as file:
            logging.info(f'Writing to file: {timestamp}.html')
            file.write(data.get('html'))

if __name__ == '__main__':
    logging.basicConfig(level = logging.INFO)
    execute()