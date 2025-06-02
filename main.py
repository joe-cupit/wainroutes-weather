from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

from src.district_weather import scrape_met_site
from src.point_weather import request_weather_points


if __name__ == "__main__":
  log.info("Starting the Lake District Weather retreival")
  scrape_met_site()
  request_weather_points()
  log.info("Finished the Lake District Weather retreival")
