"""
deploy.py — Creates S3 bucket + CloudFront distribution with OAC.
Run: python deploy.py
"""

import boto3
import json
import uuid
import sys

BUCKET_NAME = "my-secure-static-site-" + str(uuid.uuid4())[:8]
REGION = "us-east-1"


def create_s3_bucket():
    s3 = boto3.client("s3", region_name=REGION)
    print(f"Creating S3 bucket: {BUCKET_NAME}")

    if REGION == "us-east-1":
        s3.create_bucket(Bucket=BUCKET_NAME)
    else:
        s3.create_bucket(
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )

    # Block ALL public access
    s3.put_public_access_block(
        Bucket=BUCKET_NAME,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    print("  Public access blocked on bucket.")
    return BUCKET_NAME


def create_oac(cf_client):
    print("Creating Origin Access Control (OAC)...")
    response = cf_client.create_origin_access_control(
        OriginAccessControlConfig={
            "Name": f"OAC-{BUCKET_NAME}",
            "Description": "OAC for secure S3 access",
            "SigningProtocol": "sigv4",
            "SigningBehavior": "always",
            "OriginAccessControlOriginType": "s3",
        }
    )
    oac_id = response["OriginAccessControl"]["Id"]
    print(f"  OAC created: {oac_id}")
    return oac_id


def create_cloudfront_distribution(bucket_name, oac_id):
    cf = boto3.client("cloudfront", region_name="us-east-1")
    origin_domain = f"{bucket_name}.s3.{REGION}.amazonaws.com"
    print(f"Creating CloudFront distribution for origin: {origin_domain}")

    response = cf.create_distribution(
        DistributionConfig={
            "CallerReference": str(uuid.uuid4()),
            "Comment": "Secure static website",
            "DefaultRootObject": "index.html",
            "Origins": {
                "Quantity": 1,
                "Items": [
                    {
                        "Id": "S3Origin",
                        "DomainName": origin_domain,
                        "S3OriginConfig": {"OriginAccessIdentity": ""},
                        "OriginAccessControlId": oac_id,
                    }
                ],
            },
            "DefaultCacheBehavior": {
                "TargetOriginId": "S3Origin",
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]},
                "ForwardedValues": {
                    "QueryString": False,
                    "Cookies": {"Forward": "none"},
                },
                "MinTTL": 0,
                "DefaultTTL": 86400,
                "MaxTTL": 31536000,
            },
            "CustomErrorResponses": {
                "Quantity": 1,
                "Items": [
                    {
                        "ErrorCode": 403,
                        "ResponsePagePath": "/error.html",
                        "ResponseCode": "404",
                        "ErrorCachingMinTTL": 300,
                    }
                ],
            },
            "Enabled": True,
            "HttpVersion": "http2",
            "PriceClass": "PriceClass_100",
        }
    )

    dist = response["Distribution"]
    dist_id = dist["Id"]
    domain = dist["DomainName"]
    print(f"  CloudFront distribution created: {dist_id}")
    print(f"  Domain: https://{domain}")
    return dist_id, domain


def attach_bucket_policy(bucket_name, dist_id):
    s3 = boto3.client("s3", region_name=REGION)
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCloudFrontOAC",
                "Effect": "Allow",
                "Principal": {"Service": "cloudfront.amazonaws.com"},
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
                "Condition": {
                    "StringEquals": {
                        "AWS:SourceArn": f"arn:aws:cloudfront::{account_id}:distribution/{dist_id}"
                    }
                },
            }
        ],
    }
    s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
    print("  Bucket policy attached — only CloudFront can read objects.")


def save_config(bucket_name, dist_id, domain):
    config = {"bucket": bucket_name, "distribution_id": dist_id, "domain": domain}
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
    print("  Saved config.json for use by other scripts.")


def main():
    print("=== Deploying Secure Static Website on AWS ===\n")
    try:
        bucket = create_s3_bucket()
        cf = boto3.client("cloudfront", region_name="us-east-1")
        oac_id = create_oac(cf)
        dist_id, domain = create_cloudfront_distribution(bucket, oac_id)
        attach_bucket_policy(bucket, dist_id)
        save_config(bucket, dist_id, domain)
        print(f"\nDeployment complete!")
        print(f"  Bucket : {bucket}")
        print(f"  Website: https://{domain}")
        print(f"\nNote: CloudFront takes ~10-15 min to deploy globally.")
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
