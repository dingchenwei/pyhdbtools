# pyhdbtools
A tool for interacting with the hdbits api and downloading torrents

## Getting Started

### Prerequisites
* Linux, OS X, Windows
* Python 2.7
* Python packages: lxml, requests 
```
pip install lxml requests
```

### First Run
To run the program, type

	$ python pyhdbtools.py --makeconf

You will need to know your hdbits username, passkey, and where to store the fetched .torrent files

### Fetching featured torrents

To auto fetch featured torrents you must first save a copy of the [featured queue](https://hdbits.org/featuredqueue.php) as an html file,
then feed that into the program. This is required as the site forbids tools scraping the site. Once you
have saved the file, you can run the following command to add all of the upcoming featured torrents to 
the watchlist.

	$ python pyhdbtools.py --update-featured featuredqueue.html

You can then tell the app to check the upcoming queue to see if any of them are available for freeleech.

	$ python pyhdbtools.py --fetch-featured

### Additional Options

    pyhdbtools.py [OPTIONS] [FILE]

	RUN MODES

	-f, --fetch-free
		Checks the most recent 30 uploads and downloads any that are freeleech

	-F, --fetch-featured
		Checks the list of upcoming featured torrents and downloads any that are freeleech. High number 
		of API calls. Not recommended to be run more than once every 5 minutes.

	-h, --help
		display this help and exits

	--makeconf
		Generates json.config and exits

	-q, --scrape-queue
		fetches featuredqueue.html from hdbits.org and updates watchlist. Requires valid cookie set. Will
		likely get you banned. Use --update-featured instead.

	-t, -torrentid ######
		Download .torrent file of the matching id

	-u, --update-featured filename.html
		Processes the "Featured Torrents Queue"	page from hdbits and adds them to a watchlist. Local
		files only. Does not accept URLs avoid breaking rule prohibiting site scraping.

	--version
		Shows version number

	MODIFIERS

	--allowdupes
		Bypasses checks to not download dupes

	--noverify
		Skips SSL verification for API queries

	-v
		Verbose output

### Automation

Sample crontab to check new torrents every minute and featured torrents every 5 minutes

	* * * * *       /usr/bin/python ~/pyhdbtools/pyhdbtools.py --fetch-free
	*/5 * * * *     /usr/bin/python ~/pyhdbtools/pyhdbtools.py --fetch-featured

###config.json

config.json is created in the following format:

	{
		"username":"barackobama",
		"passkey":"A1B2C3",
		"outputdir":"~/rtorrent/watchdir/"
	    "cookie": {
	        "hash": "1a2b3c4d1a2b3c4d1a2b3c4d1a2b3c4d",
	        "uid": "1234567",
	        "pass": "5e6f7a8b5e6f7a8b5e6f7a8b5e6f7a8b"
	    }
	}