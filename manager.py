import sys, glob, os
import argparse
from datetime import datetime
#need to then change cwd to the local directory if calling from elsewhere
scriptPath = os.path.realpath(os.path.dirname(sys.argv[0]))
os.chdir(scriptPath)
sys.path.append('./scripts/')
import tools

parser = argparse.ArgumentParser(description='Tool for accessing Genomics Data Archive information for MaGIC')
parser.add_argument('-m','--method',choices=['Upload','Download','Report'],help='Select which tool to use. Options: Upload, Download, or Report', required=True)
parser.add_argument('-u','--upload_dir', help='Path to upload directory. This should be "GENOMICS_DATA_ARCHIVE", and will default to this if nothing else added.')
parser.add_argument('-c', '--clean_upload', help='Add this command to delete what is being uploaded after the upload is completed.', action=argparse.BooleanOptionalAction, default=False)
parser.add_argument('-d','--download_dir', help='Path to the download directory. Required for download')
parser.add_argument('-b','--download_bucket', help='Bucket prefix for download. Required for download.')
parser.add_argument('-r','--report_subbucket', help='Bucket prefix for report generation. Defaults to full Archive')

args=parser.parse_args()

def upload(dir_start, delete):
    log_path = "UploadLog"+datetime.today().strftime('%Y-%m-%d')+'.txt'
    with open(log_path, 'w') as fileout:
        for dirpath, dirnames, filenames in os.walk(dir_start,topdown=True):
            for f in filenames:
                sname=os.path.join(dirpath,f)
                md5_check=tools.calculate_md5(sname)
                if args.upload_dir is not None:
                    aname=sname.lstrip('/')
                else:
                    aname=sname.split('GENOMICS_DATA_ARCHIVE')[1].lstrip('/')
                status=tools.uploader('genomics-archival-storage',sname, aname, md5_check)
                fileout.write(status)
                fileout.write('\n')
                #Once the file has been uploaded it should be removed from local
                if "ERROR" in status:
                    print('Failure upload')
                else:
                    print('Success up')
                    if delete == True:
                        os.remove(os.path.join(dirpath, f))                   
        fileout.close()
    body='Please see the attached report for the Upload to Genomics Archival Storage on AWS. This should be a log file containing the matchups of MD5 checksums between the AWS tag and local checks. Search key ERROR for any errors.'
    tools.slacker("MaGIC Upload Report for "+ datetime.today().strftime('%Y-%m-%d'), body, log_path)

def download(target_bucket, prefix_path, down_dir):
    status=tools.downloader(target_bucket, prefix_path, down_dir)
    body='Please see the attached report for the Download from Genomics Archival Storage on AWS. This should be a log file containing the matchups of MD5 checksums between the AWS tag and local checks. Search key ERROR for any errors.'
    tools.slacker("MaGIC Download Report for "+ datetime.today().strftime('%Y-%m-%d'), body, status)
  
def report():
    if args.report_subbucket is None or len(args.report_subbucket)==0:
        bucket_prefix = ''
        body='Please see the attached report for the Genomics Archival Storage on AWS. This table should contain the individual subdirectories and summed file size per each.'
    else:
        bucket_prefix = args.report_subbucket
        body='Please see the attached report for the Genomics Archival Storage on AWS. This table should contain the individual subdirectories of '+str(bucket_prefix)+ ' and summed file size per each.'

    report_path=tools.get_bucket_size("genomics-archival-storage",bucket_prefix)
    
    tools.slacker("MaGIC Storage Report for "+ datetime.today().strftime('%Y-%m-%d'), body, report_path)

if args.method == 'Upload':
    if args.upload_dir is not None:
        print(os.path.abspath(str(args.upload_dir)))
        upload_dir = os.path.abspath(args.upload_dir)
        print(upload_dir)
    else:
        upload_dir = os.path.abspath('/media/xdrive/GENOMICS_DATA_ARCHIVE')
    upload(upload_dir, args.clean_upload)
    
if args.method == 'Download':
    if args.download_dir is not None:
        if args.download_bucket is not None:
            download("genomics-archival-storage",args.download_bucket, args.download_dir)
    else:
        print('Something is wrong with your path or bucket')

if args.method == 'Report':
    report()