import matplotlib.pyplot as plt
import numpy as np
import json,requests
from bs4 import BeautifulSoup
import urllib,time,sys
import geopy
import pandas as pd

def get_zipcode(geolocator, lat_field, lon_field):        #used while using API
    location = geolocator.reverse(lat_field + "," + lon_field)
    return location.raw['address']['postcode']

def default_function(user_entered_zipcode):
    list_of_tuples_with_given_zipcodes = []
    id_of_apartments = []
    
    #scraping data
    for i in range(1,2):                      #might take a long time in running because the page has to wait for 1 second othetwise it blocks my device's IP.
        content = requests.get('https://losangeles.craigslist.org/search/apa?s = ' + str(i),time.sleep(1))  #https://losangeles.craigslist.org/search/apa?s=120
        soup = BeautifulSoup(content.content, 'html.parser')
        my_anchors = list(soup.find_all("a",{"class": "result-image gallery"}))
        for index,each_anchor_tag in enumerate(my_anchors):
            URL_to_look_for_zipcode = soup.find_all("a",{"class": "result-title"})      #taking set so that a page is not visited twice.
        for each_href in URL_to_look_for_zipcode:
            content_href = requests.get(each_href['href'],time.sleep(1))   #script id="ld_posting_data" type="application/ld+json">
            # print(each_href['href'])
            soup_href = BeautifulSoup(content_href.content, 'html.parser')
            my_script_tags = soup_href.find("script",{"id": "ld_posting_data"})
            if my_script_tags:
                res = json.loads(str(list(my_script_tags)[0]))
                if res and 'address' in list(res.keys()):
                    if res['address']['postalCode'] == user_entered_zipcode:            #use the input zipcode entered by the user.
                        list_of_tuples_with_given_zipcodes.append(each_href['href'])
        print("\n Now Scraping page : ",i)
        
    #fetching the prices and addresses of these apartments

    all_flat_rents_in_the_given_zipcode = []
    addresses_of_flats = []
    for each_link in list_of_tuples_with_given_zipcodes:
        content = requests.get(each_link,time.sleep(1))   #https://losangeles.craigslist.org/search/apa?s=120
        if content.status_code == 200:
            print("\n Scraping individual links...\n ")
            soup = BeautifulSoup(content.content, 'html.parser')
            prices_of_apartments = soup.find("span",{"class" : "price"})
            address_of_apartments = soup.find("script",{"id": "ld_posting_data"})
            if prices_of_apartments:
                flat_rent = float(prices_of_apartments.get_text()[1:].replace(",",""))
                all_flat_rents_in_the_given_zipcode.append(flat_rent)
            if address_of_apartments:
                address_for_each_flat = json.loads(str(list(address_of_apartments)[0]))["address"]["streetAddress"]
                # print(address_for_each_flat)
                addresses_of_flats.append(address_for_each_flat)
                
    #creating a dataframe first with all the data obtained from scrapping

    web_scraped_data_df = pd.concat([pd.DataFrame(addresses_of_flats),pd.DataFrame(all_flat_rents_in_the_given_zipcode)],axis = 1)
    web_scraped_data_df.columns = ["Address in that zipcode","Apartment prices"]
    print("\n Actual size of the dataset for default mode obtained by Web scrapping is : ",web_scraped_data_df.shape,"\n\n")
    print("\n Printing Scraped Data for default mode by Web Scrapping \n\n", web_scraped_data_df.head(10))   #printing the first 10 rows that I obtaiend using Web Scrapping.
    web_scraped_data_df.to_csv("dataset/CSV of apartment price in the given zipcode.csv", encoding='utf-8',sep='\t',header = False,index = False)      #creating CSV file with the scrapped data
    
    #API part
    #get zipcodes using API
    #93a7c63ebde45261d9278d756059f9e3, my key for using the website thezipcodes.com.
    list_of_lat_long_values = []
    found_USA = False
    # user_entered_zipcode = input("Enter Zipcode : ")
    # print(user_entered_zipcode,type(user_entered_zipcode))
    URL_search = "https://thezipcodes.com/api/v1/search?zipCode=" + user_entered_zipcode + "&apiKey=93a7c63ebde45261d9278d756059f9e3"   #here you have to take the input zipcode as given by the user.
    # URL_search = "https://thezipcodes.com/api/v1/search?zipCode=90007&apiKey=93a7c63ebde45261d9278d756059f9e3"   #here you have to take the input zipcode as given by the user.
    location_response_json = requests.get(URL_search).json()['location']
    for each_item in location_response_json:
        if "US" in each_item['country']:
            found_USA = True
            list_of_lat_long_values.append((each_item['latitude'],each_item['longitude']))
    if not found_USA:
        print("Zipcode has to be from Los Angeles in USA, retry...")
        
    traffic_accidents_dataframe = pd.read_csv("/Users/soumyarn/USC/Spring_2022/DSCI_510/HWs/HW3/Traffic_Collision_Data_from_2010_to_Present-Copy1.csv")
    df = traffic_accidents_dataframe.copy()
    
    rows_with_same_latitude = traffic_accidents_dataframe[traffic_accidents_dataframe['Location'].str.contains(list_of_lat_long_values[0][0])]
    rows_with_same_longitude = traffic_accidents_dataframe[traffic_accidents_dataframe['Location'].str.contains(list_of_lat_long_values[0][1])]
    dataframe_with_same_lat_long = pd.merge(rows_with_same_latitude,rows_with_same_longitude,how="outer")
    
    geolocator = geopy.Nominatim(user_agent="myApp")          #double checking with coordinates to obtain the most authentic data.
    indices_with_same_zipcodes = []
    for i in range(len(dataframe_with_same_lat_long)):
        if not dataframe_with_same_lat_long.iloc[i]['Location'] or dataframe_with_same_lat_long.iloc[i]['Location'].strip() == "":
            print("No Matching data found! Try with correct zipcode values...")
            break
        else:
            list_of_coordinates = tuple(map(str, dataframe_with_same_lat_long.iloc[i]['Location'].replace("(","").replace(")","").split(',')))    #In the original dataframe ofmPandas, the values inside column 'Location' are stoed as strings so had to first convert them to tuples.
            zipcode_value = get_zipcode(geolocator,list_of_coordinates[0],list_of_coordinates[1])
            if zipcode_value == user_entered_zipcode or user_entered_zipcode in zipcode_value:
                indices_with_same_zipcodes.append(i)
    
    
    #getting the years when the accidents took place

    list_of_accidents_with_years = dataframe_with_same_lat_long.loc[indices_with_same_zipcodes]['Date Occurred'].tolist()
    dict_of_year_and_accidents = {}
    for index,value in enumerate(list_of_accidents_with_years):
        year_extracted = list_of_accidents_with_years[index].split("/")[2]
        if year_extracted not in dict_of_year_and_accidents.keys():
            dict_of_year_and_accidents[year_extracted] = 1
        else:
            dict_of_year_and_accidents[year_extracted] = dict_of_year_and_accidents.get(year_extracted) + 1
    
    dataframe_with_accidents_every_year_for_zip = pd.DataFrame(dict_of_year_and_accidents.values(),index=pd.Index(list(dict_of_year_and_accidents.keys())),columns=["Number of Accidents"])
    print("\n Actual size of the dataset obtained using API for default mode: ",dataframe_with_accidents_every_year_for_zip.shape,"\n\n")
    print("\n Printing data obtained for default mode using API \n\n",dataframe_with_accidents_every_year_for_zip.head(10))
    dataframe_with_accidents_every_year_for_zip.to_csv("dataset/CSV of accidents every year.csv", encoding='utf-8',sep='\t')    #creating CSV file with the API data
    
    #creating final dataset containing the average rent in a given zipcode as well as the total number of accidents there in 10 years.
    final_dataframe_rent_accidents_in_zip = pd.DataFrame([user_entered_zipcode,web_scraped_data_df['Apartment prices'].mean(),sum(dict_of_year_and_accidents.values())]).transpose()
    final_dataframe_rent_accidents_in_zip.columns = ["Zipcode","Average rent","Number of accidents in 10 years"]
    final_dataframe_rent_accidents_in_zip.to_csv("dataset/Final Dataset showing average rent and accidents.csv", encoding='utf-8',sep='\t',index = False)

def scrape_function(user_entered_zipcode):
    #scrape mode
    list_of_tuples_with_given_zipcodes = []
    id_of_apartments = []
    
    #scraping data
    for i in range(1,5):                      #might take a long time in running because the page has to wait for 1 second othetwise it blocks my device's IP.
        content = requests.get('https://losangeles.craigslist.org/search/apa?s = ' + str(i),time.sleep(1))  #https://losangeles.craigslist.org/search/apa?s=120
        soup = BeautifulSoup(content.content, 'html.parser')
        my_anchors = list(soup.find_all("a",{"class": "result-image gallery"}))
        for index,each_anchor_tag in enumerate(my_anchors):
            URL_to_look_for_zipcode = soup.find_all("a",{"class": "result-title"})      #taking set so that a page is not visited twice.
        for each_href in URL_to_look_for_zipcode:
            content_href = requests.get(each_href['href'],time.sleep(1))   #script id="ld_posting_data" type="application/ld+json">
            # print(each_href['href'])
            soup_href = BeautifulSoup(content_href.content, 'html.parser')
            my_script_tags = soup_href.find("script",{"id": "ld_posting_data"})
            if my_script_tags:
                res = json.loads(str(list(my_script_tags)[0]))
                if res and 'address' in list(res.keys()):
                    if res['address']['postalCode'] == user_entered_zipcode:            #use the input zipcode entered by the user.
                        list_of_tuples_with_given_zipcodes.append(each_href['href'])
        print("\n Now Scraping page : ",i,"\n")
        
    #fetching the prices and addresses of these apartments

    all_flat_rents_in_the_given_zipcode = []
    addresses_of_flats = []
    for each_link in list_of_tuples_with_given_zipcodes:
        content = requests.get(each_link,time.sleep(1))   #https://losangeles.craigslist.org/search/apa?s=120
        if content.status_code == 200:
            print("Scraping individual links...")
            soup = BeautifulSoup(content.content, 'html.parser')
            prices_of_apartments = soup.find("span",{"class" : "price"})
            address_of_apartments = soup.find("script",{"id": "ld_posting_data"})
            if prices_of_apartments:
                flat_rent = float(prices_of_apartments.get_text()[1:].replace(",",""))
                all_flat_rents_in_the_given_zipcode.append(flat_rent)
            if address_of_apartments:
                address_for_each_flat = json.loads(str(list(address_of_apartments)[0]))["address"]["streetAddress"]
                addresses_of_flats.append(address_for_each_flat)
                
    #creating a dataframe first with all the data obtained from scrapping

    web_scraped_data_df = pd.concat([pd.DataFrame(addresses_of_flats),pd.DataFrame(all_flat_rents_in_the_given_zipcode)],axis = 1)
    web_scraped_data_df.columns = ["Address in that zipcode","Apartment prices"]
    print("\n Actual size of the dataset obtained using API for scrape mode: ",web_scraped_data_df.shape,"\n\n")
    print("Printing scrapped data for scrape mode by Web Scrapping : \n\n ", web_scraped_data_df.head(10))   #printing the first 10 rows that I obtaiend using Web Scrapping.
    web_scraped_data_df.to_csv("dataset/CSV of apartment price in the given zipcode.csv", encoding='utf-8',sep='\t',header = False,index = False)
    
    
def static_function(path_to_static_data):
    #static mode
    #reading the CSV file of the final dataset that will show the user the average rent in the given zipcode and the number of accidents in that zicode over last 10 years.
    try:
        with open(path_to_static_data, 'r') as f:
            for index, line in enumerate(f):
                print("\n",line,"\n")
    except:
        print("File not yet created... run with default or scrape modes first!")

if __name__ == '__main__': #for your purpose, you can think of this line as the saying "run this chunk of code first"
    # print("Sys.argv",sys.argv)
    if len(sys.argv) == 1: #default mode
        user_entered_zipcode = input("Enter Zipcode : ")
        default_function(user_entered_zipcode)
        # exit()
    elif sys.argv[1] == '--scrape': #scrape mode
        user_entered_zipcode = input("Enter Zipcode : ")
        scrape_function(user_entered_zipcode)
        # exit()
    elif sys.argv[1] == '--static': #static mode
        path_to_static_data = sys.argv[2]
        static_function(path_to_static_data)
        # exit()