# aws-manager
# Docker container to manage AWS S3 storage and send messages during workflows
[![run with docker](https://img.shields.io/badge/run%20with-docker-0db7ed?labelColor=000000&logo=docker)](https://www.docker.com/)
[![run with singularity](https://img.shields.io/badge/run%20with-singularity-1d355c.svg?labelColor=000000)](https://sylabs.io/docs/)

This project is a containerized environment for managing files on the MaGIC AWS genomics archive. Each function is meant for minimal access operations, and no delete will be provided. Use this to upload data to the archive either manually or from the isilon storage, download data if not using Globus, and run reports for billing purposes. 

## Credentials
To properly run this workflow you would need to apply your respective credentials. In our case, we have a .aws directory and a credentials file within and should contain the following lines (excluding the -)
- aws_access_key_id = myACCESSkey
- aws_secret_access_key = mySECRETkey
- region = us-east-1
- slack_channel_id = slackCHANNELid
- slack_token = slackBOTtoken

## Messaging
All messaging within this application are default set to send notifications via Slack. In our case we set up a bot to send job notifications as well as upload/attach log files. We originally had email (some code might be a little legacy as I clean it up from that), but the newest wave of 2FA made that untenable. 

## Example functions
Some examples to help assist in remembering what the heck to do here.

### Uploading
There are several options for uploading. Since this is operating within docker, you would need to appropriately serve the volumes to the container and then define the path. In general:
```bash
docker run -v $local_dir:$container_dir alemenze/magic-aws-manager -m Upload -u $container_dir
```

If you want to run it for default through the genomics data archive you can do:
```bash
docker run -v $local_dir:/media/xdrive/GENOMICS_DATA_ARCHIVE alemenze/magic-aws-manager -m Upload
```
In this case $local_dir should be where it is mounted, by default should be /media/xdrive/GENOMICS_DATA_ARCHIVE

You also can include the clean flag, to delete the files after they have been successfully uploaded. 
```bash
docker run -v $local_dir:/media/xdrive/GENOMICS_DATA_ARCHIVE alemenze/magic-aws-manager -m Upload -c
```

### Download
Downloading in most cases should be handled via Globus using the S3 connector. If that is not functioning correctly, you can use as below. 
```bash
docker run -v $local_dir:/Download alemenze/magic-aws-manager -m Download -d /Download -b "$AWS_bucket_prefix"
```

### Report
To generate a quick report for billing purposes you can use the functions below. The first will generate the full billing report, split by PI as the archive is structured. 
```bash
docker run alemenze/magic-aws-manager -m Report
```

The second option will allow you to select a specific sub-object prefix to take it down layers if PIs are ever questioning subsets of their data. 
```bash
docker run alemenze/magic-aws-manager -m Report -r "$AWS_bucket_prefix"
```