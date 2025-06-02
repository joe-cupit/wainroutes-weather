import boto3
from botocore.client import Config
from io import BytesIO
import json

import os
from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s (%(name)s) : %(message)s")
log = logging.getLogger(__name__)

from src.district_weather import scrape_met_site
from src.point_weather import request_weather_points


if __name__ == "__main__":

  log.info("Initialising boto3 client")
  r2_client = boto3.client(
    's3',
    region_name='auto',
    endpoint_url=os.environ["R2_ENDPOINT_URL"],
    aws_access_key_id=os.environ["R2_ACCESS_KEY"],
    aws_secret_access_key=os.environ["R2_SECRET_KEY"],
    config=Config(signature_version='s3v4')
  )

  log.info("Starting the Lake District Weather retreival")
  weather = scrape_met_site()
  weather_points = request_weather_points()
  log.info("Finished the Lake District Weather retreival")

  try:
    log.info("Converting data and uploading to R2 Bucket")
    if weather_points:
      json_bytes = json.dumps(weather).encode("utf-8")
      json_file_obj = BytesIO(json_bytes)
      r2_client.upload_fileobj(json_file_obj, os.environ["R2_BUCKET_NAME"], "weather.json")
      log.info("Successfully uploaded weather.json to R2 Bucket")
    else:
      log.warning("No weather object to upload")
  except Exception as e:
    log.error("Failed to upload weather.json to R2 Bucket")

  try:
    if weather_points:
      json_bytes = json.dumps(weather_points).encode("utf-8")
      json_file_obj = BytesIO(json_bytes)
      r2_client.upload_fileobj(json_file_obj, os.environ["R2_BUCKET_NAME"], "weather_points.json")
      log.info("Successfully uploaded weather_points.json to R2 Bucket")
    else:
      log.warning("No weather_points object to upload")
  except Exception as e:
    log.error("Failed to upload weather_points.json to R2 Bucket")
