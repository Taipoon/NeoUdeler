# NeoUdeler | Udemy Course Downloader (CUI)

Command-line video downloader for Udemy Business, porting only the download functionality of FaisalUmair/udemy-downloader-gui.

## This project is WORK IN PROGRESS

We welcome pull requests and issues for errors, 
defects and any other concerns to improve the quality of NeoUdeler.

# Requirements for running NeoUdeler

- python 3.11 or higher

# How to set up

### Clone of this project

```shell
git clone git@github.com:Taipoon/NeoUdeler.git
```

### Move to project directory

```shell
cd /path/to/NeoUdeler
```

### Install dependencies

```shell
pip install -r requirements.txt
```

### Creating .env 

```shell
cp .env.example .env
```

### Entering authentication information

```dotenv
# Sub domain of your organization for Udemy Business (default 'www')

# For example,
# "abc" if you are using Udemy Business with the URL "https://abc.udemy.com/".
SUB_DOMAIN='www'

# Your mail address for udemy business
UDEMY_EMAIL='YOUR EMAIL HERE'

# Udemy Business login password
UDEMY_PASSWORD='YOUR PASSWORD HERE'

# Udemy API Access Token
# Set if an access token can already be specified.
# If you do not know your access token, DO NOT WORRY.
# Because NeoUdeler will automatically set the value
# when you authenticate to Udemy with the values UDEMY_EMAIL, UDEMY_PASSWORD.
ACCESS_TOKEN=
```

### Running the Python file

```shell
python main.py
```
