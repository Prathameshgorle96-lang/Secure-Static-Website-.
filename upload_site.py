"""
upload_site.py — Uploads website/ folder to the S3 bucket.
Run: python upload_site.py
"""

import boto3
import json
import os
import mimetypes

WEBSITE_DIR = "website"


def load_config():
    with open("config.json") as f:
        return json.load(f)


def upload_files(bucket_name):
    s3 = boto3.client("s3")
    print(f"Uploading files from '{WEBSITE_DIR}/' to s3://{bucket_name}/\n")

    for root, dirs, files in os.walk(WEBSITE_DIR):
        for filename in files:
            local_path = os.path.join(root, filename)
            s3_key = os.path.relpath(local_path, WEBSITE_DIR)
            content_type, _ = mimetypes.guess_type(local_path)
            content_type = content_type or "application/octet-stream"

            s3.upload_file(
                local_path,
                bucket_name,
                s3_key,
                ExtraArgs={"ContentType": content_type},
            )
            print(f"  Uploaded: {s3_key}  [{content_type}]")

    print(f"\nAll files uploaded successfully.")


def main():
    config = load_config()
    upload_files(config["bucket"])
    print(f"\nVisit: https://{config['domain']}")


if __name__ == "__main__":
    main()
