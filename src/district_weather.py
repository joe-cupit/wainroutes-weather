import json
import requests
from bs4 import BeautifulSoup, Tag

import os
from dotenv import load_dotenv
load_dotenv()

import logging
log = logging.getLogger(__name__)


def scrape_met_site(save_local=False):
  log.info("Starting Met Office weather scrape")
  response = requests.get(os.environ["MET_OFFICE_WEATHER_URL"])
  if response.status_code != 200:
    log.error(f"Failed to retrieve data. Status code: {response.status_code}")
    return

  soup = BeautifulSoup(response.content, "html.parser")
  scraped = scrape_soup(soup)

  if save_local:
    with open("weather.json", "w") as f:
      json.dump(scraped, f)

  log.info("Finished souping")
  return scraped


def scrape_soup(soup: BeautifulSoup):
  weather_data = dict()

  weather_data["update_time"] = soup.find(class_="issue-time").find("time").text.strip()
  weather_data["confidence"] = soup.find(class_="confidence").find("p").text.strip()

  days = []
  for day_n in ["day0", "day1", "day2", "day3"]:
    day = soup.find(id=day_n)
    if day:
      days.append(scrape_day(day))
  weather_data["days"] = days

  return weather_data


def get_suntime(suntime: Tag):
  return {
    "sunrise": suntime[0].find("time").text.strip(),
    "sunset": suntime[1].find("time").text.strip()
  }


def get_p_text_by_class(tag: Tag, class_name: str):
  return " ".join(tag.find(class_=class_name).find("p").text.strip().split())


def get_temperature_data(tag: Tag, class_name: str):
  temperature_data = dict()
  for li in tag.find(class_=class_name).find("ul").find_all("li"):
    li_title = li.find("span").text.strip()
    temperature_data[li_title] = li.text.replace(li_title, "").strip()

  return temperature_data


def scrape_day_forecast(forecast: Tag):
  weather_table = forecast.find(class_="weather-table").find("table")
  times = [t.text.strip() for t in weather_table.find("thead").find("tr").find_all("th")[1:]]

  weather_data = weather_table.find("tbody").find_all("tr")
  weather_types = [d.find("img")["alt"] for d in weather_data[0].find_all("td")]
  precip_chances = [d.text.strip() for d in weather_data[1].find_all("td")]


  wind_table = forecast.find(class_="wind-table").find("table")
  wind_row = [w for w in wind_table.find("tbody").find("tr").find_all("td")]
  wind_speeds = [w.find(class_="speed").text.strip() for w in wind_row]
  wind_dirs = [w.find("span")["data-value"] for w in wind_row]

  gust_table = forecast.find(class_="wind-gust-table").find("table")
  wind_gusts = [w.text.strip() for w in gust_table.find("tbody").find("tr").find_all("td")]


  temp_table = forecast.find(class_="temperature-table").find("table")
  temps = [t["data-temp"] for t in temp_table.find("tbody").find("tr").find_all("td")]

  temp_table = forecast.find(class_="feels-temperature-table").find("table")
  temp_feels = [t["data-temp"] for t in temp_table.find("tbody").find("tr").find_all("td")]


  return {
    "time": times,
    "type": weather_types,
    "precip": precip_chances,
    "wind_speed": wind_speeds,
    "wind_gust": wind_gusts,
    "wind_dir": wind_dirs,
    "temp": temps,
    "feel_temp": temp_feels
  }


def scrape_hazard_level(hazard_details: Tag):
  hazards = [hazard.text.strip() for hazard in hazard_details.find_all(class_="hazard-header")]
  hazards_desc = [desc.text.strip().replace("\u00e2\u20ac\u02dc", "'").replace("\u00e2\u20ac\u2122", "'") for desc in hazard_details.find_all(class_="hazard-description")]
  return {hazards[i]: hazards_desc[i] for i in range(len(hazards))}

def scrape_hazards(mountain_hazard: Tag):
  hazard_accordian = mountain_hazard.find(id="accordion-group")

  levels = [level.text.split()[0].strip().lower() for level in hazard_accordian.find_all(class_="accordion-header")]
  hazard_details = [details for details in hazard_accordian.find_all(class_="accordion-panel")]

  return {levels[i]: scrape_hazard_level(hazard_details[i]) for i in range(len(levels))}


def scrape_day(day: Tag):
  day_weather = dict()

  day_classes = [c for c in day["class"] if c not in ["tab-content", "no-js-block"]]
  day_type = day_classes[-1] if len(day_classes) > 0 else "current-day"
  day_weather["type"] = day_type

  if day_type != "further-outlook":
    if day_type != "this-evening":
      day_weather["date"] = day["data-content-id"]
    day_weather = day_weather | get_suntime(day.find_all(class_="sunrise-sunset"))


  if day_type == "current-day":

    hazard_details = day.find(class_="mountain-hazard")
    if hazard_details:
      day_weather["hazards"] = scrape_hazards(hazard_details)

    day_details = day.find(class_="mountain-additional-info")

    day_weather["meteorologist_view"] = get_p_text_by_class(day_details, "meteorologist-view")
    day_weather["summary"] = get_p_text_by_class(day_details, "weather")
    day_weather["cloud_free_top"] = get_p_text_by_class(day_details, "cloud-free-top")
    day_weather["visibility"] = get_p_text_by_class(day_details, "visibility")
    day_weather["ground_conditions"] = get_p_text_by_class(day_details, "ground-conditions")

    day_forecast = day.find(class_="mountain-forecast")
    day_weather["weather"] = day_forecast.find(class_="weather-forecast").find("p").text.strip()
    day_weather["forecast"] = scrape_day_forecast(day_forecast)

  elif day_type == "tomorrows-tab":
    day_details = day.find(class_="mountain-additional-info")

    day_weather["summary"] = get_p_text_by_class(day_details, "weather")
    day_weather["cloud_free_top"] = get_p_text_by_class(day_details, "cloud-free-top")
    day_weather["max_wind"] = get_p_text_by_class(day_details, "max-wind")
    day_weather["temperature"] = get_temperature_data(day_details, "temperature")
    day_weather["visibility"] = get_p_text_by_class(day_details, "visibility")

  elif day_type == "this-evening":
    day_weather["summary"] = day.find(class_="evening-summary").find("p").text.strip()

  elif day_type == "further-outlook":
    outlook_list = []
    for outlook in day.find_all(class_="outlook-day"):
      outlook_list.append({"date": outlook.find("h4").text.strip()} | get_suntime(outlook.find_all(class_="sunrise-sunset")) | {"summary": outlook.find("p").text.strip()})
    day_weather["days"] = outlook_list

  return day_weather


if __name__ == "__main__":
  scrape_met_site(save_local=True)
