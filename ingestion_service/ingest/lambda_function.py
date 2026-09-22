import boto3
from process_data import clean_data   # hàm Python có sẵn của bạn

s3 = boto3.client("s3")

def lambda_handler(event, context):
    bucket, raw_key, job_id = event["bucket"], event["rawKey"], event["jobId"]

    splitted_raw_key = raw_key.split("/")
    filename = splitted_raw_key[len(splitted_raw_key)-1]
    local_in, local_out = "/tmp/in", "/tmp/out"

    s3.download_file(bucket, raw_key, local_in)
    rows = clean_data(local_in, local_out)            # hàm của bạn
    cleaned_key = f"cleaned/{job_id}/{filename}"
    s3.upload_file(local_out, bucket, cleaned_key)

    return {"jobId": job_id, "bucket": bucket, "cleanedKey": cleaned_key, "rows": rows}