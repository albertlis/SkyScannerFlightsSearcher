import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pprint import pprint

import requests

FILTER_DIRECT = True
URL = "https://partners.api.skyscanner.net/apiservices/v3/flights/indicative/search"
HEADERS = {'x-api-key': 'sh428739766321522266746152871799'}


def get_place_from_id(id: str, places: dict) -> str:
    place = places[id]
    if 'AIRPORT' in place['type']:
        return place['name']
    return f"{place['name']}_{place['type']}"


def check_flights_from_date(year: int, month: int, day: int, origin_airport: str) -> list:
    body = {
        'query': {
            'currency': 'PLN',
            'locale': 'pl-PL',
            'market': 'PL',
            # 'dateTimeGroupingType': 'DATE_TIME_GROUPING_TYPE_BY_DATE',
            'queryLegs': [
                {
                    'originPlace': {
                        'queryPlace': {
                            'iata': origin_airport,
                        },
                    },
                    'destinationPlace': {
                        'anywhere': True,
                    },
                    "fixedDate": {
                        "year": year,
                        "month": month,
                        "day": day

                    },
                },
            ],
        },
    }

    response = requests.post(URL, headers=HEADERS, json=body)
    response = response.json()['content']['results']

    if FILTER_DIRECT:
        response['quotes'] = {k: v for k, v in response['quotes'].items() if v['isDirect']}

    flights = []
    for flight_info in response['quotes'].values():
        assert flight_info['minPrice']['unit'] == 'PRICE_UNIT_WHOLE'
        flights.append(
            dict(
                price=int(flight_info['minPrice']['amount']),
                origin_place=get_place_from_id(flight_info['outboundLeg']['originPlaceId'], response['places']),
                destination_place=get_place_from_id(flight_info['outboundLeg']['destinationPlaceId'],
                                                    response['places']),
                when=flight_info['outboundLeg']['departureDateTime'],
            )
        )
    return flights


def all_weekday_dates_in_year(year: int, weekday: int = 4, month: int = 1, day: int = 1) -> list[datetime.date]:
    # January 1st of the given year
    date = datetime.date(year, month, day)

    # Find the first Saturday of the year
    while date.weekday() != weekday:  # Saturday is represented by 5
        date += datetime.timedelta(days=1)

    # Loop through the Saturdays and print them
    dates = []
    while date.year == year:
        dates.append(date)
        date += datetime.timedelta(weeks=1)
    return dates


current_date = datetime.date.today()
# Call the function for the year 2023
all_fridays = all_weekday_dates_in_year(2023, weekday=4, month=current_date.month, day=current_date.day)
all_saturdays = all_weekday_dates_in_year(2023, weekday=5, month=current_date.month, day=current_date.day)
all_dates = [*all_fridays, *all_saturdays]

all_flights = []
with ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(check_flights_from_date, f_date.year, f_date.month, f_date.day, origin)
        for f_date in all_dates for origin in ['WRO', 'POZ']
    ]
    for future in as_completed(futures):
        all_flights.extend(future.result())

pprint(all_flights)
