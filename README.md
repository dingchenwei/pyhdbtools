# hdbits-fetchfree
A tool for automatically fetching new freeleech and featured torrents at hdbits

## Getting Started

### Prerequisites
Python 2.7
pip install lxml

Create a config.json with the following format in the same directory as hdbits-fetchfree.py

```
{
	"username":"barackobama",
	"passkey":"A1B2C3",
	"output_dir":"~/rtorrent/watchdir/"
}
```

### First Run
To run the program, type

```
$ python hdbits-fetchfree.py
```

### Additional Options

	hdbits-fetchfree.py [OPTIONS] [FILE]

	-f, --fetch-featured
		Checks the list of upcoming featured torrents and downloads any that are freeleech. High number 
		of API calls. Not recommended to be run more than once every 5 minutes.

	--makeconf
		Generates json.config

	-u, --update-featured filename.html
		Processes the "Featured Torrents Queue"	page from hdbits and adds them to a watchlist. Local
		files only. Does not accept URLs to not break rule prohibiting site scraping.

### Automation

Sample Crontab to check new torrents every minute and featured every 5

```
* * * * *       /usr/bin/python2.7 ~/hdbits-fetchfree/hdbits-fetchfree.py
*/5 * * * *     /usr/bin/python2.7 ~/hdbits-fetchfree/hdbits-fetchfree.py -f
```