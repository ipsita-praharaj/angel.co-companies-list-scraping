import argparse
import os.path
import time

import requests

return requests.get(url).json()

import pandas as pd
import requests
from bs4 import BeautifulSoup

JS = "https://angel.co/company_filters/search_data"
HEADERS = {"X-Requested-With": "XMLHttpRequest",
           "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.75 Safari/537.36"}

BASE_URL = "https://angel.co/companies/startups?ids%5B%5D={}&total={}&page={}&sort=signal&new=false&hexdigest={}"
DF_COLUMNS = ['name', 'desc', 'website', 'location', 'employees', 'raised', 'angel_url', 'angel_id']
CSV_FILENAME = 'all_companies.csv'


def parse_companies(companies):
    df = pd.DataFrame(columns=DF_COLUMNS)
    for idx, company in enumerate(companies):
        if idx % 4 == 0:
            print('{} company'.format(idx))
        name = company.findAll("a", {"class": "startup-link"})[1].text

        description = company.findAll("div", {"class": "pitch"})[0].text.strip('\n')
        if len(description) == 0:
            description = '-'

        company_column = company.findAll("div", {"class": "company column"})[0]
        angel_list_url = company_column.findAll('a', href=True)[0]['href']

        location_tag = company.findAll("div", {"class": "location"})[0]
        location = location_tag.findAll("div", {"class": "value"})[0].text.strip('\n')

        employees_tag = company.findAll("div", {"class": "company_size"})[0]
        employees = employees_tag.findAll("div", {"class": "value"})[0].text.strip('\n')

        raised_tag = company.findAll("div", {"class": "raised"})[0]
        raised = raised_tag.findAll("div", {"class": "value"})[0].text.strip('\n')

        website_tag = company.findAll("div", {"class": "website"})[0]
        a = website_tag.findAll('a', href=True)
        website = '-'
        if len(a) > 0:
            website = a[0]['href']

        angel_id = company.findAll("a", {"class": "startup-link"})[0]['data-id']
        full_company = pd.DataFrame([[name, description, angel_list_url, location,
                                      employees, raised, website, angel_id]], columns=DF_COLUMNS)

        df = df.append(full_company)
    return df


def get_next_pages(search_query='', start_page=1):
    with requests.Session() as s:
        response = s.post(JS, data={"sort": "signal", "page": start_page, 'filter_data[markets][]': search_query},
                          headers=HEADERS)
        params = response.json()
        companies = s.get(BASE_URL.format("&ids%5B%5D=".join(map(str, params["ids"])),
                                          params["page"],
                                          params["total"],
                                          params["hexdigest"]), headers=HEADERS)
        soup = BeautifulSoup(companies.json()["html"], "html.parser")
        companies = soup.findAll(name="div", attrs={"class": "base startup"})
        yield companies

        while True:
            # increment page count from previous.
            page = params["page"] + 1
            params = s.post(JS, data={"sort": "signal", "page": page}, headers=HEADERS).json()

            # keep going until we have reached the maximum queries
            if "ids" not in params:
                break

            companies = s.get(BASE_URL.format("&ids%5B%5D=".join(map(str, params["ids"])),
                                              params["page"],
                                              params["total"],
                                              params["hexdigest"]),
                              headers=HEADERS)
            soup = BeautifulSoup(companies.json()["html"], "html.parser")
            companies = soup.findAll(name="div", attrs={"class": "base startup"})

            # don't hammer with requests
            time.sleep(.3)
            yield companies


def create_csv():
    df = pd.DataFrame(columns=DF_COLUMNS)
    df.to_csv(CSV_FILENAME, index=None)


def add_parsed_companies_to_all(parsed_df):
    if not os.path.isfile(CSV_FILENAME):
        create_csv()

    all_companies = pd.read_csv(CSV_FILENAME, index_col='name')
    parsed_df = parsed_df.set_index('name')
    all_companies = pd.concat([all_companies, parsed_df])
    unique_companies = all_companies.drop_duplicates()
    unique_companies.to_csv(CSV_FILENAME)
    print('data has been written')


def start(query):
    companies = get_next_pages(search_query=query)
    df = pd.DataFrame(columns=DF_COLUMNS)

    for idx, comps in enumerate(companies):
        print('batch index {}'.format(idx))
        parsed_companies = parse_companies(comps)
        df = df.append(parsed_companies)

    add_parsed_companies_to_all(df)


if __name__ == '__main__':
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("-q", "--query", required=False,
                                 help="Search companies with specific market query")

    args = argument_parser.parse_args()
    start(args.query)
