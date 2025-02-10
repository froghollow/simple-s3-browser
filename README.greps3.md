# greps3.py

[**greps3.py**](https://github.com/froghollow/simple-s3-browser/blob/main/python/grepS3.py), a python utility that can be run from the command line, operates like grep on S3 objects without needing to download them.

### Usage:
 `python grepS3.py {search_term} {S3_prefix} {S3_filter}`
-   arguments: 
    -   `{search_term}` = sys.argv[1]   # regular expression to search for within files, or `--listonly` to list S3 file names without searching contents
    -   `{s3_prefix}`   = sys.argv[2]   # S3 folder/key prefix to select files
    -   `{s3_filter}`   = sys.argv[3]   # (optional) regular expression to filter file selection 

You can set environment variables for the Cross-Account Role ARN, and for a default bucket so you don’t need to include it in the S3_folder spec.
                                                
Windows:<br>
    `PS> $env:GREPS3_ROLEARN = arn:aws-us-gov:iam::{account_id}:role\{role_name}`<br>
    `PS> $env:GREPS3_BUCKET  = {bucket_name}`

Unix:<br>
    `export GREPS3_ROLEARN = arn:aws-us-gov:iam::{account_id}:role\{role_name}`<br>
    `export GREPS3_BUCKET  = ‘wc2h-dtl-prd-landing-pad’`


### Examples:

1.  Search for all filenames having the S3 prefix<br>
`python grepS3.py --listonly s3://my-landing-pad-bucket/SYS/FOLDER/INFILE.BADADR`

2.  Search for lines that contain 'AUG-22' within all files having the S3 prefix<br>
`python grepS3.py AUG-22 s3://my-landing-pad-bucket/SYS/FOLDER/INFILE.BADADR`

3.  Search for lines that contain 'AUG-22' within all files having the S3 prefix and D2408 (month of Aug 2024) somewhere in the filename<br>
`python grepS3.py AUG-22 s3://my-landing-pad-bucket/SYS/FOLDER/INFILE.BADADR D2408`

The `--listonly` option uses less overhead, so it is a good way to narrow down the set of objects to be grepped.  It can still take a few minutes to comb thru Thousands of files.

