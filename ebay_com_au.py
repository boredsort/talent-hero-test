import json
import logging
import re
import math
from datetime import datetime

from bs4 import BeautifulSoup
import requests

from utils.user_agents import random_agent
from utils.decorators import attribute


logger = logging.getLogger(__name__)

def download(url, headers={}, timeout=60, data=None, callback=None, **kwargs):
    try:

        response = None
        if data:
            response = requests.post(url, headers=headers, timeout=timeout, data=data)
        else:
            response = requests.get(url, headers=headers, timeout=timeout)

        if callback:
            response = callback(response)

        logger.info('Connecting: ' + url)
        if response and response.status_code in [200, 201]:
            logger.info('Connected')
        else:
            logger.info('Failed to Connected')
            response = None

    except Exception as e:
        logger.error(str(e))
        response = None

    return response

class EbayProductStrategy:

    def __init__(self):

        self.user_agent = random_agent()
        self.origin_url = None

    def execute(self, url):

        self.origin_url = url
        result = {}
        response = self.fetch(url)
        if response:
            result = self.parse(response.text)
            result.update({
                "html": response.text
            })


        return result

    def fetch(self, url):

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.5',
            'Host': 'www.ebay.com.au',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'TE': 'trailers',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self.user_agent
        }

        response = download(url, headers=headers)

        return response
    
    def parse(self, raw):
        logging.info('Parsing')
        soup = BeautifulSoup(raw, 'lxml')

        results = {}

        vehicles_compatible = self.get_vehicle_compatibility(soup)
        title = self.get_title(soup)
        price = self.get_price(soup)
        category = self.get_category_tree(soup)
        specs = self.get_specifications(soup)
        seller_info = self.get_seller_info(soup)
        description = self.get_description(soup)
        image_urls = self.get_image_urls(soup)
        shipping = self.get_shipping(soup)

        results.update({
        "data": {
            "url": self.origin_url,
            "title": title,
            "price": price,
            "shipping": shipping,
            "category_tree": category,
            "specifications": specs,
            "description": description,
            "seller_info": seller_info,
            "image_urls": image_urls,
            "compatibility": vehicles_compatible,
        }})
        logging.info('Parse complete')
        return results


    @attribute
    def get_title(self, soup):
        tag = soup.select_one('.x-item-title') or soup.select_one('[data-testid="x-item-title"]')
        if tag:
            return tag.get_text().strip()
        return None

    @attribute
    def get_price(self, soup):
        tag = soup.select_one('.x-buybox__price-section .x-price-primary span')
        if tag:
            return tag.get_text().strip()
        
        return None

    @attribute
    def get_category_tree(self, soup):
        paths = []
        tags = soup.select('.seo-breadcrumb-text')
        if tags:
            for tag in tags:
                paths.append(tag.get_text().strip())

            # clear whitespace
            paths = [path for path in paths if path.strip() != '']
            if paths:
                return ' > '.join(paths)

        return None

    @attribute
    def get_vehicle_compatibility(self, soup):

        value = self.fetch_part_finder_api(soup)
        return value

    @attribute
    def get_specifications(self, soup):

        specs = {}
        key_tags = soup.select('.x-about-this-item .ux-labels-values__labels')
        val_tags = soup.select('.x-about-this-item .ux-labels-values__values-content')
        if key_tags and val_tags:
            for key_tag, val_tag in zip(key_tags, val_tags):
                key = key_tag.get_text().strip()
                val = val_tag.get_text().strip()
                specs.update({key: val})

        return specs

    @attribute
    def get_description(self, soup):
        extra_raw = self.fetch_description_api(soup)
        extra_soup = BeautifulSoup(extra_raw, 'lxml')
        tag = extra_soup.select_one('.tabs label > span:contains(Description) + section') or extra_soup.select_one('.tabs #content1')
        if tag:
            txt = tag.get_text().strip()
            if txt:
                return txt
    
        return None
    
    @attribute
    def get_seller_info(self, soup):
        info = {}

        seller_info_tag = soup.select_one('.d-stores-info-categories__wrapper')
        if seller_info_tag:
            name_tag = seller_info_tag.select_one('.d-stores-info-categories__container__info__section__title')
            if name_tag:
                name = name_tag.get_text().strip()
                if name:
                    info.update({"name": name})
            feedback_tag = seller_info_tag.select_one('.d-stores-info-categories__container__info__section__item:contains("Feedback")')
            if feedback_tag:
                feedback = feedback_tag.get_text().strip()
                if feedback:
                    info.update({"feedback": feedback})
            sold_tag = seller_info_tag.select_one('.d-stores-info-categories__container__info__section__item:contains("sold")')
            if sold_tag:
                sold = sold_tag.get_text().strip()
                if sold:
                    info.update({"sold": sold})

        return info

    @attribute
    def get_image_urls(self, soup):
        images = []
        image_tags = soup.select('.ux-thumb-image-carousel .image img')
        if image_tags:
            for tag in image_tags:
                if tag and tag.has_attr('src'):
                    url = tag['src']
                    images.append(url.replace('s-l64', 's-l500'))

        return images
    
    @attribute
    def get_shipping(self, soup):
        tag = soup.select_one('.ux-labels-values--shipping')
        if tag:
            a_tag = tag.select_one('[data-testid="ux-action"]')
            if a_tag:
                a_tag.extract()
            txt = tag.get_text().strip()
            if txt:
                # haxx
                return txt.replace('\xa0',' ')
        return None

    def get_item_id(self, soup):
        tag = soup.select_one('[Property="og:url"]') or soup.select_one('[rel="canonical"]')
        if tag:
            url = tag.get('content') or tag.get('href')
            if url:
                return url.split('itm/')[-1]
            
        return None
    
    def get_seller_name(self, soup):
        tag = soup.select_one('.ux-seller-section__item--seller a') or soup.select_one('[data-testid="ux-seller-section__item--seller"] a')
        if tag:
            name = tag.get_text().strip()
            if name:
                return name
            url = tag.get('href')
            if url:
                url = url.split('?')[0]
                return url.split('usr/')[-1]
            
        return None


    def get_vehicle_selection_json(self, soup):
        tag = soup.find('script', text=re.compile('"p":"VEHICLE_SELECTION"', re.IGNORECASE))
        if tag:
            try:
                txt = tag.get_text().strip().strip('$vim_C=(window.$vim_C||[]).concat(').strip(')')
                _json = json.loads(txt)
                if _json:
                    return _json
            except Exception as e:
                logger.debug(str(e))

        return {}
    
    def get_category_id(self, soup):
        _json = self.get_vehicle_selection_json(soup)
        selections = _json.get('o', {}).get('w',[])
        # needs improvement
        if selections:
            while selections:
                selection = selections.pop()
                for item in selection:
                    model = None
                    if isinstance(item, dict):
                        model = item.get('model', None)
                    if model:
                        model = item.get('model',{})
                        actions = model.get('VEHICLE_SELECTION',{}).get('callToActions',[])
                        if actions:
                            return actions[0].get('action',{}).get('params',{}).get('categoryId')

        return None
    
    def get_compatibility_max_page(self, soup):
        tag = soup.select_one('.motors-compatibility-table__details')
        if tag:
            txt = tag.get_text().strip()
            matches = re.search('(\d+)', txt)
            if matches:
                count = int(matches.group(1))
                items_per_page = 20
                return math.ceil(count / items_per_page) 
                
        else:
            # could be inaccurate
            tags = soup.select('.d-motors-compatibility-table li button.pagination__item')
            if tags:
                return len(tags)
            
        return None


    def fetch_part_finder_api(self, soup):

        def parse_table(raw):

            def item_generator(json_input, lookup_key):
                if isinstance(json_input, dict):
                    for k, v in json_input.items():
                        if k == lookup_key:
                            yield v
                        else:
                            yield from item_generator(v, lookup_key)
                elif isinstance(json_input, list):
                    for item in json_input:
                        yield from item_generator(item, lookup_key)

            try:
                _json = json.loads(raw)
                table = _json.get('modules',{}).get('COMPATIBILITY_TABLE')
                headers_cells = table.get('paginatedTable',{}).get('header',{})
                rows = table.get('paginatedTable',{}).get('rows',{})
                headers = []
                for val in item_generator(headers_cells, 'text'):
                    headers.append(val)

                compatiblity = []
                if headers:
                   
                    for row in rows:
                        compatiblity_dict = {}
                        values = []
                        for val in item_generator(row, 'text'):
                            values.append(val)

                        for key, val in zip(headers, values):
                            compatiblity_dict.update({key: val})

                        if compatiblity_dict:
                            compatiblity.append(compatiblity_dict)

                return compatiblity

            except Exception as e:
                logger.error(str(e))

            return None
        
        compatiblity_list = []
        # payloads
        # --------------------------------------------
        item_id = self.get_item_id(soup)
        seller_name = self.get_seller_name(soup)
        cat_id = self.get_category_id(soup)
        # default
        market_place_id = 'EBAY-AU'
        # --------------------------------------------
        item_per_page = 20
        max_pages = self.get_compatibility_max_page(soup)

        if item_id and seller_name and cat_id and market_place_id:
            payload = {
                "scopedContext":
                    {
                        "catalogDetails": {
                            "itemId": item_id,
                            "sellerName": seller_name,
                            "categoryId": cat_id,
                            "marketplaceId": market_place_id
                        }
                    }
            }

            headers = {
                'authority':'www.ebay.com.au',
                'accept': 'application/json',
                'accept-language':'en-US,en;q=0.9',
                'content-type':'application/json',
                'origin':'https://www.ebay.com.au',
                'referer': self.origin_url,
                'user-agent': self.user_agent
            }
            
            for page in range(0, max_pages):
                offset = page * item_per_page
                try:
                    api_url = f'https://www.ebay.com.au/g/api/finders?module_groups=PART_FINDER&referrer=VIEWITEM&offset={offset}&module=COMPATIBILITY_TABLE'
                    response = download(api_url, headers=headers, data=json.dumps(payload))
                    if response:
                        compatiblity = parse_table(response.text)
                        if compatiblity:
                            compatiblity_list.extend(compatiblity)

                except Exception as e:
                    logger.debug(str(e))

        return compatiblity_list


    def fetch_description_api(self, soup):
        name = self.get_seller_name(soup)
        item_id = self.get_item_id(soup)
        cat_id = self.get_category_id(soup)
        ts = datetime.timestamp(datetime.now())

        api_url = f'https://vi.vipr.ebaydesc.com/ws/eBayISAPI.dll?ViewItemDescV4&item={item_id}&t={ts}&category={cat_id}&seller={name}&excSoj=1&excTrk=1&lsite=15&ittenable=false&domain=ebay.com.au&descgauge=1&cspheader=1&oneClk=2&secureDesc=1'

        headers = {
            'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language':'en-US,en;q=0.9',
            'Referer':self.origin_url,
            'Sec-Fetch-Dest':'iframe',
            'Sec-Fetch-Mode':'navigate',
            'Sec-Fetch-Site':'cross-site',
            'Upgrade-Insecure-Requests':'1',
            'User-agent': self.user_agent
        }

        try:
            response = download(api_url, headers=headers)
            if response:
                return response.text

        except Exception as e:
            logger.error(str(e))

        return {}