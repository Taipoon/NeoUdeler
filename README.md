# NeoUdeler | Udemy Course Downloader (CUI)

Command-line video downloader for Udemy Business, porting only the download functionality of FaisalUmair/udemy-downloader-gui.

## This project is WORK IN PROGRESS

We welcome pull requests and issues for errors, 
defects and any other concerns to improve the quality of NeoUdeler.

# Precautions for Use

As of 2023, Udemy has begun implementing DRM protection on various contents.

NeoUdeler downloads only the subscribed courses based on the user's authentication credentials, via the sources that Udemy makes available to the user. (After being properly authenticated by Udemy, you can perform the same operation manually using a web browser. NeoUdeler simply automates this process.)
Therefore, content from private storage and DRM-protected content cannot be downloaded.

NeoUdeler does not illegally download paid courses available on Udemy.
When using this software, it is required that NeoUdeler complies with Udemy's terms of use.

# Disclaimer

- This software is intended for the purpose of downloading Udemy courses for personal use only.
- Sharing the content of subscribed courses is strictly prohibited under Udemy's terms of use.
- **All courses on Udemy are subject to copyright infringement.**
- NeoUdeler and the developers cannot be held responsible for any damages resulting from the use of this software.
- By using NeoUdeler, you agree to this disclaimer.

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
