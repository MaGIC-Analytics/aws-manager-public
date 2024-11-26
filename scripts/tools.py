import boto3, hashlib, os, csv, sys, base64
from pathlib import Path
from datetime import datetime

opts = open('./.aws/credentials','r')
opts = opts.readlines()

key_id = str(opts[0].replace('\n','').split("=")[1].strip("'").strip(" "))
secret_id = str(opts[1].replace('\n','').split("=")[1].strip("'").strip(" "))

slack_channel = str(opts[4].replace('\n','').split("=")[1].strip("'").strip(" "))
slack_token_id = str(opts[5].replace('\n','').split("=")[1].strip("'").strip(" "))

s3 = boto3.client(
    's3',
    aws_access_key_id=key_id,
    aws_secret_access_key=secret_id
)

def uploader(bucket_name, source_file_name, destination_file_name, content_md5):
    print(bucket_name, destination_file_name, content_md5)
    try:
        # Step 1: Initiate multipart upload
        response = s3.create_multipart_upload(
            Bucket=bucket_name,
            Key=destination_file_name,
            ContentType='application/octet-stream'
        )
        upload_id = response['UploadId']
        part_number = 1
        parts = []
        upmd5 = []

        # Step 2: Upload parts
        with open(source_file_name, 'rb') as file:
            while True:
                data = file.read(800 * 1024 * 1024)  # Read 800 MB chunks
                if not data:
                    break
                part_md5 = hashlib.md5(data).digest()
                upmd5.append(hashlib.md5(data))
                response = s3.upload_part(
                    Bucket=bucket_name,
                    Key=destination_file_name,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=data,
                    ContentMD5=base64.b64encode(part_md5).decode('utf-8')
                )
                parts.append({'PartNumber': part_number, 'ETag': response['ETag']})
                part_number += 1

        # Step 3: Complete multipart upload
        s3.complete_multipart_upload(
            Bucket=bucket_name,
            Key=destination_file_name,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )

        print("Multipart upload completed successfully.")
    except Exception as error:
        print("Error during multipart upload:", error)
        s3.abort_multipart_upload(
            Bucket=bucket_name,
            Key=destination_file_name,
            UploadId=upload_id
        )

    md5_pull = s3.head_object(Bucket=bucket_name, Key=destination_file_name)
    server_md5 = md5_pull['ETag'][1:-1]

    if len(upmd5) < 1:
        print('{}'.format(hashlib.md5().hexdigest()))

    if len(upmd5) == 1:
        print('{}'.format(upmd5[0].hexdigest()))

    digests = b''.join(m.digest() for m in upmd5)
    digests_md5 = hashlib.md5(digests)
    #Need the hash of the hash to compute back to AWS hash
    digested_md5='{}-{}'.format(digests_md5.hexdigest(), len(upmd5))
    print(digested_md5)

    print(server_md5)

    if digested_md5 == server_md5:
        outstring = "MD5 Checksums match for {} after upload.".format(str(destination_file_name))
        print(outstring)
        return outstring
    else:
        outstring = "MD5 Checksums ERROR for {} after upload.".format(str(destination_file_name))
        print(outstring)
        return outstring

def calculate_md5(file_path):
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(800 * 1024 * 1024), b''):
            md5.update(chunk)
    md5s = [base64.b64encode(md5.digest()).decode('utf-8'), md5.hexdigest()]
    return md5s

def downloader(bucket_name, sub_bucket, download_dir):
    objects = s3.list_objects(Bucket=bucket_name, Prefix=sub_bucket)['Contents']
    log_path = "DownloadLog"+datetime.today().strftime('%Y-%m-%d')+'.txt'
    with open(log_path, 'w') as f:
        for obj in objects:
            key=obj['Key']
            download_path = os.path.join(download_dir, key)        
            download_path_dir = download_path.split('/')[:-1]
            download_path_dir = "/".join(download_path_dir)
            try:
                os.makedirs(download_path_dir, exist_ok=True)
            except:
                pass
            s3.download_file(bucket_name, key, download_path)

            md5_pull = s3.head_object(Bucket=bucket_name, Key=key)
            server_md5 = md5_pull['ETag'][1:-1]
            content_md5 = calculate_md5(download_path)
            if content_md5[1] == server_md5:
                outstring = "MD5 Checksums match for {} after download.".format(str(download_path))
                print(outstring)
                f.write(outstring)
                f.write('\n')
            else:
                outstring = "MD5 Checksums ERROR for {} after download.".format(str(download_path))
                f.write(outstring)
                f.write('\n')
                print(outstring)
        f.close()
    return(log_path)
def get_bucket_size(bucket_name,bucket_prefix):
    total_size = 0
    # Get a list of all sub-buckets
    s3buck = boto3.resource('s3', aws_access_key_id=key_id, aws_secret_access_key=secret_id)
    bucket=s3buck.Bucket(bucket_name)
    resp = bucket.meta.client.list_objects(Bucket=bucket_name, Prefix=bucket_prefix, Delimiter='/')
    subs = [x['Prefix'] for x in resp['CommonPrefixes']]

    csv_path="Report"+datetime.today().strftime('%Y-%m-%d')+'.csv'

    with open(csv_path, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["Subdirectory","Size (GB)","Cost per month (Dollars USD)"])
        writer.writeheader()

        for sub_bucket in subs:
            # List all objects in the sub-bucket
            objects = s3.list_objects_v2(Bucket=bucket_name, Prefix=sub_bucket)['Contents'] #Adding delimiter here causes it to abort. 

            # Calculate the total size of objects in the sub-bucket
            sub_bucket_size = sum(obj['Size'] for obj in objects)
            total_size += sub_bucket_size

            #Convert to GB
            gb_size = sub_bucket_size / 1000000000
            
            #Calculate cost based on AWS costs
            cost = (gb_size * 0.023) + (gb_size * 0.0036) + 5
            row = {"Subdirectory":sub_bucket, "Size (GB)":gb_size, "Cost per month (Dollars USD)":cost}
            writer.writerow(row)

    print("Total Size of all sub-buckets: {} bytes".format(total_size))
    return(csv_path)

import smtplib
import sys,os
import requests
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
     
def slacker(title, body, file_path):
    attachment = open(file_path, "rb")

    slack_channel_id = slack_channel
    slack_token = slack_token_id
    slack_client = WebClient(token=slack_token)

    file_size=os.path.getsize(file_path)
    if file_size==0:
        print('File is empty due to no upload')
        slack_webhook_url='https://hooks.slack.com/services/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'

        payload = {
            "text": body+' upload was completed- nothing to upload at this time',
        }

        response = requests.post(slack_webhook_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'})

        if response.status_code == 200:
            print("Message sent successfully")
        else:
            print(f"Failed to send message. Status code: {response.status_code}")
    
    else:
        # Step 1/4: Get the URL to upload to.
        url_for_uploading = slack_client.files_getUploadURLExternal(
            token=slack_token,
            filename=file_path,
            length=file_size,
        )

        if url_for_uploading["ok"]:
            for item in url_for_uploading:
                print(f"{item}")
        else:
            raise ValueError(
                f"Failed to get the URL for uploading the attachment to Slack Response: {url_for_uploading}"
            )

        # Step 2/4: Upload the file to the URL.
        payload = {
            "filename": file_path,
            "token": slack_token,
        }
        response = requests.post(
            url_for_uploading["upload_url"], params=payload, data=attachment
        )

        if response.status_code == 200:
            print(
                f"Response from Slack: {response.status_code}, {response.text}"
            )
        else:
            raise ValueError(
                f"Response from Slack: {response.status_code}, {response.text}, {response.headers}"
            )

        file_id = url_for_uploading["file_id"]

        # Step 3/4: Make the file accessible in the channel.
        slack_client.files_completeUploadExternal(
            token=slack_token,
            files=[{"id": file_id, "title": file_path}],
            channel_id=slack_channel_id,
            initial_comment=None,
            thread_ts=None,
        )

        attachment_with_slack_url = {
            "title": file_path,
            "image_url": url_for_uploading["upload_url"],
        }

        # Step 4/4: Send the message to the specified Slack channel.
        response = slack_client.chat_postMessage(
            channel=slack_channel_id,
            text=body,
            attachments=[attachment_with_slack_url],
        )

        # Check if message sending was successful.
        if response.status_code != 200:
            raise ValueError(
                f"Failed to send the message to Slack! Status code returned from the Slack API: {response.status_code}"
            )