# hdbits-fetchfree
A tool for automatically fetching new freeleech and featured torrents at hdbits

## Getting Started

### Prerequisites
* Linux / OS X. Windows support will come soon.
* Python 2.7
* lxml
```
pip install lxml
```

### First Run
To run the program, type

	$ python hdbits-fetchfree.py --makeconf

You will need to know your hdbits username, passkey, and where to store the fetched .torrent files


### Additional Options

	hdbits-fetchfree.py [OPTIONS] [FILE]

	-f, --fetch-featured
		Checks the list of upcoming featured torrents and downloads any that are freeleech. High number 
		of API calls. Not recommended to be run more than once every 5 minutes.

	--makeconf
		Generates json.config

	--noverify
		Skips SSL verification for API queries

	-u, --update-featured filename.html
		Processes the "Featured Torrents Queue"	page from hdbits and adds them to a watchlist. Local
		files only. Does not accept URLs to not break rule prohibiting site scraping.

	-v
		Verbose output

	--version
		Shows version number

### Automation

Sample crontab to check new torrents every minute and featured every 5

	* * * * *       /usr/bin/python ~/hdbits-fetchfree/hdbits-fetchfree.py
	*/5 * * * *     /usr/bin/python ~/hdbits-fetchfree/hdbits-fetchfree.py -f

###json.config

json.config is created in the following format:

	{
		"username":"barackobama",
		"passkey":"A1B2C3",
		"output_dir":"~/rtorrent/watchdir/"
	}