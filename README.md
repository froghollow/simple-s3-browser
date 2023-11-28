# SIMPLE S3 Browser
The standard Amazon S3 Console is oriented toward viewing and managing all buckets within a particular IAM Sign-in account.  Granting users S3 Console access in multiple accounts is cumbersome, and fraught with security concerns, when all users need is access to a set of particular subfolders within particular buckets.  This project provides a basic GUI that enables the user to view and manage S3 Objects among multiple buckets which can reside different accounts.

- [s3_browser.ipynb](./s3_browser.ipynb) -- Jupyter Notebook to configure buckets and invoke the GUI application
- [python/batch_simple_2311.py](./python/batch_simple_2311.py) -- Common Python module containing S3 help functions, among other things used by SIMPLE projects.
- [python/simple_s3_gui.py](./python/simple_s3_gui.py) -- Basic GUI implemented using [ipywidgets]( https://ipywidgets.readthedocs.io/en/stable/index.html)
