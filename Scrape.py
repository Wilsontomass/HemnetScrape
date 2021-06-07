import pandas as pd
import numpy as np
import json
import tqdm

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def add_item(address, property_dict, data, version=1):
    """
    Add property to data. Adds modifier to duplicate addresses, so long as there is some difference in attributes.
    
    property dict contains whatever label: value pairs youd like/have
    """
    if address in data:
        if data[address] == property_dict:
            print("Duplicate property: ", address)
            return False, data
        return add_item(address + str(version), property_dict, data, version + 1)
    else:
        data[address] = property_dict
        return True, data

    
def find_with_coverage(driver, xpath, name="attribute"):
    try:
        attribute = driver.find_element_by_xpath(xpath)
    except NoSuchElementException:
        print("No", name, "found for: ", driver.current_url)
        return None
    
    return attribute
    

def nybyggnad(driver, wait):
    try:
        build_list = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "new-construction-project__property-list")))
    except TimeoutException:
        print("No new construction properties found for: ", driver.current_url)
        return False
    new_buildings = driver.find_elements_by_class_name("new-construction-project__property")
    for building in new_buildings:
        address = building.find_element_by_xpath("//a/div[1]/span[1]").text
        rooms = building.find_element_by_class_name("attributes.rooms.first").text
        area = building.find_element_by_class_name("living-area").text
        price = building.find_element_by_class_name("price").text
        avgift = building.find_element_by_class_name("fee").text
        
        new_data = {
            "type": "nybyggnad",
            "price": price,
            "Antal rum": rooms,
            "Boarea": area,
            "Byggår": 2022,
            "Avgift": avgift
        }
        
        return (address, new_data)

    
def find_mäklare(driver):
    try:
        return driver.find_element_by_xpath("//div[@class='broker-card__info']/a").text
    except NoSuchElementException:  # they may not have a link, in which case, take the last component of the mäklare card
        mäklare = find_with_coverage(driver, "//div[@class='broker-card__info']", "mäklare")
        if mäklare is None:  # Still None? No mäklare
            return None
        return mäklare.text.split("\n")[-1]  # The last item should be the mäklare name
    
def sold(driver, wait):
    
    attribute_table = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "sold-property__attributes")))
    
    address = find_with_coverage(driver, "/html/body/div[3]/div[2]/div/div[1]/h1", "address")
    final_price = find_with_coverage(driver, "//span[@class='sold-property__price-value']", "final_price")
    price = find_with_coverage(driver, "//dl[@class='sold-property__price-stats']/dd[2]", "price")
    
    if address is None or final_price is None or price is None:
        return None, None
    else:
        address = address.text.split("\n")[-1]  # The last item should be the address
        final_price = final_price.text
        price = price.text
    
    mäklare = find_mäklare(driver)
    if mäklare is None:  # Still None? No mäklare
        return None, None      
    
    map_element = driver.find_element_by_xpath("//div[@class='sold-property__map js-listing-map-sold']")
    cool_data_dict = json.loads(map_element.get_attribute("data-initial-data"))
    location = cool_data_dict["listing"]["coordinate"]
    latitude = location[0]
    longitude = location[1]
    sold_date = cool_data_dict["listing"]["sale_date"].split()[-1]  # Only want the date
    location_name = driver.find_element_by_class_name("sold-property__metadata qa-sold-property-metadata").text.split(" - ")[1]

    new_data = {
                "type": "sold",
                "final_price": final_price,
                "price": price,
                "latitude": latitude,
                "longitude": longitude,
                "location_name": location_name,
                "sold_date": sold_date,
                "mäklare": mäklare
            }
    
    attributes = driver.find_element_by_class_name("sold-property__attributes")
    labels = attributes.find_elements_by_class_name("sold-property__attribute")
    values = attributes.find_elements_by_class_name("sold-property__attribute-value")
    for i, label in enumerate(labels):
        new_data[label.text] = values[i].text
        
    return (address, new_data)


def listing(driver, wait):
    try:
        attribute_ex = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "property-attributes-table__value")))
    except TimeoutException:
        return nybyggnad(driver, wait)
        
    address = find_with_coverage(driver, "//div[@class='property-address']/h1", "address")
    price = find_with_coverage(driver, "/html/body/div[3]/div/div[2]/div[1]/div[3]/section/div/div[2]/p", "price")
    if address is None or price is None:
        return None, None
    else:
        address = address.text
        price = price.text
        
    mäklare = find_mäklare(driver)
    if mäklare is None:  # Still None? No mäklare
        return None, None 
        
    karta_section = driver.find_element_by_id("karta")
    driver.execute_script("arguments[0].scrollIntoView();", karta_section)
    
    try:
        location_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@title='Öppna detta område i Google Maps (i ett nytt fönster)']")))
        location = location_link.get_attribute("href").split("&")[0].split("=")[1].split(",")
        latitude = location[0]
        longitude = location[1]
    except TimeoutException:
        latitude = np.nan
        longitude = np.nan

    location_name = driver.find_element_by_class_name("property-address__area").text
    hemnet_sublocation = driver.find_element_by_xpath("//ul[@class='breadcrumbs']/li[3]/a").text
    attributes = driver.find_elements_by_class_name("property-attributes-table__row")

    new_data = {
        "type": "listing",
        "price": price,
        "latitude": latitude,
        "longitude": longitude,
        "location_name": location_name,
        "hemnet_sublocation": hemnet_sublocation,
        "sold_date": "2021-06-15",  # Today + 8, 8*2 = ~17 being the average time a place was on hemnet before it was sold. 
        "mäklare": mäklare
    }
    for attribute in attributes:
        label = attribute.find_element_by_class_name("property-attributes-table__label").text
        value = attribute.find_element_by_class_name("property-attributes-table__value").text
        new_data[label] = value
    
    return address, new_data
    

def scrape(data=None, what="sold", max_num=None):
    scrape_listing = True if what == "listing" else False
    data = {} if data is None else data
    if scrape_listing:
        result_url = "https://www.hemnet.se/bostader?location_ids%5B%5D=473448&expand_locations=2000"
        hit_class_name = "normal-results__hit.js-normal-list-item"
    else:
        result_url = "https://www.hemnet.se/salda/bostader?location_ids%5B%5D=473448&expand_locations=2000&page=1&sold_age=3m"
        hit_class_name = "sold-results__normal-hit"
        
    driver = webdriver.Firefox()
    driver.get(result_url)

    wait = WebDriverWait(driver, 20)
    
    try:
        consent_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@class='consent__buttons']/div[2]/button")))
        consent_button.click()
    except TimeoutException:
        raise Exception()
        driver.close()
        
    properties_looked_at = 0
    pages = 0
    added_properties = 0
    t = tqdm.tqdm(total=float("inf"), position=0, leave=True)
    while max_num is None or added_properties < max_num:
        try:
            results = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, hit_class_name)))
        except (TimeoutException, NoSuchElementException) as e:
            break
        pages += 1
        for i, result in enumerate(results):
            properties_looked_at += 1
            t.update()
            t.set_description("page {}, property #{}".format(pages, properties_looked_at))
            result.click()
            driver.switch_to.window(driver.window_handles[1])  # go to new page
     
            address, new_data = listing(driver, wait) if scrape_listing else sold(driver, wait)
            driver.switch_to.window(driver.window_handles[0])  # go back to root.
            if address is None:
                continue

            added, data = add_item(address, new_data, data)
            if added:
                added_properties += 1 

        try:
            next_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "next_page.hcl-button.hcl-button--primary.hcl-button--full-width")))
            next_button.click()
        except TimeoutException:
            break
        #driver.get(driver.current_url.replace("&page=" + str(pages), "&page=" + str(pages + 1)))        

    driver.close()
    print("Added {} of {} observed properties across {} pages".format(added_properties, properties_looked_at, pages))
    
    return data
    
    
def scrape_listing(url):
    """Scrape a single apartment listing"""
    driver = webdriver.Firefox()
    driver.get(url)
    wait = WebDriverWait(driver, 20)
    
    try:
        consent_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@class='consent__buttons']/div[2]/button")))
        consent_button.click()
    except TimeoutException:
        raise Exception()
        driver.close()
        
    address, new_data = listing(driver, wait)
    
    return {address: new_data}